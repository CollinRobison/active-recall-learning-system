"""Small evidence summary over persisted session records."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any
import re

from .frontmatter import parse
from .workspace import iter_records


def summarize(root: Path, *, topic_id: str | None = None) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    sessions = 0
    questions = 0
    dimensions: Counter[str] = Counter()
    calibration: Counter[str] = Counter()
    for path, metadata, body in iter_records(root, {"study-session"}):
        if topic_id and topic_id not in metadata.get("scope_ids", []):
            continue
        sessions += 1
        questions += int(metadata.get("question_count", 0))
        for status in ("correct", "partial", "incorrect", "unsupported"):
            counts[status] += body.count(f"**Evaluation:** {status}")
        dimensions.update(re.findall(r"\*\*Evidence dimension:\*\* (recall|explanation|application)", body))
        for confidence, evaluation in re.findall(r"\*\*Confidence before feedback:\*\* (\d+) / 5.*?\*\*Evaluation:\*\* (correct|partial|incorrect|unsupported)", body, re.S):
            value = int(confidence)
            if evaluation != "correct" and value >= 4:
                calibration["overconfident"] += 1
            elif evaluation == "correct" and value <= 2:
                calibration["underconfident"] += 1
            else:
                calibration["calibrated"] += 1
    confusion = sum(1 for _, metadata, _ in iter_records(root, {"confusion-item"}) if metadata.get("status") == "open" and (not topic_id or metadata.get("topic_id") == topic_id))
    return {"sessions": sessions, "questions": questions, "evaluations": dict(counts), "evidence_dimensions": dict(dimensions), "calibration": dict(calibration), "open_confusion": confusion, "limitations": "Evidence summary, not an objective mastery score."}
