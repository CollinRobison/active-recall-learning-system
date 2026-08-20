"""Safe, dependency-light source ingestion with provenance and optional OCR."""
from __future__ import annotations

import fnmatch
import hashlib
import html.parser
import re
import shutil
import subprocess
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .frontmatter import parse, render
from .workspace import append_catalog, atomic_write, iter_records, now_iso, sha256_file, slugify

SUPPORTED = {".md", ".markdown", ".txt", ".text", ".pdf", ".docx", ".epub", ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".h", ".cpp", ".hpp", ".go", ".rs", ".rb", ".php", ".cs", ".sh", ".yaml", ".yml", ".json", ".toml", ".html", ".css"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
REPOSITORY_EXCLUDED = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".tox", ".mypy_cache", ".pytest_cache"}
SECRET_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore"}


def _extract_zip_xml(path: Path, member: str) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read(member))
    return "\n".join(part.strip() for part in root.itertext() if part.strip()) + "\n"


def _extract_docx(path: Path) -> tuple[str, list[str]]:
    return _extract_zip_xml(path, "word/document.xml"), []


def _html_text(value: str) -> str:
    parser = _HTMLTextExtractor(); parser.feed(value); return parser.text()


def _extract_epub(path: Path) -> tuple[str, list[str]]:
    with zipfile.ZipFile(path) as archive:
        names = sorted(name for name in archive.namelist() if name.lower().endswith((".xhtml", ".html", ".htm")))
        text = "\n".join(_html_text(archive.read(name).decode("utf-8", errors="replace")) for name in names)
    return text, []


def _ignore_patterns(workspace: Path) -> list[str]:
    ignore = workspace / ".learningignore"
    if not ignore.exists(): return []
    return [line.strip() for line in ignore.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]


def _ignored(path: Path, workspace: Path, patterns: list[str]) -> bool:
    try: relative = path.relative_to(workspace).as_posix()
    except ValueError: relative = path.as_posix()
    return any(fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(relative, pattern) for pattern in patterns)


def _unsafe_repository_path(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in REPOSITORY_EXCLUDED for part in relative.parts): return True
    return path.name in SECRET_NAMES or path.suffix.lower() in SECRET_SUFFIXES or path.name.startswith(".env.")


class _HTMLTextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.parts: list[str] = []; self.heading_level: int | None = None
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}: self.heading_level = int(tag[1])
        elif tag in {"p", "li", "br", "div"}: self.parts.append("\n")
    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}: self.parts.append("\n"); self.heading_level = None
    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value: return
        if self.heading_level: self.parts.append(f"{'#' * self.heading_level} {value}\n"); self.heading_level = None
        else: self.parts.append(value + " ")
    def text(self) -> str: return re.sub(r"\n{3,}", "\n\n", "".join(self.parts)).strip() + "\n"


def _ocr_image(path: Path, mode: str) -> tuple[str, list[str]]:
    if mode == "never": return "", [f"OCR skipped for image {path.name} (--ocr never)"]
    executable = shutil.which("tesseract")
    if not executable:
        message = "OCR unavailable: optional 'tesseract' executable is not installed"
        if mode == "required": raise RuntimeError(message)
        return "", [message]
    result = subprocess.run([executable, str(path), "stdout"], capture_output=True, text=True, timeout=120, check=False)
    if result.returncode:
        message = f"OCR failed for {path.name}: {result.stderr.strip() or 'tesseract returned nonzero'}"
        if mode == "required": raise RuntimeError(message)
        return "", [message]
    return result.stdout, [f"OCR extracted text from image {path.name}"]


