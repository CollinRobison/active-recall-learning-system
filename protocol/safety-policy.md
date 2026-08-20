# Safety and file policy

## Privacy defaults

- Local-first; no telemetry is required.
- Ask before sending source material, answers, or metadata to a cloud service or web search.
- Never write API keys, credentials, private keys, cookies, tokens, `.env` files, or unrelated secrets into learning records.
- Do not index secrets or unrelated directories. Respect `.learningignore`.
- Label web-derived and cloud-generated content as external.

## Confirmation boundaries

Low-risk generated session, confusion, review, and progress records may be written automatically when configured. Require confirmation before changing canonical notes, source authority, learning paths, prerequisites, deleting records, archiving sources, or copying original documents.

## Recovery

Before bulk ingestion or reorganization, recommend a Git commit or backup. Show a summary of paths and records changed. Avoid destructive rewrites. Preserve superseded records where practical. If an update fails, keep the prior file and write a diagnostic rather than leaving a partial record.

## Source handling

Store original path/URL, checksum when available, extraction warnings, and provenance. Do not copy original books/PDFs by default. Keep extracted Markdown authoritative for retrieval, while retaining enough location metadata to audit citations.

## Failure behavior

If indexing, OCR, extraction, or retrieval fails, continue with Markdown and direct file search where possible. Report degraded capability explicitly; never claim an index is current when it is unavailable or stale.
