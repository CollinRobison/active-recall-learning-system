---
name: learning-dashboard
description: "Use when a learner wants a local, queryable workspace dashboard."
---

# Learning dashboard

Generate a read-only HTML snapshot of a learning workspace when the learner asks for a visual overview of progress, topics, paths, sources, sessions, or confusion.

## Agent workflow

1. Identify the learning workspace from the request or configured context.
2. CLI-driven canonical creation/update actions automatically create or refresh `<workspace>/dashboard.html` after a successful write. Do not run a second dashboard command merely because an ordinary CLI action completed.
3. **Direct-write requirement:** if you bypass the CLI and create, edit, move, or resolve canonical source/topic/path/session/review/progress/confusion records yourself, immediately run:

   ```bash
   learning dashboard WORKSPACE
   ```

   Do this after the canonical write is successful. Do not treat dashboard-generation failure as a reason to undo the learning-state write; report the dashboard failure separately.
4. If the learner asks for current information after external/manual edits, regenerate with the same command. It reads canonical Markdown records and overwrites only `dashboard.html`.
5. Tell the learner the exact local path and explain that the static HTML is automatically refreshed by CLI actions but requires regeneration after external direct edits; it does not live-watch files.

## What it shows

- source, topic, path, session, question, open-confusion, and transparent completion-percent counts;
- interactive evaluation, per-path completion, and study-activity charts, all scopeable to the workspace, a topic, a learning path, or a source;
- queryable/filterable topics, paths, content records, open/resolved confusion records, and sessions; the **Explore all** view searches and filters across every record class at once;
- source/topic/path associations, prerequisites, extraction provenance, and record paths;
- a compact copyable progress summary.

## Safety and portability

- The dashboard is a derived, read-only snapshot. Canonical workspace Markdown remains authoritative.
- It is self-contained: opening `dashboard.html` does not require a web server, database, credentials, or network access.
- It can be committed to a private learning repo if the learner wants the snapshot shared; otherwise add `dashboard.html` to that workspace's `.gitignore`.
- Do not interpret dashboard totals as an objective mastery score. Review source-grounded evidence and open confusion before recommending an action.

## Verification

After generation, verify the file exists. If browser tooling is available, open it and check that the overview and at least one record filter render without console errors.
