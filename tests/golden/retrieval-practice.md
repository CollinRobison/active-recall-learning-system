# Golden learning case: retrieval practice

## Source fixture

```markdown
# Retrieval Practice

Retrieval practice requires recalling information without consulting the source.

## Why it works

Attempting recall exposes gaps that rereading can conceal.
```

## Question contract

```json
{
  "question": "What does retrieval practice require, and what gap can it expose?",
  "concept_id": "retrieval-practice",
  "question_type": "explanation",
  "expected_evidence": ["recalling information", "without consulting the source", "exposes gaps"],
  "source_support": ["source-golden-retrieval, section Why it works"]
}
```

## Evaluation cases

- **correct:** Explains recall without looking and that it exposes gaps.
- **partial:** Mentions recall but omits the purpose or source constraint.
- **incorrect:** Claims retrieval practice means rereading notes.
- **overconfident incorrect:** Gives that rereading claim with confidence 5/5; the evaluator must retain the calibration evidence and schedule review.
- **alternative wording correct:** Says “bring the material to mind without looking” and “reveals weak spots”; this is correct despite not repeating the reference wording.
- **conflicting source:** A second, explicitly cited source can describe a different classroom activity; report both positions rather than merge them.
- **missing context:** If the passage does not establish a claimed benefit, return insufficient evidence rather than infer it.

Every support location must be validated against an exact heading, page marker, line range, URL, or excerpt in `extracted.md`.
