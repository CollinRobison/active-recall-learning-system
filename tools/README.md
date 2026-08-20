# Optional helper tools

The portable core works without helper tools. Add a small local utility only when extraction, OCR, embedding, or large-scale retrieval is unreliable through the harness.

Helpers must:

- accept explicit input/output paths;
- avoid credentials in arguments or records;
- return machine-readable status plus human-readable diagnostics;
- preserve source locations and provenance;
- fail without deleting Markdown source of truth;
- support a dry run where practical.

See [`ingest-interface.md`](ingest-interface.md) and [`index-interface.md`](index-interface.md).
