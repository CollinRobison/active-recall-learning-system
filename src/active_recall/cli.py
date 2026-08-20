"""Command-line entry point for the dependency-free workspace tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .citations import validate_citation
from .index import query_manifest, rebuild_manifest
from .ingest import ingest_local, ingest_url
from .progress import summarize
from .session import append_turn, start_session, update_status
from .workspace import init_workspace, iter_records


def _workspace(value: str) -> Path:
    return Path(value).expanduser().resolve()


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

    catalog = sub.add_parser("list", help="list available topics, sources, paths, and open confusion")
    catalog.add_argument("workspace", type=Path)

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

    citation = sub.add_parser("validate-citation", help="verify a citation refers to a known source")
    citation.add_argument("workspace", type=Path)
    citation.add_argument("text")
    return parser


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
            result = ingest_local(Path(args.input), _workspace(str(args.workspace)), title=args.title, source_type=args.source_type)
        print(json.dumps(result, indent=2))
    elif args.command == "list":
        records = []
        for path, metadata, _ in iter_records(_workspace(str(args.workspace))):
            if metadata.get("kind") in {"topic", "source", "path", "confusion-item"}:
                records.append({"id": metadata.get("id"), "kind": metadata.get("kind"), "status": metadata.get("status"), "path": str(path)})
        print(json.dumps(sorted(records, key=lambda item: (item["kind"], item["id"] or "")), indent=2))
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
    elif args.command == "validate-citation":
        print(json.dumps(validate_citation(_workspace(str(args.workspace)), args.text), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
