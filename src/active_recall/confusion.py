"""Stable concept-based confusion records."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .frontmatter import parse, render
from .workspace import atomic_write, now_iso, slugify


def _find_open(root: Path, topic_id: str, concept: str) -> tuple[Path, dict[str, Any], str] | None:
    for path in (root / "confusion" / "open").glob("*.md"):
        try:
            metadata, body = parse(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if metadata.get("topic_id") == topic_id and metadata.get("concept") == concept:
            return path, metadata, body
    return None


def record_confusion(
    root: Path,
    *,
    topic_id: str,
    concept: str,
    question: str,
    answer: str,
    missing: str,
    source_location: str,
    source_ids: list[str] | None = None,
    session_id: str | None = None,
    severity: str = "moderate",
) -> Path:
    """Create or merge a confusion item by stable topic/concept identity."""
    root = root.expanduser().resolve()
    concept_id = slugify(concept)
    existing = _find_open(root, topic_id, concept_id)
    if existing:
        path, metadata, body = existing
        sessions = metadata.get("origin_sessions", [])
        if session_id and session_id not in sessions:
            sessions.append(session_id)
        metadata["origin_sessions"] = sessions
        metadata["review_count"] = int(metadata.get("review_count", 0)) + 1
        metadata["updated_at"] = now_iso()
        body += f"\n\n## Additional evidence ({now_iso()})\n\n**Question:** {question}\n\n**Answer:** {answer}\n\n**Missing or incorrect:** {missing}\n"
        atomic_write(path, render(metadata, body))
        return path
    current = datetime.now(timezone.utc)
    confusion_id = f"confusion-{current.strftime('%Y%m%d%H%M%S')}-{concept_id}"
    metadata = {
        "id": confusion_id,
        "kind": "confusion-item",
        "status": "open",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "topic_id": topic_id,
        "concept": concept_id,
        "severity": severity,
        "source_ids": source_ids or [],
        "origin_sessions": [session_id] if session_id else [],
        "prerequisites": [],
        "review_count": 0,
        "next_review_at": now_iso(),
    }
    body = (
        f"# Confusion: {concept}\n\n## What I was asked\n\n{question}\n\n"
        f"## What I said\n\n{answer}\n\n## What was missing or incorrect\n\n{missing}\n\n"
        f"## Where to review\n\n- {source_location}\n\n## Recommended remediation\n\n"
        "1. Reread the exact location.\n2. Explain the distinction in one sentence.\n"
        "3. Apply it to a new example.\n4. Reattempt a delayed retrieval question.\n\n"
        "## Resolution evidence\n"
    )
    path = root / "confusion" / "open" / f"{confusion_id}.md"
    atomic_write(path, render(metadata, body))
    return path
