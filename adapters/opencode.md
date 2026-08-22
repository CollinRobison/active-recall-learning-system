# OpenCode adapter

## Install

Add the portable-core instruction to the target repository's `AGENTS.md`:

```sh
printf '\nFor learning requests, read /absolute/path/to/active-recall-learning-system/protocol/learning-policy.md and the applicable skills/*.md in that repository. Enforce source citations, confirmation, incremental persistence, and `learning dashboard WORKSPACE` after every successful write to canonical workspace records (the CLI refreshes it automatically; direct edits do not).\n' >> AGENTS.md
python -m pip install -e /absolute/path/to/active-recall-learning-system
```

## Invoke

Start OpenCode in the repository containing `AGENTS.md`, then request `Use active-recall <skill> for WORKSPACE`. For example, `Use active-recall catalog for ~/Learning`; execute `learning recommend ~/Learning` when helper output is needed. All policy remains in the shared Markdown files rather than this adapter.
