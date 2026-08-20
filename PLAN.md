# Cross-Harness Active Recall Learning System

## Planning document

**Status:** Active implementation plan
**Implementation status:** Protocol, schemas, portable skills, runtime workspace tools, optional embeddings/Milvus boundary, grounded model adapters, and durable single-turn tutor/session orchestration are implemented; catalog/paths, adaptive review, ingestion hardening, and production validation remain.
**Primary goal:** Create a portable Markdown-based learning system that can be used from Pi, Claude Code, Codex CLI, Gemini CLI, Cursor, OpenCode, Copilot CLI, Hermes, and similar agent harnesses.

## Current implementation status and next work

The repository now contains the Phase 0 protocol package plus a Python runtime for workspace initialization, Markdown/text/PDF/URL ingestion, sessions, confusion records, review scheduling, citation checks, lexical retrieval, optional embeddings/Milvus Lite, and source-grounded model question/evaluation adapters. The current implementation is intentionally provider-agnostic and preserves Markdown as the source of truth.

The next work is tracked in this order:

1. **Catalog and learning paths:** add topic/path creation and editing, prerequisites, relationships, source associations, confirmation workflows, and ranked next-study recommendations.
2. **Adaptive review:** maintain due-review files and history, confidence calibration, recall/explanation/application evidence, interleaving, and delayed-review scheduling.
3. **Ingestion completeness:** add OCR for scanned PDFs/images, DOCX/EPUB extraction, better webpage parsing, repository/code ingestion, metadata confirmation, and source-conflict handling.
4. **Milvus hardening:** validate against an installed Milvus Lite version, support incremental/stale-record updates, approved-note collections, topic/path filters, and rebuild integration tests.
5. **Evaluation and adapters:** add golden learning examples, exact citation-location tests, provider integration tests, and concrete installation/invocation instructions for each harness adapter.

The catalog runtime now creates, edits (with explicit preview/confirmation), and validates Markdown topic/path records; maintains reciprocal source associations; rejects prerequisite cycles; and produces a transparent ranking of open confusion, unblocked active path order, and active topics. Its prerequisite gate uses explicit completion or persisted correct evidence without unresolved confusion. Adaptive review now maintains one current due entry per topic plus append-only history, records recall/explanation/application evidence, delayed-review status, and confidence calibration, and supplies recent concepts to question generation for interleaving. Ingestion now supports safe opt-in repository/code traversal, optional local image OCR with explicit degraded/required modes, metadata provenance and confirmation, and duplicate-source conflict records. Milvus now has generation-safe full rebuild publication, incremental updates, and source/topic/path query filters; deterministic fake-client tests cover that boundary without requiring pymilvus. PDF page rendering OCR, richer webpage parsing, and installed-Milvus compatibility validation remain.

---

## 1. Executive summary

Build the system as a **harness-agnostic learning protocol**, not as a large application tied to one agent framework.

The system should use:

1. **Markdown files as the human-readable source of truth.**
2. **Portable skills and prompt contracts** that any capable agent can follow.
3. **A configurable learning workspace** containing topics, sources, paths, sessions, confusion items, progress, and recommendations.
4. **Small local helper tools** only where the harness cannot reliably perform the operation itself.
5. **Milvus Lite as an optional local retrieval index** for books and heavy documents, while keeping Markdown and extracted source text authoritative.
6. **Explicit state in files**, rather than relying on an agent's conversation memory.
7. **Source-grounded teaching by default**, with permission required before using outside knowledge or web research.

The first deliverable should be a detailed set of portable skills, prompt contracts, data schemas, workflows, and adapter requirements. It should not require LangChain, LlamaIndex, FastAPI, Chroma, or a particular model provider.

---

## 2. User requirements captured

The system must support:

- Teaching topics and listing available topics and sources.
- Explanation-based quizzing, not merely flashcards or multiple choice.
- Active Recall sessions.
- Feynman-style teach-back sessions.
- Hints, retries, confidence ratings, applications, comparisons, and multiple-choice questions when selected.
- Adaptive sessions and sessions with an explicitly chosen learning mode.
- Human-readable Markdown session notes.
- Automatic tracking of progress, confusion, review history, coverage, and recommendations.
- Recommendations that identify exactly where in the source material to review a confusing concept.
- Source metadata collection, including metadata that is not naturally present in the source.
- Per-topic folders.
- Courses, learning paths, ordered curricula, tags, prerequisites, and relationships between topics and sources.
- Commands/intents for initialization, listing, teaching, sessions, ingestion, confusion review, progress, and index rebuilding.
- Ingestion of Markdown, text, PDFs/books, webpages, code repositories, transcripts, images, OCR text, and diagrams where practical.
- Required citations for explanations and corrections.
- Source conflict detection and source authority metadata.
- Pause/resume, early stopping, retry, skip, comparison, and recovery from accidental changes.
- Local-first behavior and protection of secrets.
- Optional automatic Milvus Lite indexing.
- A small directory footprint: do not copy original books or PDFs unless explicitly requested.

