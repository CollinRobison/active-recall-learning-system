"""Dependency-free Markdown/text ingestion with line and heading locations."""

from __future__ import annotations

import fnmatch
import hashlib
import html.parser
import re
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .frontmatter import render
from .workspace import append_catalog, atomic_write, sha256_file, slugify, now_iso

SUPPORTED = {".md", ".markdown", ".txt", ".text", ".pdf", ".docx", ".epub"}


def _extract_zip_xml(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read(member))
    return "\n".join(part.strip() for part in root.itertext() if part.strip()) + "\n"


def _extract_docx(path: Path) -> tuple[str, list[str]]:
    return _extract_zip_xml(path, "word/document.xml"), []


def _extract_epub(path: Path) -> tuple[str, list[str]]:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith((".xhtml", ".html", ".htm"))]
        text = "\n".join(_HTMLTextExtractor_text(archive.read(name).decode("utf-8", errors="replace")) for name in names)
    return text, []


def _HTMLTextExtractor_text(value: str) -> str:
    parser = _HTMLTextExtractor(); parser.feed(value); return parser.text()



def _ignore_patterns(workspace: Path) -> list[str]:
    ignore = workspace / ".learningignore"
    if not ignore.exists():
        return []
    return [line.strip() for line in ignore.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]


def _ignored(path: Path, workspace: Path, patterns: list[str]) -> bool:
    relative = path.as_posix()
    try:
        relative = path.relative_to(workspace).as_posix()
    except ValueError:
        pass
    return any(fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(relative, pattern) for pattern in patterns)


class _HTMLTextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.heading_level: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_level = int(tag[1])
        elif tag in {"p", "li", "br", "div"}:
            self.parts.append("\\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\\n")
            self.heading_level = None

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value:
            return
        if self.heading_level:
            self.parts.append(f"{'#' * self.heading_level} {value}\\n")
            self.heading_level = None
        else:
            self.parts.append(value + " ")

    def text(self) -> str:
        return re.sub(r"\\n{3,}", "\\n\\n", "".join(self.parts)).strip() + "\\n"


