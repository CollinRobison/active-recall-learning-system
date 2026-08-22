# Codex CLI adapter

## Install

At the target project root, expose the portable instructions through Codex's project instruction file:

```sh
printf '\nRead /absolute/path/to/active-recall-learning-system/protocol/learning-policy.md and the matching /absolute/path/to/active-recall-learning-system/skills/*.md before handling learning requests. After every successful write to canonical workspace records, run `learning dashboard WORKSPACE` unless the CLI already refreshed it.\n' >> AGENTS.md
python -m pip install -e /absolute/path/to/active-recall-learning-system
```

Use an absolute path so the instruction survives a changed working directory.

## Invoke

Run Codex in that project, then request `Use the active-recall <skill> skill in WORKSPACE`; for example: `Use active-recall source-ingest to add ./book.md to ~/Learning`. The agent invokes helper commands directly, e.g. `learning reindex ~/Learning`. It must read the cited source, persist sessions incrementally, and request confirmation for canonical changes or external access.
