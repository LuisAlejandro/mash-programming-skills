# Plan Sections

This reference describes what makes a great implementation plan. It does NOT prescribe how the plan looks on the page — rendering is handled by `references/markdown-rendering.md`.

## The outcome

A great plan enables three audiences to act:

- **The implementing agent** (`rosey-work` or a human) starts from an informed baseline — load-bearing decisions are named, research breadcrumbs orient their own investigation, unit boundaries are clear. The plan gives the implementer a starting point, not a substitute for their own investigation.
- **The reviewer** identifies the load-bearing decisions and the boundaries of what's being changed in one pass.
- **The future reader** (anyone returning months later) traces why the work was done, what shaped it, and where the artifacts live.

Sections earn their place by serving one of these audiences. Omit padding.

## Section ID Registry

These are the stable logical sections and their exact markdown headings. Downstream skills locate content by these heading names, so the names are the contract — not a hint layered over free-form headings.

| Logical section | Markdown heading | Reader use |
|---|---|---|
| Goal Capsule | `## Goal Capsule` | Objective, Means, stop conditions |
| Summary | `## Summary` | What the plan proposes |
| Problem Frame | `## Problem Frame` | Why the work is being done |
| Requirements | `## Requirements` | R-IDs for review and implementation trace |
| Key Technical Decisions | `## Key Technical Decisions` | KTDs that constrain implementation |
| Implementation Units | `## Implementation Units` | U-ID work packets for execution |
| Verification Contract | `## Verification Contract` | Repo-specific commands and quality gates |
| Definition of Done | `## Definition of Done` | Global and per-unit completion criteria |

### Wayfinding: map before reading

A short plan can just be read in full — that is cheaper than scanning and ranging. An implementation-ready plan is often long, so for anything beyond short, do not load the whole artifact to find your way around. Scan headings first (`rg -n '^#{1,3} ' <plan>` gives the section map plus the `### U<N>.` units), then read only the ranges the task needs — typically the Goal Capsule, the active unit plus its cited R/F/AE/KTD, the Verification Contract, and the Definition of Done.

## Hard floor

When a plan doc is warranted, these sections are present. They carry the contracts downstream consumers depend on. **Required means required** — a plan missing any of them is incomplete, and Phase 5.1 flags it.

- **Goal Capsule** — the Objective, the Means when an approach is fixed, and the stop conditions. This is the fastest way for an executor to avoid drifting from the plan, and it matters most on long autonomous runs where nobody is watching.
  - The **Objective** is always the outcome: what is true for users or operators afterwards, phrased so it would still read as the goal under a different implementation. It must be checkable by someone outside the component being changed. The usual failure is an objective about the component's own execution — the wall-clock it no longer holds, what stays isolated inside it — which only its internals can settle. Infrastructure and refactor work has such an outcome too: the reason that component's behavior mattered to someone.
  - The **Means** is the chosen approach, on its own line, citing the KTD that owns it (`Means: … (KTD2)`) rather than restating its mechanism. Include it only when the request or the plan has fixed an approach; never invent one for outcome-only work.
  - **Test:** if the implementation changed, would the Objective still be the goal? No → it is a Means. When a request supplies only its approach ("move X out of A into B"), that is the Means; derive the Objective from the request's motivation.
