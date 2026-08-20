from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from active_recall.citations import validate_citation
from active_recall.confusion import record_confusion
from active_recall.embeddings import CommandEmbeddingProvider, HashEmbeddingProvider
from active_recall.model import CommandModelProvider
from active_recall.frontmatter import parse, render
from active_recall.index import query_manifest, rebuild_manifest
from active_recall.ingest import confirm_source_metadata, ingest_local
from active_recall.milvus_index import MilvusLiteIndex
from active_recall.schedule import next_review_at
from active_recall.session import append_turn, load_session, start_session, update_status
from active_recall.tutor import Tutor
from active_recall.orchestrator import TutorSession
from active_recall.catalog import create_path, create_topic, recommend, update_topic
from active_recall.progress import summarize
from active_recall.reviews import record_review
from active_recall.workspace import init_workspace, iter_records


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

    def test_repository_requires_opt_in_and_metadata_conflicts_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); workspace = root / "workspace"; repository = root / "repo"
            (repository / ".git").mkdir(parents=True); (repository / "node_modules").mkdir()
            (repository / "main.py").write_text("# safe\nvalue = 1\n", encoding="utf-8")
            (repository / ".env").write_text("TOKEN=nope", encoding="utf-8")
            (repository / "node_modules" / "bad.js").write_text("secret", encoding="utf-8")
            init_workspace(workspace)
            with self.assertRaises(ValueError): ingest_local(repository, workspace)
            first = ingest_local(repository, workspace, allow_repository=True)
            self.assertNotIn("TOKEN", (workspace / "sources" / first["source_id"] / "extracted.md").read_text(encoding="utf-8"))
            second = ingest_local(repository, workspace, allow_repository=True, title="Repo copy")
            self.assertTrue(second["conflict_ids"])
            self.assertTrue((workspace / "conflicts/open").glob("*.md"))
            self.assertEqual(confirm_source_metadata(workspace, first["source_id"])["status"], "confirmed")

    def test_docling_is_optional_and_records_converter_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); workspace = root / "workspace"; source = root / "textbook.pdf"
            source.write_bytes(b"not a real PDF because the converter is mocked")
            init_workspace(workspace)
            with patch("active_recall.ingest._extract_docling", return_value=("# Chapter One\n\nStructured evidence.\n", ["Docling test conversion"])):
                result = ingest_local(source, workspace, docling="required")
            record = workspace / "sources" / result["source_id"] / "source.md"
            metadata, _ = parse(record.read_text(encoding="utf-8"))
            self.assertEqual(result["extraction_engines"], ["docling"])
            self.assertEqual(metadata["extraction_engines"], ["docling"])
            self.assertIn("Structured evidence", (record.parent / "extracted.md").read_text(encoding="utf-8"))

    def test_docling_auto_degrades_to_builtin_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); workspace = root / "workspace"; source = root / "lesson.docx"
            source.write_bytes(b"placeholder")
            init_workspace(workspace)
            with patch("active_recall.ingest._extract_docling", side_effect=RuntimeError("Docling extraction requires optional dependency 'docling'")), patch("active_recall.ingest._extract_docx", return_value=("# Built in\n\nFallback text.\n", [])):
                result = ingest_local(source, workspace, docling="auto")
            self.assertEqual(result["extraction_engines"], ["builtin-docx"])
            self.assertTrue(any("used built-in extraction" in warning for warning in result["warnings"]))


class FakeMilvus:
    def __init__(self): self.collections = {}; self.calls = []
    def has_collection(self, name): return name in self.collections
    def create_collection(self, collection_name, **kwargs): self.collections[collection_name] = {}; self.calls.append(("create", collection_name))
    def insert(self, collection_name, data): self.collections[collection_name].update({row["record_id"]: row for row in data}); self.calls.append(("insert", collection_name, len(data)))
    def upsert(self, collection_name, data): self.collections[collection_name].update({row["record_id"]: row for row in data}); self.calls.append(("upsert", collection_name, len(data)))
    def delete(self, collection_name, ids):
        for item in ids: self.collections[collection_name].pop(item, None)
        self.calls.append(("delete", collection_name, tuple(ids)))
    def search(self, collection_name, data, limit, filter, output_fields):
        rows = list(self.collections[collection_name].values())
        if filter:
            source = filter.split('"')[1]; rows = [row for row in rows if row["source_id"] == source]
        return [[{"id": row["record_id"], "distance": 1.0, "entity": {key: row[key] for key in output_fields}} for row in rows[:limit]]]


