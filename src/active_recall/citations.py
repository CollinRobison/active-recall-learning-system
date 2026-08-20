"""Citation validation against ingested source records and exact extracted locations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .frontmatter import parse


_LOCATION = re.compile(r"\b(page|pages|chapter|section|line|lines|url|location)\s*[:#]?\s*(.+?)(?=\s*(?:[,;]|$))", re.I)


def source_ids_in(citation: str) -> set[str]:
    return set(re.findall(r"\bsource-[a-z0-9][a-z0-9-]*\b", citation.lower()))


def _source_directory(workspace: Path, source_id: str) -> Path | None:
    candidate = workspace / "sources" / source_id / "source.md"
    if candidate.exists():
        metadata, _ = parse(candidate.read_text(encoding="utf-8"))
        if str(metadata.get("id", "")).lower() == source_id:
            return candidate.parent
    return None


def _location_matches(source_dir: Path, location_type: str, value: str) -> tuple[bool, str]:
    """Check a claimed location against stable extraction markers or source metadata."""
    source_metadata, _ = parse((source_dir / "source.md").read_text(encoding="utf-8"))
    extracted_path = source_dir / "extracted.md"
    extracted = extracted_path.read_text(encoding="utf-8") if extracted_path.exists() else ""
    normalized = " ".join(value.split()).casefold()
    if location_type.lower() == "url":
        original = str(source_metadata.get("original_location", ""))
        return (normalized in original.casefold(), "original URL does not contain cited URL" if normalized not in original.casefold() else "")
    if location_type.lower() in {"page", "pages"}:
        pages = [int(number) for number in re.findall(r"\d+", value)]
        if not pages:
            return False, "page location has no page number"
        unavailable = [str(page) for page in pages if not re.search(rf"<!--\s*page:\s*{page}\s*-->", extracted, re.I)]
        return (not unavailable, f"page marker(s) not found: {', '.join(unavailable)}" if unavailable else "")
    if location_type.lower() in {"line", "lines"}:
        numbers = [int(number) for number in re.findall(r"\d+", value)]
        line_count = len(extracted.splitlines())
        if not numbers or any(number < 1 or number > line_count for number in numbers):
            return False, f"line location outside extracted text (1-{line_count})"
        return True, ""
    if location_type.lower() in {"section", "chapter"}:
        # A heading is the stable location for extracted Markdown; exact title matching avoids substring guesses.
        target = normalized.removeprefix("the ")
        headings = [" ".join(match.group(1).split()).casefold() for line in extracted.splitlines() if (match := re.match(r"^#{1,6}\s+(.+?)\s*$", line))]
        if target in headings:
            return True, ""
        return False, f"{location_type.lower()} heading not found in extracted text"
    # "location" accepts an exact non-empty excerpt only, not an unverified label.
    return (normalized in " ".join(extracted.split()).casefold(), "location text not found in extracted text")


def validate_citation(workspace: Path, citation: str) -> dict[str, Any]:
    """Validate source identity and that every stated location exists exactly in the source."""
    ids = source_ids_in(citation)
    location = _LOCATION.search(citation)
    location_type = location.group(1).lower() if location else None
    location_value = location.group(2).strip() if location else None
    missing: list[str] = []
    location_errors: dict[str, str] = {}
    for source_id in sorted(ids):
        source_dir = _source_directory(workspace, source_id)
        if source_dir is None:
            missing.append(source_id)
        elif location_type and location_value:
            valid, reason = _location_matches(source_dir, location_type, location_value)
            if not valid:
                location_errors[source_id] = reason
    valid = bool(ids) and bool(location) and not missing and not location_errors
    return {
        "valid": valid,
        "source_ids": sorted(ids),
        "missing_source_ids": missing,
        "has_location": bool(location),
        "location_type": location_type,
        "location": location_value,
        "location_errors": location_errors,
        "citation_status": "verified" if valid else "unverified",
    }
