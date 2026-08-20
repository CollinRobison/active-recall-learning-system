# Skill: catalog

## Purpose
Answer what the learner can study and rank useful next options.

## Files to read
`catalog/*.md`, topic/source/path records, due reviews, open confusion items, and progress summaries.

## Procedure
1. Parse available records and exclude archived items unless requested.
2. Filter by the user's scope, tags, source, path, or prerequisites.
3. Rank due confusion/reviews, weak but important concepts, uncovered material, and path order.
4. Present a balanced menu with a reason and exact record/source location for each recommendation.

## Output contract
Use readable sections for topics, sources, paths, due work, open confusion, and recommended next actions. Do not return an unranked directory listing.

## Safety
Treat inferred relationships as suggestions. Ask before creating or changing catalog structure.
