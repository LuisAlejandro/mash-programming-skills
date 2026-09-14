# Brainstorm Sections

This reference describes what makes a great brainstorm requirements document. It does NOT prescribe how the doc looks on the page — rendering is handled by `references/markdown-rendering.md`.

## The outcome

A great brainstorm produces a doc that enables three audiences to act:

- **The planning agent** (`rosey-plan` or a human) produces an implementation plan without inventing user behavior, scope boundaries, or success criteria — the brainstorm answered those.
- **The reviewer** sees the framing choices, distinguishes pinned from open, and catches scope gaps before planning.
- **The future reader** traces why the proposed thing matters, who it's for, and what success looks like.

Sections earn their place by serving one of these audiences. Omit padding.

## Match depth to content

Depth matches what the dialogue produced. A brainstorm with sparse content produces a sparse doc; one with rich content produces a rich doc. Don't add ceremony to make a slim brainstorm look substantial.

## Hard floor

These are always present.

- **Summary** — what is being proposed, in 1-3 lines. Forward-looking. Orients the reader before they invest in detail.
- **Requirements** (with stable R-IDs) — what must be true about the proposed thing. For very sparse brainstorms (≤3 simple items where the bullets ARE the summary), plain bullets without IDs are acceptable; the trigger for R-IDs is whether downstream consumers will reference them. When requirements span distinct concerns (e.g., "Packaging" / "Migration and compatibility" / "Contributor workflow"), group them under bold inline headers within the Requirements section — group by capability or concern, not by the order requirements were discussed. The trigger is distinct concerns, not item count — even four requirements benefit if they cover three different topics. Skip grouping only when all requirements are genuinely about the same thing; a long flat list is a smell that subgroups were missed. R-IDs stay continuous across groups (R1, R2 in the first group; R3, R4 in the second; never restart at R1 per group). **This heading is the software-origin marker:** `rosey-plan` treats a `*-requirements.md` as software only when `## Requirements` is present; a universal wrap-up omits it.

## Include when material

The agent decides per brainstorm whether each section carries information that isn't covered elsewhere. Filling a section with placeholder prose is worse than omitting it.

- **Problem Frame** — include when motivation isn't obvious from Summary alone (the *why* needs paragraphs, not a sentence). Backward-looking / situational. Does NOT restate the proposal; the remedy lives in Summary.

- **Key Decisions** — include when the brainstorm produced opinionated framing choices (defaults, scope narrowings, foundational technical picks) that constrain Requirements / Flows / Scope below. Each entry names the decision in bold with prose rationale. Sits high in the rendered doc so readers encounter the framing choices before descending into detail.

- **Actors** — include when the proposed thing has multi-party behavior (multiple humans, agents, or systems meaningfully involved). Skip for non-behavioral brainstorms (naming briefs, data-shape briefs, pure research, decision frameworks).

- **Key Flows** — include when the proposed thing has multi-step behavior. Expected by default for behavioral brainstorms unless the proposed thing is genuinely non-flow-shaped (pure API surface, policy, artifact output) and Actors / Requirements / Scope Boundaries / Acceptance Examples together prevent downstream invention of paths. When omitting from a behavioral brainstorm, note the reason in the doc.

- **Visualizations** — include a diagram when the brainstorm contains a diagram-shaped concept that a picture carries faster than prose. Common shapes: a data-shape transformation (before/after schema or field mapping), a source-of-truth fan-out (one authority feeding many derived surfaces), state-or-lifecycle logic, a multi-step flow, or a quantitative comparison. A diagram is cross-cutting, not a section of its own — it sits next to the Key Decision, Requirements group, or Flow it illustrates. The named test: *does the picture let a reader grasp the concept faster than the paragraph alone?* If yes, add it; if the prose already conveys it at a glance, skip it. One diagram per load-bearing concept — don't add visuals for ceremony.

  **Diagrams complement prose; they never replace it.** A diagram is an on-ramp to the prose it illustrates, not a substitute. The IDed prose (Requirements, Key Decisions, Acceptance Examples) stays complete and standalone — a reader who ignores every diagram still gets the full content in text, and a downstream agent that reads the artifact as linear text is never left with a relationship that exists only in an SVG. Adding a before/after diagram is not license to thin the requirement or decision prose it depicts.

- **Acceptance Examples** — include when any requirement has a state-dependent or conditional shape ("When X, Y") where prose alone leaves ambiguity about edge cases. **Always include AEs covering behavioral-conditional requirements** — that's where the ambiguity bites hardest. Skip when all requirements are unconditional and unambiguous.

- **Success Criteria** — include when there are quality / metric / handoff signals that Requirements don't already carry: quantitative metrics ("p95 latency under 200ms"), qualitative criteria ("the agent's output reads as one voice"), process / handoff quality ("rosey-doc-review can act on this without follow-ups"). Skip when Requirements ARE the success criteria (every R is "done when the R is true").

