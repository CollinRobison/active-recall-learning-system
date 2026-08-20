# Ingestion interface

A future helper may expose:

```text
learning ingest INPUT --workspace WORKSPACE [--type TYPE] [--ocr auto|never|required] [--docling auto|never|required]
```

## Contract

Input may be a file, folder, URL, repository, transcript, or image. The helper must identify type, checksum when possible, extract normalized Markdown and structure, preserve page/section/line markers, and return JSON like:

```json
{
  "status": "complete|partial|failed",
  "source_id": "source-example",
  "files": ["sources/source-example/source.md"],
  "metadata": {},
  "warnings": [],
  "checksum": "sha256:..."
}
```

### Optional Docling conversion

The dependency-free extractor is the default. For layout-sensitive PDFs, DOCX, HTML, or images, install `python -m pip install -e '.[docling]'` (Python 3.10+; Docling can require substantial model/runtime downloads) and request `--docling auto` or `--docling required`. `auto` records a warning and uses the built-in extractor if Docling is unavailable or conversion fails; `required` fails visibly. Successful source metadata records `extraction_engines: [docling]`; this describes provenance only and never replaces the canonical `extracted.md` record.

The agent remains responsible for user confirmation, topic/path associations, and catalog updates. Do not copy the original input unless explicitly requested.
