# Pi adapter

## Install

Put a project instruction in the directory where Pi is launched:

```sh
printf '\nFor active-recall requests, read /absolute/path/to/active-recall-learning-system/protocol/learning-policy.md and applicable /absolute/path/to/active-recall-learning-system/skills/*.md. Preserve citations, confirmations, incremental state, and regenerate `learning dashboard WORKSPACE` after every successful write to canonical workspace records (the CLI does this automatically; direct edits require the explicit command).\n' >> AGENTS.md
python -m pip install -e /absolute/path/to/active-recall-learning-system
```

## Invoke

Launch Pi from that directory and say `Use active-recall study-session for WORKSPACE` (or the named skill). Pi can execute `learning ingest INPUT --workspace WORKSPACE`, `learning reindex WORKSPACE`, and other documented helpers. The workspace is not this protocol checkout; name it explicitly in each request.
