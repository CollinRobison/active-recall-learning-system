"""Confirmed, relationship-aware removal of canonical learning records."""
from __future__ import annotations

import shutil
import re
from pathlib import Path
from typing import Any

from .frontmatter import render
from .index import rebuild_manifest
from .workspace import atomic_write, iter_records, now_iso

_REMOVABLE_KINDS = {"source", "topic", "path"}


def _records(root: Path) -> dict[str, tuple[Path, dict[str, Any], str]]:
    return {str(metadata["id"]): (path, metadata, body) for path, metadata, body in iter_records(root) if metadata.get("id")}


def _plan(root: Path, record_id: str) -> tuple[dict[str, set[str]], dict[str, tuple[Path, dict[str, Any], str]]]:
    records = _records(root)
    if record_id not in records or records[record_id][1].get("kind") not in _REMOVABLE_KINDS:
        raise ValueError("remove expects an existing source, topic, or path ID")
    kind = str(records[record_id][1]["kind"])
    removed = {"source": set(), "topic": set(), "path": set()}
    removed[kind].add(record_id)
    changed = True
    while changed:
        changed = False
        # A source that was the only source of a topic removes that topic and its downstream artifacts.
        for candidate_id, (_, metadata, _) in records.items():
            if metadata.get("kind") != "topic" or candidate_id in removed["topic"]:
                continue
            sources = set(map(str, metadata.get("source_ids", [])))
            if sources & removed["source"] and not (sources - removed["source"]):
                removed["topic"].add(candidate_id); changed = True
        # Keep paths when they still contain a topic or another directly-associated source.
        for candidate_id, (_, metadata, _) in records.items():
            if metadata.get("kind") != "path" or candidate_id in removed["path"]:
                continue
            if candidate_id == record_id and kind == "path":
                continue
            topics = set(map(str, metadata.get("topic_ids", []))) - removed["topic"]
            sources = set(map(str, metadata.get("source_ids", []))) - removed["source"]
            if not topics and not sources:
                removed["path"].add(candidate_id); changed = True
    return removed, records


def _remove_catalog_entries(root: Path, ids: set[str]) -> None:
    for name in ("topics.md", "paths.md", "sources.md"):
        path = root / "catalog" / name
        if not path.exists():
            continue
        before = path.read_text(encoding="utf-8")
        after = "\n".join(line for line in before.splitlines() if not any(f"`{record_id}`" in line for record_id in ids)).rstrip() + "\n"
        if after != before:
            atomic_write(path, after)


def _purge_review_artifacts(root: Path, ids: set[str]) -> None:
    due = root / "reviews" / "due.md"
    if due.exists():
        before = due.read_text(encoding="utf-8")
        after = "\n".join(line for line in before.splitlines() if not any(record_id in line for record_id in ids)).rstrip() + "\n"
        if after != before:
            atomic_write(due, after)
    history = root / "reviews" / "history.md"
    if history.exists():
        before = history.read_text(encoding="utf-8")
        parts = before.split("\n## ")
        after = parts[0] + "".join("\n## " + part for part in parts[1:] if not any(record_id in part for record_id in ids))
        if after != before:
            atomic_write(history, after.rstrip() + "\n")


def _revised_body(kind: str, metadata: dict[str, Any], body: str) -> str:
    """Keep generated relationship summaries consistent with pruned metadata."""
    if kind == "path":
        topics = [str(value) for value in metadata.get("topic_ids", [])]
        curriculum = "\n".join(f"{number}. `{topic_id}`" for number, topic_id in enumerate(topics, 1)) or "No topics assigned yet."
        return re.sub(r"(## Ordered curriculum\n\n).*?(?=\n## |\Z)", lambda match: match.group(1) + curriculum + "\n", body, flags=re.DOTALL)
    if kind == "study-session":
        scope = f"- Scope: {metadata.get('scope_type', 'topic')} ({', '.join(map(str, metadata.get('scope_ids', [])))})"
        return re.sub(r"^- Scope:.*$", scope, body, count=1, flags=re.MULTILINE)
    return body


