# Prompt contract: question generation

Generate one question for the requested scope and mode. Use only supplied source context and explicit workspace evidence unless external use is approved.

Return:

```yaml
question: ...
concept_id: ...
objective: ...
question_type: factual | conceptual | procedural | application | comparison
expected_evidence: []
difficulty: 1-5
source_support: []
needs_more_context: false
```

Prefer important, uncovered, or due concepts. Do not reveal the answer in wording. Include citation-ready source locations in `source_support`.
