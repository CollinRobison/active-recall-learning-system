# Prompt contract: answer evaluation

Judge the learner answer against supplied source evidence, not unsupported memory. Credit correct alternative wording and separate correctness from completeness and clarity.

Return exactly these conceptual fields:

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
needs_more_context: false
```

If source context is inadequate, set `classification: unsupported`, `needs_more_context: true`, and do not invent a grade or citation.
