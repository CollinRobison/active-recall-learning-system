# Skill: study-session

## Purpose
Run a resumable, one-question-at-a-time study session and persist evidence.

## Procedure
1. Ask only missing setup fields: scope, mode, objective, length, difficulty.
2. Create the session record before the first question.
3. Select one concept, ask one question, and wait for the answer.
4. Capture confidence when useful; evaluate with `prompts/answer-evaluation.md`.
5. Provide feedback and citations; create/merge confusion and schedule review as needed.
6. Save after every turn. Handle `pause`, `stop and save`, `retry`, `skip`, and mode changes explicitly.
7. On resume, read the session and related records, reconcile any pending turn, and continue without losing evidence.
8. Complete only with a summary and next recommendation.

## Output contract
A valid session record with status, setup, turn evidence, citations, confusion/review actions, and summary.

## Safety
Do not rewrite prior turns. Preserve the old record if an update fails.
