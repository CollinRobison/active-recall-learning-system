# Skill: remove learning records

## Purpose
Safely remove one canonical source, topic, or learning path from a workspace without deleting unrelated curriculum content.

## Procedure
1. Identify the exact canonical record ID using `learning list WORKSPACE` or dashboard records. Do not guess IDs.
2. Preview the relationship-aware impact first:

   ```bash
   learning remove WORKSPACE RECORD_ID
   ```

3. Report the planned deleted sources/topics/paths/sessions and the records whose associations will be pruned. State that the original input book/file outside the workspace is not affected.
4. Obtain the learner's explicit approval of that exact preview. Then execute:

   ```bash
   learning remove WORKSPACE RECORD_ID --confirm
   ```

5. Report that the lexical manifest was rebuilt, the optional local vector cache was cleared, and the dashboard was refreshed. If vector retrieval is wanted again, run `learning vector-reindex WORKSPACE ...` with the learner's configured embedding provider.

## Cascading policy

- Removing a source removes topics only when it was their last source association.
- Paths survive when they still contain another topic or source; only removed associations are pruned.
- A path is deleted only after it has neither topics nor sources.
- Single-scope sessions, related confusion records, and review entries for removed records are removed. Mixed-scope sessions are retained with the removed scope pruned.
- Removing a topic/path follows the same policy for remaining references.

## Safety

- This is permanent canonical-data deletion after confirmation. Never add `--confirm` from an ambiguous request.
- Do not delete original files outside the workspace.
- Do not bypass the CLI for removal: it owns reciprocal-reference cleanup, derived-index invalidation, and dashboard regeneration.
