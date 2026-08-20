# Prompt contract: source conflict analysis

Compare only the supplied passages. Do not silently reconcile contradictory claims.

Return:

```yaml
conflict: true | false
claims:
  - source_id: ...
    location: ...
    claim: ...
    authority: ...
analysis: ...
impact_on_objective: low | medium | high
recommended_action: prefer-authority | ask-user | teach-both | research-with-permission
citations: []
```

Respect user-marked authority within its declared scope and preserve both positions in the record.
