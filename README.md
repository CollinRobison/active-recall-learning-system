# Portable Active Recall Learning System

A harness-agnostic, Markdown-first learning protocol for Pi, Claude Code, Codex CLI, Gemini CLI, Cursor, OpenCode, Copilot CLI, Hermes, and compatible agents.

## Status

The protocol package and runtime are implemented. The runtime covers workspace initialization, local Markdown/text/PDF ingestion (PDF support uses optional `pypdf`), approved URL ingestion, session persistence, confusion merging, transparent review scheduling, citation checks, lexical indexing, progress summaries, optional embeddings/Milvus Lite, and model-driven source-grounded tutoring.

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
6. Start and persist a session:
   `learning session-start ~/Learning --scope-id topic-example`, then use `learning session-turn ...`.
7. Inspect evidence: `learning progress ~/Learning`.
8. Build the optional vector index: `python -m pip install -e '.[milvus,local-embeddings]'`, then `learning vector-reindex ~/Learning --embedding-provider sentence-transformers`.
9. Generate/evaluate model-driven turns through a local JSON adapter:
   `learning tutor-question ~/Learning --provider-command 'my-model-adapter' "explain variables"`.

The Markdown skills remain the behavior contract for an agent tutor. See [`skills/study-session.md`](skills/study-session.md), [`skills/source-ingest.md`](skills/source-ingest.md), [`tools/index-interface.md`](tools/index-interface.md), and [`tools/model-interface.md`](tools/model-interface.md). URL ingestion requires explicit `--allow-network`; PDF, Milvus, and local embedding providers are optional extras.

## Workspace

The active workspace is user-configured and should not be confused with this protocol repository. Its expected layout is documented in [`protocol/data-conventions.md`](protocol/data-conventions.md). Never copy source PDFs or books into the workspace unless explicitly requested.

## Safety

Do not place credentials, private keys, tokens, unrelated secrets, or raw environment files in the workspace. Configure an ignore file before ingestion. See [`protocol/safety-policy.md`](protocol/safety-policy.md).

## Validation

Run `PYTHONPATH=src python -m unittest discover -s tests -v`. The deterministic suite covers frontmatter, non-destructive initialization, ingestion, sessions, confusion merging, scheduling, citation checks, lexical manifest retrieval, embedding/model command contracts, and tutor evidence validation.
