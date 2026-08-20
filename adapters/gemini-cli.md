# Gemini CLI adapter

## Install

Create a project instruction file containing links to the shared core:

```sh
cat > GEMINI.md <<'EOF'
For learning requests, read /absolute/path/to/active-recall-learning-system/protocol/learning-policy.md and the applicable /absolute/path/to/active-recall-learning-system/skills/*.md. Follow their confirmation, citation, and incremental-save requirements.
EOF
python -m pip install -e /absolute/path/to/active-recall-learning-system
```

## Invoke

Start Gemini CLI in the project containing `GEMINI.md`, then ask `Use active-recall teach for WORKSPACE and TOPIC` or `Use active-recall source-ingest for INPUT in WORKSPACE`. Helper invocations are ordinary commands, such as `learning query ~/Learning "concept"`. Do not enable web access or apply canonical workspace changes without the required confirmation.
