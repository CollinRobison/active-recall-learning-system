"""Optional Milvus Lite vector index with explicit degraded-mode reporting."""

from __future__ import annotations

import json
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
    except ImportError:
        return False
    return True


class MilvusLiteIndex:
    def __init__(self, workspace: Path, *, collection: str = COLLECTION) -> None:
        try:
            from pymilvus import MilvusClient
        except ImportError as exc:
            raise RuntimeError("Milvus Lite requires optional dependency 'pymilvus'") from exc
        self.workspace = workspace.expanduser().resolve()
        self.collection = collection
        self.database = self.workspace / "index" / "milvus" / "workspace.db"
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.client = MilvusClient(uri=str(self.database))

    def _ensure_collection(self, dimension: int) -> None:
        if not self.client.has_collection(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                dimension=dimension,
                primary_field_name="record_id",
                id_type="VARCHAR",
                vector_field_name="embedding",
                metric_type="COSINE",
                auto_id=False,
            )

    def rebuild(self, provider: EmbeddingProvider) -> dict[str, Any]:
        manifest_result = rebuild_manifest(self.workspace)
        entries = read_manifest(self.workspace)
        if self.client.has_collection(self.collection):
            self.client.drop_collection(self.collection)
        self._ensure_collection(provider.dimension)
        if entries:
            vectors = provider.embed([entry["content"] for entry in entries])
            rows = []
            for entry, vector in zip(entries, vectors):
                rows.append({
                    "record_id": entry["record_id"],
                    "embedding": vector,
                    "source_id": entry["source_id"],
                    "topic_ids": json.dumps(entry.get("topic_ids", [])),
                    "path_ids": json.dumps(entry.get("path_ids", [])),
                    "section": entry.get("section") or "",
                    "line_start": entry.get("line_start", 0),
                    "content_hash": entry["content_hash"],
                    "workspace_file": entry["workspace_file"],
                    "content": entry["content"],
                })
            self.client.insert(collection_name=self.collection, data=rows)
        status = {
            "status": "current",
            "backend": "milvus-lite",
            "collection": self.collection,
            "database": str(self.database.relative_to(self.workspace)),
            "records": len(entries),
            "updated_at": now_iso(),
            **embedding_metadata(provider),
        }
        atomic_write(self.workspace / STATUS_FILE, json.dumps(status, indent=2) + "\n")
        return {**manifest_result, **status}

    def query(self, provider: EmbeddingProvider, text: str, *, limit: int = 5, source_id: str | None = None) -> list[dict[str, Any]]:
        if not self.client.has_collection(self.collection):
            return []
        filter_expression = f'source_id == "{source_id}"' if source_id else ""
        result = self.client.search(
            collection_name=self.collection,
            data=provider.embed([text]),
            limit=limit,
            filter=filter_expression,
            output_fields=["source_id", "section", "line_start", "content_hash", "workspace_file", "content"],
        )
        matches: list[dict[str, Any]] = []
        for hit in result[0] if result else []:
            entity = hit.get("entity", {})
            matches.append({"record_id": hit.get("id"), "score": hit.get("distance"), **entity})
        return matches


def vector_status(workspace: Path) -> dict[str, Any]:
    path = workspace.expanduser().resolve() / STATUS_FILE
    if not milvus_available():
        return {"status": "unavailable", "backend": "milvus-lite", "reason": "pymilvus is not installed"}
    if not path.exists():
        return {"status": "not-built", "backend": "milvus-lite"}
    return json.loads(path.read_text(encoding="utf-8"))
