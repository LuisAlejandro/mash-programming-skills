# Final Review and Plan Write

Phase 5.1 through 5.3.2 of `rosey-plan`. Read this before the pre-write review.

### Phase 5: Final Review, Write File, and Handoff

#### 5.1 Review Before Writing

Before finalizing, check:
- **The hard floor is present.** Goal Capsule, Summary, Problem Frame, Requirements, Key Technical Decisions, Implementation Units, Verification Contract, and Definition of Done all exist. A plan missing any of them is incomplete — these are required, not include-when-material.
- **The Goal Capsule's Objective is an outcome, not a Means.** It would still read as the goal under a different implementation, and someone outside the changed component could tell whether it was met. If the request supplied only an approach, that approach is on the `Means:` line citing its owning KTD, and the Objective is the outcome it serves.
- **The Verification Contract names the repo's actual commands**, not generic "run tests" — with a measurable threshold when the goal is optimization-shaped.
- **The Definition of Done carries a cleanup criterion** so a long run cannot declare done with dead-end code still in the diff.
- The plan does not invent product behavior that should have been defined in `rosey-brainstorm`
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
- Blocking questions were either resolved, explicitly assumed, or sent back to `rosey-brainstorm`
- Every section of the origin document is addressed in the plan — scan each section to confirm nothing was silently dropped
- If origin supplies A/F/AE IDs: every origin R/F/AE that *affects implementation* is referenced in Requirements, a U-ID unit, test scenarios, verification, scope boundaries, or explicitly deferred. Actors are carried forward when they affect behavior, permissions, UX, orchestration, handoff, or verification. The standard is preservation of product intent, not mandatory ID spam — irrelevant origin IDs may be omitted
- If origin was Deep-product (origin contains an `Outside this product's identity` subsection): the plan's Scope Boundaries preserves the three-way split — `Deferred for later` and `Outside this product's identity` carried verbatim from origin, `Deferred to Follow-Up Work` reserved for plan-local implementation sequencing

#### 5.1.5 Scoping Synthesis

Surface plan-time call-outs to the user before Phase 5.2 commits the plan to disk — the latest cheap moment to catch plan-time scope errors. The brainstorm already validated WHAT to build; this phase surfaces HOW the plan will execute on the forks that matter.

Fires on every run except the Phase 0.1 fast paths (resume normal, deepen-intent). Resume and deepen fast paths do not re-run the scoping synthesis. Every plan is brainstorm-sourced — the missing-origin stop at Phase 0.3b guarantees an origin document.

**Read `references/synthesis-summary.md` before composing the scoping synthesis** — and the shared reference it points to. Between them they carry the two-stage shape, the affirmability and keep tests, the detail test, budgets, granularity rules, anti-patterns, both literal templates, the auto-proceed guard, soft-cut behavior, self-redirect, the worked compression example, and non-interactive routing. Composing without them reliably produces malformed output.

**Required gate output — do not skip; silent proceeding is not allowed.** Compose the internal three-bucket draft, derive call-outs, then emit the reference's confirmation template (or its auto-proceed template, which fires only for Lightweight depth with zero call-outs surviving) before continuing to Phase 5.2. On the confirmation path, wait for the user.

**Synthesis is pre-plan-write.** The agent does NOT yet know how plan-write will sequence the work. Do not claim PR count ("one PR"), commit/branch shape, effort or time estimates, Implementation Unit boundaries, or exact file paths. The synthesis surfaces decisions knowable at THIS point (brainstorm + research + agent posture); plan-write produces the rest. This holds even when the agent formed plan-write opinions earlier in the session — those stay internal until plan-write.

**Do NOT enumerate the touch surface.** Sentences like "The touch surface is...", "This plan touches...", "The implementation reaches into...", "Files modified include..." are plan-pitch leaks. File paths, module names, directory introductions, and per-file change descriptions belong in the plan body (Implementation Units at Phase 5.2). The synthesis names *what* the plan targets, not *where* the code lives.

#### 5.2 Write Plan File

**REQUIRED: Write the plan file to disk before presenting any options.**

Use the Write tool to save the complete plan:

```text
rosey/plans/YYYY-MM-DD-NNN-<type>-<descriptive-name>-plan.md
```

Sequence number `NNN` is derived from existing `.md` plan files in `rosey/plans/` to ensure unique daily ordering. Reserve the path with exclusive creation and take the next `NNN` on collision rather than overwriting.

Compose the plan using the content from `references/plan-sections.md` and `references/markdown-rendering.md`.

**Write tight.** A section being material is not license to pad it. Lead with the decision or outcome, one idea per sentence, a requirement or unit is intent plus at most one qualifier, defer forks to Open Questions rather than specifying both arms, and resolve superseded text in place rather than stacking strata. Before declaring the plan written, run the test: could the implementer find a contradiction in each section in one pass?

Write the Sentrux topology artifact beside the plan using the same basename:

```text
rosey/plans/YYYY-MM-DD-NNN-<type>-<descriptive-name>-plan.topology.json
```

Reference this path from the plan's Architecture Baseline (Sentrux), Sources / Research, or metadata so `rosey-work` can discover it from the plan path.

Confirm (use absolute path so the reference is clickable in modern terminals):

```text
Plan written to <absolute path to plan>
```

**Non-interactive mode:** When `mode:non-interactive` is active, skip interactive questions. Make the needed choices automatically and proceed to writing the plan. Then emit the handoff envelope below in place of the confirmation line above.

##### Handoff envelope (`mode:non-interactive` only)

Emit a compact, stable envelope so an automated caller can consume the result without parsing prose. [`rosey-parallel`](../../rosey-parallel/SKILL.md)'s `plan:` phase reads `PLAN PATH:` from this block and passes it to the `work:` phase that follows.

```text
ROSEY_PLAN_HANDOFF
PLAN PATH: <repo-relative path to the plan, empty when blocked>
FILES: <union of the per-unit Files lists, repo-relative, one per line>
BLOCKERS: <none | one-line blocker>
END_ROSEY_PLAN_HANDOFF
```

- **Paths are repo-relative**, matching `FILES_CHANGED` in `rosey-work`'s envelope and this skill's never-absolute-paths rule. A worker runs with its worktree as `cwd` while the orchestrator resolves against the repo root, and the value is interpolated into the *next* phase's prompt — an absolute path would point outside that phase's own worktree.
- **`FILES` comes from every unit body's `**Files:**` field, not from the large-plan Unit Index.**
- **`BLOCKERS:` is the only failure channel.** When the run cannot safely produce a plan, leave `PLAN PATH:` empty and state the reason in one line. A caller that receives a blocker stops the task legibly instead of timing out.
- Emit the envelope in non-interactive mode only. Interactive runs keep the `Plan written to <absolute path>` confirmation above, which is for a human reading chat.

#### 5.3 Confidence Check and Deepening

After writing the plan file, automatically evaluate whether the plan needs strengthening.

**Two deepening postures** — this is a separate axis from `mode:interactive` / `mode:non-interactive`, which govern the run as a whole:

- **Integrate-directly** (default during plan generation): Runs without asking the user for approval. The user sees what is being strengthened but does not need to make a decision. Sub-agent findings are synthesized directly into the plan.
- **Review-each-finding** (activated by the re-deepen fast path in Phase 0.1, interactive runs only): The user explicitly asked to deepen an existing plan. Sub-agent findings are presented individually for review before integration. The user can accept, reject, or discuss each agent's findings. Only accepted findings are synthesized into the plan.

Review-each-finding exists because on-demand deepening is a different user posture — the user already has a plan they are invested in and wants to be surgical about what changes. This applies whether the plan was generated by this skill, written by hand, or produced by another tool.

`rosey-doc-review` and this confidence check are different:
- Use the `rosey-doc-review` skill when the document needs clarity, simplification, completeness, or scope control
- This confidence check strengthens rationale, sequencing, risk treatment, and system-wide thinking when the plan is structurally sound but still needs stronger grounding

**Non-interactive mode:** This phase always uses the integrate-directly posture when `mode:non-interactive` is active — there is no synchronous user to review findings with.

##### 5.3.1 Classify Plan Depth and Topic Risk

Determine the plan depth from the document:
- **Lightweight** - small, bounded, low ambiguity, usually 2-4 implementation units
- **Standard** - moderate complexity, some technical decisions, usually 3-6 units
- **Deep** - cross-cutting, high-risk, or strategically important work, usually 4-8 units or phased delivery

Build a risk profile. Treat these as high-risk signals:
- Authentication, authorization, or security-sensitive behavior
- Payments, billing, or financial flows
- Data migrations, backfills, or persistent data changes
- External APIs or third-party integrations
- Privacy, compliance, or user data handling
- Cross-interface parity or multi-surface behavior
- Significant rollout, monitoring, or operational concerns

##### 5.3.2 Gate: Decide Whether to Deepen

- **Lightweight** plans usually do not need deepening unless they are high-risk
- **Standard** plans often benefit when one or more important sections still look thin
- **Deep** or high-risk plans often benefit from a targeted second pass
- **Thin local grounding override:** If Phase 1.2 triggered external research because local patterns were thin (fewer than 3 direct examples or adjacent-domain match), always proceed to scoring regardless of how grounded the plan appears. When the plan was built on unfamiliar territory, claims about system behavior are more likely to be assumptions than verified facts. The scoring pass is cheap — if the plan is genuinely solid, scoring finds nothing and exits quickly
- **Load-bearing external research override:** If Phase 1.4 marked external research as load-bearing (it materially shaped a KTD, Alternative, Scope boundary, or Risk), always proceed to scoring — **even when local implementation patterns are strong**. A landscape or prior-art finding can shape recommendations the local codebase cannot verify, and the thin-grounding override above would miss it. This enters the scoring pass only; it does not force deepening

If the plan already appears sufficiently grounded and neither the thin-grounding nor the load-bearing-external-research override applies, report "Confidence check passed — no sections need strengthening", then **load `references/plan-handoff.md` now and execute 5.3.8 → 5.3.9 → 5.4 in sequence**. Document review is a user-selected option in Phase 5.4, not an automatic gate.


##### 5.3.3 onward

When deepening is warranted, read `references/deepening-workflow.md` and execute 5.3.3 through 5.3.7 from that file. Then read `references/plan-handoff.md` for 5.3.8 (ponytail sanity-check), 5.3.9 (final checks), and 5.4 (post-generation handoff, including the optional document-review choice).