---

## 3. Design principles

### 3.1 Markdown is authoritative

The vector index is a derived cache. It must be rebuildable from the workspace files. No important learning state should exist only in Milvus.

### 3.2 Files are the memory

The agent must be able to resume after a context reset, harness change, or new session by reading the workspace. It must not depend on hidden conversation memory.

### 3.3 Portable core, optional adapters

The shared core should consist of plain Markdown instructions, schemas, prompt contracts, and workflow rules. Harness-specific files should be thin adapters that explain how to invoke the shared core.

### 3.4 Source-grounded by default

The tutor should teach only from indexed/user-provided sources unless the user explicitly approves external information. Any external information must be labeled as external and must not silently become authoritative workspace knowledge.

### 3.5 Human-readable records first

A user should be able to open a session, understand what happened, see their answers, inspect citations, and continue studying without a database viewer.

### 3.6 Smallest necessary technology footprint

Use specialized tools only for tasks that are difficult or unreliable for an agent to perform directly:

- PDF/DOCX/EPUB extraction
- OCR and image processing
- Embedding generation
- Milvus Lite indexing and retrieval

Do not require an orchestration framework merely to call a model or manage a state machine.

### 3.7 Evidence over a single score

Mastery should be inferred from repeated evidence across recall, explanation, application, confidence, and delayed review. A single LLM score must never be treated as definitive.

---

## 4. Proposed architecture

```text
┌─────────────────────────────────────────────────────────┐
│ Agent harnesses                                         │
│ Pi / Claude Code / Codex / Gemini / Cursor / others     │
└──────────────────────┬──────────────────────────────────┘
                       │ reads shared Markdown protocol
┌──────────────────────▼──────────────────────────────────┐
│ Portable learning skills                               │
│ init / catalog / ingest / teach / quiz / review / index │
└──────────────────────┬──────────────────────────────────┘
                       │ reads and writes explicit files
┌──────────────────────▼──────────────────────────────────┐
│ Learning workspace                                     │
│ Markdown records + extracted source text + manifests   │
└──────────────────────┬──────────────────────────────────┘
                       │ optional derived cache
┌──────────────────────▼──────────────────────────────────┐
│ Local helper tools                                    │
│ parsing / OCR / embeddings / Milvus Lite              │
└─────────────────────────────────────────────────────────┘
```

### 4.1 Portable core

The portable core should define:

- Required workspace folders.
- File naming and metadata conventions.
- Session lifecycle rules.
- Prompt contracts.
- Evaluation rubric.
- Citation requirements.
- Confusion-item rules.
- Progress and scheduling rules.
- Safe file-update rules.
- Optional helper command interfaces.

### 4.2 Harness adapters

Each adapter should only explain:

- Where to install or link the shared skills.
- How the harness invokes a skill.
- Which file-reading, file-writing, shell, search, and web tools are available.
- How to request user confirmation.
- How to invoke the optional helper commands.

The tutor behavior itself should not be duplicated across harnesses.

### 4.3 Common-denominator assumption

The system can assume:

- Read files.
- Write files.
- Search files.
- Run local commands when available.
- Ask the user questions.
- Access the internet only when the user approves it.

It should not assume:

- Persistent agent memory.
- A specific model vendor.
- A specific prompt framework.
- A hosted API.
- A running web server.
- A database server.

---

## 5. Proposed workspace layout

The workspace location should be configurable. A default such as `~/Learning/` is reasonable, but the active workspace should be selectable at session start.

```text
learning-workspace/
├── README.md
├── workspace.md
├── config.md
├── catalog/
│   ├── topics.md
│   ├── sources.md
│   ├── paths.md
│   └── study-options.md
├── topics/
│   └── python-basics/
│       ├── topic.md
│       ├── notes.md
│       ├── progress.md
│       └── questions.md
├── paths/
│   └── python-for-data-science/
│       └── path.md
├── sources/
│   └── source-20260820-example-book/
│       ├── source.md
│       ├── extracted.md
│       ├── structure.md
│       └── assets/
├── sessions/
│   └── 2026/
│       └── 08/
│           └── session-20260820-001.md
├── confusion/
│   ├── open/
│   │   └── confusion-0001.md
│   └── resolved/
├── reviews/
│   ├── due.md
│   └── history.md
├── progress/
│   ├── overall.md
│   └── snapshots/
├── inbox/
│   └── README.md
└── index/
    ├── README.md
    ├── manifest.jsonl
    └── milvus/
        └── workspace.db
```

### 5.1 Footprint strategy

Do not copy original PDFs, books, or local source files by default.

For each source, retain:

- Original path or URL.
- File checksum or source version identifier.
- Extracted/normalized Markdown text.
- Structure and location metadata.
- A source manifest.
- Optional extracted images only when needed for citation or visual understanding.

