# User guide

This guide describes the executable, Markdown-first learning workspace from first setup through cross-machine continuation. It is written for a learner; harness-specific setup belongs in [`../adapters/`](../adapters/).

## 1. What is stored where

The **workspace** is your learning repo. It is separate from this protocol/code repository.

```text
my-learning/
├── sources/                 # canonical teaching text and source metadata
├── topics/                  # concepts or units of study
├── paths/                   # ordered curricula
├── sessions/                # saved questions, answers, feedback
├── reviews/                 # current review queue and append-only history
├── confusion/               # unresolved misconceptions
├── progress/                # evidence summaries
└── index/                   # derived search caches; safe to rebuild
```

For an ingested book, the portable source of truth is:

```text
sources/<source-id>/
├── source.md       # stable ID, original location, checksum, associations, status
├── extracted.md    # normalized teaching text used for retrieval and reindexing
└── structure.md    # extracted headings and locations
```

`extracted.md`, not the optional vector database, is the canonical teaching copy. The original PDF/EPUB/DOCX is referenced by `source.md` and is not copied by default. Keep the original separately if you need it later.

## 2. Install and initialize

Requires Python 3.9+. From this repository:

```bash
python -m pip install -e .
learning init ~/Learning
```

Optional local features:

```bash
# PDF text extraction and Milvus Lite vector search
python -m pip install -e '.[pdf,milvus]'

# OCR of standalone image sources also requires the system `tesseract` command.
```

`learning init` is non-destructive: it creates missing workspace folders and starter files, but does not overwrite populated records.

## 3. Ingest a source

Supported local inputs are Markdown, text, PDF, DOCX, EPUB, image files, safe folders, and explicitly approved Git repositories.

```bash
learning ingest ~/Books/my-book.epub --workspace ~/Learning --title "My Book"
learning ingest ~/Notes --workspace ~/Learning
learning ingest https://example.com/article --workspace ~/Learning --allow-network
learning ingest ~/Code/project --workspace ~/Learning --allow-repository
```

Before ingesting, review `~/Learning/.learningignore`. It excludes common secrets by default. Repository ingestion requires `--allow-repository`, skips VCS/dependency/cache paths, and never follows symlinks.

### OCR behavior

```bash
learning ingest scan.png --workspace ~/Learning --ocr auto
learning ingest scan.png --workspace ~/Learning --ocr required
learning ingest scan.png --workspace ~/Learning --ocr never
```

- `auto`: uses `tesseract` if installed; otherwise records a warning and continues.
- `required`: fails rather than pretending OCR succeeded.
- `never`: never invokes OCR.

PDF text extraction uses `pypdf`; scanned PDF pages without embedded text receive an explicit warning. PDF-page image rendering is not performed automatically.

### Confirm source metadata

Ingestion records derived metadata as requiring confirmation. Inspect the source first, then confirm it:

```bash
learning source-confirm ~/Learning source-YYYYMMDD-my-book-abcdefgh
learning source-confirm ~/Learning source-YYYYMMDD-my-book-abcdefgh --authority primary
```

If a source has the same original location or checksum as another source, the runtime creates an open record in `conflicts/open/`. Resolve that deliberately rather than assuming the files are interchangeable.

## 4. Find and inspect material

Build the dependency-free lexical manifest and search it:

```bash
learning reindex ~/Learning
learning query ~/Learning "the core concept" --limit 5
learning query ~/Learning "the core concept" --source source-... --topic topic-... --path path-...
learning list ~/Learning
```

The lexical manifest is deterministic and derived from `extracted.md`. Search results include source IDs, sections, line starts, and workspace-file locations.

## 5. Create a curriculum

Create a topic linked to a source:

```bash
learning topic-create ~/Learning "Book foundations" \
  --source source-... \
  --objective "Explain the central ideas"
```

Create an ordered path from existing topics:

```bash
learning path-create ~/Learning "My Book Path" \
  --topic topic-book-foundations \
  --source source-... \
  --target-outcome "Explain and apply the book's main ideas"
```

Add prerequisites at creation time with `--prerequisite topic-...`. Topic relationships are ID-based; prerequisite cycles are rejected.

Canonical topic edits are previewed first and only written with `--confirm`:

```bash
learning topic-edit ~/Learning topic-book-foundations --status completed
learning topic-edit ~/Learning topic-book-foundations --status completed --confirm
```

Ask what is next:

```bash
learning recommend ~/Learning
```

Recommendations prioritize open confusion and unblocked path steps. A prerequisite is ready only when it is explicitly complete, or has enough persisted correct evidence without unresolved confusion.

## 6. Study and resume

A session is durable Markdown state, not chat-only state:

```bash
learning session-start ~/Learning \
  --scope-id topic-book-foundations \
  --objective "Explain the foundations"
```

The command prints the session path. You can append a manual turn:

```bash
learning session-turn ~/Learning/sessions/YYYY/MM/session-...md \
  --question "What is the central claim?" \
  --answer "..." \
  --evaluation partial \
  --confidence 2
```

Or use a model provider through a local JSON command:

```bash
learning tutor-session-question ~/Learning SESSION_PATH \
  --provider-command 'my-model-adapter'
learning tutor-session-answer ~/Learning SESSION_PATH 'my answer' \
  --confidence 3 \
  --provider-command 'my-model-adapter'
learning tutor-session-hint ~/Learning SESSION_PATH
```

Pause, resume, or complete a session:

```bash
learning session-status SESSION_PATH paused
learning session-status SESSION_PATH in-progress
learning session-status SESSION_PATH completed
```

A model endpoint is also supported, but it requires `--allow-network`, `--endpoint`, and `--model`. See [`../tools/model-interface.md`](../tools/model-interface.md).

## 7. Use a compatible agent harness

