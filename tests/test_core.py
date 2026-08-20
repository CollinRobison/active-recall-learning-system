from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from active_recall.citations import validate_citation
from active_recall.confusion import record_confusion
from active_recall.frontmatter import parse, render
from active_recall.index import query_manifest, rebuild_manifest
from active_recall.ingest import ingest_local
from active_recall.schedule import next_review_at
from active_recall.session import append_turn, load_session, start_session, update_status
from active_recall.workspace import init_workspace


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


class ScheduleTests(unittest.TestCase):
    def test_schedule_is_transparent_and_deterministic(self) -> None:
        current = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date, reason = next_review_at("partial", now=current)
        self.assertEqual(date, "2026-01-03T00:00:00Z")
        self.assertIn("partial", reason)


if __name__ == "__main__":
    unittest.main()