This permits citation, re-indexing, and auditing without duplicating large source files. A source can optionally be archived into the workspace later.

### 5.2 Human-readable versus generated records

Keep canonical human-authored notes separate from generated records.

Generated content must not silently overwrite `notes.md`. A generated explanation may be promoted into human notes only through an explicit user action.

Session notes, confusion items, progress records, and recommendations are generated records. They remain readable Markdown and may be edited by the user.

---

## 6. Markdown record conventions

Use YAML frontmatter for stable identity, status, and filtering, followed by ordinary Markdown for readable content.

### 6.1 Topic record

```markdown
---
id: topic-python-basics
kind: topic
name: Python Basics
slug: python-basics
status: active
created_at: 2026-08-20T00:00:00Z
updated_at: 2026-08-20T00:00:00Z
tags:
  - programming
prerequisites: []
related_topics:
  - topic-data-structures
---

# Python Basics

## Purpose

Why I am studying this topic.

## Learning objectives

- Explain variables, expressions, and control flow.
- Apply Python syntax to small problems.

## Sources

- source-20260820-example-book

## Notes

Human-authored notes belong here.
```

### 6.2 Source record

```markdown
---
id: source-20260820-example-book
kind: source
title: Example Book
author: Example Author
source_type: pdf
original_location: /path/to/original.pdf
checksum: sha256:...
ingested_at: 2026-08-20T00:00:00Z
last_indexed_at: 2026-08-20T00:00:00Z
authority: user-marked
authority_scope:
  - python-basics
topics:
  - topic-python-basics
learning_paths:
  - path-python-for-data-science
extraction_status: complete
index_status: current
---

# Example Book

## Why this source is being used

User-provided purpose.

## Extraction notes

- Parsed chapters automatically.
- Page references available.
- OCR not required.

## Structure

See `structure.md`.

## Citation policy

Use page, chapter, section, and exact excerpt whenever available.
```

### 6.3 Session record

Every session should be independently understandable.

```markdown
---
id: session-20260820-001
kind: study-session
started_at: 2026-08-20T00:00:00Z
ended_at: 2026-08-20T00:45:00Z
status: completed
scope_type: topic
scope_ids:
  - topic-python-basics
mode: active-recall
objective: Explain Python control flow and apply it to examples
question_count: 5
---

# Study Session: Python Basics

## Session setup

- Mode: Active Recall
- Difficulty: Adaptive
- User objective: ...

## Summary

- Strong areas: ...
- Weak areas: ...
- New confusion items: ...
- Recommended next step: ...

## Turns

### Turn 1 — Explain conditional branching

**Question:** ...

**My answer:** ...

**Confidence before feedback:** 3/5

**Evaluation:** Partially correct

**Rubric:**

- Accuracy: 3/4
- Completeness: 2/4
- Explanation: 3/4
- Application: not assessed

**Feedback:** ...

**Citation:** `Example Book`, Chapter 2, p. 41

> Exact excerpt...

**Action:** Added confusion item `confusion-0001`.
```

### 6.4 Confusion item

```markdown
---
id: confusion-0001
kind: confusion-item
status: open
created_at: 2026-08-20T00:20:00Z
updated_at: 2026-08-20T00:20:00Z
topic_id: topic-python-basics
concept: conditional-branching
severity: moderate
source_ids:
  - source-20260820-example-book
origin_session: session-20260820-001
review_count: 0
next_review_at: 2026-08-21T00:00:00Z
---

# Confusion: Conditional branching

## What I was asked

...

## What I said

...

## What was missing or incorrect

...

## Where to review

- Example Book, Chapter 2, pages 40–43.
- Section: `if`, `elif`, and `else`.

## Recommended remediation

1. Reread the cited section.
2. Explain the distinction in one sentence.
3. Apply it to a new example.
4. Reattempt a retrieval question tomorrow.

## Resolution evidence

Leave empty until later performance demonstrates understanding.
```

---

## 7. Portable skill set

Each skill should be a Markdown instruction file with the same conceptual structure:

```markdown
# Skill: <name>

## Purpose
## When to use
## Required inputs
## Files to read
## User interaction rules
## Procedure
## Output contract
## Files to write
## Safety and confirmation rules
## Failure handling
```

### 7.1 `workspace-init`

Responsibilities:

- Choose or create an active workspace.
- Create the folder structure.
- Create `workspace.md`, `config.md`, and empty catalogs.
- Explain the workspace to the user.
- Detect existing learning files and propose organization.
- Ask for the first source or offer a demonstration session.

### 7.2 `catalog`

Responsibilities:

- List topics.
- List sources.
- List learning paths.
- List available study options.
- Show due reviews, open confusion items, low-mastery areas, and uncovered material.
- Provide a balanced menu rather than returning an unranked directory listing.

