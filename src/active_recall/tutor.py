"""Source-grounded model-driven question generation and answer evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .citations import source_ids_in
from .embeddings import EmbeddingProvider, HashEmbeddingProvider, SentenceTransformerProvider
from .index import query_manifest, read_manifest, rebuild_manifest
from .milvus_index import MilvusLiteIndex, milvus_available, vector_status
from .model import ModelProvider

SYSTEM_RULES = """You are a source-grounded active-recall tutor.
Use only the supplied workspace evidence. Do not invent facts, citations, pages, excerpts, or source relationships.
Ask one question at a time. Be concise, respectful, and explicit about uncertainty.
Return JSON only. Do not expose chain-of-thought; provide only concise educational rationale.
External knowledge is disallowed unless the user has explicitly approved it, and then it must be labeled external.
"""

QUESTION_FIELDS = ("question", "concept_id", "question_type", "expected_evidence", "source_support")
EVALUATION_FIELDS = ("classification", "scores", "missing_concepts", "misconceptions", "source_support", "needs_confusion_item", "recommended_action")
VALID_CLASSIFICATIONS = {"correct", "partial", "incorrect", "unsupported"}
VALID_ACTIONS = {"explain", "hint", "retry", "review-later", "advance"}


class InsufficientContext(RuntimeError):
    pass


def _source_ids(evidence: Iterable[dict[str, Any]]) -> set[str]:
    return {str(item.get("source_id")) for item in evidence if item.get("source_id")}


def _citation_ids(value: Any) -> set[str]:
    if isinstance(value, str):
        return source_ids_in(value)
    if isinstance(value, list):
        return {source_id for item in value for source_id in _citation_ids(item)}
    if isinstance(value, dict):
        return _citation_ids(" ".join(str(item) for item in value.values()))
    return set()


def _validate_citations(payload: dict[str, Any], allowed: set[str]) -> None:
    cited = _citation_ids(payload.get("source_support", []))
    if not cited:
        raise ValueError("model response did not provide a source citation")
    unsupported = cited - allowed
    if unsupported:
        raise ValueError(f"model cited sources not present in retrieved evidence: {sorted(unsupported)}")


def _context_text(evidence: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"[Evidence {number}] source_id={item.get('source_id')} location={item.get('workspace_file')}:{item.get('line_start')}\n{item.get('content', '')}"
        for number, item in enumerate(evidence, 1)
    )


@dataclass
class Tutor:
    workspace: Path
    provider: ModelProvider
    retrieval_engine: str = "auto"
    embedding_provider: EmbeddingProvider | None = None
    vector_index: Any | None = None

    def _retrieve(self, text: str, *, source_id: str | None = None, topic_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        root = self.workspace.expanduser().resolve()
        if not read_manifest(root):
            rebuild_manifest(root)
        if self.retrieval_engine not in {"auto", "lexical", "vector"}:
            raise ValueError("retrieval_engine must be auto, lexical, or vector")
        if self.retrieval_engine != "lexical":
            try:
                vector = self._vector_retrieve(root, text, source_id=source_id, topic_id=topic_id, limit=limit)
                if vector:
                    return vector
            except Exception:
                # A derived retrieval cache must never block access to canonical workspace evidence.
                pass
        return query_manifest(root, text, source_id=source_id, topic_id=topic_id, limit=limit)

    def _vector_retrieve(self, root: Path, text: str, *, source_id: str | None, topic_id: str | None, limit: int) -> list[dict[str, Any]]:
        status = vector_status(root) if self.vector_index is None else {}
        if self.vector_index is None and status.get("status") != "current":
            return []
        index = self.vector_index
        if index is None:
            if not milvus_available():
                return []
            index = MilvusLiteIndex(root)
        provider = self.embedding_provider
        if provider is None:
            provider_name = status.get("provider")
            if provider_name == "hash":
                provider = HashEmbeddingProvider(int(status["dimension"]))
            elif provider_name == "sentence-transformers" and status.get("model_name"):
                provider = SentenceTransformerProvider(str(status["model_name"]))
            else:
                return []
        if status and (status.get("provider") != provider.name or int(status.get("dimension") or 0) != provider.dimension):
            return []
        return index.query(provider, text, source_id=source_id, topic_id=topic_id, limit=limit)

    def generate_question(
        self,
        objective: str,
        *,
        mode: str = "active-recall",
        source_id: str | None = None,
        topic_id: str | None = None,
        limit: int = 5,
        avoid_concepts: list[str] | None = None,
    ) -> dict[str, Any]:
        evidence = self._retrieve(objective, source_id=source_id, topic_id=topic_id, limit=limit)
        if not evidence:
            raise InsufficientContext("no indexed source evidence matched the objective")
        user = json.dumps({"mode": mode, "objective": objective, "avoid_recent_concepts": avoid_concepts or [], "evidence": _context_text(evidence)}, ensure_ascii=False)
        payload = self.provider.complete(
            system=SYSTEM_RULES + "Return fields: question, concept_id, objective, question_type, expected_evidence, difficulty, source_support, needs_more_context. When avoid_recent_concepts is nonempty, interleave by selecting a different concept when evidence permits.",
            user=user,
        )
        missing = [field for field in QUESTION_FIELDS if field not in payload]
        if missing:
            raise ValueError(f"model question response missing fields: {missing}")
        _validate_citations(payload, _source_ids(evidence))
        if payload.get("needs_more_context"):
            raise InsufficientContext("model reported insufficient source context")
        return payload

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        *,
        objective: str | None = None,
        confidence: int | None = None,
        source_id: str | None = None,
        topic_id: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        search_text = objective or question
        evidence = self._retrieve(search_text, source_id=source_id, topic_id=topic_id, limit=limit)
        if not evidence:
            raise InsufficientContext("no indexed source evidence matched the question")
        user = json.dumps(
            {"question": question, "answer": answer, "confidence_rating": confidence, "evidence": _context_text(evidence)},
            ensure_ascii=False,
        )
        payload = self.provider.complete(
            system=SYSTEM_RULES + "Return the structured answer-evaluation contract: classification, scores, confidence_rating, missing_concepts, misconceptions, source_support, needs_confusion_item, recommended_action, needs_more_context.",
            user=user,
        )
        missing = [field for field in EVALUATION_FIELDS if field not in payload]
        if missing:
            raise ValueError(f"model evaluation response missing fields: {missing}")
        if payload.get("classification") not in VALID_CLASSIFICATIONS:
            raise ValueError("model returned an invalid evaluation classification")
        if payload.get("recommended_action") not in VALID_ACTIONS:
            raise ValueError("model returned an invalid recommended action")
        _validate_citations(payload, _source_ids(evidence))
        if payload.get("needs_more_context"):
            raise InsufficientContext("model reported insufficient source context")
        return payload