- **Summary** — what the plan proposes, in 1-3 lines. Forward-looking; orients the reader before they invest in detail.
- **Problem Frame** — why the work is being done. Backward-looking / situational. May merge with Summary for compact plans where the motivation is a single sentence.
- **Requirements** (with stable R-IDs) — what must be true after the work ships. Reviewer's checklist; downstream code review verifies against these.
- **Key Technical Decisions** (KTDs) — the load-bearing choices that constrain implementation. Each entry is `<decision>: <rationale>`. Without these, the implementer can't tell which design choices are open and which are pinned.
- **Implementation Units** (with stable U-IDs) — the discrete units of work, sized so each is independently landable. `rosey-work` consumes these to execute. For trivial single-step plans the work may collapse into Summary prose and U-IDs may be omitted; this is rare.
  - **Unit Index (large plans only, ~10+ units).** When the plan has roughly ten or more units, open the section with a compact navigation table — one row per unit: **U-ID · one-line title · files touched · depends-on**. It lets an executor map units to files and resolve dependency order without scanning every unit body. It is a **navigation aid only**: the unit bodies stay authoritative, it carries nothing beyond those four fields (no approach, tests, or rationale), and `files touched` is the key paths rather than an exhaustive restatement. **Never use it to derive a file footprint** — `rosey-parallel` sequences tracks from each unit's `Files:` section, and the index is deliberately non-exhaustive, so a footprint taken from it would silently under-report overlap. **Omit it below ~10 units**, where the per-unit `Dependencies` and `Files` already suffice and an index would be ceremony.
- **Verification Contract** — the repo-specific commands and quality gates that prove the plan: which tests to run, which lint or build gates apply, and what behavioral checks are required. Name the repo's actual commands; avoid generic "run tests" language when concrete ones exist. When the goal is optimization-shaped (build time, latency, coverage, bundle size), express a measurable threshold as the exit criterion (e.g. "p95 latency < 200ms", "build time reduced 30%") — a metric target is a sharper done signal than a boolean check.
- **Definition of Done** — global and per-unit completion criteria. This is the completion contract for long-running or autonomous execution. Include a **cleanup criterion**: a long run accumulates dead-end and experimental code from approaches that did not pan out, and declaring done requires that abandoned-attempt code is removed, not left in the diff.

## Include when material

These sections are present when they carry information that isn't covered elsewhere. The test is not "is this a substantial plan?" — it is *"does this specific plan have content this section would surface?"* Filling a section with placeholder prose is worse than omitting it.

- **High-Level Technical Design** — include when the technical approach has shape that prose alone doesn't carry well: architecture across components, sequencing across processes, state machines, branching gates. Visualizations (component topology, sequence, swim lane, flowchart, data-flow) typically live here. Skip when the approach is a one-paragraph pattern application that the prose itself conveys.

- **Scope Boundaries** — include when scope is contested, when there are tempting non-goals worth naming explicitly, or when "deferred for later" needs distinguishing from "outside the product's identity." Skip when scope is obvious from Requirements alone.

- **Open Questions** — include when there are genuinely unresolved items that block planning or implementation. Skip when the plan is complete; an empty "Open Questions: none" section signals false uncertainty.

- **System-Wide Impact** — include when the change affects cross-cutting concerns (data lifecycles, auth boundaries, performance posture, cardinal rules, shared infrastructure). Skip for changes localized to one component where the impact is self-evident.

- **Risks & Dependencies** — include when there are real risks worth flagging (external service changes, version pins under churn, behavioral assumptions worth highlighting) or material upstream dependencies. Skip for low-risk localized work.

- **Acceptance Examples** — include when any requirement has a state-dependent or conditional shape ("When X, Y") where the prose alone leaves ambiguity about edge cases. Skip when all requirements are unconditional and unambiguous.

- **Documentation / Operational Notes** — include when documentation, monitoring, runbooks, or rollout steps need explicit notes. Skip when the work is purely internal and uses existing operational scaffolding without modification.