The CLI is the durable tool layer; it is not intended to be a menu you must operate manually every day. A compatible harness can read this workspace and invoke the same operations on your behalf.

For example, you can ask an agent:

- “Ingest this EPUB into my machine-learning workspace.”
- “Create a learning path for this book.”
- “What should I study next?”
- “I have 20 minutes. Continue where I left off and quiz me.”
- “Show me the concepts I am confused about.”
- “Prepare this workspace so I can continue on my other machine.”

A well-configured harness should identify the workspace, inspect due reviews/open confusion/path order, retrieve only source-grounded evidence, ask one question at a time, and persist the resulting answers, evaluations, review scheduling, and confusion state. See [`../adapters/`](../adapters/) for harness-specific installation and invocation notes.

### Actions that require your explicit confirmation

The protocol deliberately requires a preview and/or confirmation before an agent makes a consequential canonical change. Expect it to ask before it:

- changes canonical source metadata or authority;
- changes topic/path relationships or marks a topic complete;
- resolves or deletes a confusion record;
- decides how to handle a duplicate-source conflict;
- ingests a URL or repository;
- uses outside/web knowledge; or
- commits and pushes your learning workspace to Git.

You can still use any individual CLI command directly when you want to inspect or control an operation precisely.

## 8. Review, confusion, and progress

Tutor answer evaluation persists evidence by recall, explanation, and application; it updates a per-topic current due queue and appends review history. Incorrect or incomplete answers can create or merge stable confusion records.

```bash
learning progress ~/Learning
learning progress ~/Learning --topic topic-book-foundations
learning recommend ~/Learning
```

Read `reviews/due.md` for the current queue, `reviews/history.md` for history, and `confusion/open/` for the concepts needing remediation.

## 9. Optional semantic vector search

Milvus Lite is a local, disposable retrieval cache. It stores vector embeddings plus citation metadata for chunks from `extracted.md`; it does not own learning state or original source material.

```bash
learning vector-reindex ~/Learning --embedding-provider hash --dimension 256
learning vector-query ~/Learning "why does this matter?" \
  --embedding-provider hash --dimension 256 --limit 5
learning vector-status ~/Learning
```

Use `--incremental` to update only changed chunks:

```bash
learning vector-reindex ~/Learning --embedding-provider hash --dimension 256 --incremental
```

A full rebuild writes a new vector generation, publishes it only after building it, and records the active generation in `index/vector-status.json`. It takes a recovery snapshot under `index/milvus/backups/`. If it fails, the workspace Markdown and lexical manifest remain usable.

`hash` is deterministic and good for testing; use `sentence-transformers` or a command embedding provider for better semantic retrieval.

## 10. Optional high-fidelity Docling conversion

The default extractor is dependency-light and remains the portable baseline. For layout-sensitive PDFs, DOCX, HTML, and images—such as textbooks with columns, tables, formulas, or scans—Docling can produce more structured canonical Markdown.

Install it only on machines where you need it (**Python 3.10+; its models/runtime can require substantial downloads**):

```bash
python -m pip install -e '.[docling]'
learning ingest ./textbook.pdf --workspace ~/Learning/machine-learning --docling auto
```

- `--docling never` (the default) uses the built-in extractor.
- `--docling auto` tries Docling and records a warning before falling back to the built-in extractor if it is missing or fails.
- `--docling required` fails rather than accepting a fallback extraction.

The resulting `extracted.md` remains the portable canonical teaching text. `source.md` records `extraction_engines` for provenance; Docling models, caches, and the original file do not need to be committed or copied to another machine.

## 11. Use one learning repo on multiple machines

Put the workspace in a private Git repository. Commit the durable Markdown state and ignore derived local caches:

```gitignore
index/milvus/
index/vector-status.json
index/manifest.jsonl
```

On the machine you finish using:

```bash
git add .
git commit -m "study: update learning progress"
git push
```

On the next machine:

```bash
git pull --ff-only
learning reindex /path/to/my-learning
learning vector-reindex /path/to/my-learning --embedding-provider hash --dimension 256
```

You can resume because the synced workspace includes `extracted.md`, topics, paths, sessions, reviews, confusion records, and progress. An `original_location` in `source.md` may point to the first machine and be unavailable on the second; that does not block teaching or reindexing. It only matters if you need to re-ingest or inspect the original file.

Do not edit on both machines concurrently. Pull before a study session and commit/push afterward.

## 12. Recovery and troubleshooting

| Problem | What to do |
| --- | --- |
| Original EPUB/PDF path is unavailable on this machine | Use the synced `sources/<id>/extracted.md`; reindex normally. Restore the original separately only if you need it. |
| Milvus is missing or broken | Use `learning reindex` and `learning query`; then install the optional Milvus dependency and run `learning vector-reindex`. |
| Vector rebuild fails | Read `index/vector-status.json`, retain the listed backup, and use lexical retrieval. Do not delete `sources/`, `sessions/`, or `reviews/`. |
| OCR is unavailable | Install system `tesseract`, or use `--ocr auto` for a recorded warning. `--ocr required` intentionally fails. |
| Ingestion finds a duplicate | Inspect `conflicts/open/` and confirm whether it replaces, duplicates, or remains separate. |
| Tutor cannot connect to a provider | Use a local `--provider-command`, or provide the explicit network flags required by the CLI. |

## 13. Reference map

- [Data conventions](../protocol/data-conventions.md)
- [Safety policy](../protocol/safety-policy.md)
- [Source-ingest procedure](../skills/source-ingest.md)
- [Study-session procedure](../skills/study-session.md)
- [Index maintenance](../skills/index-maintenance.md)
- [Model-provider contract](../tools/model-interface.md)
- [Index interface](../tools/index-interface.md)
- [Harness adapters](../adapters/)