class MilvusBoundaryTests(unittest.TestCase):
    def test_generation_incremental_updates_and_filters_without_pymilvus(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); workspace = root / "workspace"; source = root / "lesson.md"
            source.write_text("# One\nalpha retrieval\n", encoding="utf-8"); init_workspace(workspace)
            source_id = ingest_local(source, workspace)["source_id"]
            source_record = next(path for path, metadata, _ in iter_records(workspace, {"source"}) if metadata["id"] == source_id)
            metadata, body = parse(source_record.read_text(encoding="utf-8")); metadata["topic_ids"] = ["topic-one"]; metadata["path_ids"] = ["path-one"]; source_record.write_text(render(metadata, body), encoding="utf-8")
            fake = FakeMilvus(); index = MilvusLiteIndex(workspace, client=fake); provider = HashEmbeddingProvider(8)
            built = index.rebuild(provider); self.assertEqual(built["generation"], 1); self.assertTrue(built["collection"].endswith("_g1"))
            self.assertEqual(len(index.query(provider, "retrieval", source_id=source_id, topic_id="topic-one", path_id="path-one")), 1)
            (workspace / "sources" / source_id / "extracted.md").write_text("# One\nbeta retrieval\n", encoding="utf-8")
            updated = index.incremental(provider)
            self.assertEqual(updated["incremental"]["upserted"], 1)
            self.assertEqual(updated["generation"], 1)
            (workspace / "sources" / source_id / "extracted.md").unlink()
            stale = index.incremental(provider)
            self.assertEqual(stale["incremental"]["removed"], 1)
            self.assertTrue(any(call[0] == "delete" for call in fake.calls))


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

    def test_openai_compatible_provider_request_and_response_contract(self) -> None:
        from active_recall.model import OpenAICompatibleProvider

        received: dict[str, object] = {}
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received["authorization"] = self.headers.get("Authorization")
                received["payload"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                body = json.dumps({"choices": [{"message": {"content": json.dumps({"ok": True})}}]}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            def log_message(self, *_): pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever); thread.start()
        try:
            import os
            previous = os.environ.get("TEST_ACTIVE_RECALL_KEY"); os.environ["TEST_ACTIVE_RECALL_KEY"] = "integration-secret"
            provider = OpenAICompatibleProvider(f"http://127.0.0.1:{server.server_port}/v1/chat/completions", "test-model", "TEST_ACTIVE_RECALL_KEY")
            self.assertEqual(provider.complete(system="system rule", user="user request"), {"ok": True})
            self.assertEqual(received["authorization"], "Bearer integration-secret")
            self.assertEqual(received["payload"]["model"], "test-model")
            self.assertEqual(received["payload"]["response_format"], {"type": "json_object"})
        finally:
            if previous is None: os.environ.pop("TEST_ACTIVE_RECALL_KEY", None)
            else: os.environ["TEST_ACTIVE_RECALL_KEY"] = previous
            server.shutdown(); thread.join(); server.server_close()


class CitationLocationTests(unittest.TestCase):
    def test_citations_require_exact_section_page_and_line_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); workspace = root / "workspace"; source = root / "lesson.md"
            source.write_text("# Exact Heading\n\nEvidence is here.\n", encoding="utf-8"); init_workspace(workspace)
            source_id = ingest_local(source, workspace)["source_id"]
            self.assertTrue(validate_citation(workspace, f"{source_id}, section Exact Heading")["valid"])
            invalid_section = validate_citation(workspace, f"{source_id}, section Invented Heading")
            self.assertFalse(invalid_section["valid"])
            self.assertIn(source_id, invalid_section["location_errors"])
            self.assertTrue(validate_citation(workspace, f"{source_id}, lines 1-3")["valid"])
            self.assertFalse(validate_citation(workspace, f"{source_id}, line 99")["valid"])
            extracted = workspace / "sources" / source_id / "extracted.md"
            extracted.write_text("<!-- page: 4 -->\n\n# Exact Heading\nEvidence\n", encoding="utf-8")
            self.assertTrue(validate_citation(workspace, f"{source_id}, page 4")["valid"])
            self.assertFalse(validate_citation(workspace, f"{source_id}, page 5")["valid"])


