# Portable Active Recall Learning System

A harness-agnostic, Markdown-first learning protocol for Pi, Claude Code, Codex CLI, Gemini CLI, Cursor, OpenCode, Copilot CLI, Hermes, and compatible agents.

## Status

Phase 0 is implemented: protocol, record conventions, prompt contracts, portable skills, schemas, adapter guidance, and helper interfaces. Runtime helpers and automated tests are intentionally deferred until the Markdown workflow is validated.

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

1. Choose a workspace outside this repository, for example `~/Learning/`.
2. Invoke [`skills/workspace-init.md`](skills/workspace-init.md) and confirm the location.
3. Add a source with [`skills/source-ingest.md`](skills/source-ingest.md), or create a topic manually from [`schemas/topic.md`](schemas/topic.md).
4. Start [`skills/study-session.md`](skills/study-session.md) in active-recall or teach-back mode.
5. Save a session after every turn; review [`skills/progress.md`](skills/progress.md) and [`skills/confusion-review.md`](skills/confusion-review.md).
6. Add an index only when retrieval scale requires it; follow [`tools/index-interface.md`](tools/index-interface.md).

## Workspace

The active workspace is user-configured and should not be confused with this protocol repository. Its expected layout is documented in [`protocol/data-conventions.md`](protocol/data-conventions.md). Never copy source PDFs or books into the workspace unless explicitly requested.

## Safety

Do not place credentials, private keys, tokens, unrelated secrets, or raw environment files in the workspace. Configure an ignore file before ingestion. See [`protocol/safety-policy.md`](protocol/safety-policy.md).

## Validation

The documentation package is intentionally plain Markdown. A future implementation should add deterministic checks for frontmatter, IDs, citations, session transitions, scheduling, and index manifests before introducing model-dependent behavior.
