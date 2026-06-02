---
description: Task and Memory best practices
---

# Task-Driven Workflow

> **Adapted from the parent accelerator's `memory-workflow.instructions.md`.** The original assumes both `todo-md` and `memory` MCP tools are available. In this repo, default to `/memories/session/` files (via the `memory` tool that ships with VS Code Copilot) for in-progress notes, and `/memories/repo/` for repository-scoped knowledge. The MCP `memory` graph tool may also be used if configured.

## 1. Break down work into a series of high-level tasks

- Capture each task in [`.docs/specs/<spec>/tasks.md`](../../.docs/specs/) with a stable ID (e.g. `T0001-01`).
- Mirror in-progress tasks into `/memories/session/active-task.md` so a new agent session can resume.
- Update the todo list (via the `manage_todo_list` tool when available) as you work; mark items completed immediately when done.

## 2. Resume work from prior session

When asked to resume work:

1. Read `/memories/session/active-task.md` for the most recent state.
2. Read the active spec's `tasks.md` for the canonical task list and completion markers.
3. Use `manage_todo_list` to rebuild the in-context todo array.
4. Pick the next uncompleted task and proceed.

## 3. Record decisions immediately after discovery

For repo-wide insights, append a bullet to `/memories/repo/doc-ingest-pipeline.md`.
For decisions that change the product direction or override a previous one, add a new ADR to [`.docs/product/decisions.md`](../../.docs/product/decisions.md) using the `DEC-XXX` schema.

## 4. Plan and track progress incrementally

After completing each meaningful step:

- Update the `manage_todo_list` entry.
- If the step established a new pattern or workaround that future sessions would benefit from, write a short bullet into `/memories/repo/` or `/memories/session/`.
- Keep these notes **short** (one line per fact) — they are loaded into context automatically.

## 5. Close out cleanly

When finishing a spec:

1. Mark every task `[x]` in tasks.md.
2. Flip the spec.md `Status:` header to `Complete` once the PR merges.
3. Update [`component-reuse-map.md`](../../component-reuse-map.md) Notes column with the parent commit SHA for any files ported from the upstream accelerator.
4. Append a one-line completion entry to `/memories/repo/doc-ingest-pipeline.md`.
5. Remove the corresponding `/memories/session/` notes if they were spec-specific.

## 6. Cleanup

Prune `/memories/session/` files when the conversation that wrote them ends — they are not meant to persist forever. Keep `/memories/repo/` lean: one fact per line, organized by topic.

## Chaining Rule of Thumb

**Fetch → Validate → Write → Link → Log → Summarize → (optionally) Prune**

Every write should be immediately followed by a back-reference (e.g. linking a new ADR to the spec that drove it). Every major step should append an observation to the active-task note for traceability.
