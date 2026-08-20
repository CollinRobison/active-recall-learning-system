"""Markdown-backed review queue and append-only evidence history."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .frontmatter import parse, render
from .workspace import atomic_write, now_iso


def calibration_for(classification: str, confidence: int | None) -> str:
    """Classify confidence only as evidence; this is not a mastery judgment."""
    if confidence is None:
        return "unrecorded"
    if classification != "correct" and confidence >= 4:
        return "overconfident"
    if classification == "correct" and confidence <= 2:
        return "underconfident"
    return "calibrated"


def record_review(root: Path, *, topic_id: str, session_id: str, classification: str, confidence: int | None, next_review_at: str, citation: str, evidence_dimension: str = "recall", delayed: bool = False) -> dict[str, Any]:
    root = root.expanduser().resolve(); due = root / "reviews" / "due.md"; history = root / "reviews" / "history.md"
    key = topic_id
    calibration = calibration_for(classification, confidence)
    entry = {"topic_id": topic_id, "session_id": session_id, "classification": classification, "confidence": confidence, "calibration": calibration, "evidence_dimension": evidence_dimension, "delayed": delayed, "next_review_at": next_review_at, "citation": citation, "updated_at": now_iso()}
    existing = due.read_text(encoding="utf-8") if due.exists() else "# Due reviews\n"
    lines = [line for line in existing.splitlines() if key not in line]
    lines.append(f"- `{key}` — due {next_review_at}; result={classification}; evidence={evidence_dimension}; delayed={str(delayed).lower()}; calibration={calibration}; confidence={confidence if confidence is not None else 'unrecorded'}; citation={citation or 'unavailable'}")
    atomic_write(due, "\n".join(lines).rstrip() + "\n")
    old = history.read_text(encoding="utf-8") if history.exists() else "# Review history\n"
    atomic_write(history, old.rstrip() + f"\n\n## {entry['updated_at']}\n\n- Topic: `{topic_id}`\n- Session: `{session_id}`\n- Result: {classification}\n- Evidence dimension: {evidence_dimension}\n- Delayed review: {str(delayed).lower()}\n- Calibration: {calibration}\n- Confidence: {confidence if confidence is not None else 'unrecorded'}\n- Next review: {next_review_at}\n- Citation: {citation or 'unavailable'}\n")
    return entry
