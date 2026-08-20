from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from active_recall.citations import validate_citation
from active_recall.confusion import record_confusion
from active_recall.embeddings import CommandEmbeddingProvider, HashEmbeddingProvider
from active_recall.model import CommandModelProvider
from active_recall.frontmatter import parse, render
from active_recall.index import query_manifest, rebuild_manifest
from active_recall.ingest import ingest_local
from active_recall.schedule import next_review_at
from active_recall.session import append_turn, load_session, start_session, update_status
from active_recall.tutor import Tutor
from active_recall.orchestrator import TutorSession
from active_recall.catalog import create_path, create_topic, recommend
from active_recall.workspace import init_workspace


class FakeModel:
    name = "fake"

    def __init__(self, responses):
        self.responses = iter(responses)

    def complete(self, *, system, user):
        return next(self.responses)


class FrontmatterTests(unittest.TestCase):
    def test_round_trip_scalars_and_lists(self) -> None:
        text = render({"id": "topic-one", "kind": "topic", "tags": ["a", "b"], "active": True}, "\n# Topic\n")
        metadata, body = parse(text)
        self.assertEqual(metadata["id"], "topic-one")
        self.assertEqual(metadata["tags"], ["a", "b"])
        self.assertTrue(metadata["active"])
        self.assertEqual(body, "# Topic\n")


class WorkspaceTests(unittest.TestCase):
    def test_init_is_non_destructive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "learning"
            created = init_workspace(root)
            self.assertTrue(created)
            readme = root / "README.md"
            readme.write_text("custom\n", encoding="utf-8")
            init_workspace(root)
            self.assertEqual(readme.read_text(encoding="utf-8"), "custom\n")
            self.assertTrue((root / "index/manifest.jsonl").exists())


class IngestionTests(unittest.TestCase):
    def test_markdown_ingest_preserves_headings_and_does_not_copy_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            source = root / "lesson.md"
            source.write_text("# Heading\n\n## Detail\nText.\n", encoding="utf-8")
            init_workspace(workspace)
            result = ingest_local(source, workspace)
            source_dir = workspace / "sources" / result["source_id"]
            self.assertEqual(result["status"], "complete")
            self.assertIn("L1: # Heading", (source_dir / "structure.md").read_text(encoding="utf-8"))
            self.assertIn("L3: ## Detail", (source_dir / "structure.md").read_text(encoding="utf-8"))
            self.assertFalse((source_dir / source.name).exists())
            self.assertIn(result["source_id"], (workspace / "catalog/sources.md").read_text(encoding="utf-8"))
            index_result = rebuild_manifest(workspace)
            self.assertEqual(index_result["records"], 1)
            matches = query_manifest(workspace, "detail")
            self.assertEqual(matches[0]["source_id"], result["source_id"])
            citation = validate_citation(workspace, f"{result['source_id']}, section Detail")
            self.assertTrue(citation["valid"])

    def test_learningignore_excludes_matching_folder_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            source_dir = root / "sources"
            source_dir.mkdir()
            (source_dir / "keep.md").write_text("keep", encoding="utf-8")
            (source_dir / "private.md").write_text("private", encoding="utf-8")
            init_workspace(workspace)
            (workspace / ".learningignore").write_text("private.md\n", encoding="utf-8")
            result = ingest_local(source_dir, workspace)
            extracted = (workspace / "sources" / result["source_id"] / "extracted.md").read_text(encoding="utf-8")
            self.assertIn("keep", extracted)
            self.assertNotIn("private", extracted)


class ConfusionTests(unittest.TestCase):
    def test_related_confusion_is_merged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            init_workspace(workspace)
            first = record_confusion(workspace, topic_id="topic-one", concept="Control Flow", question="Q1", answer="A1", missing="M1", source_location="Book, page 2", session_id="session-one")
            second = record_confusion(workspace, topic_id="topic-one", concept="Control Flow", question="Q2", answer="A2", missing="M2", source_location="Book, page 2", session_id="session-two")
            self.assertEqual(first, second)
            metadata, body = parse(first.read_text(encoding="utf-8"))
            self.assertEqual(metadata["review_count"], 1)
            self.assertIn("Additional evidence", body)
            self.assertEqual(len(list((workspace / "confusion/open").glob("*.md"))), 1)


class SessionTests(unittest.TestCase):
    def test_session_turn_pause_resume_and_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            init_workspace(workspace)
            path = start_session(workspace, scope_type="topic", scope_ids=["topic-one"], session_id="session-test")
            append_turn(path, question="What is retrieval?", answer="Recall.", evaluation="partial", confidence=2, feedback="Add the mechanism.", citation="source-one, section 1", action="review-later")
            metadata, body = load_session(path)
            self.assertEqual(metadata["question_count"], 1)
            self.assertIn("What is retrieval?", body)
            update_status(path, "paused")
            update_status(path, "in-progress")
            update_status(path, "completed")
            with self.assertRaises(ValueError):
                update_status(path, "in-progress")

    def test_invalid_confidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            init_workspace(workspace)
            path = start_session(workspace, scope_type="topic", scope_ids=["topic-one"], session_id="session-test")
            with self.assertRaises(ValueError):
                append_turn(path, question="Q", answer="A", confidence=6)


class EmbeddingTests(unittest.TestCase):
    def test_command_embedding_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "embed.py"
            script.write_text("import json, sys\nrequest = json.load(sys.stdin)\nprint(json.dumps({'embeddings': [[1.0, 0.0] for _ in request['texts']]}))\n", encoding="utf-8")
            provider = CommandEmbeddingProvider([sys.executable, str(script)], dimension=2)
            self.assertEqual(provider.embed(["a", "b"]), [[1.0, 0.0], [1.0, 0.0]])

    def test_hash_embeddings_are_normalized_and_deterministic(self) -> None:
        provider = HashEmbeddingProvider(dimension=16)
        first = provider.embed(["retrieval practice"])[0]
        second = provider.embed(["retrieval practice"])[0]
        self.assertEqual(first, second)
        self.assertAlmostEqual(sum(value * value for value in first), 1.0)