- **Sources / Research** — surface the research that orients the implementer or justifies load-bearing choices. The test: *"if I were the implementer reading this cold, would this breadcrumb help me make better choices?"* Yes → surface (code locations like `services/convex/reports.ts:174-176`, external docs, RFCs, constraints, prior plans — the category is inclusive, not enumerated). Process exhaust (reading the user's prompt, glancing at obvious entry points, restating prose) → omit. Surface inline next to the KTD or unit it justifies, or as a dedicated section — both shapes work.

- **Architecture Baseline (Sentrux)** — include when the Sentrux topology artifact exists. Summarize the quality signal, dominant bottleneck, and planning guidance in prose or a compact table. If Sentrux was unavailable, state that structural baseline was unavailable and point to the topology artifact with `status: "unavailable"`.

## Agent agency

The catalog is a floor, not a ceiling. When the plan's content doesn't fit any catalog section, introduce a new one — don't force the content into a section it doesn't belong in. Content drives section choices, not vice versa.

The agent also picks per artifact:

- Whether Problem Frame merges into Summary
- Sub-groupings (Requirements by capability, KTDs by component, Units phased into milestones)
- How much detail each section carries
- Whether HTD has one diagram, several, or none — and whether visualizations live in HTD or embedded in other sections

## Plan metadata fields

Every plan carries a small set of stable metadata fields that downstream tooling depends on. The contract is format-independent: in markdown these fields appear as YAML frontmatter at the top of the file; in HTML they appear as visible header text (typically a `<dl>` of `<dt>`/`<dd>` pairs or a stats strip). Field names and semantics are the same across both formats so consumers can locate them without knowing which format produced the plan.

### Required

- **`title`** — verbatim plan title. Matches the H1 so file metadata and visible heading don't drift.
- **`type`** — conventional-commit-prefix-aligned classification (`feat`, `fix`, `refactor`, `chore`, `docs`, `perf`, `test`, etc.). Carries the intent the eventual commit message should reflect.
- **`date`** — creation date in ISO 8601 (`YYYY-MM-DD`), ASCII digits only.

No `status` or lifecycle field. A plan is a point-in-time record, not a tracked work item — whether the work shipped is derived from git, not stored in the doc.

### Optional but well-known

These fields are not required, but when set they have fixed names and semantics so downstream tooling can rely on them:

- **`origin`** — repo-relative path to the upstream brainstorm requirements doc (e.g., `rosey/brainstorms/2026-05-12-pagination-requirements.md`). Always set: every plan has an origin. Carried for traceability and re-resolved when `rosey-plan` re-deepens.
- **`deepened`** — ISO 8601 date marking the first time the confidence check substantively strengthened the plan. Presence affects Phase 0.1 resume fast-path logic (see `references/deepening-workflow.md`).

Field names are stable across plan revisions — never rename a field or repurpose its semantics. Agents composing new plans MUST use these exact names; adding new fields is fine, but renaming `title` to `name` or `origin` to `source` breaks the downstream consumers above.

## ID and content rules

These apply regardless of rendering format.

- **Stable IDs.** R-IDs (Requirements), U-IDs (Implementation Units), A-IDs (if Actors fire), F-IDs (if Flows fire), AE-IDs (if Acceptance Examples fire). IDs are stable across plan revisions — never renumber to "clean up gaps."
- **Plain prefix.** `R1.`, `U1.` as bullet prefixes. Do not bold; the prefix is visually distinctive on its own.
- **Repo-relative paths.** Always. Never absolute paths in plan content; they break portability across machines, worktrees, teammates.
- **No process exhaust.** No "captured at Phase X" notes, no `## Next Steps` pointing to the next skill, no italic provenance lines. Engineering process metadata belongs in commit messages and tool output, not the artifact.
- **Group Requirements by concern when they span distinct logical areas.** The trigger is distinct concerns, not item count — even four requirements benefit from grouping if they cover three different topics. Skip grouping only when all requirements are genuinely about the same thing; a long flat list is a smell that subgroups were missed. Group by capability (e.g., "Packaging", "Migration and compatibility", "Contributor workflow"), not by the order requirements were discussed. R-IDs stay continuous across groups (R1, R2 in the first group; R3, R4 in the second; never restart at R1 per group).

## Rendering

Read `references/markdown-rendering.md` for how to render these sections.

This reference (`plan-sections.md`) is about WHAT the plan contains; the markdown rendering reference is about HOW to present it on the page. The section catalog is the same regardless of format.
