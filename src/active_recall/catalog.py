"""Markdown-first catalog records, confirmed edits, and prerequisite-aware recommendations."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .frontmatter import render
from .progress import summarize
from .workspace import append_catalog, atomic_write, iter_records, now_iso, slugify


def _records(root: Path) -> dict[str, tuple[Path, dict[str, Any], str]]:
    return {str(metadata["id"]): (path, metadata, body) for path, metadata, body in iter_records(root) if metadata.get("id")}


def _validate_ids(records: dict[str, tuple[Path, dict[str, Any], str]], ids: list[str], kinds: set[str], field: str) -> None:
    unknown = [value for value in ids if value not in records]
    wrong = [value for value in ids if value in records and records[value][1].get("kind") not in kinds]
    if unknown or wrong:
        raise ValueError(f"invalid {field}: {unknown + wrong}")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _check_topic_cycles(records: dict[str, tuple[Path, dict[str, Any], str]], topic_id: str, prerequisites: list[str]) -> None:
    """Reject direct and indirect prerequisite cycles before any Markdown is changed."""
    graph = {record_id: list(metadata.get("prerequisites", [])) for record_id, (_, metadata, _) in records.items() if metadata.get("kind") == "topic"}
    graph[topic_id] = prerequisites
    stack = list(prerequisites)
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current == topic_id:
            raise ValueError(f"topic prerequisite cycle includes {topic_id}")
        if current not in seen:
            seen.add(current)
            stack.extend(graph.get(current, []))


def _sync_source_associations(root: Path, records: dict[str, tuple[Path, dict[str, Any], str]], *, owner_id: str, owner_kind: str, old_source_ids: list[str], source_ids: list[str]) -> None:
    """Keep source topic/path metadata readable and reciprocal with explicit catalog records."""
    field = "topic_ids" if owner_kind == "topic" else "path_ids"
    for source_id in set(old_source_ids) | set(source_ids):
        source_path, source_metadata, source_body = records[source_id]
        associated = [str(value) for value in source_metadata.get(field, [])]
        if source_id in source_ids and owner_id not in associated:
            associated.append(owner_id)
        if source_id not in source_ids:
            associated = [value for value in associated if value != owner_id]
        source_metadata[field] = associated
        source_metadata["updated_at"] = now_iso()
        atomic_write(source_path, render(source_metadata, source_body))


def create_topic(root: Path, *, name: str, objectives: list[str] | None = None, source_ids: list[str] | None = None,
                 prerequisites: list[str] | None = None, related_topics: list[str] | None = None, path_ids: list[str] | None = None) -> Path:
    root = root.expanduser().resolve()
    records = _records(root)
    source_ids, prerequisites, related_topics, path_ids = (_dedupe(source_ids or []), _dedupe(prerequisites or []), _dedupe(related_topics or []), _dedupe(path_ids or []))
    _validate_ids(records, source_ids, {"source"}, "source_ids")
    _validate_ids(records, prerequisites + related_topics, {"topic"}, "topic relationships")
    _validate_ids(records, path_ids, {"path"}, "path_ids")
    slug = slugify(name); topic_id = f"topic-{slug}"; path = root / "topics" / slug / "topic.md"
    if topic_id in records or path.exists():
        raise FileExistsError(f"topic already exists: {topic_id}")
    _check_topic_cycles(records, topic_id, prerequisites)
    metadata = {"id": topic_id, "kind": "topic", "name": name, "slug": slug, "status": "active", "created_at": now_iso(), "updated_at": now_iso(),
                "tags": [], "prerequisites": prerequisites, "related_topics": related_topics, "source_ids": source_ids, "path_ids": path_ids}
    body = f"# {name}\n\n## Purpose\n\nDefine why this topic matters.\n\n## Learning objectives\n\n" + "\n".join(f"- {item}" for item in (objectives or ["Define learning objectives."])) + "\n\n## Notes\n\nHuman-authored notes only.\n"
    atomic_write(path, render(metadata, body)); append_catalog(root, "topics.md", "Topics", [f"- `{topic_id}` — {name}"])
    _sync_source_associations(root, records, owner_id=topic_id, owner_kind="topic", old_source_ids=[], source_ids=source_ids)
    return path


def create_path(root: Path, *, name: str, topic_ids: list[str], source_ids: list[str] | None = None,
                prerequisites: list[str] | None = None, target_outcome: str = "") -> Path:
    root = root.expanduser().resolve(); records = _records(root)
    source_ids, prerequisites, topic_ids = _dedupe(source_ids or []), _dedupe(prerequisites or []), _dedupe(topic_ids)
    _validate_ids(records, topic_ids, {"topic"}, "topic_ids"); _validate_ids(records, source_ids, {"source"}, "source_ids"); _validate_ids(records, prerequisites, {"path"}, "prerequisites")
    slug = slugify(name); path_id = f"path-{slug}"; path = root / "paths" / slug / "path.md"
    if path_id in records or path.exists(): raise FileExistsError(f"learning path already exists: {path_id}")
    metadata = {"id": path_id, "kind": "path", "name": name, "slug": slug, "status": "active", "created_at": now_iso(), "updated_at": now_iso(), "target_outcome": target_outcome, "prerequisites": prerequisites, "topic_ids": topic_ids, "source_ids": source_ids}
    curriculum = "\n".join(f"{number}. `{topic_id}`" for number, topic_id in enumerate(topic_ids, 1)) or "No topics assigned yet."
    body = f"# {name}\n\n## Purpose\n\n{target_outcome or 'Define the intended outcome.'}\n\n## Ordered curriculum\n\n{curriculum}\n\n## Progress notes\n\nGenerated evidence belongs in topic/session records.\n"
    atomic_write(path, render(metadata, body)); append_catalog(root, "paths.md", "Learning paths", [f"- `{path_id}` — {name}"])
    _sync_source_associations(root, records, owner_id=path_id, owner_kind="path", old_source_ids=[], source_ids=source_ids)
    return path


def update_topic(root: Path, topic_id: str, *, source_ids: list[str] | None = None, prerequisites: list[str] | None = None,
                 related_topics: list[str] | None = None, path_ids: list[str] | None = None, status: str | None = None,
                 confirm: bool = False) -> dict[str, Any]:
    """Preview or apply a canonical topic edit; callers must explicitly confirm writes."""
    root = root.expanduser().resolve(); records = _records(root)
    if topic_id not in records or records[topic_id][1].get("kind") != "topic":
        raise ValueError(f"unknown topic: {topic_id}")
    path, current, body = records[topic_id]
    proposed = dict(current)
    updates = {"source_ids": source_ids, "prerequisites": prerequisites, "related_topics": related_topics, "path_ids": path_ids, "status": status}
    for field, value in updates.items():
        if value is not None:
            proposed[field] = _dedupe(value) if isinstance(value, list) else value
    if proposed.get("status") not in {"active", "completed", "archived"}:
        raise ValueError("topic status must be active, completed, or archived")
    _validate_ids(records, list(proposed.get("source_ids", [])), {"source"}, "source_ids")
    _validate_ids(records, list(proposed.get("prerequisites", [])) + list(proposed.get("related_topics", [])), {"topic"}, "topic relationships")
    _validate_ids(records, list(proposed.get("path_ids", [])), {"path"}, "path_ids")
    _check_topic_cycles(records, topic_id, list(proposed.get("prerequisites", [])))
    changes = {field: {"from": current.get(field), "to": proposed.get(field)} for field in updates if current.get(field) != proposed.get(field)}
    preview = {"status": "applied" if confirm else "confirmation-required", "record": topic_id, "changes": changes,
               "confirmation": "Re-run with confirm=True (or CLI --confirm) to modify canonical Markdown."}
    if not confirm or not changes:
        return preview
    proposed["updated_at"] = now_iso()
    atomic_write(path, render(proposed, body))
    _sync_source_associations(root, records, owner_id=topic_id, owner_kind="topic", old_source_ids=list(current.get("source_ids", [])), source_ids=list(proposed.get("source_ids", [])))
    return preview


def _topic_ready(root: Path, metadata: dict[str, Any]) -> tuple[bool, str]:
    if metadata.get("status") == "completed":
        return True, "marked completed"
    evidence = summarize(root, topic_id=str(metadata["id"]))
    # This deliberately remains conservative: a completed prerequisite is the normal gate;
    # repeated correct evidence with no unresolved confusion is an explicit alternative.
    if evidence["evaluations"].get("correct", 0) >= 2 and evidence["open_confusion"] == 0:
        return True, "two correct persisted evaluations and no open confusion"
    return False, "not completed and lacks two correct persisted evaluations without open confusion"


def recommend(root: Path, *, limit: int = 5) -> list[dict[str, str]]:
    root = root.expanduser().resolve(); records = _records(root); options: list[tuple[int, str, dict[str, str]]] = []
    for _, metadata, _ in records.values():
        if metadata.get("kind") == "confusion-item" and metadata.get("status") == "open":
            options.append((0, str(metadata.get("next_review_at", "")), {"kind": "confusion-review", "id": str(metadata["id"]), "reason": "Open confusion item; review its cited source location."}))
    for _, metadata, _ in records.values():
        if metadata.get("kind") == "path" and metadata.get("status") == "active":
            for topic_id in metadata.get("topic_ids", []):
                topic = records.get(str(topic_id))
                if not topic or topic[1].get("status") != "active":
                    continue
                blocked = [prerequisite for prerequisite in topic[1].get("prerequisites", []) if prerequisite in records and not _topic_ready(root, records[prerequisite][1])[0]]
                if blocked:
                    continue
                options.append((1, str(metadata["id"]), {"kind": "path-topic", "id": str(topic_id), "path_id": str(metadata["id"]), "reason": "First unblocked ordered topic in an active learning path."})); break
    for _, metadata, _ in records.values():
        if metadata.get("kind") == "topic" and metadata.get("status") == "active":
            blocked = [prerequisite for prerequisite in metadata.get("prerequisites", []) if prerequisite in records and not _topic_ready(root, records[prerequisite][1])[0]]
            if not blocked:
                options.append((2, str(metadata["id"]), {"kind": "topic", "id": str(metadata["id"]), "reason": "Active topic with explicit learning objectives and satisfied prerequisites."}))
    seen: set[str] = set(); result = []
    for _, _, option in sorted(options):
        key = option["kind"] + option["id"]
        if key not in seen: seen.add(key); result.append(option)
        if len(result) >= limit: break
    return result