class ModelProviderTests(unittest.TestCase):
    def test_command_model_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "model.py"
            script.write_text("import json\nprint(json.dumps({'ok': True}))\n", encoding="utf-8")
            response = CommandModelProvider([sys.executable, str(script)]).complete(system="rules", user="request")
            self.assertEqual(response, {"ok": True})


class TutorTests(unittest.TestCase):
    def test_tutor_uses_retrieved_evidence_and_rejects_unknown_citations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            source = root / "lesson.md"
            source.write_text("# Retrieval\n\nRetrieval practice requires recalling information.\n", encoding="utf-8")
            init_workspace(workspace)
            result = ingest_local(source, workspace)
            source_id = result["source_id"]
            good_question = {
                "question": "What does retrieval practice require?",
                "concept_id": "retrieval-practice",
                "question_type": "conceptual",
                "expected_evidence": ["recalling information"],
                "source_support": [source_id + ", section Retrieval"],
            }
            tutor = Tutor(workspace, FakeModel([good_question]))
            response = tutor.generate_question("retrieval practice", source_id=source_id)
            self.assertEqual(response["question"], good_question["question"])
            bad = dict(good_question, source_support=["source-not-retrieved, section X"])
            with self.assertRaises(ValueError):
                Tutor(workspace, FakeModel([bad])).generate_question("retrieval practice", source_id=source_id)

    def test_evaluation_contract_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            source = root / "lesson.md"
            source.write_text("# Concept\n\nA concept has an example.\n", encoding="utf-8")
            init_workspace(workspace)
            result = ingest_local(source, workspace)
            response = {
                "classification": "partial",
                "scores": {"accuracy": 3, "completeness": 2, "reasoning": 2, "application": None},
                "missing_concepts": ["example"],
                "misconceptions": [],
                "source_support": [result["source_id"] + ", section Concept"],
                "needs_confusion_item": True,
                "recommended_action": "retry",
            }
            evaluation = Tutor(workspace, FakeModel([response])).evaluate_answer("Explain the concept", "It is an idea", source_id=result["source_id"])
            self.assertEqual(evaluation["classification"], "partial")


class TutorSessionTests(unittest.TestCase):
    def test_question_answer_hint_and_confusion_are_durably_orchestrated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            source = root / "lesson.md"
            source.write_text("# Retrieval\n\nRetrieval practice requires recalling information.\n", encoding="utf-8")
            init_workspace(workspace)
            source_id = ingest_local(source, workspace)["source_id"]
            path = start_session(workspace, scope_type="topic", scope_ids=["topic-retrieval"], objective="retrieval practice", session_id="session-orchestrated")
            question = {"question": "What does retrieval practice require?", "concept_id": "retrieval-practice", "question_type": "conceptual", "expected_evidence": ["recalling information"], "source_support": [source_id + ", section Retrieval"]}
            evaluation = {"classification": "partial", "scores": {"accuracy": 2, "completeness": 2, "reasoning": 2, "application": None}, "missing_concepts": ["recalling information"], "misconceptions": [], "source_support": [source_id + ", section Retrieval"], "needs_confusion_item": True, "recommended_action": "retry"}
            session = TutorSession(workspace, Tutor(workspace, FakeModel([question, evaluation])))
            self.assertEqual(session.next_question(path, source_id=source_id)["question"], question["question"])
            self.assertEqual(session.hint(path), "recalling information")
            result = session.submit_answer(path, "Reading it again", confidence=2, source_id=source_id)
            self.assertEqual(result["evaluation"]["classification"], "partial")
            metadata, body = load_session(path)
            self.assertNotIn("pending_question", metadata)
            self.assertEqual(metadata["question_count"], 1)
            self.assertIn("next review", body)
            self.assertEqual(len(list((workspace / "confusion/open").glob("*.md"))), 1)
            self.assertIn("topic-retrieval", (workspace / "reviews/due.md").read_text(encoding="utf-8"))
            self.assertIn("session-orchestrated", (workspace / "reviews/history.md").read_text(encoding="utf-8"))
            session.set_mode_or_difficulty(path, mode="feynman-teachback", difficulty="easier")
            metadata, _ = load_session(path)
            self.assertEqual(metadata["mode"], "feynman-teachback")


class CatalogTests(unittest.TestCase):
    def test_topics_paths_validate_relationships_and_rank_next_study(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); workspace = root / "workspace"; source = root / "book.md"
            source.write_text("# Foundations\n\nImportant material.\n", encoding="utf-8"); init_workspace(workspace)
            source_id = ingest_local(source, workspace)["source_id"]
            first = create_topic(workspace, name="Foundations", source_ids=[source_id], objectives=["Explain foundations"])
            topic_id = parse(first.read_text(encoding="utf-8"))[0]["id"]
            path = create_path(workspace, name="Book path", topic_ids=[topic_id], source_ids=[source_id], target_outcome="Learn the book")
            self.assertTrue(path.exists())
            self.assertEqual(recommend(workspace)[0]["id"], topic_id)
            with self.assertRaises(ValueError): create_path(workspace, name="Broken", topic_ids=["topic-missing"])


class ScheduleTests(unittest.TestCase):
    def test_schedule_is_transparent_and_deterministic(self) -> None:
        current = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date, reason = next_review_at("partial", now=current)
        self.assertEqual(date, "2026-01-03T00:00:00Z")
        self.assertIn("partial", reason)


if __name__ == "__main__":
    unittest.main()
