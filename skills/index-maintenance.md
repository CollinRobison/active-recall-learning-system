# Skill: index-maintenance

## Purpose
Maintain an optional local retrieval cache without making it canonical.

## Procedure
1. Read source/note manifests and configured embedding provider/model/dimension.
2. Exclude secrets, raw transcripts unless configured, and unapproved notes.
3. Detect changed content hashes and stale records.
4. Upsert source chunks and approved notes with citation metadata and filters.
5. Before replacing a Milvus collection, create a timestamped database snapshot under `index/milvus/backups/`; on failure, report that snapshot and keep using the lexical manifest.
6. Remove stale vectors only after the Markdown source remains safe.
7. Report current, stale, failed, and skipped records.
8. For rebuild, recreate the cache entirely from workspace files and verify counts.

## Output contract
Index status, collection/model metadata, changed/removed/failed counts, and degraded-mode instructions.

## Safety
Milvus Lite is optional. If unavailable, use direct file search and say retrieval is degraded; never silently report current status.
