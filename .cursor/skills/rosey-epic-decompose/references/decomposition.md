# Decomposition heuristics

Deeper guidance for the four rules in `SKILL.md`. Read this when a decomposition is ambiguous or the epic is large.

## Asking bias

Default to **asking, not guessing**. Under-asking is the dangerous failure mode: a skipped question becomes a guessed footprint, and a wrong footprint collapses tracks to serial — silently. Over-asking only costs the user a few questions. So enumerate every decomposition decision and ask the ones the repo does not definitively resolve.

The question set is bounded by the decomposition decisions, not by the user's patience:

- **Task boundaries** — what are the distinct deliverables? (e.g. page vs CRUD vs design: one task or three?)
- **Per-task footprints** — for each task, which files does it touch? Where does it live?
- **Dependency edges** — what cross-task constraints exist that file overlap cannot infer?
- **Shared surfaces** — do multiple tasks touch the same components/types? (the disjointness question)

Ask a question only when the repo cannot answer it. The repo answers "where does the page live" (module structure); it does not answer "what does CRUD mean for this domain" or "what does design mean." Those are exactly the questions to ask.

### Question shape

Ask with the `AskQuestion` tool, one decision per question:

- **Options you generate** — 2–4 concrete named options per question, each a real answer to the decision. Do not use generic "yes/no" options; name the actual choices.
- **Always recommend one** — put your recommended option first, marked `(Recommended)`.
- **Always include the escape** — every question ends with an option like "I don't know — I want to discuss it further." When picked, discuss the decision with the user until it resolves, then re-ask. Never guess.

Example for "what does design mean":

- Reuse the existing design system (Recommended)
- Build new components from scratch
- A mix — reuse tokens, build new page components
- I don't know — I want to discuss it further

### Divergence detector

If answers spawn new unknowns faster than they resolve (each answer opens two more questions), stop and declare the epic under-specified — it needs a brainstorm, not a decompose. This is a divergence check, not a question-count cap.

## Footprint estimation

A footprint is a **best-effort prediction** of the files a task will touch. It is not a plan — `rosey-parallel` re-derives real footprints from each task's plan and re-sequences. Your job is to make the *likely* footprints disjoint so the sequencer has something to parallelize.

Estimate from:

- The deliverable's natural module boundaries (a route file, a component dir, a schema).
- Existing code structure — where would this change land?
- The epic's own grouping (if the epic already names modules, honor them).

## When to merge vs split

| Signal | Action |
| --- | --- |
| Two tasks touch the same file | Merge them, or split the file's responsibility so each owns a distinct part |
| A task is a whole epic | Split it |
| A task is a micro-step (one function) | Merge it into its parent |
| Many tasks share one interface | Promote the interface to a contract task; consumers depend on it |

## Contract tasks

A contract task owns a shared surface (types, schemas, interfaces, stubs) that several other tasks consume. It runs first; consumers depend on it. This mirrors `rosey-parallel`'s scaffold phase (R10).

Rules:

- One contract task per shared surface, not one per consumer.
- A contract task must be small and independently verifiable (the interface compiles / the schema validates).
- If two consumers need *different* parts of a surface, split the surface so each consumer's contract is disjoint.

## Dependency declaration

Declare a dependency only when file overlap cannot express the constraint:

- "t2 consumes the type t1 adds" → `deps: ["t1"]`.
- "t2 and t3 both edit `auth.py`" → that is overlap, not a dependency. Fix the overlap instead.

Do not over-declare. Every dependency serializes work. A dependency that is really just file overlap is a decomposition failure, not a scheduling fact.

## Granularity by scale

| Epic size | Target tasks | Notes |
| --- | --- | --- |
| Small (1–2 deliverables) | 1–3 | Often one task; do not force a split |
| Medium (typical) | 2–5 | The sweet spot for `rosey-parallel` |
| Large (audit, 20+ issues) | ~20–23 | Edge case; group related issues into tasks, keep tracks file-disjoint |

## Validation checklist

Before emitting `run-inputs.json`:

- [ ] Unique, lowercase-hyphen ids
- [ ] Every task has a one-sentence, independently verifiable goal
- [ ] No self-deps, unknown deps, or cycles
- [ ] No two parallel tasks share a footprint
- [ ] Shared interfaces are contract tasks with consumers depending on them
- [ ] Granularity matches the epic's scale
- [ ] `base_branch` correct (default `develop`)
