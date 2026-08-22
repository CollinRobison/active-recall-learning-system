# Copilot CLI adapter

## Install

At the repository where Copilot will operate, add a Copilot instruction file:

```sh
mkdir -p .github
cat > .github/copilot-instructions.md <<'EOF'
For active-recall learning requests, read /absolute/path/to/active-recall-learning-system/protocol/learning-policy.md and the matching skills/*.md. Citations, explicit confirmation, incremental session saves, and regenerating `learning dashboard WORKSPACE` after canonical writes are mandatory. The CLI refreshes it automatically; direct edits require the explicit command.
EOF
python -m pip install -e /absolute/path/to/active-recall-learning-system
```

## Invoke

Run Copilot CLI from that repository and ask `Use the active-recall active-recall skill for WORKSPACE` or `Use source-ingest for INPUT`. It may call helpers such as `learning session-start WORKSPACE --scope-id TOPIC`; it must not use web research or mutate canonical records without confirmation.
