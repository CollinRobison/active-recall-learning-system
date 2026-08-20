"""Rebuildable lexical retrieval manifest with an optional Milvus boundary."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .frontmatter import parse
from .workspace import atomic_write, iter_records, sha256_file, now_iso

MANIFEST = "index/manifest.jsonl"


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{2,}", text.lower())}


def _chunks(text: str, *, size: int = 1400) -> list[tuple[int, str]]:
    lines = text.splitlines()
    chunks: list[tuple[int, str]] = []
    current: list[str] = []
    start = 1
    length = 0
    for number, line in enumerate(lines, 1):
        if current and length + len(line) + 1 > size:
            chunks.append((start, "\n".join(current).strip()))
            current, length, start = [], 0, number
        current.append(line)
        length += len(line) + 1
    if current:
        chunks.append((start, "\n".join(current).strip()))
    return [(line, chunk) for line, chunk in chunks if chunk]


def rebuild_manifest(workspace: Path) -> dict[str, Any]:
    """Build the deterministic fallback manifest from source Markdown."""
    workspace = workspace.expanduser().resolve()
    entries: list[dict[str, Any]] = []
    for source_path, metadata, _ in iter_records(workspace, {"source"}):
        extracted = source_path.parent / "extracted.md"
        if not extracted.exists():
            continue
        text = extracted.read_text(encoding="utf-8")
        for order, (line, content) in enumerate(_chunks(text), 1):
            entry = {
                "record_id": f"chunk-{metadata['id']}-{order:04d}",
                "source_id": metadata["id"],
                "topic_ids": metadata.get("topic_ids", []),
                "path_ids": metadata.get("path_ids", []),
                "source_type": metadata.get("source_type"),
                "section": next((x.lstrip("# ") for x in content.splitlines() if x.startswith("#")), None),
                "line_start": line,
                "chunk_order": order,
                "content_hash": sha256_file(extracted),
                "authority": metadata.get("authority", "unverified"),
                "workspace_file": str(extracted.relative_to(workspace)),
                "content": content,
            }
            entries.append(entry)
    manifest = workspace / MANIFEST
    atomic_write(manifest, "".join(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n" for entry in entries))
    return {"status": "current", "manifest": str(manifest), "records": len(entries), "updated_at": now_iso()}


def read_manifest(workspace: Path) -> list[dict[str, Any]]:
    path = workspace / MANIFEST
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def query_manifest(workspace: Path, text: str, *, source_id: str | None = None, topic_id: str | None = None, path_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """Perform transparent lexical retrieval when no vector backend is configured."""
    wanted = _tokens(text)
    scored = []
    for entry in read_manifest(workspace):
        if source_id and entry.get("source_id") != source_id:
            continue
        if topic_id and topic_id not in entry.get("topic_ids", []):
            continue
        if path_id and path_id not in entry.get("path_ids", []):
            continue
        overlap = len(wanted & _tokens(entry.get("content", "")))
        if overlap:
            scored.append((overlap, entry))
    scored.sort(key=lambda item: (-item[0], item[1]["record_id"]))
    return [{**entry, "score": score} for score, entry in scored[:limit]]
