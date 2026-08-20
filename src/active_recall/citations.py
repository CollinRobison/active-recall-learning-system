"""Citation validation against source records."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .frontmatter import parse


def source_ids_in(citation: str) -> set[str]:
    return set(re.findall(r"\bsource-[a-z0-9][a-z0-9-]*\b", citation.lower()))


def validate_citation(workspace: Path, citation: str) -> dict[str, Any]:
    """Validate source identity and require a non-empty location marker."""
    ids = source_ids_in(citation)
    existing: set[str] = set()
    for path in (workspace / "sources").glob("*/source.md") if (workspace / "sources").exists() else ():
        metadata, _ = parse(path.read_text(encoding="utf-8"))
        if metadata.get("id"):
            existing.add(str(metadata["id"]).lower())
    missing = sorted(ids - existing)
    has_location = bool(re.search(r"(?:page|chapter|section|line|url|location)\s*[:#]?\s*\S+", citation, re.I))
    return {
        "valid": bool(ids) and not missing and has_location,
        "source_ids": sorted(ids),
        "missing_source_ids": missing,
        "has_location": has_location,
        "citation_status": "verified" if bool(ids) and not missing and has_location else "unverified",
    }
