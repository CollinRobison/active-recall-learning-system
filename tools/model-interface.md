# Model adapter interface

Model-driven tutoring is opt-in. The core never sends source material to a provider unless the user or harness explicitly invokes a provider.

## Local command contract

Configure `--provider-command` with an argv-style command. The runtime writes one JSON request to stdin:

```json
{
  "system": "source-grounded tutor rules",
  "user": "JSON-encoded objective, answer, and retrieved evidence",
  "response_format": "json"
}
```

The command must write one JSON object to stdout. It must not print logs to stdout; diagnostics belong on stderr. The question contract is defined in `prompts/question-generation.md`; evaluation uses `prompts/answer-evaluation.md`.

## OpenAI-compatible endpoint

`OpenAICompatibleProvider` supports an explicitly configured endpoint. The API key is read from an environment variable (default `ACTIVE_RECALL_MODEL_API_KEY`) and is never written to workspace files or logs. CLI use requires `--allow-network`.

## Grounding safeguards

- Retrieved evidence is included in the request with source ID and location metadata.
- Responses that cite sources not in retrieved evidence are rejected.
- Missing or inadequate context produces an error rather than an invented answer.
- Model output is validated before it can be saved as a session turn.
- Provider name, model, and external status should be recorded by a harness when creating a session.
