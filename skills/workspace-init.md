# Skill: workspace-init

## Purpose
Create or select a local learning workspace without destroying existing files.

## When to use
When the user asks to set up, initialize, move, or inspect a learning workspace.

## Required inputs
Workspace path, or permission to use the default `~/Learning/`.

## Procedure
1. Confirm the path and inspect whether it already contains learning records.
2. If new, create the layout in `protocol/data-conventions.md` and starter README/config/catalog files.
3. Create `.learningignore` before ingesting anything.
4. If existing, do not reorganize automatically; report discovered records and propose changes.
5. Ask for the first topic/source or offer a demonstration with a small Markdown passage.

## Output contract
Report workspace path, created/existing directories, configuration defaults, and any warnings.

## Files to write
Workspace scaffolding only, plus a setup summary. Do not create canonical topic relationships without confirmation.

## Safety and failure handling
Do not copy source files by default. Stop before modifying an existing workspace if the path is ambiguous or contains unrelated data.
