"""Workspace creation, record discovery, and safe file updates."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .frontmatter import parse, render

WORKSPACE_DIRS = (
    "catalog",
    "topics",
    "paths",
    "sources",
    "sessions",
    "confusion/open",
    "confusion/resolved",
    "reviews",
    "progress/snapshots",
    "inbox",
    "index/milvus",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "untitled"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def init_workspace(root: Path, *, overwrite_empty_files: bool = False) -> list[Path]:
    """Create the documented workspace and return paths created/updated."""
    root = root.expanduser().resolve()
    created: list[Path] = []
    for directory in WORKSPACE_DIRS:
        path = root / directory
        if not path.exists():
            path.mkdir(parents=True)
            created.append(path)
    starters = {
        "README.md": "# Learning workspace\n\nManaged by the portable active recall protocol.\n",
        "workspace.md": "# Workspace\n\nConfigure this workspace and its study goals here.\n",
        "config.md": "# Configuration\n\n- Default mode: active-recall\n- Default questions: 5\n- Index: disabled\n",
        ".learningignore": "# One glob per line; secrets and unrelated directories should be excluded.\n.env\n*.pem\n*.key\n",
        "catalog/topics.md": "# Topics\n\nNo topics yet.\n",
        "catalog/sources.md": "# Sources\n\nNo sources yet.\n",
        "catalog/paths.md": "# Learning paths\n\nNo paths yet.\n",
        "catalog/study-options.md": "# Study options\n\nSee the shared protocol for available modes.\n",
        "reviews/due.md": "# Due reviews\n\nNo reviews due.\n",
        "reviews/history.md": "# Review history\n",
        "progress/overall.md": "# Overall progress\n\nNo study evidence yet.\n",
        "inbox/README.md": "# Inbox\n\nPlace sources here only when you intend to ingest them.\n",
        "index/README.md": "# Index\n\nDerived retrieval cache; Markdown remains authoritative.\n",
        "index/manifest.jsonl": "",
    }
    for relative, content in starters.items():
        path = root / relative
        if not path.exists() or (overwrite_empty_files and not path.read_text(encoding="utf-8")):
            atomic_write(path, content)
            created.append(path)
    return created


def iter_records(root: Path, kinds: Iterable[str] | None = None) -> Iterable[tuple[Path, dict[str, Any], str]]:
    """Yield Markdown records with valid frontmatter."""
    wanted = set(kinds or ())
    for path in root.rglob("*.md"):
        if "/.git/" in path.as_posix():
            continue
        try:
            metadata, body = parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if metadata and (not wanted or metadata.get("kind") in wanted):
            yield path, metadata, body


def append_catalog(root: Path, catalog_name: str, title: str, lines: list[str]) -> None:
    path = root / "catalog" / catalog_name
    existing = path.read_text(encoding="utf-8") if path.exists() else f"# {title}\n"
    block = "\n" + "\n".join(lines).rstrip() + "\n"
    atomic_write(path, existing.rstrip() + "\n" + block)
