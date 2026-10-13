# Final Review and Plan Write

Phase 5.1 through 5.2 of `mash-plan`. Read this before the pre-write review.

### Phase 5: Final Review, Write File, and Handoff

#### 5.1 Review Before Writing

Before finalizing, check:
- **The hard floor is present.** Goal Capsule, Summary, Problem Frame, Requirements, Key Technical Decisions, Implementation Units, Verification Contract, and Definition of Done all exist. A plan missing any of them is incomplete — these are required, not include-when-material.
- **The Goal Capsule's Objective is an outcome, not a Means.** It would still read as the goal under a different implementation, and someone outside the changed component could tell whether it was met. If the request supplied only an approach, that approach is on the `Means:` line citing its owning KTD, and the Objective is the outcome it serves.
- **The Verification Contract names the repo's actual commands**, not generic "run tests" — with a measurable threshold when the goal is optimization-shaped.
- **The Definition of Done carries a cleanup criterion** so a long run cannot declare done with dead-end code still in the diff.
- The plan does not invent product behavior that should have been defined in `mash-brainstorm`
- Every major decision is grounded in the origin document or research
- Each implementation unit is concrete, dependency-ordered, and implementation-ready
- If test-first or characterization-first posture was explicit or strongly implied, the relevant units carry it forward with a lightweight `Execution note`
- Each feature-bearing unit has test scenarios from every applicable category (happy path, edge cases, error paths, integration) — right-sized to the unit's complexity, not padded or skimped
- Test scenarios name specific inputs, actions, and expected outcomes without becoming test code
- Feature-bearing units with blank or missing test scenarios are flagged as incomplete — feature-bearing units must have actual test scenarios, not just an annotation, **unless** the repo has no configured test runner (`Test expectation: none -- no test runner configured in this repo` plus replacement verification). The `Test expectation: none -- [reason]` annotation is also valid for non-feature-bearing units (pure config, scaffolding, styling)
- Deferred items are explicit and not hidden as fake certainty
- **High-Level Technical Design presence audit (load-bearing).** For each architecture trigger in Phase 3.4 that the plan content satisfies (3+ components with directed relationships, 3+ protocol steps, 3+ state machine states, lifecycle, 3+ decision points, 3+ data-flow stages, mode/flag combinations, DSL/API surface design, non-obvious single-component shape), verify a corresponding sketch/diagram is present in the High-Level Technical Design section. Count the firing triggers; count the sketches; the sketch count must be at least the count of distinct trigger categories that fired. Missing the section when a trigger fired, OR including the section but skipping a triggered sketch within it, is incomplete — return to Phase 3.4 and add the missing sketch. Token cost is not a valid reason to fail this check.
- If a High-Level Technical Design section is included, it uses the right medium for the work, carries the non-prescriptive framing, and does not contain implementation code (no imports, exact signatures, or framework-specific syntax)
- Per-unit technical design fields, if present, are concise and directional rather than copy-paste-ready
- If the plan creates a new directory structure, would an Output Structure tree help reviewers see the overall shape?
- If Scope Boundaries lists items that are planned work for a separate PR, issue, or repo, are they under `### Deferred to Follow-Up Work` rather than mixed with true non-goals?
- U-IDs are unique within the plan and follow the stability rule — no two units share an ID; reordering or splitting did not renumber existing units; gaps from deletions are preserved
- Would a visual aid (dependency graph, interaction diagram, comparison table) help a reader grasp the plan structure faster than scanning prose alone?

If the plan originated from a requirements document, re-read that document and verify:
- The chosen approach still matches the product intent
- Scope boundaries and success criteria are preserved
- Blocking questions were either resolved, explicitly assumed, or sent back to `mash-brainstorm`
- Every section of the origin document is addressed in the plan — scan each section to confirm nothing was silently dropped
- If origin supplies A/F/AE IDs: every origin R/F/AE that *affects implementation* is referenced in Requirements, a U-ID unit, test scenarios, verification, scope boundaries, or explicitly deferred. Actors are carried forward when they affect behavior, permissions, UX, orchestration, handoff, or verification. The standard is preservation of product intent, not mandatory ID spam — irrelevant origin IDs may be omitted
- If the origin contains an `Outside this product's identity` subsection: the plan's Scope Boundaries preserves the three-way split — `Deferred for later` and `Outside this product's identity` carried verbatim from origin, `Deferred to Follow-Up Work` reserved for plan-local implementation sequencing

#### 5.2 Write Plan File

**REQUIRED: Write the plan file to disk before presenting any options.**

Use the Write tool to save the complete plan:

```text
.mash/plans/YYYY-MM-DD-NNN-<type>-<descriptive-name>-plan.md
```

Sequence number `NNN` is derived from existing `.md` plan files in `.mash/plans/` to ensure unique daily ordering. Reserve the path with exclusive creation and take the next `NNN` on collision rather than overwriting.

Compose the plan using the content from `references/plan-sections.md` and `references/markdown-rendering.md`.

**Write tight.** A section being material is not license to pad it. Lead with the decision or outcome, one idea per sentence, a requirement or unit is intent plus at most one qualifier, defer forks to Open Questions rather than specifying both arms, and resolve superseded text in place rather than stacking strata. Before declaring the plan written, run the test: could the implementer find a contradiction in each section in one pass?

Write the Sentrux topology artifact beside the plan using the same basename:

```text
.mash/plans/YYYY-MM-DD-NNN-<type>-<descriptive-name>-plan.topology.json
```

Reference this path from the plan's Architecture Baseline (Sentrux), Sources / Research, or metadata so `mash-work` can discover it from the plan path.

Confirm (use absolute path so the reference is clickable in modern terminals):

```text
Plan written to <absolute path to plan>
```

**Interactive confirmation.** After the file is on disk, ask one question, using the blocking question tool when it exists: the plan is at that path. Does this match what you want, or what should change? If the user confirms, continue. If they name a change, edit the file and continue. Do not ask a second time. Then read `references/plan-handoff.md`.

**Non-interactive mode:** Do not ask. Read `references/plan-handoff.md`, which emits the handoff envelope after the ponytail check.
