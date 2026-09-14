# Phase 3: Write the Area Documents

One requirements document per work area. Each one stands alone as a planning origin — a planning agent reads it without needing the other areas' documents or this conversation.

## Filename (hard contract)

```
rosey/brainstorms/<area-id>-requirements.md
```

**No date prefix.** The parallel runner derives this exact path from the area id when it wires each task to its origin document. A date-prefixed filename does not match, so the runner writes a thin projected stub alongside your real document, the stub wins as the task's origin, and everything written here is orphaned.

The area id must survive the transform unchanged: lowercase letters, digits, and hyphens only. `user-panel-crud-api` produces `rosey/brainstorms/user-panel-crud-api-requirements.md`.

Write to the flat directory only — never a subdirectory.

## Frontmatter

```yaml
---
date: YYYY-MM-DD
topic: <area-id>
---
```

`topic` is the area id verbatim, so the filename and the frontmatter agree. Never rename these fields or repurpose their semantics; adding fields is fine.

## Hard floor

These are always present in every area document.

- **Summary** — what this area delivers, in 1-3 lines. Forward-looking. **Make it distinctive.** Several sibling documents share one flat directory, and a planning run may need to tell them apart on Summary alone — name the specific outcome, not the epic. "Read and edit views for user records" is distinctive; "part of the user panel work" is not.
- **Requirements** (with stable R-IDs) — what must be true about this area. Group under bold inline headers when they span distinct concerns; R-IDs stay continuous across groups.
- **Scope Boundaries** — what this area does not cover, including **an explicit sibling-area exclusion**. Name the other areas of this epic and state that their work is out of scope here. Without it, a planning run against one area can absorb another area's work and two parallel tasks collide.
- **How This Work Fits Together** — this area's place in the epic: what it consumes from which sibling areas, what consumes it, and what it deliberately assumes about their shape. This is where the declared dependencies become readable prose.

## Include when material

- **Problem Frame** — why this area exists, when the Summary alone leaves it unclear.
- **Key Decisions** — decisions made during dialogue, with rationale.
- **Actors** (A-IDs) — when more than one actor touches this area, or the actor is non-obvious.
- **Key Flows** (F-IDs) — when the area has a multi-step path worth naming.
- **Acceptance Examples** (AE-IDs) — concrete cases that demonstrate the requirements. Strongly preferred: each area must be independently verifiable, and acceptance examples are what make that checkable.
- **Success Criteria** — when success is measurable and not already implied by the requirements.
- **Dependencies and Assumptions** — external dependencies, and every bet recorded rather than validated.
- **Outstanding Questions** — split into questions that must be resolved before planning and questions deferred to planning.

## ID and content rules

- **Stable IDs.** R-IDs (Requirements), A-IDs (Actors), F-IDs (Flows), AE-IDs (Acceptance Examples). **No other ID namespaces** — downstream planning reads these four and nothing else. Area identity lives in the filename and the area list, never as an in-document ID.
- **Plain prefix.** `R1.`, `A1.`, `F1.`, `AE1.` as bullet prefixes. Do not bold them.
- **IDs are per-document.** Each area starts at `R1`. They are not continuous across the epic.
- **Repo-relative paths.** Always. Never absolute paths.
- **No implementation detail by default.** Libraries, schemas, endpoint shapes, file layouts, and code structure stay out. Downstream planning decides those. The exception is a decision that is itself architectural and was settled in dialogue — then it is a Key Decision with its rationale.
- **No process exhaust.** No "captured at Phase X" notes, no next-steps sections pointing at another skill, no italic provenance lines.

## Write tight

A section being material is not license to pad it. Lead with the decision or outcome, one idea per sentence, a requirement is intent plus at most one qualifier. Defer forks to Outstanding Questions rather than specifying both arms. Depth matches what the dialogue produced — a thin area gets a thin document, and that is correct.

## Summary vs. Problem Frame

Summary answers "what does this area deliver?" — forward-looking, 1-3 lines. Problem Frame answers "why does this area exist?" — backward-looking, paragraphs. Don't restate the proposal in Problem Frame; don't pad Summary with situational context.

## Before moving on

Confirm every area document exists at its exact contracted path, that each Summary reads distinctly from its siblings, and that each Scope Boundaries section names the sibling areas it excludes.