Example intents:

- “What can I study?”
- “List my topics.”
- “What should I work on today?”
- “Which sources are associated with machine learning?”

### 7.3 `source-ingest`

Responsibilities:

- Accept a local path, folder, URL, inbox item, or repository.
- Detect source type.
- Extract text and document structure.
- Use OCR when the source is scanned.
- Detect images and diagrams when useful.
- Create source metadata and extracted Markdown.
- Suggest topics and learning-path relationships.
- Ask for confirmation on important uncertain metadata.
- Generate embeddings and update the optional index.
- Report warnings and extraction limitations.

### 7.4 `teach`

Responsibilities:

- Teach one topic, source, learning path, or user objective.
- Ask whether to choose a session mode or let the agent choose.
- Use source-grounded explanations.
- Provide citations.
- Transition from explanation into retrieval practice rather than ending with passive reading.

### 7.5 `study-session`

Responsibilities:

- Create a session record immediately.
- Ask for scope, mode, objective, length, and optional difficulty.
- Support pause, resume, stop, retry, skip, and completion.
- Save progress incrementally so an interrupted session is not lost.
- Use one question at a time.
- Ask for confidence before feedback when appropriate.
- Offer hints without immediately revealing the answer.
- Evaluate, cite, record confusion, and select the next question.

### 7.6 `active-recall`

Responsibilities:

- Ask free-response questions.
- Prefer retrieval before explanation.
- Cover important concepts, not merely random chunks.
- Mix factual, conceptual, procedural, and application questions.
- Revisit weak concepts after a delay rather than immediately repeating the answer.

### 7.7 `feynman-teachback`

Responsibilities:

- Ask the user to explain a concept in their own words.
- Adopt a curious-student stance.
- Ask targeted why/how/what-if follow-ups.
- Correct factual errors clearly and respectfully.
- Distinguish a true error from an incomplete explanation.
- Stop a false branch, repair the misconception, and create a review item.
- Move to a new concept after adequate depth or a configured limit.

The plan should not claim that the named “Feynman Technique” is itself a single fully validated learning protocol. It should describe the implementation as teach-back, self-explanation, elaboration, and retrieval practice.

### 7.8 `application-practice`

Responsibilities:

- Generate a problem, scenario, example, or transfer task.
- Require the user to solve or predict before showing an answer.
- Evaluate both the result and reasoning.
- Link errors to prerequisite concepts and source locations.

### 7.9 `confusion-review`

Responsibilities:

- Show open confusion items.
- Rank them by due date, severity, recurrence, and importance.
- Provide the exact source location to review.
- Offer a short remediation choice: reread, explain, compare, apply, or retry.
- Mark an item resolved only after evidence, not merely after the user says it is resolved.

### 7.10 `progress`

Responsibilities:

- Show topic and path progress.
- Show recent evidence and trends.
- Show due reviews.
- Show repeated confusion.
- Recommend next actions with reasons.
- Avoid presenting an uncalibrated LLM score as objective truth.

### 7.11 `index-maintenance`

Responsibilities:

- Create the local Milvus Lite database when enabled.
- Index source chunks and approved learning notes.
- Store metadata needed for filters and citations.
- Detect stale records through checksums and timestamps.
- Rebuild the index from Markdown and extracted source files.
- Never treat the index as the only copy of learning data.

---

## 8. Standard session setup

When the user starts a session, the agent should ask only for information that is missing. It should offer sensible defaults.

```text
What would you like to study?
1. Topic
2. Source
3. Learning path
4. Open confusion items
5. Let me choose based on your progress

Which mode?
1. Active recall
2. Feynman teach-back
3. Explain, then quiz
4. Application practice
5. Compare and contrast
6. Multiple choice
7. Spaced review
8. Let me choose

How long?
- Number of questions
- Approximate time
- Until a stopping condition

What is your goal?
- Explain
- Remember
- Apply
- Prepare for an assessment
- Explore
```

The agent should not force all questions every time. It should infer defaults from context and record the choices in the session file.

---

## 9. Teaching and quiz interaction contract

A normal turn should follow this sequence:

1. Select one concept or objective.
2. Retrieve relevant source chunks.
3. Ask one question.
4. Wait for the user's answer.
5. Ask for confidence before feedback when useful.
6. Evaluate against the retrieved source and rubric.
7. Give a hint, correction, or explanation according to the adaptive policy.
8. Show citations.
9. Update the session record.
10. Create or update a confusion item if warranted.
11. Select the next question based on coverage, difficulty, spacing, and confusion.

The agent should support these user controls at any time:

- “Hint.”
- “Let me try again.”
- “Explain it.”
- “Show the source.”
- “Skip this.”
- “Pause.”
- “Stop and save.”
- “Make it harder/easier.”
- “Switch to Feynman mode.”

---

## 10. Evidence-based learning policy

The system should use the following principles.

