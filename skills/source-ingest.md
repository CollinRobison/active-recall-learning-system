# Skill: source-ingest

## Purpose
Turn a local file, folder, URL, repository, transcript, image, or inbox item into auditable Markdown source records.

## Procedure
1. Confirm input and `.learningignore`; never ingest secrets or unrelated directories.
2. Compute a checksum where possible and identify source type.
3. Extract text, headings, pages, sections, code, tables, and useful figures; use OCR for scans.
4. Write `source.md`, `extracted.md`, and `structure.md` with extraction warnings and provenance.
5. Preserve location markers for citations and avoid copying the original file.
6. Ask for missing title, author, purpose, authority, audience, prerequisites, and associations when important.
7. Suggest topics/paths separately; require confirmation for important relationships.
8. Update catalog and optional index only after source files are valid.

## Output contract
Report source ID, files written, metadata provenance, extraction status, warnings, suggested associations, and index status.

## Failure handling
Keep partial extraction marked `partial`; never claim citations are valid when location data was lost. Continue without indexing if the optional helper is unavailable.
