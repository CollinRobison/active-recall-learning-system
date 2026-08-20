"""Transparent first-version review scheduling."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


INTERVALS = {
    "incorrect": (1, "failed or seriously confused; review soon"),
    "partial": (2, "partial answer; review shortly"),
    "correct-low-confidence": (2, "correct but low confidence; review soon"),
    "correct": (7, "correct and confident; longer interval"),
    "application-correct": (14, "correct application after delay; extend interval"),
}


def next_review_at(result: str, *, now: datetime | None = None) -> tuple[str, str]:
    """Return an ISO date and transparent reason for a result category."""
    if result not in INTERVALS:
        raise ValueError(f"unknown review result: {result}")
    current = now or datetime.now(timezone.utc)
    days, reason = INTERVALS[result]
    return (current + timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z"), reason
