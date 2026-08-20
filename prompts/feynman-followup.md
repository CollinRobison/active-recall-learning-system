# Prompt contract: teach-back follow-up

Given the learner's explanation and source context, ask one targeted follow-up that probes why, how, consequence, boundary, or counterexample. Prefer the smallest question that distinguishes omission from misconception.

Return:

```yaml
follow_up: ...
probe_type: why | how | what-if | compare | example | boundary
concept_id: ...
source_support: []
reason: concise educational rationale
```

Never smuggle the correction into the question. If the explanation is factually false, the next feedback turn must stop the false branch and repair it clearly.
