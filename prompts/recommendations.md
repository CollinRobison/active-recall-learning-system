# Prompt contract: recommendations

Rank next actions from explicit evidence: due dates, severity, recurrence, path order, source coverage, confidence calibration, and recent performance.

Each recommendation must include:

```yaml
action: reread | explain | compare | apply | retry | new-topic
reason: ...
priority: high | medium | low
scope_id: ...
source_locations: []
evidence_ids: []
expected_evidence: recall | explanation | application | delayed-review
```

Do not present a single uncalibrated mastery score as truth. Say when a recommendation is inferred or source location is approximate.
