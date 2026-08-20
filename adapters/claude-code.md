# Claude Code adapter

## Install

From the protocol repository root, make the package visible to the project:

```sh
mkdir -p .claude/skills
ln -sfn ../../skills .claude/skills/active-recall
ln -sfn ../../protocol .claude/skills/active-recall-protocol
```

If symlinks are unsuitable, copy those directories instead. Keep this repository and the learning workspace separate.

## Invoke

In Claude Code, say `Use the active-recall study-session skill for WORKSPACE` (or `source-ingest`, `catalog`, `teach`, etc.). Claude reads `.claude/skills/active-recall/<skill>.md`, the linked protocol, and performs the specified file/tool operations. For runtime helpers use `learning init WORKSPACE`, `learning ingest INPUT --workspace WORKSPACE`, and the commands documented in `README.md`.

Require confirmation before canonical metadata/path edits or network access; save every turn before asking the next question.
