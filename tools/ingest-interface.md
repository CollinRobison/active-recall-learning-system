# Ingestion interface

A future helper may expose:

```text
learning-ingest INPUT --workspace WORKSPACE [--type TYPE] [--ocr auto|always|never] [--dry-run]
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

The agent remains responsible for user confirmation, topic/path associations, and catalog updates. Do not copy the original input unless explicitly requested.
