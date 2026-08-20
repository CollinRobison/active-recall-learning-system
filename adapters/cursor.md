# Cursor adapter

## Install

Create a Cursor project rule that points at the portable core:

```sh
mkdir -p .cursor/rules
cat > .cursor/rules/active-recall.mdc <<'EOF'
---
description: Markdown-first active-recall learning protocol
globs: ["**/*"]
alwaysApply: false
---
For learning tasks, read /absolute/path/to/active-recall-learning-system/protocol/learning-policy.md and the applicable skills/*.md from that repository. Preserve citations, confirmations, and incremental session saves.
EOF
python -m pip install -e /absolute/path/to/active-recall-learning-system
```

## Invoke

In Cursor Agent chat, use `Apply the active-recall rule and run the study-session skill for WORKSPACE`. Use terminal helper commands such as `learning progress WORKSPACE`; confirm canonical metadata/path edits and all external research before execution.