### 10.1 Retrieval before explanation

Ask the user to retrieve or explain before displaying a full explanation whenever the user has enough prior exposure. This creates a desirable level of difficulty and gives the system evidence about what is actually known.

### 10.2 Spacing

Do not mark a concept mastered because it was answered correctly once. Schedule later retrieval after increasing intervals, with shorter intervals after failures.

### 10.3 Interleaving

After basic familiarity is established, mix related topics and problem types. This helps distinguish concepts and choose the right procedure instead of repeating one blocked practice pattern.

### 10.4 Elaboration

Ask why, how, what-if, compare, and consequence questions. Request connections to prior knowledge and concrete examples.

### 10.5 Generation and application

Ask the user to predict, solve, design, classify, or apply before revealing the solution.

### 10.6 Metacognitive calibration

Ask for a confidence rating before feedback. Compare confidence with performance over time. Record overconfidence and underconfidence as useful learning signals.

### 10.7 Feedback timing

Use hints and retries when the user can productively recover. Give a clear correction when the answer contains a dangerous, foundational, or strongly misleading misconception. Do not force endless retries.

### 10.8 Mastery evidence

Track at least three evidence dimensions:

- **Recall:** Can the user retrieve the idea?
- **Explanation:** Can the user explain it accurately and completely?
- **Application:** Can the user use it in a new context?

A concept should be considered provisionally strong only after success across more than one dimension and at least one later review.

### 10.9 Spaced scheduling recommendation

Use a simple transparent scheduler for the first version:

- Failed or seriously confused: review soon.
- Partial answer: review later the same day or next day.
- Correct but low-confidence: review soon.
- Correct and confident: schedule a longer interval.
- Correct application after delay: extend the interval.

A later version may adopt FSRS or another scheduler, but the schedule should remain visible and overrideable by the user.

---

## 11. Answer evaluation rubric

The evaluator should return structured data internally, even if the harness displays natural language.

```yaml
classification: correct | partial | incorrect | unsupported
scores:
  accuracy: 0-4
  completeness: 0-4
  reasoning: 0-4
  application: 0-4 | null
confidence_rating: 1-5 | null
missing_concepts: []
misconceptions: []
source_support: []
needs_confusion_item: true | false
recommended_action: explain | hint | retry | review-later | advance
```

### 11.1 Evaluation rules

- Judge against source evidence, not the model's unsupported memory.
- Give credit for correct alternative wording.
- Do not penalize harmless omissions if the question did not require them.
- Separate factual correctness from completeness and clarity.
- Identify uncertainty when the source itself is ambiguous.
- Never invent a citation.
- If retrieval returned inadequate context, say so and retrieve again instead of confidently grading.

### 11.2 Feedback format

Feedback should normally contain:

1. What was correct.
2. What was missing or incorrect.
3. A concise corrected explanation.
4. One or more citations.
5. The next action.

Do not expose hidden chain-of-thought. Store only the concise rationale necessary for learning and auditing.

---

## 12. Confusion-list policy

Create or update a confusion item when:

- The answer is incorrect.
- A major misconception is present.
- The answer is incomplete on a required concept.
- The user requests a hint or expresses uncertainty.
- The user is repeatedly overconfident and incorrect.
- A source conflict prevents a clear answer.

Do not create a new duplicate item for every failed turn. Merge related failures under a stable concept when appropriate, while preserving session references.

Each item must include:

- Concept.
- User's original answer.
- What was correct.
- What was wrong or missing.
- Source location.
- Exact excerpt when available.
- Prerequisites.
- Recommended remediation.
- Review history.
- Resolution evidence.

The agent should recommend where to look, not merely say “study more.”

---

## 13. Topic, source, and learning-path relationships

The data model should support many-to-many relationships:

- One source can support multiple topics.
- One topic can use multiple sources.
- A source can belong to multiple learning paths.
- A topic can appear in multiple paths.
- A path can declare prerequisites.
- A topic can have related or contrasting topics.

### 13.1 Learning path record

A path should contain:

- Name and purpose.
- Target outcome.
- Ordered topics.
- Prerequisites.
- Recommended sources.
- Optional milestones.
- Alternative routes.
- Current progress.

The agent may suggest paths or associations, but should ask for confirmation before creating important new structure unless the user has enabled automatic maintenance.

---

## 14. Source ingestion plan

### 14.1 Input methods

Support:

- Local file path.
- Local folder.
- URL.
- Inbox folder.
- Existing workspace discovery.
- Repository path for code.

### 14.2 Processing stages

1. Identify source and compute a checksum where possible.
2. Extract text and document structure.
3. Detect title, author, chapters, headings, pages, sections, code blocks, tables, and figures.
4. Use OCR for scanned pages.
5. Extract or reference images when they contain learning-relevant information.
6. Normalize into Markdown without destroying page/section boundaries.
7. Chunk by document structure, with small overlap only when needed.
8. Create source metadata and extraction warnings.
9. Ask for confirmation on important uncertain metadata.
10. Suggest topic and path associations.
11. Generate embeddings if indexing is enabled.
12. Update the manifest and catalog.