def remove_record(root: Path, record_id: str, *, confirm: bool = False) -> dict[str, Any]:
    """Preview or permanently remove a source/topic/path and only its orphaned dependents."""
    root = root.expanduser().resolve()
    removed, records = _plan(root, record_id)
    delete_ids = set().union(*removed.values())
    updates: list[str] = []
    deleted_sessions: set[str] = set()
    deleted_confusion: set[str] = set()
    # Sessions that scope only to removed records are deleted; mixed scopes are retained and pruned.
    for candidate_id, (path, metadata, body) in records.items():
        if metadata.get("kind") != "study-session":
            continue
        old_scope = list(map(str, metadata.get("scope_ids", [])))
        new_scope = [item for item in old_scope if item not in delete_ids]
        if old_scope == new_scope:
            continue
        if not new_scope:
            delete_ids.add(candidate_id); deleted_sessions.add(candidate_id)
        else:
            updates.append(candidate_id)
    for candidate_id, (path, metadata, body) in records.items():
        if metadata.get("kind") == "confusion-item" and str(metadata.get("topic_id", "")) in removed["topic"]:
            delete_ids.add(candidate_id); deleted_confusion.add(candidate_id)
    # Include every retained record whose canonical references or generated relationship text will change.
    for candidate_id, (_, metadata, body) in records.items():
        if candidate_id in delete_ids:
            continue
        revised = dict(metadata)
        for field, deleted in (("source_ids", removed["source"]), ("topic_ids", removed["topic"]), ("path_ids", removed["path"]),
                               ("prerequisites", removed["topic"] | removed["path"]), ("related_topics", removed["topic"]), ("scope_ids", set(delete_ids))):
            if field in revised:
                revised[field] = [value for value in revised[field] if str(value) not in deleted]
        if revised != metadata or _revised_body(str(metadata.get("kind")), revised, body) != body:
            updates.append(candidate_id)
    preview = {
        "status": "applied" if confirm else "confirmation-required",
        "requested": record_id,
        "delete": {kind: sorted(ids) for kind, ids in removed.items()},
        "delete_session_ids": sorted(deleted_sessions),
        "delete_confusion_ids": sorted(deleted_confusion),
        "update_record_ids": sorted(set(updates)),
        "confirmation": "Re-run with confirm=True (or CLI --confirm) to permanently remove these records and their orphaned artifacts.",
    }
    if not confirm:
        return preview

    for candidate_id, (path, metadata, body) in records.items():
        if candidate_id in delete_ids:
            continue
        kind = metadata.get("kind")
        revised = dict(metadata)
        for field, deleted in (("source_ids", removed["source"]), ("topic_ids", removed["topic"]), ("path_ids", removed["path"]),
                               ("prerequisites", removed["topic"] | removed["path"]), ("related_topics", removed["topic"]), ("scope_ids", set(delete_ids))):
            if field in revised:
                revised[field] = [value for value in revised[field] if str(value) not in deleted]
        revised_body = _revised_body(str(kind), revised, body)
        if revised != metadata or revised_body != body:
            revised["updated_at"] = now_iso()
            atomic_write(path, render(revised, revised_body))

    _remove_catalog_entries(root, set().union(*removed.values()))
    _purge_review_artifacts(root, set().union(*removed.values(), deleted_sessions))
    for candidate_id in delete_ids:
        path, _, _ = records[candidate_id]
        # Only remove the owned record directory for source/topic/path; other artifacts are individual files.
        if path.name in {"source.md", "topic.md", "path.md"}:
            shutil.rmtree(path.parent)
        elif path.exists():
            path.unlink()
    # Purge/rebuild derived retrieval artifacts so deleted material cannot be returned later.
    rebuild_manifest(root)
    shutil.rmtree(root / "index" / "milvus", ignore_errors=True)
    (root / "index" / "vector-status.json").unlink(missing_ok=True)
    return preview
