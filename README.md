# Portable Active Recall Learning System

A harness-agnostic, Markdown-first learning protocol for Pi, Claude Code, Codex CLI, Gemini CLI, Cursor, OpenCode, Copilot CLI, Hermes, and compatible agents.

## Status

The protocol package and runtime are implemented. The runtime covers workspace initialization, safe local Markdown/text/PDF/DOCX/EPUB/code ingestion (PDF support uses optional `pypdf`), optional local image OCR using `tesseract`, approved URL ingestion, metadata provenance/confirmation and duplicate-source conflict records, session persistence, confusion merging, transparent review scheduling, exact source-location citation checks, lexical indexing, progress summaries, optional embeddings/Milvus Lite, and model-driven source-grounded tutoring.

## Design commitments

- Markdown files are the source of truth; indexes are rebuildable caches.
- Study behavior is source-grounded and citations are required.
- State is explicit and resumable; sessions save incrementally.
- Canonical notes, metadata, paths, and authority changes require confirmation.
- The core does not require a model provider, hosted service, web server, or database.
- External research is opt-in and must be labeled as external.

## Package map

- [`protocol/`](protocol/): rules shared by every harness.
- [`skills/`](skills/): portable procedures for common user intents.
- [`prompts/`](prompts/): model-facing contracts and structured output requirements.
- [`schemas/`](schemas/): Markdown record templates.
- [`adapters/`](adapters/): thin harness-specific invocation notes.
- [`tools/`](tools/): optional ingestion and index interfaces.
- [`PLAN.md`](PLAN.md): the originating design and implementation plan.

## Quick start

1. Install in an environment with Python 3.9+: `python -m pip install -e .`
2. Create a workspace: `learning init ~/Learning`
3. Add a local source: `learning ingest ./notes.md --workspace ~/Learning`
4. Rebuild the fallback index: `learning reindex ~/Learning`
5. Search it: `learning query ~/Learning "concept"`
6. Start a persisted model-driven session: `learning session-start ~/Learning --scope-id topic-example`, then call `learning tutor-session-question ~/Learning SESSION_PATH --provider-command 'my-model-adapter'` and `learning tutor-session-answer ~/Learning SESSION_PATH 'my answer' --provider-command 'my-model-adapter'`.
7. Create a durable curriculum: `learning topic-create ~/Learning "Book foundations" --source source-... --objective "Explain the central ideas"`, then `learning path-create ~/Learning "My book path" --topic topic-book-foundations --source source-...`; ask `learning recommend ~/Learning` for the ranked next step. Preview a canonical topic change with `learning topic-edit ~/Learning topic-book-foundations --status completed`, then add `--confirm` to apply it.
8. Inspect evidence: `learning progress ~/Learning`.
9. Build the optional vector index: `python -m pip install -e '.[milvus,local-embeddings]'`, then `learning vector-reindex ~/Learning --embedding-provider sentence-transformers`. Full rebuilds publish a new generation only after it is built; use `--incremental` to upsert changed chunks in the current published generation.
10. Generate/evaluate model-driven turns through a local JSON adapter:
   `learning tutor-question ~/Learning --provider-command 'my-model-adapter' "explain variables"`.

The Markdown skills remain the behavior contract for an agent tutor. See [`skills/study-session.md`](skills/study-session.md), [`skills/source-ingest.md`](skills/source-ingest.md), [`tools/index-interface.md`](tools/index-interface.md), and [`tools/model-interface.md`](tools/model-interface.md). URL ingestion requires explicit `--allow-network`; Git repositories require `--allow-repository` and exclude VCS, dependency/cache folders, symlinks, and common secret files. Image OCR is safe to degrade when `tesseract` is absent (`--ocr auto`); `--ocr required` fails instead. Inspect then confirm derived source fields with `learning source-confirm WORKSPACE SOURCE_ID`. Vector queries accept `--source`, `--topic`, and `--path` filters. PDF, Milvus, OCR, and local embedding providers are optional extras.

## Workspace

The active workspace is user-configured and should not be confused with this protocol repository. Its expected layout is documented in [`protocol/data-conventions.md`](protocol/data-conventions.md). Never copy source PDFs or books into the workspace unless explicitly requested.

## Safety

Do not place credentials, private keys, tokens, unrelated secrets, or raw environment files in the workspace. Configure an ignore file before ingestion. See [`protocol/safety-policy.md`](protocol/safety-policy.md).

## Validation

Run `PYTHONPATH=src python -m unittest discover -s tests -v`. The deterministic suite covers frontmatter, non-destructive initialization, safe ingestion and provenance/conflict records, sessions, confusion merging, scheduling, exact heading/page/line citation validation, a hand-authored golden learning/evaluation case, lexical manifest retrieval, generation-safe/incremental vector behavior through a fake Milvus client (no `pymilvus` required), embedding/model command contracts, an in-process OpenAI-compatible HTTP provider integration, and tutor evidence validation. Each listed harness has concrete installation and invocation instructions under [`adapters/`](adapters/); live vendor-harness acceptance requires those harnesses and credentials to be installed locally.
