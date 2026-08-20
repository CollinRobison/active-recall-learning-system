"""Markdown-first topic/path catalog records and transparent next-study recommendations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .frontmatter import render
from .workspace import append_catalog, atomic_write, iter_records, now_iso, slugify


def _records(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    return {str(metadata["id"]): (path, metadata) for path, metadata, _ in iter_records(root) if metadata.get("id")}


def _validate_ids(records: dict[str, tuple[Path, dict[str, Any]]], ids: list[str], kinds: set[str], field: str) -> None:
    unknown = [value for value in ids if value not in records]
    wrong = [value for value in ids if value in records and records[value][1].get("kind") not in kinds]
    if unknown or wrong:
        raise ValueError(f"invalid {field}: {unknown + wrong}")


def create_topic(root: Path, *, name: str, objectives: list[str] | None = None, source_ids: list[str] | None = None,
                 prerequisites: list[str] | None = None, related_topics: list[str] | None = None, path_ids: list[str] | None = None) -> Path:
    root = root.expanduser().resolve()
    records = _records(root)
    source_ids, prerequisites, related_topics, path_ids = source_ids or [], prerequisites or [], related_topics or [], path_ids or []
    _validate_ids(records, source_ids, {"source"}, "source_ids")
    _validate_ids(records, prerequisites + related_topics, {"topic"}, "topic relationships")
    _validate_ids(records, path_ids, {"path"}, "path_ids")
    slug = slugify(name); topic_id = f"topic-{slug}"; path = root / "topics" / slug / "topic.md"
    if topic_id in records or path.exists(): raise FileExistsError(f"topic already exists: {topic_id}")
    metadata = {"id": topic_id, "kind": "topic", "name": name, "slug": slug, "status": "active", "created_at": now_iso(), "updated_at": now_iso(),
                "tags": [], "prerequisites": prerequisites, "related_topics": related_topics, "source_ids": source_ids, "path_ids": path_ids}
    body = f"# {name}\n\n## Purpose\n\nDefine why this topic matters.\n\n## Learning objectives\n\n" + "\n".join(f"- {item}" for item in (objectives or ["Define learning objectives."])) + "\n\n## Notes\n\nHuman-authored notes only.\n"
    atomic_write(path, render(metadata, body)); append_catalog(root, "topics.md", "Topics", [f"- `{topic_id}` — {name}"])
    return path


def create_path(root: Path, *, name: str, topic_ids: list[str], source_ids: list[str] | None = None,
                prerequisites: list[str] | None = None, target_outcome: str = "") -> Path:
    root = root.expanduser().resolve(); records = _records(root)
    source_ids, prerequisites = source_ids or [], prerequisites or []
    _validate_ids(records, topic_ids, {"topic"}, "topic_ids"); _validate_ids(records, source_ids, {"source"}, "source_ids"); _validate_ids(records, prerequisites, {"path"}, "prerequisites")
    slug = slugify(name); path_id = f"path-{slug}"; path = root / "paths" / slug / "path.md"
    if path_id in records or path.exists(): raise FileExistsError(f"learning path already exists: {path_id}")
    metadata = {"id": path_id, "kind": "path", "name": name, "slug": slug, "status": "active", "created_at": now_iso(), "updated_at": now_iso(), "target_outcome": target_outcome, "prerequisites": prerequisites, "topic_ids": topic_ids, "source_ids": source_ids}
    curriculum = "\n".join(f"{number}. `{topic_id}`" for number, topic_id in enumerate(topic_ids, 1)) or "No topics assigned yet."
    body = f"# {name}\n\n## Purpose\n\n{target_outcome or 'Define the intended outcome.'}\n\n## Ordered curriculum\n\n{curriculum}\n\n## Progress notes\n\nGenerated evidence belongs in topic/session records.\n"
    atomic_write(path, render(metadata, body)); append_catalog(root, "paths.md", "Learning paths", [f"- `{path_id}` — {name}"])
    return path


def recommend(root: Path, *, limit: int = 5) -> list[dict[str, str]]:
    root = root.expanduser().resolve(); records = _records(root); options: list[tuple[int, str, dict[str, str]]] = []
    for _, metadata in records.values():
        if metadata.get("kind") == "confusion-item" and metadata.get("status") == "open":
            options.append((0, str(metadata.get("next_review_at", "")), {"kind": "confusion-review", "id": str(metadata["id"]), "reason": "Open confusion item; review its cited source location."}))
    for _, metadata in records.values():
        if metadata.get("kind") == "path" and metadata.get("status") == "active":
            for topic_id in metadata.get("topic_ids", []):
                topic = records.get(str(topic_id))
                if topic and topic[1].get("status") == "active":
                    options.append((1, str(metadata["id"]), {"kind": "path-topic", "id": str(topic_id), "path_id": str(metadata["id"]), "reason": "Next ordered topic in an active learning path."})); break
    for _, metadata in records.values():
        if metadata.get("kind") == "topic" and metadata.get("status") == "active":
            options.append((2, str(metadata["id"]), {"kind": "topic", "id": str(metadata["id"]), "reason": "Active topic with explicit learning objectives."}))
    seen: set[str] = set(); result = []
    for _, _, option in sorted(options):
        key = option["kind"] + option["id"]
        if key not in seen: seen.add(key); result.append(option)
        if len(result) >= limit: break
    return result
