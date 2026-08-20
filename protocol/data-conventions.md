# Data conventions

## Workspace layout

```text
learning-workspace/
├── README.md
├── workspace.md
├── config.md
├── .learningignore
├── catalog/
│   ├── topics.md
│   ├── sources.md
│   ├── paths.md
│   └── study-options.md
├── topics/<topic-slug>/
│   ├── topic.md
│   ├── notes.md
│   ├── progress.md
│   └── questions.md
├── paths/<path-slug>/path.md
├── sources/<source-id>/
│   ├── source.md
│   ├── extracted.md
│   ├── structure.md
│   └── assets/                             # only when needed
├── sessions/YYYY/MM/session-<timestamp>-<seq>.md
├── confusion/{open,resolved}/
├── reviews/{due,history}.md
├── progress/{overall.md,snapshots/}
├── inbox/README.md
└── index/{README.md,manifest.jsonl,milvus/}
```

`index/` is derived. Deleting it must not lose learning state. A reindex reads `sources/<source-id>/source.md` and `extracted.md` again; it does not delete, move, or rewrite those files, topic/path records, sessions, confusion records, or reviews. Milvus rebuilds take a timestamped database snapshot in `index/milvus/backups/` before replacing the vector collection. If embedding fails, the source workspace remains usable through the lexical manifest and the status file identifies the recovery snapshot.

## Portable Git workspaces

A workspace may be a private Git repository shared sequentially between machines. Commit the canonical Markdown records (`sources/`, `topics/`, `paths/`, `sessions/`, `reviews/`, `confusion/`, and `progress/`), then pull before starting work on another machine. Ignore `index/milvus/`, `index/vector-status.json`, and `index/manifest.jsonl`: they are local derived caches and can be rebuilt from `extracted.md` after a pull. A source's `original_location` may be unavailable on the second machine; that does not prevent retrieval, tutoring, or reindexing because `extracted.md` is the portable teaching record. Keep original PDFs/EPUBs separately if they are not committed.

## Frontmatter

Use YAML frontmatter for stable identity, filtering, and lifecycle fields. IDs are immutable slugs with a kind prefix (`topic-`, `source-`, `path-`, `session-`, `confusion-`). Timestamps use ISO 8601 UTC. Arrays are YAML arrays, not comma-separated strings.

Required common fields:

```yaml
id: <immutable-id>
kind: topic | source | path | study-session | confusion-item | progress
status: active | draft | paused | completed | open | resolved | archived
created_at: 2026-08-20T00:00:00Z
updated_at: 2026-08-20T00:00:00Z
```

Write `origin: user-provided | extracted | inferred | user-confirmed | generated` for metadata whose provenance matters. Never overwrite user-confirmed values with later inference.

## Updates and naming

- Create records with unique IDs before asking the first study question.
- Save session state after setup and after each turn.
- Prefer append-only history and small targeted edits.
- Keep generated records separate from `topics/*/notes.md`; promotion into canonical notes requires explicit confirmation.
- Use lowercase kebab-case directory names and stable filenames.
- When a record is moved, retain its ID and add `moved_from` rather than creating a duplicate.

## Relationships

Relationships are IDs, not display names: `topic_ids`, `source_ids`, `path_ids`, `prerequisites`, and `related_topics`. Validate references when creating or editing a record; reject direct or indirect topic-prerequisite cycles. Many-to-many relationships are expected. When a topic/path source association is changed, update the source's reciprocal `topic_ids`/`path_ids` in the same confirmed edit.

Preview edits to canonical topic metadata and require an explicit confirmation before writing. A recommendation must not bypass an unmet prerequisite: treat it as ready only when it is explicitly `completed`, or when it has at least two persisted correct evaluations and no open confusion item. This is a transparent gate, not a claim of mastery.

## Evidence and mastery

Record evidence by dimension (`recall`, `explanation`, `application`) with source session, date, result, confidence, and citations. A single score never establishes mastery. A provisional strong state requires more than one evidence dimension and a later review.

## Citation shape

A citation should identify `source_id`, a human-readable title, and the strongest available location: page, chapter, section, line range, or URL anchor. Include a short exact excerpt whenever copyright and source size make that practical. If no reliable location exists, state `location: unavailable` and do not invent one.
