# Skill: catalog

## Purpose
Answer what the learner can study and rank useful next options.

## Files to read
`catalog/*.md`, topic/source/path records, due reviews, open confusion items, and progress summaries.

## Procedure
1. Parse available records and exclude archived items unless requested.
2. Filter by the user's scope, tags, source, path, or prerequisites. Do not recommend a topic whose prerequisite is neither marked `completed` nor supported by two persisted correct evaluations with no open confusion item.
3. Rank due confusion/reviews, weak but important concepts, uncovered material, and path order.
4. Present a balanced menu with a reason and exact record/source location for each recommendation.

## Output contract
Use readable sections for topics, sources, paths, due work, open confusion, and recommended next actions. Do not return an unranked directory listing.

## Confirmation and safe edits
Treat inferred relationships as suggestions. Ask before creating or changing catalog structure. Preview a canonical topic edit (relationships or lifecycle status) before applying it; only write after explicit confirmation. The runtime exposes this as `learning topic-edit WORKSPACE TOPIC_ID ...` and requires `--confirm` to write. It validates every referenced ID, prevents prerequisite cycles, and keeps source `topic_ids` reciprocal with the topic's `source_ids`.

Creating a topic or path from explicit user input is a confirmed creation. Do not overwrite human notes while editing catalog metadata.

## Removal

Use [`remove-learning-records.md`](remove-learning-records.md) for destructive curriculum changes. Agents must preview `learning remove WORKSPACE RECORD_ID`, obtain explicit approval of the impact plan, and only then use `--confirm`; do not directly unlink catalog records because reciprocal associations, dependent artifacts, indexes, and the dashboard need coordinated cleanup.
