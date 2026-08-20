"""Small evidence summary over persisted session records."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .frontmatter import parse
from .workspace import iter_records


def summarize(root: Path, *, topic_id: str | None = None) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    sessions = 0
    questions = 0
    for path, metadata, body in iter_records(root, {"study-session"}):
        if topic_id and topic_id not in metadata.get("scope_ids", []):
            continue
        sessions += 1
        questions += int(metadata.get("question_count", 0))
        for status in ("correct", "partial", "incorrect", "unsupported"):
            counts[status] += body.count(f"**Evaluation:** {status}")
    confusion = sum(1 for _, metadata, _ in iter_records(root, {"confusion-item"}) if metadata.get("status") == "open" and (not topic_id or metadata.get("topic_id") == topic_id))
    return {"sessions": sessions, "questions": questions, "evaluations": dict(counts), "open_confusion": confusion, "limitations": "Evidence summary, not an objective mastery score."}