- **Scope Boundaries** — include when scope is contested or there are tempting non-goals worth naming explicitly. When the brainstorm is about positioning a product against adjacent ones the team could have built but is rejecting, split into "Deferred for later" (eventually but not v1) and "Outside this product's identity" (positioning decision). Otherwise, a single list is fine.

- **Dependencies / Assumptions** — include when material upstream dependencies exist or when load-bearing assumptions need to be surfaced.

- **How This Work Fits Together** — include when the coherent-work gate narrowed one area from a broader request (see `references/phase-0.md`). Describe the current area's place among sibling areas, mark tentative relationships as tentative, and do not treat sibling areas as active scope.

- **Outstanding Questions** — include when there are unresolved items. Use this lifecycle mapping (canonical headings; do not invent aliases):

| Lifecycle | Canonical heading |
| --- | --- |
| Product decision blocks planning | `### Resolve Before Planning` |
| Answered during planning | `### Deferred to Planning` — plan consumes these during research and does not copy them as unresolved |
| Still unresolved when the plan is written | Plan `## Open Questions` |
| Intentionally answered during execution | Plan `### Deferred to Implementation` under Open Questions |

- **Sources / Research** — surface research that orients the planner or justifies framing choices. The test: *"if I were the planner reading this cold, would this breadcrumb help me make better choices?"* Yes → surface (code locations, external docs, RFCs, constraints, prior plans — the category is inclusive, not enumerated). Process exhaust (reading the user's prompt, glancing at obvious files) → omit.

## Agent agency

The catalog is a floor, not a ceiling. When the brainstorm's content doesn't fit any catalog section, introduce a new one — don't force the content into a section it doesn't belong in. Content drives section choices, not vice versa.

The agent also picks per artifact:

- Whether Acceptance Examples render as a separate section or embed in each requirement
- How much depth each present section gets

(Requirements grouping is covered above in the Hard Floor item — group by concern by default, rendering a flat list only when all requirements are about the same thing, with continuous R-IDs across groups.)

## Brainstorm metadata fields

Every brainstorm carries a small set of stable metadata fields that downstream tooling depends on. In markdown these fields appear as YAML frontmatter at the top of the file.

### Required

- **`date`** — creation date in ISO 8601 (`YYYY-MM-DD`), ASCII digits only. Used in the filename (`rosey/brainstorms/YYYY-MM-DD-<topic>-requirements.md`).
- **`topic`** — kebab-case slug identifying the brainstorm subject (e.g., `surface-scope-earlier`, `demo-reel-local-save`). Used in the filename alongside `date` and as the resume-detection key when `rosey-brainstorm`'s Phase 0.1 scans `rosey/brainstorms/` for an existing artifact to continue.

### Field-name stability

Field names are stable across brainstorm revisions — never rename a field or repurpose its semantics. Agents composing new brainstorms MUST use these exact names; adding new fields is fine, but renaming `topic` to `subject` or `date` to `created` breaks filename construction and resume detection.

## ID and content rules

Same shape as plan rules.

- **Stable IDs.** R-IDs (Requirements), A-IDs (if Actors fire), F-IDs (if Flows fire), AE-IDs (if Acceptance Examples fire). No other ID namespaces.
- **Plain prefix.** `R1.`, `A1.`, `F1.`, `AE1.` as bullet prefixes. Do not bold; the prefix is visually distinctive on its own.
- **Bold leader labels** inside Flows and Acceptance Examples (`**Trigger:**`, `**Covers R4, R8.**`) provide structure without deeper heading levels.
- **Repo-relative paths.** Always. Never absolute paths.
- **No process exhaust.** No "captured at Phase X" notes, no `## Next Steps` pointing to rosey-plan, no italic provenance lines. Engineering process metadata belongs in commit messages and tool output, not the artifact.
- **No implementation details by default.** Libraries, schemas, endpoints, file layouts, code structure stay out unless the brainstorm itself is inherently about a technical or architectural change and those details are the subject of the decision.

## Discipline: Summary vs Problem Frame

When both sections are present, they earn separate sections only by holding to different purposes:

| Section | Question it answers | Time direction | Length |
|---|---|---|---|
| `## Summary` | What is this doc proposing? | Forward-looking | 1-3 lines |
| `## Problem Frame` | Why does this proposal exist? | Backward-looking / situational | Paragraphs |

- **Summary doesn't need problem context.** A reader scanning Summary gets the proposal at a glance.
- **Problem Frame doesn't restate the proposal.** It establishes the situation, the specific moment of pain, and the cost shape — then stops. The remedy lives in Summary; restating it in Problem Frame is the duplication that makes the two sections feel redundant.

## Rendering

Read `references/markdown-rendering.md` for how to render these sections.

This reference (`brainstorm-sections.md`) is about WHAT the brainstorm contains; the markdown rendering reference is about HOW to present it on the page. The section catalog is the same regardless of format.