class GoldenLearningCaseTests(unittest.TestCase):
    def test_golden_case_declares_source_grounded_question_and_three_outcomes(self) -> None:
        golden = Path(__file__).parent / "golden" / "retrieval-practice.md"
        text = golden.read_text(encoding="utf-8")
        contract = json.loads(text.split("```json\n", 1)[1].split("\n```", 1)[0])
        self.assertEqual(contract["question_type"], "explanation")
        self.assertTrue(contract["expected_evidence"])
        self.assertIn("source-golden-retrieval, section Why it works", contract["source_support"])
        for outcome in ("**correct:**", "**partial:**", "**incorrect:**", "**overconfident incorrect:**", "**alternative wording correct:**", "**conflicting source:**", "**missing context:**"):
            self.assertIn(outcome, text)


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
            self.assertIn("**Evidence dimension:** recall", body)
            self.assertEqual(len(list((workspace / "confusion/open").glob("*.md"))), 1)
            self.assertIn("topic-retrieval", (workspace / "reviews/due.md").read_text(encoding="utf-8"))
            self.assertIn("session-orchestrated", (workspace / "reviews/history.md").read_text(encoding="utf-8"))
            self.assertIn("calibrated", (workspace / "reviews/history.md").read_text(encoding="utf-8"))
            evidence = summarize(workspace, topic_id="topic-retrieval")
            self.assertEqual(evidence["evidence_dimensions"], {"recall": 1})
            self.assertEqual(evidence["calibration"], {"calibrated": 1})
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

    def test_topic_edit_requires_confirmation_syncs_sources_and_blocks_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); workspace = root / "workspace"; source = root / "book.md"
            source.write_text("# Foundations\n\nImportant material.\n", encoding="utf-8"); init_workspace(workspace)
            source_id = ingest_local(source, workspace)["source_id"]
            prerequisite_path = create_topic(workspace, name="Prerequisite", source_ids=[source_id])
            prerequisite_id = parse(prerequisite_path.read_text(encoding="utf-8"))[0]["id"]
            dependent_path = create_topic(workspace, name="Dependent", prerequisites=[prerequisite_id])
            dependent_id = parse(dependent_path.read_text(encoding="utf-8"))[0]["id"]
            preview = update_topic(workspace, dependent_id, source_ids=[source_id])
            self.assertEqual(preview["status"], "confirmation-required")
            self.assertEqual(parse(dependent_path.read_text(encoding="utf-8"))[0]["source_ids"], [])
            applied = update_topic(workspace, dependent_id, source_ids=[source_id], confirm=True)
            self.assertEqual(applied["status"], "applied")
            source_record = next(metadata for _, metadata, _ in iter_records(workspace, {"source"}))
            self.assertIn(dependent_id, source_record["topic_ids"])
            recommendations = recommend(workspace)
            self.assertNotIn(dependent_id, [item["id"] for item in recommendations])
            update_topic(workspace, prerequisite_id, status="completed", confirm=True)
            self.assertIn(dependent_id, [item["id"] for item in recommend(workspace)])
            with self.assertRaises(ValueError):
                update_topic(workspace, prerequisite_id, prerequisites=[dependent_id], confirm=True)


class ScheduleTests(unittest.TestCase):
    def test_schedule_is_transparent_and_deterministic(self) -> None:
        current = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date, reason = next_review_at("partial", now=current)
        self.assertEqual(date, "2026-01-03T00:00:00Z")
        self.assertIn("partial", reason)

    def test_review_queue_is_per_topic_and_keeps_calibration_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary); init_workspace(workspace)
            record_review(workspace, topic_id="topic-one", session_id="session-a", classification="incorrect", confidence=5, next_review_at="2026-01-02T00:00:00Z", citation="source-one, section One")
            record_review(workspace, topic_id="topic-one", session_id="session-b", classification="correct", confidence=1, next_review_at="2026-01-08T00:00:00Z", citation="source-one, section One", evidence_dimension="application", delayed=True)
            due = (workspace / "reviews/due.md").read_text(encoding="utf-8")
            history = (workspace / "reviews/history.md").read_text(encoding="utf-8")
            self.assertEqual(due.count("`topic-one`"), 1)
            self.assertIn("underconfident", due)
            self.assertIn("overconfident", history)
            self.assertIn("Evidence dimension: application", history)


if __name__ == "__main__":
    unittest.main()