def _extract_pdf(path: Path, ocr: str) -> tuple[str, list[str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc: raise RuntimeError("PDF ingestion requires optional dependency 'pypdf'") from exc
    pages: list[str] = []; warnings: list[str] = []
    for number, page in enumerate(PdfReader(str(path)).pages, 1):
        text = page.extract_text() or ""
        if not text.strip():
            message = f"page {number} contains no extractable text; PDF page OCR requires an external renderer and was not attempted"
            if ocr == "required": raise RuntimeError(message)
            warnings.append(message)
        pages.append(f"\n<!-- page: {number} -->\n\n{text.rstrip()}\n")
    return "".join(pages), warnings


def _extract_url(url: str) -> tuple[str, list[str], str]:
    request = urllib.request.Request(url, headers={"User-Agent": "portable-active-recall/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read(); content_type = response.headers.get_content_type()
    if content_type == "text/html": return _html_text(raw.decode("utf-8", errors="replace")), [], "webpage"
    return raw.decode("utf-8", errors="replace"), [f"content type {content_type} treated as text"], content_type


def _headings(text: str) -> list[dict[str, Any]]:
    return [{"level": len(match.group(1)), "title": match.group(2), "line": number} for number, line in enumerate(text.splitlines(), 1) if (match := re.match(r"^(#{1,6})\s+(.+?)\s*$", line))]


def _source_id(title: str, checksum: str, when: datetime) -> str:
    return f"source-{when.strftime('%Y%m%d')}-{slugify(title)[:40]}-{checksum[-8:]}"


def _conflicts(workspace: Path, *, location: str, checksum: str, title: str) -> list[str]:
    matches = []
    for _, metadata, _ in iter_records(workspace, {"source"}):
        if metadata.get("original_location") == location or metadata.get("checksum") == checksum:
            matches.append(str(metadata.get("id")))
    if not matches: return []
    conflict_id = f"source-conflict-{slugify(title)}-{checksum[-8:]}"
    path = workspace / "conflicts" / "open" / f"{conflict_id}.md"
    if not path.exists():
        metadata = {"id": conflict_id, "kind": "source-conflict", "status": "open", "created_at": now_iso(), "candidate_source_ids": matches, "incoming_location": location, "incoming_checksum": checksum}
        atomic_write(path, render(metadata, f"# Source conflict: {title}\n\n## Why confirmation is needed\n\nThe incoming source has the same original location or checksum as an existing source. Confirm whether it replaces, duplicates, or should remain separate from: {', '.join(matches)}.\n"))
    return [conflict_id]


def ingest_local(path: Path, workspace: Path, *, title: str | None = None, source_type: str | None = None, ocr: str = "auto", allow_repository: bool = False) -> dict[str, Any]:
    """Ingest a local source. Repository traversal requires explicit opt-in and never follows symlinks."""
    if ocr not in {"auto", "never", "required"}: raise ValueError("ocr must be auto, never, or required")
    path = path.expanduser().resolve(); workspace = workspace.expanduser().resolve()
    if not path.exists(): raise FileNotFoundError(path)
    patterns = _ignore_patterns(workspace)
    if _ignored(path, workspace, patterns): raise ValueError(f"input is excluded by .learningignore: {path}")
    is_repository = path.is_dir() and (path / ".git").exists()
    if is_repository and not allow_repository: raise ValueError("repository ingestion requires explicit allow_repository=True")
    if path.is_file(): files = [path]
    else: files = sorted(p for p in path.rglob("*") if p.is_file() and not p.is_symlink() and p.suffix.lower() in SUPPORTED | IMAGE_SUFFIXES and not _ignored(p, workspace, patterns) and (not is_repository or not _unsafe_repository_path(p, path)))
    if not files: raise ValueError("no supported safe source files found")
    if path.is_file() and path.suffix.lower() not in SUPPORTED | IMAGE_SUFFIXES: raise ValueError(f"unsupported local source type: {path.suffix}")
    chunks: list[str] = []; warnings: list[str] = []; checksums: list[str] = []
    for file in files:
        checksums.append(sha256_file(file)); suffix = file.suffix.lower()
        if suffix == ".pdf": text, notes = _extract_pdf(file, ocr)
        elif suffix == ".docx": text, notes = _extract_docx(file)
        elif suffix == ".epub": text, notes = _extract_epub(file)
        elif suffix in IMAGE_SUFFIXES: text, notes = _ocr_image(file, ocr)
        else: text, notes = file.read_text(encoding="utf-8", errors="replace"), []
        warnings.extend(notes)
        if not text.strip(): warnings.append(f"empty or unextracted file: {file}"); continue
        relative = file.relative_to(path).as_posix() if path.is_dir() else file.name
        chunks.append((f"\n\n<!-- source-file: {relative} -->\n\n" if len(files) > 1 else "") + text.rstrip() + "\n")
    combined = "".join(chunks); checksum = checksums[0] if len(checksums) == 1 else f"sha256:{hashlib.sha256(''.join(checksums).encode()).hexdigest()}"
    display_title = title or (path.stem.replace("-", " ").replace("_", " ").title() if path.is_file() else path.name)
    source_id = _source_id(display_title, checksum, datetime.now(timezone.utc)); source_dir = workspace / "sources" / source_id
    if source_dir.exists(): raise FileExistsError(f"source already exists: {source_dir}")
    conflict_ids = _conflicts(workspace, location=str(path), checksum=checksum, title=display_title)
    headings = _headings(combined)
    metadata: dict[str, Any] = {"id": source_id, "kind": "source", "title": display_title, "author": "Unknown", "source_type": source_type or (path.suffix.lower().lstrip(".") if path.is_file() else ("repository" if is_repository else "folder")), "original_location": str(path), "checksum": checksum, "ingested_at": now_iso(), "updated_at": now_iso(), "authority": "unverified", "topic_ids": [], "path_ids": [], "extraction_status": "complete" if combined else "partial", "index_status": "disabled", "metadata_confirmation": "required", "metadata_provenance": {"title": "user-supplied" if title else "derived-from-path", "author": "default-unknown", "source_type": "detected", "original_location": "local-filesystem", "checksum": "sha256-computed"}, "warnings": warnings, "conflict_ids": conflict_ids}
    structure = "# Structure\n\n" + ("\n".join(f"- L{x['line']}: {'#' * x['level']} {x['title']}" for x in headings) or "No Markdown headings detected.") + "\n"
    atomic_write(source_dir / "source.md", render(metadata, f"# {display_title}\n\n## Why this source is being used\n\nAdd the learner's purpose.\n\n## Extraction notes\n\nImported without copying the original file. Metadata confirmation is required before treating derived fields as authoritative.\n"))
    atomic_write(source_dir / "extracted.md", f"# {display_title}\n\n{combined}"); atomic_write(source_dir / "structure.md", structure)
    append_catalog(workspace, "sources.md", "Sources", [f"- **{display_title}** (`{source_id}`) — `{source_dir.relative_to(workspace)}`"])
    return {"status": metadata["extraction_status"], "source_id": source_id, "files": [str(p.relative_to(workspace)) for p in source_dir.glob("*.md")], "warnings": warnings, "checksum": checksum, "metadata_confirmation": "required", "conflict_ids": conflict_ids}


def ingest_url(url: str, workspace: Path, *, title: str | None = None) -> dict[str, Any]:
    text, warnings, detected_type = _extract_url(url); workspace = workspace.expanduser().resolve(); checksum = f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"; display_title = title or url.rstrip("/").rsplit("/", 1)[-1] or "web source"; source_id = _source_id(display_title, checksum, datetime.now(timezone.utc)); source_dir = workspace / "sources" / source_id
    if source_dir.exists(): raise FileExistsError(f"source already exists: {source_dir}")
    conflict_ids = _conflicts(workspace, location=url, checksum=checksum, title=display_title)
    metadata: dict[str, Any] = {"id": source_id, "kind": "source", "title": display_title, "author": "Unknown", "source_type": "webpage", "original_location": url, "checksum": checksum, "ingested_at": now_iso(), "updated_at": now_iso(), "authority": "unverified", "topic_ids": [], "path_ids": [], "extraction_status": "complete" if text.strip() else "partial", "index_status": "disabled", "metadata_confirmation": "required", "metadata_provenance": {"title": "user-supplied" if title else "derived-from-url", "author": "default-unknown", "source_type": "http-content-type", "original_location": "user-approved-network-fetch", "checksum": "sha256-computed"}, "warnings": warnings, "conflict_ids": conflict_ids}
    atomic_write(source_dir / "source.md", render(metadata, f"# {display_title}\n\n## Why this source is being used\n\nAdd the learner's purpose.\n")); atomic_write(source_dir / "extracted.md", f"# {display_title}\n\n{text}"); atomic_write(source_dir / "structure.md", "# Structure\n\n" + ("\n".join(f"- L{x['line']}: {'#' * x['level']} {x['title']}" for x in _headings(text)) or "No headings detected.") + "\n"); append_catalog(workspace, "sources.md", "Sources", [f"- **{display_title}** (`{source_id}`) — `{source_dir.relative_to(workspace)}`"])
    return {"status": metadata["extraction_status"], "source_id": source_id, "warnings": warnings, "checksum": checksum, "source_type": detected_type, "metadata_confirmation": "required", "conflict_ids": conflict_ids}


def confirm_source_metadata(workspace: Path, source_id: str, *, authority: str | None = None) -> dict[str, Any]:
    for path, metadata, body in iter_records(workspace, {"source"}):
        if metadata.get("id") == source_id:
            metadata["metadata_confirmation"] = "confirmed"; metadata["metadata_confirmed_at"] = now_iso()
            if authority: metadata["authority"] = authority
            atomic_write(path, render(metadata, body)); return {"status": "confirmed", "source_id": source_id, "authority": metadata["authority"]}
    raise ValueError(f"unknown source: {source_id}")
