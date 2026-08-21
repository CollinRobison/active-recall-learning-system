# Skill: source-ingest

## Purpose
Turn a local file, folder, URL, repository, transcript, image, or inbox item into auditable Markdown source records.

## Procedure
1. Confirm input and `.learningignore`; never ingest secrets or unrelated directories.
2. Compute a checksum where possible and identify source type.
3. Extract text, headings, pages, sections, and supported code. Image OCR uses local `tesseract` when available: report a warning and retain a partial source in automatic mode, or fail only when OCR was explicitly required. Do not claim PDF-page OCR: it needs an external renderer and is not provided by the runtime.
4. Write `source.md`, `extracted.md`, and `structure.md` with extraction warnings and provenance.
5. Preserve location markers for citations and avoid copying the original file.
6. Record field-level metadata provenance and mark derived metadata as requiring confirmation. Confirm title/authority deliberately before treating it as authoritative. When an original location or checksum matches an existing source, write an open source-conflict record rather than silently merging it.
7. Suggest topics/paths separately; require confirmation for important relationships.
8. Update catalog and optional index only after source files are valid.

## Output contract
Report source ID, files written, metadata provenance, extraction status, warnings, suggested associations, and index status.

## Failure handling
Keep partial extraction marked `partial`; never claim citations are valid when location data was lost. Continue without indexing if the optional helper is unavailable.

## Repository safety
Repository traversal requires explicit opt-in. Never follow symlinks; exclude VCS directories, dependency/build/cache folders, `.env` variants, and common credential/key filenames. The user can extend exclusions with `.learningignore`.

## Removing an ingested source
Use [`remove-learning-records.md`](remove-learning-records.md), never direct filesystem deletion. Preview `learning remove WORKSPACE SOURCE_ID`, obtain explicit approval, then use `--confirm`; this prunes only source-dependent curriculum artifacts and preserves unrelated path content.