### 14.3 Metadata that should be requested when absent

- Title.
- Author or creator.
- Topic.
- Purpose for studying.
- Authority or trust level.
- Intended audience/difficulty.
- Prerequisites.
- Publication/version information.
- Reading order.
- Relevant chapters or sections.

The system should distinguish:

- `extracted`: found directly in the source.
- `inferred`: estimated by the agent.
- `user-confirmed`: confirmed by the user.
- `user-provided`: entered by the user.

### 14.4 Extraction uncertainty

Important uncertainty should be stored and surfaced. For example:

```yaml
metadata_confidence:
  title: high
  author: medium
  chapter_structure: low
warnings:
  - Page 17 appears to be image-only; OCR may be incomplete.
```

### 14.5 Source conflicts

When sources disagree:

1. Flag the disagreement.
2. Show both source positions.
3. Respect user-marked authority at the topic level.
4. Ask which source should be preferred when necessary.
5. Create a research/confusion item if the disagreement matters to the learning objective.
6. Never silently merge conflicting claims into one fact.

---

## 15. Milvus Lite design

Milvus Lite is an optional local retrieval component, not the canonical database.

### 15.1 Recommended layout

Use one Milvus Lite database per workspace:

```text
learning-workspace/index/milvus/workspace.db
```

Use metadata filters for:

- Workspace.
- Topic.
- Learning path.
- Source.
- Record type.
- Authority.
- Extraction method.
- Version.

### 15.2 Recommended collections

A minimal design can use:

- `source_chunks`
- `approved_learning_notes`

Do not index every raw transcript by default. Full transcripts can create noisy retrieval and duplicate information. Session summaries, confusion records, and promoted notes may be indexed when configured.

### 15.3 Source chunk metadata

Each vector record should retain:

```json
{
  "record_id": "chunk-source-20260820-example-book-0042",
  "source_id": "source-20260820-example-book",
  "topic_ids": ["topic-python-basics"],
  "path_ids": ["path-python-for-data-science"],
  "source_type": "pdf",
  "page": 41,
  "section": "Conditional branching",
  "chunk_order": 42,
  "content_hash": "sha256:...",
  "authority": "user-marked",
  "extraction_method": "native-text",
  "workspace_file": "sources/source-20260820-example-book/extracted.md"
}
```

### 15.4 Rebuild behavior

`reindex` should:

1. Read the source and note manifests.
2. Detect changed content hashes.
3. Remove stale vectors.
4. Re-embed changed records.
5. Recreate missing records.
6. Report failures without deleting the Markdown source of truth.

### 15.5 Embedding strategy

The design should support:

- A local embedding model for privacy and predictable operation.
- A configured cloud embedding provider when explicitly allowed.
- A harness-provided embedding command if available.

The embedding model name, dimension, provider, and version must be recorded. Changing the model should trigger a full or collection-specific rebuild.

### 15.6 Graceful degradation

If Milvus Lite is unavailable:

- Continue supporting topic listing and Markdown-based sessions.
- Use direct file search for small workspaces.
- Tell the user that retrieval quality and large-document support are reduced.
- Never silently pretend the vector index is current.

---

## 16. Standard commands/intents

These should be documented in portable skills and optionally exposed as aliases.

| Intent | Example |
|---|---|
| `init` | “Set up my learning workspace.” |
| `list` | “What topics, sources, and paths can I study?” |
| `teach` | “Teach me Python generators.” |
| `session` | “Start a Feynman session on chapter 3.” |
| `ingest` | “Add this PDF to my machine-learning path.” |
| `confusion` | “Review my open confusion items.” |
| `progress` | “How am I doing with Python?” |
| `recommend` | “What should I study next and why?” |
| `reindex` | “Rebuild the local learning index.” |
| `show-source` | “Show me the source behind that correction.” |
| `pause` | “Pause and save this session.” |
| `resume` | “Resume my interrupted session.” |

Natural language should remain supported; commands are predictable aliases, not a requirement for usability.

---

## 17. Prompt contract plan

The final skill package should include prompt templates for:

1. Tutor system behavior.
2. Source-grounded explanation.
3. Active Recall question generation.
4. Feynman follow-up generation.
5. Application-problem generation.
6. Answer evaluation.
7. Hint generation.
8. Correction and feedback.
9. Metadata extraction.
10. Topic/path classification.
11. Confusion-item extraction.
12. Remediation recommendation.
13. Source conflict analysis.
14. Progress summary.
15. Study-option ranking.

Every prompt should specify:

- Allowed evidence.
- Required structured fields.
- Citation requirements.
- What to do when context is insufficient.
- What not to invent.
- How to handle uncertainty.
- Whether the output is user-facing or internal.