def _extract_pdf(path: Path) -> tuple[str, list[str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF ingestion requires optional dependency 'pypdf'") from exc
    reader = PdfReader(str(path))
    pages: list[str] = []
    warnings: list[str] = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if not text.strip():
            warnings.append(f"page {number} contains no extractable text; OCR may be required")
        pages.append(f"\\n<!-- page: {number} -->\\n\\n{text.rstrip()}\\n")
    return "".join(pages), warnings


def _extract_url(url: str) -> tuple[str, list[str], str]:
    request = urllib.request.Request(url, headers={"User-Agent": "portable-active-recall/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read()
        content_type = response.headers.get_content_type()
    if content_type == "text/html":
        parser = _HTMLTextExtractor()
        parser.feed(raw.decode("utf-8", errors="replace"))
        return parser.text(), [], "webpage"
    return raw.decode("utf-8", errors="replace"), [f"content type {content_type} treated as text"], content_type


def _headings(text: str) -> list[dict[str, Any]]:
    result = []
    for line_number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            result.append({"level": len(match.group(1)), "title": match.group(2), "line": line_number})
    return result


def _source_id(title: str, checksum: str, when: datetime) -> str:
    return f"source-{when.strftime('%Y%m%d')}-{slugify(title)[:40]}-{checksum[-8:]}"


def ingest_local(path: Path, workspace: Path, *, title: str | None = None, source_type: str | None = None) -> dict[str, Any]:
    """Ingest one local Markdown/text/PDF file or a folder of such files."""
    path = path.expanduser().resolve()
    workspace = workspace.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    patterns = _ignore_patterns(workspace)
    if _ignored(path, workspace, patterns):
        raise ValueError(f"input is excluded by .learningignore: {path}")
    files = [path] if path.is_file() else sorted(
        p for p in path.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED and not _ignored(p, workspace, patterns)
    )
    if not files:
        raise ValueError("no supported Markdown, text, or PDF files found")
    if path.is_file() and path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"unsupported local source type: {path.suffix}")
    chunks = []
    warnings: list[str] = []
    checksums = []
    for file in files:
        checksums.append(sha256_file(file))
        if file.suffix.lower() == ".pdf":
            text, pdf_warnings = _extract_pdf(file)
            warnings.extend(pdf_warnings)
        elif file.suffix.lower() == ".docx":
            text, extracted_warnings = _extract_docx(file)
            warnings.extend(extracted_warnings)
        elif file.suffix.lower() == ".epub":
            text, extracted_warnings = _extract_epub(file)
            warnings.extend(extracted_warnings)
        else:
            text = file.read_text(encoding="utf-8")
        if not text.strip():
            warnings.append(f"empty file: {file}")
            continue
        relative = file.relative_to(path).as_posix() if path.is_dir() else file.name
        if len(files) > 1:
            chunks.append(f"\n\n<!-- source-file: {relative} -->\n\n{text.rstrip()}\n")
        else:
            chunks.append(text.rstrip() + "\n")
    combined = "".join(chunks)
    current = datetime.now(timezone.utc)
    if len(checksums) == 1:
        checksum = checksums[0]
    else:
        digest = hashlib.sha256("".join(checksums).encode("utf-8")).hexdigest()
        checksum = f"sha256:{digest}"
    display_title = title or (path.stem.replace("-", " ").replace("_", " ").title() if path.is_file() else path.name)
    source_id = _source_id(display_title, checksum, current)
    source_dir = workspace / "sources" / source_id
    if source_dir.exists():
        raise FileExistsError(f"source already exists: {source_dir}")
    headings = _headings(combined)
    metadata: dict[str, Any] = {
        "id": source_id,
        "kind": "source",
        "title": display_title,
        "author": "Unknown",
        "source_type": source_type or (path.suffix.lower().lstrip(".") if path.is_file() else ("repository" if (path / ".git").exists() else "folder")),
        "original_location": str(path),
        "checksum": checksum,
        "ingested_at": now_iso(),
        "updated_at": now_iso(),
        "authority": "unverified",
        "topic_ids": [],
        "path_ids": [],
        "extraction_status": "complete" if combined else "partial",
        "index_status": "disabled",
        "metadata_confidence": {"title": "high" if title else "medium"},
        "warnings": warnings,
    }
    structure = "# Structure\n\n" + ("\n".join(f"- L{item['line']}: {'#' * item['level']} {item['title']}" for item in headings) or "No Markdown headings detected.") + "\n"
    atomic_write(source_dir / "source.md", render(metadata, f"# {display_title}\n\n## Why this source is being used\n\nAdd the learner's purpose.\n\n## Extraction notes\n\nImported without copying the original file.\n"))
    atomic_write(source_dir / "extracted.md", f"# {display_title}\n\n{combined}")
    atomic_write(source_dir / "structure.md", structure)
    append_catalog(workspace, "sources.md", "Sources", [f"- **{display_title}** (`{source_id}`) — `{source_dir.relative_to(workspace)}`"])
    return {"status": metadata["extraction_status"], "source_id": source_id, "files": [str(p.relative_to(workspace)) for p in source_dir.glob("*.md")], "warnings": warnings, "checksum": checksum}


def ingest_url(url: str, workspace: Path, *, title: str | None = None) -> dict[str, Any]:
    """Fetch and ingest a URL; callers must make network permission explicit."""
    text, warnings, detected_type = _extract_url(url)
    current = datetime.now(timezone.utc)
    checksum = f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"
    display_title = title or url.rstrip("/").rsplit("/", 1)[-1] or "web source"
    source_id = _source_id(display_title, checksum, current)
    source_dir = workspace.expanduser().resolve() / "sources" / source_id
    if source_dir.exists():
        raise FileExistsError(f"source already exists: {source_dir}")
    metadata: dict[str, Any] = {
        "id": source_id, "kind": "source", "title": display_title, "author": "Unknown",
        "source_type": "webpage", "original_location": url, "checksum": checksum,
        "ingested_at": now_iso(), "updated_at": now_iso(), "authority": "unverified",
        "topic_ids": [], "path_ids": [], "extraction_status": "complete" if text.strip() else "partial",
        "index_status": "disabled", "metadata_confidence": {"title": "medium"}, "warnings": warnings,
    }
    atomic_write(source_dir / "source.md", render(metadata, f"# {display_title}\n\n## Why this source is being used\n\nAdd the learner's purpose.\n"))
    atomic_write(source_dir / "extracted.md", f"# {display_title}\n\n{text}")
    atomic_write(source_dir / "structure.md", "# Structure\n\n" + ("\\n".join(f"- L{x['line']}: {'#' * x['level']} {x['title']}" for x in _headings(text)) or "No headings detected.") + "\\n")
    append_catalog(workspace, "sources.md", "Sources", [f"- **{display_title}** (`{source_id}`) — `{source_dir.relative_to(workspace)}`"])
    return {"status": metadata["extraction_status"], "source_id": source_id, "files": [str(p.relative_to(workspace)) for p in source_dir.glob("*.md")], "warnings": warnings, "checksum": checksum, "source_type": detected_type}
