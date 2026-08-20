# Citation policy

## Default

Every source-grounded explanation, correction, evaluation, and recommendation must cite the evidence used. Citations are part of the learning record, not decorative links.

## Required citation fields

```yaml
source_id: source-example
label: Example Book
location_type: page | chapter | section | lines | url | unavailable
location: Chapter 2, pages 40-43
excerpt: "...short exact excerpt..."
source_status: user-provided | indexed | external-approved
```

Use the most precise stable location available. Preserve page and section boundaries during extraction.

## Rules

1. Judge answers against retrieved or directly read source evidence, not unsupported model memory.
2. Never invent a page, section, quote, URL anchor, or source relationship.
3. If context is insufficient, say so and retrieve/read more before grading.
4. If sources conflict, cite each position separately and mark the conflict.
5. External web or model knowledge requires user approval for the specific use and must be labeled `external-approved`; it does not silently become workspace authority.
6. Quote only the minimum excerpt needed for learning and respect source copyright.
7. A generated recommendation must cite the confusion item's source location and say when the location is inferred.

## Citation validity

A citation is valid only when the cited source record exists and the location can be found in `extracted.md`, the source URL, or the original user-provided location. If validity cannot be checked, mark `citation_status: unverified` and explain why.

## Feedback pattern

- What was correct.
- What was missing or incorrect.
- Concise correction grounded in evidence.
- Citation(s), with excerpt where available.
- Next action.

Do not store hidden chain-of-thought. Store only concise educational rationale, evidence, uncertainty, and the next action.