### 17.1 Core tutor rules

The tutor should:

- Be Socratic by default.
- Adapt difficulty based on correctness, confidence, prior history, and user override.
- Ask one question at a time.
- Prefer retrieval before explanation.
- Give useful feedback without shaming.
- Be concise unless depth is requested.
- Cite the source used.
- Ask permission before using external sources.
- Save state incrementally.
- Never claim a concept is mastered based on one turn.

---

## 18. Privacy and file safety

Required defaults:

- Local-first.
- No telemetry.
- No credentials in Markdown files.
- No API keys in source records, logs, prompts, or session notes.
- Ask permission before sending source material or answers to external services.
- Clearly label cloud-generated or web-derived information.
- Do not index secrets, environment files, private keys, or unrelated directories.
- Respect an ignore file such as `.learningignore`.

### 18.1 File updates

Use a two-stage update policy:

1. Write low-risk append-only session and progress records automatically.
2. Require confirmation before changing canonical topic notes, source authority, learning paths, or deleting records.

### 18.2 Recovery

Use Git when available. The skill should:

- Recommend committing before large imports or reorganizations.
- Show a change summary before important updates.
- Avoid destructive rewrites.
- Preserve superseded records when practical.
- Provide recovery instructions using Git history.

---

## 19. Suggested implementation phases

### Phase 0 — Protocol and schemas

Deliver:

- Shared skill file format.
- Workspace layout.
- Frontmatter schemas.
- Session and evaluation contracts.
- Citation rules.
- Portability rules.

Acceptance criteria:

- A user can understand the system without reading source code.
- The same workflow can be followed by multiple harnesses.
- All important state has a Markdown representation.

### Phase 1 — Markdown-only learning workflow

Deliver:

- `init`.
- `list`.
- `teach`.
- Active Recall session.
- Feynman session.
- Human-readable session notes.
- Confusion list.
- Progress summary.

Acceptance criteria:

- A user can study a Markdown source without any database.
- The agent can resume from saved files.
- Incorrect answers create actionable confusion records with citations.

### Phase 2 — Source ingestion

Deliver:

- Local files and folders.
- URLs.
- PDF/text/Markdown extraction.
- Metadata confirmation.
- Chapter/section detection.
- Extraction warnings.

Acceptance criteria:

- A large source becomes readable Markdown with location metadata.
- The agent can cite page/section/excerpt information.
- Original files do not need to be copied into the workspace.

### Phase 3 — Optional local indexing

Deliver:

- Embedding adapter.
- Milvus Lite workspace database.
- Source and approved-note collections.
- Incremental indexing.
- `reindex`.
- Staleness reporting.

Acceptance criteria:

- Index can be deleted and rebuilt from workspace files.
- Queries can filter by topic, source, and learning path.
- Sessions continue in degraded mode if Milvus is unavailable.

### Phase 4 — Learning-path and adaptive review

Deliver:

- Prerequisite relationships.
- Study-option ranking.
- Spacing scheduler.
- Interleaving rules.
- Confidence calibration.
- Delayed recall tracking.
- Application-performance tracking.

Acceptance criteria:

- “What should I study?” returns a reasoned menu.
- Recommendations include exact source locations.
- Mastery reflects multiple evidence types and later review.

### Phase 5 — Harness adapters

Deliver:

- Adapter documentation for Pi.
- Claude Code.
- Codex CLI.
- Gemini CLI.
- Cursor.
- OpenCode.
- Copilot CLI.
- Hermes.

Acceptance criteria:

- Each adapter points to the same shared core.
- No behavior-critical prompt is duplicated unnecessarily.
- A user can move the workspace between harnesses.

### Phase 6 — Evaluation and refinement

Deliver:

- Golden learning examples.
- Deterministic schema tests.
- Citation validity tests.
- Session state transition tests.
- Retrieval tests.
- Periodic quality evaluations.
- User feedback workflow.

Acceptance criteria:

- The evaluator does not invent citations.
- Confusion records are not duplicated excessively.
- Re-indexing does not lose Markdown state.
- Tutor behavior improves based on observed failures.

---

## 20. Testing strategy

### 20.1 Deterministic tests

Test without a real model:

- Frontmatter parsing.
- File naming.
- Workspace initialization.
- Session state transitions.
- Pause/resume.
- Confusion-item merging.
- Review scheduling.
- Manifest/checksum behavior.
- Index rebuild bookkeeping.
- Citation validation.

### 20.2 Contract tests

Test that each model, embedding, parser, and vector adapter returns the required fields and handles errors consistently.

### 20.3 Golden learning set

Create a small set of source passages and hand-authored expected answer qualities:

- Correct answer.
- Partial answer.
- Common misconception.
- Overconfident incorrect answer.
- Correct answer using alternative wording.
- Conflicting-source case.
- Missing-context case.

