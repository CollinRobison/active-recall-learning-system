---
name: learning-dashboard
description: "Use when a learner wants a local, queryable workspace dashboard."
---

# Learning dashboard

Generate a read-only HTML snapshot of a learning workspace when the learner asks for a visual overview of progress, topics, paths, sources, sessions, or confusion.

## Agent workflow

1. Identify the learning workspace from the request or configured context.
2. Check whether `<workspace>/dashboard.html` exists.
3. If it is missing, create it immediately:

   ```bash
   learning dashboard WORKSPACE
   ```

4. If it already exists but the learner asks for current information, regenerate it with the same command. This reads canonical Markdown records and overwrites only `dashboard.html`; it does not change sources, topics, paths, sessions, reviews, or confusion records.
5. Tell the learner the exact local path and explain that they can open it directly in a browser. Do not claim that it live-updates: regenerate it after new study activity.

## What it shows

- source, topic, path, session, question, open-confusion, and transparent completion-percent counts;
- interactive evaluation, per-path completion, and study-activity charts;
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
