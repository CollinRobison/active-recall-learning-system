"""Command-line entry point for the dependency-free workspace tools."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .citations import validate_citation
from .embeddings import CommandEmbeddingProvider, HashEmbeddingProvider, SentenceTransformerProvider
from .index import query_manifest, rebuild_manifest
from .ingest import confirm_source_metadata, ingest_local, ingest_url
from .milvus_index import MilvusLiteIndex, milvus_available, vector_status
from .model import CommandModelProvider, OpenAICompatibleProvider
from .progress import summarize
from .tutor import Tutor
from .orchestrator import TutorSession
from .catalog import create_path, create_topic, recommend, update_topic
from .dashboard import generate_dashboard
from .removal import remove_record
from .session import append_turn, start_session, update_status
from .workspace import find_workspace, init_workspace, iter_records


def _workspace(value: str) -> Path:
    return Path(value).expanduser().resolve()


_CANONICAL_MUTATION_COMMANDS = {
    "init", "ingest", "source-confirm", "topic-create", "topic-edit", "path-create",
    "session-start", "session-turn", "session-status", "tutor-session-question",
    "tutor-session-answer", "tutor-session-hint", "tutor-session-update",
    "remove",
}


def _refresh_dashboard_after_mutation(args: argparse.Namespace) -> None:
    """Keep the derived dashboard current without invalidating a successful write."""
    try:
        root = _workspace(str(args.workspace)) if hasattr(args, "workspace") else find_workspace(Path(args.session))
        generate_dashboard(root)
    except Exception as exc:  # Dashboard output is derived; preserve canonical-write success.
        print(f"warning: learning data was saved, but dashboard regeneration failed: {exc}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="learning", description="Portable Markdown-first learning workspace")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a learning workspace")
    init.add_argument("workspace", type=Path)

    ingest = sub.add_parser("ingest", help="ingest a local Markdown/text/PDF file, folder, or approved URL")
    ingest.add_argument("input")
    ingest.add_argument("--workspace", required=True, type=Path)
    ingest.add_argument("--title")
    ingest.add_argument("--type", dest="source_type")
    ingest.add_argument("--allow-network", action="store_true", help="required for URL ingestion")
    ingest.add_argument("--ocr", choices=["auto", "never", "required"], default="auto", help="optional image OCR mode")
    ingest.add_argument("--docling", choices=["auto", "never", "required"], default="never", help="optional local high-fidelity conversion; auto falls back to built-in extraction")
    ingest.add_argument("--allow-repository", action="store_true", help="required to traverse a Git repository; skips VCS, dependencies, and likely secrets")

    source_confirm = sub.add_parser("source-confirm", help="confirm derived source metadata after inspection")
    source_confirm.add_argument("workspace", type=Path)
    source_confirm.add_argument("source_id")
    source_confirm.add_argument("--authority", choices=["unverified", "user-marked", "primary", "secondary"])

    catalog = sub.add_parser("list", help="list available topics, sources, paths, and open confusion")
    catalog.add_argument("workspace", type=Path)

    topic_create = sub.add_parser("topic-create", help="create a topic record; relationships are validated")
    topic_create.add_argument("workspace", type=Path); topic_create.add_argument("name")
    topic_create.add_argument("--objective", action="append"); topic_create.add_argument("--source", action="append")
    topic_create.add_argument("--prerequisite", action="append"); topic_create.add_argument("--related", action="append"); topic_create.add_argument("--path", action="append")

    topic_edit = sub.add_parser("topic-edit", help="preview or explicitly confirm a canonical topic relationship/status edit")
    topic_edit.add_argument("workspace", type=Path); topic_edit.add_argument("topic_id")
    topic_edit.add_argument("--source", action="append"); topic_edit.add_argument("--prerequisite", action="append"); topic_edit.add_argument("--related", action="append"); topic_edit.add_argument("--path", action="append")
    topic_edit.add_argument("--status", choices=["active", "completed", "archived"])
    topic_edit.add_argument("--confirm", action="store_true", help="apply the previewed canonical Markdown change")

    path_create = sub.add_parser("path-create", help="create an ordered learning path from existing topics")
    path_create.add_argument("workspace", type=Path); path_create.add_argument("name")
    path_create.add_argument("--topic", action="append", required=True); path_create.add_argument("--source", action="append")
    path_create.add_argument("--prerequisite", action="append"); path_create.add_argument("--target-outcome", default="")

    remove = sub.add_parser("remove", help="preview or confirmed-remove one source, topic, or path with orphaned artifacts")
    remove.add_argument("workspace", type=Path); remove.add_argument("record_id")
    remove.add_argument("--confirm", action="store_true", help="permanently apply the relationship-aware removal plan")

    recommend_command = sub.add_parser("recommend", help="rank due confusion, path order, and active topics")
    recommend_command.add_argument("workspace", type=Path); recommend_command.add_argument("--limit", type=int, default=5)
    start = sub.add_parser("session-start", help="create a resumable session")
    start.add_argument("workspace", type=Path)
    start.add_argument("--scope-type", default="topic")
    start.add_argument("--scope-id", action="append", required=True)
    start.add_argument("--mode", default="active-recall")
    start.add_argument("--objective", default="Remember and apply the material")
    start.add_argument("--difficulty", default="adaptive")
    start.add_argument("--id", dest="session_id")

    turn = sub.add_parser("session-turn", help="append one persisted session turn")
    turn.add_argument("session", type=Path)
    turn.add_argument("--question", required=True)
    turn.add_argument("--answer")
    turn.add_argument("--evaluation", default="pending")
    turn.add_argument("--confidence", type=int)
    turn.add_argument("--feedback", default="")
    turn.add_argument("--citation", default="")
    turn.add_argument("--action", default="")

    status = sub.add_parser("session-status", help="pause, resume, complete, or stop a session")
    status.add_argument("session", type=Path)
    status.add_argument("status", choices=["in-progress", "paused", "completed", "stopped"])

    reindex = sub.add_parser("reindex", help="rebuild the dependency-free lexical manifest")
    reindex.add_argument("workspace", type=Path)

    query = sub.add_parser("query", help="search the local manifest")
    query.add_argument("workspace", type=Path)
    query.add_argument("text")
    query.add_argument("--source")
    query.add_argument("--topic")
    query.add_argument("--path")
    query.add_argument("--limit", type=int, default=5)

    progress = sub.add_parser("progress", help="summarize persisted evidence")
    progress.add_argument("workspace", type=Path)
    progress.add_argument("--topic")

    dashboard = sub.add_parser("dashboard", help="generate a standalone, queryable HTML workspace dashboard")
    dashboard.add_argument("workspace", type=Path)
    dashboard.add_argument("--output", type=Path, help="defaults to WORKSPACE/dashboard.html")

    citation = sub.add_parser("validate-citation", help="verify a citation refers to a known source")
    citation.add_argument("workspace", type=Path)
    citation.add_argument("text")

    def add_tutor_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("workspace", type=Path)
        command.add_argument("--source")
        command.add_argument("--topic")
        command.add_argument("--limit", type=int, default=5)
        command.add_argument("--provider-command", help="local command accepting model JSON on stdin")
        command.add_argument("--endpoint", help="OpenAI-compatible endpoint; requires --allow-network")
        command.add_argument("--model", default="")
        command.add_argument("--api-key-env", default="ACTIVE_RECALL_MODEL_API_KEY")
        command.add_argument("--allow-network", action="store_true")
        command.add_argument("--retrieval-engine", choices=["auto", "lexical", "vector"], default="auto", help="auto prefers a compatible current Milvus index, then falls back to lexical evidence")
        command.add_argument("--embedding-provider", choices=["hash", "command", "sentence-transformers"], help="only needed to override automatic vector-provider selection")
        command.add_argument("--embedding-dimension", type=int, help="required for hash/command provider overrides")
        command.add_argument("--embedding-model-name", default="all-MiniLM-L6-v2")
        command.add_argument("--embedding-command", help="local JSON embedding command; required for command provider override")

    question = sub.add_parser("tutor-question", help="generate one source-grounded retrieval question")
    add_tutor_options(question)
    question.add_argument("objective")
    question.add_argument("--mode", default="active-recall")

    evaluation = sub.add_parser("tutor-evaluate", help="evaluate one answer against source evidence")
    add_tutor_options(evaluation)
    evaluation.add_argument("question")
    evaluation.add_argument("answer")
    evaluation.add_argument("--objective")
    evaluation.add_argument("--confidence", type=int)

    session_question = sub.add_parser("tutor-session-question", help="generate and durably save the next tutor-session question")
    add_tutor_options(session_question)
    session_question.add_argument("session", type=Path)

    session_answer = sub.add_parser("tutor-session-answer", help="evaluate and durably save an answer to the pending session question")
    add_tutor_options(session_answer)
    session_answer.add_argument("session", type=Path)
    session_answer.add_argument("answer")
    session_answer.add_argument("--confidence", type=int)

    session_hint = sub.add_parser("tutor-session-hint", help="return a source-grounded hint for the pending question")
    session_hint.add_argument("workspace", type=Path)
    session_hint.add_argument("session", type=Path)

    session_update = sub.add_parser("tutor-session-update", help="change mode or difficulty for a resumable tutor session")
    session_update.add_argument("workspace", type=Path)
    session_update.add_argument("session", type=Path)
    session_update.add_argument("--mode")
    session_update.add_argument("--difficulty")
    vector_status_command = sub.add_parser("vector-status", help="show optional Milvus Lite status")
    vector_status_command.add_argument("workspace", type=Path)

    def add_vector_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("workspace", type=Path)
        command.add_argument("--embedding-provider", choices=["hash", "command", "sentence-transformers"], default="hash")
        command.add_argument("--dimension", type=int, default=256)
        command.add_argument("--model-name", default="all-MiniLM-L6-v2")
        command.add_argument("--embedding-command", help="local command accepting embedding JSON on stdin")

    vector_reindex = sub.add_parser("vector-reindex", help="build the optional Milvus Lite vector collection")
    add_vector_options(vector_reindex)
    vector_reindex.add_argument("--incremental", action="store_true", help="upsert changed chunks into the current published generation")

    vector_query = sub.add_parser("vector-query", help="query the optional Milvus Lite vector collection")
    add_vector_options(vector_query)
    vector_query.add_argument("text")
    vector_query.add_argument("--source")
    vector_query.add_argument("--topic")
    vector_query.add_argument("--path")
    vector_query.add_argument("--limit", type=int, default=5)
    return parser


def _embedding_provider(args: argparse.Namespace):
    if args.embedding_provider == "hash":
        return HashEmbeddingProvider(args.dimension)
    if args.embedding_provider == "sentence-transformers":
        return SentenceTransformerProvider(args.model_name)
    if not args.embedding_command:
        raise SystemExit("--embedding-command is required with --embedding-provider command")
    return CommandEmbeddingProvider.from_string(args.embedding_command, args.dimension)


def _model_provider(args: argparse.Namespace):
    if args.provider_command:
        return CommandModelProvider.from_string(args.provider_command)
    if args.endpoint:
        if not args.allow_network:
            raise SystemExit("model endpoint use requires --allow-network")
        if not args.model:
            raise SystemExit("--model is required with --endpoint")
        return OpenAICompatibleProvider(args.endpoint, args.model, args.api_key_env)
    raise SystemExit("provide --provider-command or --endpoint")


def _tutor_embedding_provider(args: argparse.Namespace):
    if not args.embedding_provider:
        return None
    if args.embedding_provider == "sentence-transformers":
        return SentenceTransformerProvider(args.embedding_model_name)
    if not args.embedding_dimension:
        raise SystemExit("--embedding-dimension is required with hash or command tutor retrieval overrides")
    if args.embedding_provider == "hash":
        return HashEmbeddingProvider(args.embedding_dimension)
    if not args.embedding_command:
        raise SystemExit("--embedding-command is required with --embedding-provider command")
    return CommandEmbeddingProvider.from_string(args.embedding_command, args.embedding_dimension)


def _tutor(args: argparse.Namespace) -> Tutor:
    return Tutor(_workspace(str(args.workspace)), _model_provider(args), retrieval_engine=args.retrieval_engine, embedding_provider=_tutor_embedding_provider(args))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        created = init_workspace(_workspace(str(args.workspace)))
        print(json.dumps({"workspace": str(_workspace(str(args.workspace))), "created": [str(p) for p in created]}, indent=2))
    elif args.command == "ingest":
        if args.input.startswith(("https://", "http://")):
            if not args.allow_network:
                raise SystemExit("URL ingestion requires --allow-network")
            result = ingest_url(args.input, _workspace(str(args.workspace)), title=args.title)
        else:
            result = ingest_local(Path(args.input), _workspace(str(args.workspace)), title=args.title, source_type=args.source_type, ocr=args.ocr, docling=args.docling, allow_repository=args.allow_repository)
        print(json.dumps(result, indent=2))
    elif args.command == "source-confirm":
        print(json.dumps(confirm_source_metadata(_workspace(str(args.workspace)), args.source_id, authority=args.authority), indent=2))
    elif args.command == "list":
        records = []
        for path, metadata, _ in iter_records(_workspace(str(args.workspace))):
            if metadata.get("kind") in {"topic", "source", "path", "confusion-item"}:
                records.append({"id": metadata.get("id"), "kind": metadata.get("kind"), "status": metadata.get("status"), "path": str(path)})
        print(json.dumps(sorted(records, key=lambda item: (item["kind"], item["id"] or "")), indent=2))
    elif args.command == "topic-create":
        print(create_topic(_workspace(str(args.workspace)), name=args.name, objectives=args.objective, source_ids=args.source, prerequisites=args.prerequisite, related_topics=args.related, path_ids=args.path))
    elif args.command == "topic-edit":
        print(json.dumps(update_topic(_workspace(str(args.workspace)), args.topic_id, source_ids=args.source, prerequisites=args.prerequisite, related_topics=args.related, path_ids=args.path, status=args.status, confirm=args.confirm), indent=2))
    elif args.command == "path-create":
        print(create_path(_workspace(str(args.workspace)), name=args.name, topic_ids=args.topic, source_ids=args.source, prerequisites=args.prerequisite, target_outcome=args.target_outcome))
    elif args.command == "remove":
        print(json.dumps(remove_record(_workspace(str(args.workspace)), args.record_id, confirm=args.confirm), indent=2))
    elif args.command == "recommend":
        print(json.dumps(recommend(_workspace(str(args.workspace)), limit=args.limit), indent=2))
    elif args.command == "session-start":
        path = start_session(_workspace(str(args.workspace)), scope_type=args.scope_type, scope_ids=args.scope_id, mode=args.mode, objective=args.objective, difficulty=args.difficulty, session_id=args.session_id)
        print(path)
    elif args.command == "session-turn":
        append_turn(args.session, question=args.question, answer=args.answer, evaluation=args.evaluation, confidence=args.confidence, feedback=args.feedback, citation=args.citation, action=args.action)
        print(args.session)
    elif args.command == "session-status":
        update_status(args.session, args.status)
        print(args.session)
    elif args.command == "reindex":
        print(json.dumps(rebuild_manifest(_workspace(str(args.workspace))), indent=2))
    elif args.command == "query":
        print(json.dumps(query_manifest(_workspace(str(args.workspace)), args.text, source_id=args.source, topic_id=args.topic, path_id=args.path, limit=args.limit), indent=2))
    elif args.command == "progress":
        print(json.dumps(summarize(_workspace(str(args.workspace)), topic_id=args.topic), indent=2))
    elif args.command == "dashboard":
        print(json.dumps(generate_dashboard(_workspace(str(args.workspace)), output=args.output), indent=2))
    elif args.command == "validate-citation":
        print(json.dumps(validate_citation(_workspace(str(args.workspace)), args.text), indent=2))
    elif args.command == "tutor-question":
        tutor = _tutor(args)
        print(json.dumps(tutor.generate_question(args.objective, mode=args.mode, source_id=args.source, topic_id=args.topic, limit=args.limit), indent=2))
    elif args.command == "tutor-evaluate":
        tutor = _tutor(args)
        print(json.dumps(tutor.evaluate_answer(args.question, args.answer, objective=args.objective, confidence=args.confidence, source_id=args.source, topic_id=args.topic, limit=args.limit), indent=2))
    elif args.command == "tutor-session-question":
        session = TutorSession(_workspace(str(args.workspace)), _tutor(args))
        print(json.dumps(session.next_question(args.session, source_id=args.source, topic_id=args.topic), indent=2))
    elif args.command == "tutor-session-answer":
        session = TutorSession(_workspace(str(args.workspace)), _tutor(args))
        print(json.dumps(session.submit_answer(args.session, args.answer, confidence=args.confidence, source_id=args.source, topic_id=args.topic), indent=2))
    elif args.command == "tutor-session-hint":
        print(json.dumps({"hint": TutorSession(_workspace(str(args.workspace)), None).hint(args.session)}, indent=2))
    elif args.command == "tutor-session-update":
        if not args.mode and not args.difficulty:
            raise SystemExit("provide --mode and/or --difficulty")
        TutorSession(_workspace(str(args.workspace)), None).set_mode_or_difficulty(args.session, mode=args.mode, difficulty=args.difficulty)
        print(args.session)
    elif args.command == "vector-status":
        print(json.dumps(vector_status(_workspace(str(args.workspace))), indent=2))
    elif args.command == "vector-reindex":
        if not milvus_available():
            print(json.dumps(vector_status(_workspace(str(args.workspace))), indent=2))
        else:
            index = MilvusLiteIndex(_workspace(str(args.workspace)))
            print(json.dumps(index.incremental(_embedding_provider(args)) if args.incremental else index.rebuild(_embedding_provider(args)), indent=2))
    elif args.command == "vector-query":
        if not milvus_available():
            print(json.dumps(vector_status(_workspace(str(args.workspace))), indent=2))
        else:
            index = MilvusLiteIndex(_workspace(str(args.workspace)))
            print(json.dumps(index.query(_embedding_provider(args), args.text, source_id=args.source, topic_id=args.topic, path_id=args.path, limit=args.limit), indent=2))
    if args.command in _CANONICAL_MUTATION_COMMANDS and not (args.command == "remove" and not args.confirm):
        _refresh_dashboard_after_mutation(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
