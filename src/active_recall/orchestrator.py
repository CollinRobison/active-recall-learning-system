"""Durable, source-grounded one-question-at-a-time tutor session orchestration."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .confusion import record_confusion
from .frontmatter import render
from .schedule import next_review_at
from .session import append_turn, load_session
from .reviews import record_review
from .workspace import atomic_write, now_iso


class TutorSession:
    """Connect a ``Tutor`` to a persisted session without hiding state in memory."""

    def __init__(self, workspace: Path, tutor: Any):
        self.workspace = workspace.expanduser().resolve()
        self.tutor = tutor

    def _write(self, path: Path, metadata: dict[str, Any], body: str) -> None:
        metadata["updated_at"] = now_iso()
        atomic_write(path, render(metadata, body))

    @staticmethod
    def _topic(metadata: dict[str, Any]) -> str:
        ids = metadata.get("scope_ids") or []
        return str(ids[0]) if metadata.get("scope_type") == "topic" and ids else "unscoped"

    def next_question(self, path: Path, *, source_id: str | None = None, topic_id: str | None = None) -> dict[str, Any]:
        metadata, body = load_session(path)
        if metadata.get("status") != "in-progress":
            raise ValueError("only an in-progress session can ask a question")
        if metadata.get("pending_question"):
            raise ValueError("answer, request a hint, retry, or clear the pending question before continuing")
        question = self.tutor.generate_question(
            str(metadata.get("objective", "")), mode=str(metadata.get("mode", "active-recall")),
            source_id=source_id, topic_id=topic_id,
            avoid_concepts=list(metadata.get("recent_concepts", []))[-2:],
        )
        metadata["pending_question"] = question
        self._write(path, metadata, body)
        return question

    def hint(self, path: Path) -> str:
        metadata, body = load_session(path)
        question = metadata.get("pending_question")
        if not isinstance(question, dict):
            raise ValueError("no pending question to hint")
        hints = question.get("expected_evidence") or []
        hint = str(hints[0]) if hints else "Review the cited source and identify the key relationship."
        metadata["hint_count"] = int(metadata.get("hint_count", 0)) + 1
        self._write(path, metadata, body)
        return hint

    def submit_answer(self, path: Path, answer: str, *, confidence: int | None = None, source_id: str | None = None, topic_id: str | None = None) -> dict[str, Any]:
        metadata, body = load_session(path)
        question = metadata.get("pending_question")
        if metadata.get("status") != "in-progress" or not isinstance(question, dict):
            raise ValueError("an in-progress session with a pending question is required")
        evaluation = self.tutor.evaluate_answer(
            str(question["question"]), answer, objective=str(metadata.get("objective", "")), confidence=confidence,
            source_id=source_id, topic_id=topic_id,
        )
        citations = evaluation.get("source_support") or question.get("source_support") or []
        citation = "; ".join(str(item) for item in citations)
        action = str(evaluation["recommended_action"])
        classification = str(evaluation["classification"])
        effective = "correct-low-confidence" if classification == "correct" and confidence is not None and confidence <= 2 else classification
        evidence_dimension = {"application": "application", "explanation": "explanation", "teach-back": "explanation", "feynman": "explanation"}.get(str(question.get("question_type", "")).lower(), "recall")
        delayed = bool(metadata.get("last_review_at"))
        if evidence_dimension == "application" and classification == "correct" and delayed:
            effective = "application-correct"
        review_at, reason = next_review_at(effective)
        append_turn(path, question=str(question["question"]), answer=answer, evaluation=classification,
                    confidence=confidence, feedback="; ".join(str(x) for x in evaluation.get("missing_concepts", [])) or action,
                    citation=citation, action=f"{action}; next review {review_at} ({reason})", evidence_dimension=evidence_dimension)
        metadata, body = load_session(path)
        metadata.pop("pending_question", None)
        metadata["next_review_at"] = review_at
        metadata["last_review_at"] = now_iso()
        metadata["recent_concepts"] = (list(metadata.get("recent_concepts", [])) + [str(question.get("concept_id", "unknown"))])[-4:]
        self._write(path, metadata, body)
        review = record_review(self.workspace, topic_id=topic_id or self._topic(metadata), session_id=str(metadata["id"]), classification=classification, confidence=confidence, next_review_at=review_at, citation=citation, evidence_dimension=evidence_dimension, delayed=delayed)
        if evaluation.get("needs_confusion_item"):
            record_confusion(self.workspace, topic_id=topic_id or self._topic(metadata), concept=str(question.get("concept_id", question["question"])),
                             question=str(question["question"]), answer=answer,
                             missing="; ".join(str(x) for x in evaluation.get("missing_concepts", [])) or classification,
                             source_location=citation or "Source location unavailable", source_ids=[], session_id=str(metadata["id"]))
        return {"evaluation": evaluation, "review": review, "next_review_at": review_at, "recommended_action": action}

    def set_mode_or_difficulty(self, path: Path, *, mode: str | None = None, difficulty: str | None = None) -> None:
        metadata, body = load_session(path)
        if metadata.get("status") not in {"in-progress", "paused"}:
            raise ValueError("cannot modify a finished session")
        if mode:
            metadata["mode"] = mode
        if difficulty:
            metadata["difficulty"] = difficulty
        self._write(path, metadata, body)
