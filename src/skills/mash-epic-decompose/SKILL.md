---
name: mash-epic-decompose
description: Decompose an epic or requirements document into a parallel-aware task list for mash-parallel, then hand it off automatically. Use when the user has an epic, requirements doc, audit, or multi-part goal and wants it run through the Mash Programming Skills pipeline in parallel — before invoking mash-parallel. Emits a validated run-inputs.json and starts the run.
---

# Mash Programming Skills Epic Decompose

## What this skill does

Turns an epic / requirements doc / audit / multi-part goal into a **task list that parallelizes well**, then hands it straight to `mash-parallel`. It is the pre-skill that closes the gap between "a validated epic" and "a task list mash-parallel can actually run in parallel."

`mash-parallel` assumes the task list arrives validated and file-disjoint. If the decomposition hands it tasks that all touch the same files, the sequencer correctly serializes them onto one track — and you get the *sum* of durations, not the longest track. This skill exists so that never happens.

## When to use

- User has an epic, requirements doc, brainstorm output, audit, or multi-part goal and wants it executed through the Mash Programming Skills pipeline in parallel.
- User is about to invoke `mash-parallel` but the task list does not exist yet, or exists but was not decomposed for parallelism.
- Do **not** use for a single task, or for a task list that already exists and is already parallel-aware.

## Output contract

Emit a `run-inputs.json` matching `mash-parallel`'s schema:

```json
{
  "tasks": [
    { "id": "t1", "goal": "…", "deps": [] },
    { "id": "t2", "goal": "…", "deps": ["t1"] }
  ],
  "base_branch": "develop",
  "max_parallel": 4,
  "timeout_budget": 1800,
  "harness": "pi"
}
```

- `id`: short, unique, lowercase-hyphen slug.
- `goal`: one sentence, independently verifiable, no cross-task references.
- `deps`: optional list of task ids this task depends on (cross-task constraints file overlap cannot infer, e.g. "t2 consumes the type t1 adds"). Default `[]`.
- `base_branch`: default `develop` unless the user says otherwise.
- `max_parallel` / `timeout_budget` / `harness`: optional; only set when the user specifies or the epic scale demands it.

Write it to `.mash/parallel/epics/<run-slug>/run-inputs.json` (create the dir), then invoke `mash-parallel` with that file.

## Decomposition rules (the core)

Decompose **for parallelism**, not just for correctness. Four properties, in priority order:

### 1. File-disjointness (the critical one)

Each task should touch a **disjoint** set of files. This is what makes tracks run in parallel. For each task, name the files it will likely touch (a rough footprint). Two tasks that both touch `auth.py` are one track, not two.

- If two tasks share a file, either merge them into one task, or split the shared file's responsibility so each task owns a distinct part.
- A task that touches a shared *interface* (a type, a schema, a signature) is a **contract task** — see rule 4.

### 2. Declared dependency edges

Surface cross-task constraints that file overlap cannot infer. If task B consumes something task A adds (a type, a function, a schema), declare `deps: ["A"]`. Do not leave these to be discovered mid-run — that is what turns a clean parallel run into a serial cascade.

### 3. Right granularity

Match the epic's scale. `mash-parallel` is tuned for **2–5 tasks typical, ~20–23 edge**.

- Too coarse (one task = whole epic) → no parallelism.
- Too fine (dozens of micro-tasks) → coordinator context pressure and per-task overhead dominate.
- If the epic is genuinely one cohesive change, say so and do not force a split.

### 4. Independent verifiability + contract tasks

Each task must be independently qa-able, so `mash-parallel`'s evidence gate can actually gate it. A task is not "done" until it emits evidence.

When several tasks share a contract (interface, types, schema, stubs), emit a **contract task** first that owns that shared surface, and make the consumers depend on it. This mirrors `mash-parallel`'s scaffold phase (R10) — the contract is defined once before executors fan out.

## Workflow

Bias toward **asking, not guessing**. Under-asking silently produces a bad schedule (wrong footprints collapse tracks to serial); over-asking only costs a few questions. Default to surfacing ambiguity.

1. **Look first** — read the repo to derive what is derivable: stack/framework, module structure, existing design system, where a change would land. The repo answers "where does the page live"; it does *not* answer "what does CRUD mean for this domain" or "what does design mean." Derive what you can, then ask what remains.
2. **Enumerate every decomposition decision** — task boundaries, per-task footprints, and dependency edges. For each, decide: is it repo-derived, or does it need the user? Ask the ones that need the user. Do not skip a decision just because a plausible guess exists.
3. **Ask the repo-unresolved decisions** — one question per unresolved task-boundary / footprint / dep. Err toward asking. If the user's answer is vague, ask a follow-up rather than guessing.

   Ask with the `AskQuestion` tool, one question at a time, in this shape:
   - **Options you generate** — 2–4 concrete named options per question, each a real answer to the decision (e.g. for "what does design mean": "reuse the existing design system", "build new components from scratch", "a mix — reuse tokens, new page components").
   - **Always recommend one** — put your recommended option first and mark it `(Recommended)`.
   - **Always include the escape** — every question ends with an option like "I don't know — I want to discuss it further." When the user picks it, discuss the decision with them until it resolves, then re-ask. Do not guess.
4. **Check disjointness** — walk the confirmed footprints. Any overlap → merge, split, or promote to a contract task. Confirm the resolution with the user if it changes a footprint.
5. **Validate** — unique ids, no self/unknown/cyclic deps, every task independently verifiable, granularity matches scale.
6. **Emit** `run-inputs.json` to `.mash/parallel/epics/<run-slug>/`.
7. **Hand off** — invoke `mash-parallel` with the file. Report the task list, the expected track count, and any contract tasks.

### Divergence detector

If the user's answers **spawn new unknowns faster than they resolve** (each answer opens two more questions), stop and say so: "This epic is too under-specified to decompose reliably — it needs a proper brainstorm, not a decompose." Do not ask forever. This is a divergence check, not a question-count cap.

## Example

Epic: "Add user auth with JWT, a profile page, and an admin dashboard."

- `t1` — contract: define the auth types + token schema. Footprint: `auth/types.py`. deps: `[]`.
- `t2` — JWT login/logout endpoints. Footprint: `auth/routes.py`. deps: `["t1"]`.
- `t3` — profile page (frontend). Footprint: `frontend/profile/`. deps: `["t1"]`.
- `t4` — admin dashboard (frontend). Footprint: `frontend/admin/`. deps: `["t1"]`.

`t2`, `t3`, `t4` are file-disjoint → three parallel tracks after `t1`. If `t3` and `t4` both touched `frontend/shared/`, they'd collapse to one track — so keep shared UI out of both, or make a shared-component task.

## Additional resources

- For the full decomposition heuristics and edge cases, see [references/decomposition.md](references/decomposition.md).
- For `mash-parallel`'s exact input contract and pipeline, see `../mash-parallel/SKILL.md`.
