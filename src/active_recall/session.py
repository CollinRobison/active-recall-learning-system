"""Incrementally persisted study-session records."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .frontmatter import parse, render
from .workspace import atomic_write, now_iso, slugify

VALID_STATUSES = {"in-progress", "paused", "completed", "stopped"}


def _session_path(root: Path, session_id: str, when: datetime) -> Path:
    return root / "sessions" / when.strftime("%Y") / when.strftime("%m") / f"{session_id}.md"


def start_session(
    root: Path,
    *,
    scope_type: str,
    scope_ids: list[str],
    mode: str = "active-recall",
    objective: str = "Remember and apply the material",
    difficulty: str = "adaptive",
    session_id: str | None = None,
    when: datetime | None = None,
) -> Path:
    current = when or datetime.now(timezone.utc)
    session_id = session_id or f"session-{current.strftime('%Y%m%d-%H%M%S')}"
    path = _session_path(root, session_id, current)
    if path.exists():
        raise FileExistsError(f"session already exists: {path}")
    metadata: dict[str, Any] = {
        "id": session_id,
        "kind": "study-session",
        "started_at": current.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "updated_at": now_iso(),
        "ended_at": None,
        "status": "in-progress",
        "scope_type": scope_type,
        "scope_ids": scope_ids,
        "mode": mode,
        "objective": objective,
        "difficulty": difficulty,
        "question_count": 0,
    }
    body = (
        f"# Study Session\n\n## Session setup\n\n"
        f"- Scope: {scope_type} ({', '.join(scope_ids)})\n"
        f"- Mode: {mode}\n- Objective: {objective}\n- Difficulty: {difficulty}\n\n"
        "## Summary\n\nSession in progress.\n\n## Turns\n"
    )
    atomic_write(path, render(metadata, body))
    return path


def load_session(path: Path) -> tuple[dict[str, Any], str]:
    metadata, body = parse(path.read_text(encoding="utf-8"))
    if metadata.get("kind") != "study-session":
        raise ValueError(f"not a study session: {path}")
    return metadata, body


def update_status(path: Path, status: str) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid session status: {status}")
    metadata, body = load_session(path)
    if metadata.get("status") in {"completed", "stopped"} and status != metadata["status"]:
        raise ValueError("completed or stopped sessions cannot be resumed")
    metadata["status"] = status
    metadata["updated_at"] = now_iso()
    if status in {"completed", "stopped"}:
        metadata["ended_at"] = now_iso()
    atomic_write(path, render(metadata, body))


def append_turn(
    path: Path,
    *,
    question: str,
    answer: str | None,
    evaluation: str = "pending",
    confidence: int | None = None,
    feedback: str = "",
    citation: str = "",
    action: str = "",
) -> None:
    metadata, body = load_session(path)
    if metadata.get("status") not in {"in-progress", "paused"}:
        raise ValueError("cannot append a turn to a finished session")
    if evaluation not in {"pending", "correct", "partial", "incorrect", "unsupported"}:
        raise ValueError(f"invalid evaluation: {evaluation}")
    if confidence is not None and confidence not in range(1, 6):
        raise ValueError("confidence must be between 1 and 5")
    number = int(metadata.get("question_count", 0)) + 1
    turn = (
        f"\n\n### Turn {number} — {slugify(question)[:60]}\n\n"
        f"**Question:** {question}\n\n"
        f"**My answer:** {answer if answer is not None else '(pending)'}\n\n"
        f"**Confidence before feedback:** {confidence if confidence is not None else 'not recorded'} / 5\n\n"
        f"**Evaluation:** {evaluation}\n\n"
        f"**Feedback:** {feedback or 'Pending evaluation.'}\n\n"
        f"**Citation:** {citation or 'Not available.'}\n\n"
        f"**Action:** {action or 'Pending.'}"
    )
    metadata["question_count"] = number
    metadata["updated_at"] = now_iso()
    atomic_write(path, render(metadata, body.rstrip() + turn))
