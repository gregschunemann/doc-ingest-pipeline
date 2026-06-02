---
description: Sequential Thinking
---

# Purpose
Drive the MCP tool **sequentialthinking** with a deterministic, no-deviation state machine to maximize branching/revision features and produce a single correct answer.

# Tool Contract (authoritative)
- name: `sequentialthinking`
- required args (every call): `thought: string`, `thoughtNumber: integer>=1`, `totalThoughts: integer>=1`, `nextThoughtNeeded: boolean`
- optional args: `isRevision?: boolean`, `revisesThought?: integer>=1`, `branchFromThought?: integer>=1`, `branchId?: string`, `needsMoreThoughts?: boolean`

# Guardrails (must obey)
1) **Monotonic counter**: start `t=1`; increment by exactly 1 on every call (linear, branch, or revision).
2) **Estimate discipline**: ensure `T >= t`; if not, set `T = t`.
3) **Branching**: if branching, **always** pass both `branchFromThought=<origin>` and a stable `branchId` reused for that branch.
4) **Revision**: if revising, set `isRevision=true` and `revisesThought=<n>`; still increment `t`.
5) **Stop switch**: set `nextThoughtNeeded=false` **only** on the final synthesis step.
6) **No hidden thought steps**: every reasoning hop triggers exactly one tool call.

# Minimal State
- `t` (current thoughtNumber), init `1`
- `T` (totalThoughts estimate), init a small, honest estimate (e.g., `5`)
- `branches` (set/map of known branchIds), init empty
- `done` (bool), init `false`

# Loop (deterministic)
While `done == false`:
1. **Plan** the next step text for `thought`:
   - Linear progress, or
   - Start/continue a branch (choose/retain `branchId`), or
   - Do a revision (`isRevision`, `revisesThought`).
2. **Assemble arguments** (always include required fields):
   - `thought`, `thoughtNumber=t`, `totalThoughts=T`, `nextThoughtNeeded=true`
   - Add **either** branch fields **or** revision fields if applicable (never both in the same call).
3. **Call** tool `sequentialthinking` with the JSON arguments.
4. **Parse response** JSON and update local state.
5. **Advance**: `t = t + 1`.

# Finalization
When ready to answer, issue **one last** call with `nextThoughtNeeded=false`, then emit the final answer to the user (no further tool calls).

# Pre-Call Checklist (every step)
- [ ] `thought` is a single, clear action (derive, test, compare, decide, etc.).
- [ ] `t` increments by 1 since last call.
- [ ] `T >= t` (if not, set `T=t`).
- [ ] If branching: include **both** `branchFromThought` and persistent `branchId`.
- [ ] If revising: include `isRevision=true` and `revisesThought`.
- [ ] Not mixing branch + revision flags in the same step.
- [ ] `nextThoughtNeeded=true` unless this is the final synthesis step.

# Prohibited
* Skipping a tool call for any reasoning step.
* Setting `nextThoughtNeeded=false` before synthesizing.
* Branching without both `branchFromThought` and `branchId`.
* Rewriting history without `isRevision`/`revisesThought`.
