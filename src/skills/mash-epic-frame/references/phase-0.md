# Phase 0: Memory Gate, Resume, Scope Floor, and Area Detection

Read this before anything else on every run. It carries the memory gate as well as Phase 0 itself.

## Memory gate (required check)

Before Phase 1 grounding:

1. Read [`mash-hindsight`](../../mash-hindsight/SKILL.md), run its availability check (daemon status **and** the `/version` fingerprint), then `memory recall`; OR document `Hindsight: unavailable — <reason>`. The skill owns the procedure — do not restate it.
2. Do not write any requirements document until step 1 completes or is explicitly marked unavailable.

"Unavailable" means the CLI failed — not "I skipped it."

## 0.0 Markdown Output

Requirements documents are always markdown (`.md`). Every area document follows `references/area-sections.md` for content and the repo's plain-markdown conventions for form: sentence-case headings, no decorative emphasis, repo-relative paths only.

When `mode:non-interactive` is active, preserve IDs and decision-bearing content and trim narrative.

## 0.1 Resume Existing Framing

If the user references an existing epic or there are recent area documents in `.mash/brainstorms/` that share an epic prefix:

- Read them
- Confirm with the user: "Found area documents for [epic]. Continue from these, or start fresh?"
- If resuming, summarize the current areas briefly, then continue from their existing decisions. Update the existing documents rather than creating duplicates.

In non-interactive mode, do not ask. Resume when the epic match is unambiguous; otherwise start fresh and record the choice as an assumption.

## 0.2 Scope Floor (hard stop)

**This skill frames epics. An epic has more than one separately-deliverable outcome.**

Before any dialogue, test the ambition against the separable-outcome test in 0.3. Then:

- **Two or more outcomes** — continue to Phase 1.
- **One outcome** — stop. Say plainly that this is a single feature, not an epic, and that framing it here would produce one document and a pointless parallel run. Name what the single outcome is, so the user can carry it forward. Do not write a document. Do not route anywhere automatically — the user chooses their next step.
- **Genuinely unclear** — ask one targeted question about whether the pieces could ship independently of each other, then re-test. When it stays uncertain after one question, treat it as a single feature and stop; a wrong stop costs one message, a wrong epic costs N documents and a parallel run.

In non-interactive mode, do not ask. Apply the test to the supplied description. When it yields one outcome, stop with a blocker naming the single outcome rather than framing it.

## 0.3 Detect the Work Areas

An outcome is its own **work area** when both hold:

- It has its own user value or acceptance boundary — someone could tell whether it was delivered, on its own terms.
- It could be delivered without completing the others. Ordering constraints are fine; a hard requirement that another area finish first means it is one area, not two.

**Coverage is not an area boundary.** Named devices, providers, views, or data sources reached through one shared path are requirements *inside* an area, not separate areas. Three payment providers behind one checkout flow is one area. Splitting on coverage produces areas that all touch the same code and collapse to a single serial track downstream.

**A shared surface is its own area.** When several outcomes consume the same interface, type set, or schema, that surface is an area the others depend on. Naming it here is what lets `mash-epic-decompose` promote it to a contract task.

Record the candidate areas as a working list. Phase 2 refines them against the seam heuristics; this phase only establishes that there is more than one.

## 0.4 Unfamiliarity Check

If the user signals they lack working knowledge of a domain the epic touches — "I don't know how our auth works", "never touched the billing side" — note the flagged territory and carry it into Phase 1. Ground that territory with the scout before probing it in dialogue, and record what could not be established as an explicit assumption in the affected area's document.

Skip this check in non-interactive mode; with no user to consult, flagged territory is handled as recorded assumptions.