### 20.4 Quality measures

Track:

- Citation accuracy.
- Citation completeness.
- Retrieval relevance.
- Evaluation agreement with human judgments.
- Repeated confusion frequency.
- Delayed recall performance.
- Explanation quality.
- Application success.
- Confidence calibration.

---

## 21. Research basis

The learning-policy recommendations are based on the following established findings and should be treated as design guidance rather than guarantees:

- **Retrieval practice:** Recalling information generally produces stronger long-term retention than repeatedly rereading it.
- **Distributed practice:** Reviews separated over time generally outperform massed practice.
- **Elaboration and self-explanation:** Explaining why and how can improve understanding when explanations are accurate and corrected when necessary.
- **Generation:** Attempting an answer or solution before seeing the answer can improve later memory and transfer.
- **Interleaving:** Mixing related problem types can improve discrimination and selection of the appropriate method.
- **Metacognition:** Confidence ratings are useful when compared with later performance rather than treated as mastery themselves.

Useful references:

1. Dunlosky, J. et al. (2013), “Improving Students’ Learning With Effective Learning Techniques.”  
   https://doi.org/10.1177/1529100612453266
2. Roediger, H. L. III & Karpicke, J. D. (2006), “Test-Enhanced Learning.”  
   https://doi.org/10.1037/0278-7393.32.2.249
3. Cepeda, N. J. et al. (2006), “Distributed Practice in Verbal Recall Tasks.”  
   https://doi.org/10.1037/0033-2909.132.3.354
4. Karpicke, J. D. & Blunt, J. R. (2011), “Retrieval Practice Produces More Learning Than Elaborative Studying.”  
   https://doi.org/10.1126/science.1199327
5. Chi, M. T. H. et al. (1994), “Eliciting Self-Explanations Improves Understanding.”  
   https://doi.org/10.1037/0022-0663.86.4.414

The system should avoid overstating the evidence for a branded “Feynman Technique.” Its implementation is best understood as a combination of retrieval practice, self-explanation, elaboration, teach-back, feedback, and application.

---

## 22. Recommended technology boundaries

### Required conceptual layer

- Markdown.
- YAML frontmatter.
- Agent skills/prompts.
- File search.
- User confirmation.

### Optional helper layer

Use a small Python utility only for:

- PDF/DOCX/EPUB extraction.
- OCR.
- Image extraction.
- Chunking.
- Embedding generation.
- Milvus Lite operations.

### Avoid initially

- LangChain.
- LlamaIndex.
- FastAPI.
- ChromaDB.
- Hosted databases.
- A web frontend.
- A mobile application.
- A multi-agent architecture.
- A complex ORM.

These may become useful later, but none is necessary to prove the portable learning workflow.

---

## 23. Final recommended first deliverable

The first actual implementation package should contain:

```text
portable-learning-system/
├── README.md
├── protocol/
│   ├── data-conventions.md
│   ├── citation-policy.md
│   ├── learning-policy.md
│   └── safety-policy.md
├── skills/
│   ├── workspace-init.md
│   ├── catalog.md
│   ├── source-ingest.md
│   ├── teach.md
│   ├── study-session.md
│   ├── active-recall.md
│   ├── feynman-teachback.md
│   ├── application-practice.md
│   ├── confusion-review.md
│   ├── progress.md
│   └── index-maintenance.md
├── prompts/
│   ├── tutor.md
│   ├── question-generation.md
│   ├── answer-evaluation.md
│   ├── feedback.md
│   ├── feynman-followup.md
│   ├── metadata-extraction.md
│   ├── conflict-analysis.md
│   └── recommendations.md
├── schemas/
│   ├── topic.md
│   ├── source.md
│   ├── path.md
│   ├── session.md
│   ├── confusion-item.md
│   └── progress.md
├── adapters/
│   ├── pi.md
│   ├── claude-code.md
│   ├── codex-cli.md
│   ├── gemini-cli.md
│   ├── cursor.md
│   ├── opencode.md
│   ├── copilot-cli.md
│   └── hermes.md
└── tools/
    ├── README.md
    ├── ingest-interface.md
    └── index-interface.md
```

This deliverable should still be documentation and protocol first. The helper tools can be implemented afterward, beginning with ingestion and Milvus Lite because those are the areas where an agent alone is least reliable for large books and complex documents.

---

## 24. Definition of success

The system is successful when the user can move the same learning workspace between compatible agent harnesses and say:

- “What can I study?”
- “Teach me this topic.”
- “Quiz me using Feynman mode.”
- “Give me an application problem.”
- “Review my confusion list.”
- “Where exactly should I reread?”
- “What should I study next?”
- “Resume yesterday’s session.”
- “Rebuild the index.”

…and receive consistent, source-grounded behavior with readable Markdown records, actionable recommendations, and no dependence on hidden conversation memory or a particular vendor’s agent framework.
