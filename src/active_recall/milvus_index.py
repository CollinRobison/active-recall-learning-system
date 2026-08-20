"""Optional Milvus Lite indexing with generation-safe rebuilds and incremental updates."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .embeddings import EmbeddingProvider, embedding_metadata
from .index import read_manifest, rebuild_manifest
from .workspace import atomic_write, now_iso

COLLECTION = "source_chunks"
STATUS_FILE = "index/vector-status.json"


def milvus_available() -> bool:
    try:
        import pymilvus  # noqa: F401
    except ImportError: return False
    return True


def _safe_filter_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class MilvusLiteIndex:
    """A vector cache: status is published only after a complete new generation exists."""
    def __init__(self, workspace: Path, *, collection: str = COLLECTION, client: Any | None = None) -> None:
        if client is None:
            try:
                from pymilvus import MilvusClient
            except ImportError as exc: raise RuntimeError("Milvus Lite requires optional dependency 'pymilvus'") from exc
        self.workspace = workspace.expanduser().resolve(); self.collection = collection
        self.database = self.workspace / "index" / "milvus" / "workspace.db"; self.database.parent.mkdir(parents=True, exist_ok=True)
        self.client = client if client is not None else MilvusClient(uri=str(self.database))

    def _ensure_collection(self, name: str, dimension: int) -> None:
        if not self.client.has_collection(name):
            self.client.create_collection(collection_name=name, dimension=dimension, primary_field_name="record_id", id_type="str", vector_field_name="embedding", metric_type="COSINE", auto_id=False)

    def _rows(self, entries: list[dict[str, Any]], provider: EmbeddingProvider) -> list[dict[str, Any]]:
        vectors = provider.embed([entry["content"] for entry in entries])
        if len(vectors) != len(entries): raise ValueError("embedding provider returned an unexpected vector count")
        return [{"record_id": entry["record_id"], "embedding": vector, "source_id": entry["source_id"], "topic_ids": json.dumps(entry.get("topic_ids", [])), "path_ids": json.dumps(entry.get("path_ids", [])), "section": entry.get("section") or "", "line_start": entry.get("line_start", 0), "content_hash": entry["content_hash"], "workspace_file": entry["workspace_file"], "content": entry["content"]} for entry, vector in zip(entries, vectors)]

    def _status(self) -> dict[str, Any]:
        path = self.workspace / STATUS_FILE
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def _write_status(self, status: dict[str, Any]) -> None:
        atomic_write(self.workspace / STATUS_FILE, json.dumps(status, indent=2, sort_keys=True) + "\n")

    def rebuild(self, provider: EmbeddingProvider) -> dict[str, Any]:
        """Build a fresh collection generation, then atomically publish it in status."""
        manifest_result = rebuild_manifest(self.workspace); entries = read_manifest(self.workspace); prior = self._status(); backup = None
        if self.database.exists():
            backup_dir = self.database.parent / "backups"; backup_dir.mkdir(parents=True, exist_ok=True); backup = backup_dir / f"workspace-{now_iso().replace(':', '-')}"
            if self.database.is_dir():
                shutil.copytree(self.database, backup)
            else:
                shutil.copy2(self.database, backup)
        generation = int(prior.get("generation") or 0) + 1; name = f"{self.collection}_g{generation}"
        try:
            self._ensure_collection(name, provider.dimension)
            if entries: self.client.insert(collection_name=name, data=self._rows(entries, provider))
        except Exception as exc:
            self._write_status({"status": "failed", "backend": "milvus-lite", "generation": prior.get("generation"), "records": len(entries), "updated_at": now_iso(), "recovery_backup": str(backup.relative_to(self.workspace)) if backup else None, "error": str(exc)})
            raise
        status = {"status": "current", "backend": "milvus-lite", "collection": name, "generation": generation, "database": str(self.database.relative_to(self.workspace)), "records": len(entries), "record_hashes": {x["record_id"]: x["content_hash"] for x in entries}, "updated_at": now_iso(), "recovery_backup": str(backup.relative_to(self.workspace)) if backup else None, **embedding_metadata(provider)}
        self._write_status(status)
        return {**manifest_result, **status}

    def incremental(self, provider: EmbeddingProvider) -> dict[str, Any]:
        """Upsert changed chunks and remove stale IDs from the published generation."""
        rebuild_manifest(self.workspace); entries = read_manifest(self.workspace); prior = self._status(); name = prior.get("collection")
        if prior.get("status") != "current" or not name or not self.client.has_collection(name): return self.rebuild(provider)
        old = prior.get("record_hashes", {}); current = {x["record_id"]: x["content_hash"] for x in entries}; changed = [x for x in entries if old.get(x["record_id"]) != x["content_hash"]]; stale = sorted(set(old) - set(current))
        try:
            if changed:
                rows = self._rows(changed, provider)
                if hasattr(self.client, "upsert"): self.client.upsert(collection_name=name, data=rows)
                else:
                    if hasattr(self.client, "delete"): self.client.delete(collection_name=name, ids=[row["record_id"] for row in rows])
                    self.client.insert(collection_name=name, data=rows)
            if stale and hasattr(self.client, "delete"): self.client.delete(collection_name=name, ids=stale)
        except Exception as exc:
            self._write_status({**prior, "status": "failed", "error": str(exc), "updated_at": now_iso()}); raise
        status = {**prior, "status": "current", "records": len(entries), "record_hashes": current, "updated_at": now_iso(), "incremental": {"upserted": len(changed), "removed": len(stale)}}; self._write_status(status); return status

    def query(self, provider: EmbeddingProvider, text: str, *, limit: int = 5, source_id: str | None = None, topic_id: str | None = None, path_id: str | None = None) -> list[dict[str, Any]]:
        name = self._status().get("collection", self.collection)
        if not self.client.has_collection(name): return []
        if hasattr(self.client, "load_collection"):
            self.client.load_collection(collection_name=name)
        expression = f'source_id == "{_safe_filter_value(source_id)}"' if source_id else ""
        result = self.client.search(collection_name=name, data=provider.embed([text]), limit=max(limit * 4, limit), filter=expression, output_fields=["source_id", "topic_ids", "path_ids", "section", "line_start", "content_hash", "workspace_file", "content"])
        matches = []
        for hit in result[0] if result else []:
            entity = hit.get("entity", {})
            for field in ("topic_ids", "path_ids"):
                if isinstance(entity.get(field), str):
                    try: entity[field] = json.loads(entity[field])
                    except json.JSONDecodeError: entity[field] = []
            if topic_id and topic_id not in entity.get("topic_ids", []): continue
            if path_id and path_id not in entity.get("path_ids", []): continue
            matches.append({"record_id": hit.get("id"), "score": hit.get("distance"), **entity})
        return matches[:limit]


def vector_status(workspace: Path) -> dict[str, Any]:
    path = workspace.expanduser().resolve() / STATUS_FILE
    if not milvus_available(): return {"status": "unavailable", "backend": "milvus-lite", "reason": "pymilvus is not installed"}
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "not-built", "backend": "milvus-lite"}
