# Structure and Write the Plan

Phase 2 through 4 of `mash-plan`. Read this before building the planning-question list.

### Phase 2: Resolve Planning Questions

Build a planning question list from:
- Deferred questions in the origin document
- Gaps discovered in repo or external research
- Technical decisions required to produce a useful plan

For each question, decide whether it should be:
- **Resolved during planning** - the answer is knowable from repo context, documentation, or user choice
- **Deferred to implementation** - the answer depends on code changes, runtime behavior, or execution-time discovery

Ask the user only when the answer materially affects architecture, scope, sequencing, or risk and cannot be responsibly inferred. Use the platform's blocking question tool when available (see Interaction Method).

**A decision the conversation already settled counts as already-probed — never re-ask it.**

**Scaffold questions on unfamiliar territory.** When the user has signaled they *cannot evaluate* the area a question lives in — an explicit "I don't know X", or earlier answers showing they cannot weigh the options rather than merely have not decided — do not ask the question naked. Present it as a taught decision: the realistic options, one clause each on the trade-off that matters for this plan, and a recommended default. If the user still cannot evaluate, record the default as an explicit assumption in the plan instead of extracting a guess. In `mode:non-interactive`, resolve to the recommended default and record it as an assumption.

**Do not** run tests, build the app, or probe runtime behavior in this phase. The goal is a strong plan, not partial execution.

### Phase 3: Structure the Plan

#### 3.1 Title and File Naming

- Draft a clear, searchable title using conventional format such as `feat: Add user authentication` or `fix: Prevent checkout double-submit`
- Determine the plan type from frontmatter `type`: `feat`, `fix`, `refactor`, `chore`, `docs`, `perf`, `test`, or another conventional-commit prefix. The filename `<type>` token is that exact value — not a three-value subset.
- Build the filename following the repository convention: `.mash/plans/YYYY-MM-DD-NNN-<type>-<descriptive-name>-plan.md`
  - Create `.mash/plans/` if it does not exist
  - Check existing files for today's date to determine the next sequence number (zero-padded to 3 digits, starting at 001)
  - **Reserve the path with exclusive creation.** If the chosen name already exists, take the next available `NNN` rather than overwriting — two plan runs on the same day must never collide. The token shape is fixed: `mash-pr` derives the branch slug by stripping `YYYY-MM-DD-NNN-<type>-` (generic `<type>`, not only feat/fix/refactor), and it stops before commit when the plan and branch slugs diverge
  - Keep the descriptive name concise (3-5 words) and kebab-cased
  - Examples: `2026-01-15-001-feat-user-authentication-flow-plan.md`, `2026-02-03-002-fix-checkout-race-condition-plan.md`, `2026-03-10-001-docs-api-error-catalog-plan.md`, `2026-04-01-001-chore-release-script-plan.md`
  - Avoid: missing sequence numbers, vague names like "new-feature", invalid characters (colons, spaces)

#### 3.2 Stakeholder and Impact Awareness

Briefly consider who is affected by this change — end users, developers, operations, other teams — and how that should shape the plan. When more than one group is affected, note them in the System-Wide Impact section.

#### 3.2b Sentrux Topology Baseline

Before defining Implementation Units, load [`mash-sentrux`](../../mash-sentrux/SKILL.md) and run the planning baseline:

1. Read the Sentrux MCP tool descriptors before calling tools.
2. Call MCP `scan` with the absolute workspace root.
3. Call MCP `health`.
4. Derive the dominant bottleneck/root cause and planning guidance using `mash-sentrux`'s bottleneck mapping.
5. Write the topology artifact beside the plan as `<plan-basename>.topology.json` after the plan filename is known.

Use the topology as planning input, not as a day-based task generator:

- Let bottlenecks shape Key Technical Decisions, Implementation Unit boundaries, and "Patterns to follow".
- Prefer extending existing modules when topology shows equality/modularity risk.
- Avoid import cycles when acyclicity is weak.
- Prefer existing helpers when redundancy is weak.

If Sentrux MCP or the binary is unavailable, write a topology artifact with `status: "unavailable"` and continue planning. Do not block plan creation.

#### 3.3 Break Work into Implementation Units

Break the work into logical implementation units. Each unit should represent one meaningful change that an implementer could typically land as an atomic commit.

Good units are:
- Focused on one component, behavior, or integration seam
- Usually touching a small cluster of related files
- Ordered by dependency
- Concrete enough for execution without pre-writing code

Avoid:
- 2-5 minute micro-steps
- Units that span multiple unrelated concerns
- Units that are so vague an implementer still has to invent the plan

Each unit carries a stable plan-local **U-ID** assigned in Phase 3.5 (`U1`, `U2`, …). U-IDs survive reordering, splitting, and deletion: new units take the next unused number, gaps are fine, and existing IDs are never renumbered. This lets `mash-work` reference units unambiguously across plan edits.

#### 3.4 High-Level Technical Design

When the plan's technical approach has shape that prose alone doesn't carry well — architecture across components, sequencing across processes, state machines, branching gates, lifecycles, quantitative comparisons — include a High-Level Technical Design section that conveys the shape. The exact form (component diagram, sequence, swim lane, flowchart, state machine, decision matrix, pseudo-code grammar, bar chart for sizing concerns) is the agent's call per artifact — pick what makes the content land fastest for the reader.

See `references/plan-sections.md` for the section catalog including HTD's "include when material" criterion. Visualizations render as Mermaid in Markdown — see `references/markdown-rendering.md`.

When the plan's approach is a one-paragraph pattern application that prose conveys directly, skip the section. The presence of HTD should earn its keep with content that genuinely benefits from visualization.

Plan diagrams render authoritative content alongside the prose — they are not "directional sketches." Do not add hedging captions like *"directional guidance for review, not implementation specification"* to plan diagrams; the prose-is-authoritative rule already governs disagreement, and the hedging weakens the diagram unnecessarily.

#### 3.4b Output Structure (Optional)

For greenfield plans that create a new directory structure (new plugin, service, package, or module), include an `## Output Structure` section with a file tree showing the expected layout. This gives reviewers the overall shape before diving into per-unit details.

**When to include it:**
- The plan creates 3+ new files in a new directory hierarchy
- The directory layout itself is a meaningful design decision

**When to skip it:**
- The plan only modifies existing files
- The plan creates 1-2 files in an existing directory — the per-unit file lists are sufficient

The tree is a scope declaration showing the expected output shape. It is not a constraint — the implementer may adjust the structure if implementation reveals a better layout. The per-unit `**Files:**` sections remain authoritative for what each unit creates or modifies.

#### 3.5 Define Each Implementation Unit

Each unit is a level-3 heading carrying a stable U-ID prefix matching the format used for R/A/F/AE in requirements docs: `### U1. [Name]`. Number sequentially within the plan starting at U1. Do not render units as bulleted list items or prefix them with `- [ ]` / `- [x]` checkbox markers. List-based unit titles fragment in every standard renderer because the per-unit fields (`**Goal:**`, `**Files:**`, `**Approach:**`, etc.) are written flush-left, which terminates CommonMark list continuation and detaches the fields from the unit they describe. Headings render correctly everywhere, are the right semantic match for sections containing multi-block content, and give each unit an anchor link. The plan is a decision artifact; execution progress is derived from git by `mash-work` rather than stored in the plan body.

**Stability rule.** Once assigned, a U-ID is never renumbered. Reordering units leaves their IDs in place (e.g., U1, U3, U5 in their new order is correct; renumbering to U1, U2, U3 is not). Splitting a unit keeps the original U-ID on the original concept and assigns the next unused number to the new unit. Deletion leaves a gap; gaps are fine. This rule holds on later edits of the same plan, which is the most likely accidental-renumber.

For each unit, include:
- **Goal** - what this unit accomplishes
- **Requirements** - which requirements or success criteria it advances (cite R-IDs, and A/F/AE IDs when origin supplies them)
- **Dependencies** - what must exist first (cite by U-ID, e.g., "U1, U3")
- **Files** - repo-relative file paths to create, modify, or test (never absolute paths)
- **Approach** - key decisions, data flow, component boundaries, or integration notes
- **Execution note** - optional override only. When absent, work uses proof-first for behavioral changes when a test runner and suitable test surface exist. Use an Execution note only to override that default (characterization-first, smoke-first, or an explicit no-test exception with replacement verification).
- **Technical design** - optional pseudo-code or diagram when the unit's approach is non-obvious and prose alone would leave it ambiguous. Frame explicitly as directional guidance, not implementation specification
- **Patterns to follow** - existing code or conventions to mirror
- **Test scenarios** - enumerate the specific test cases the implementer should write, right-sized to the unit's complexity and risk. Consider each category below and include scenarios from every category that applies to this unit. A simple config change may need one scenario; a payment flow may need a dozen. The quality signal is specificity — each scenario should name the input, action, and expected outcome so the implementer doesn't have to invent coverage. For units with no behavioral change (pure config, scaffolding, styling), use `Test expectation: none -- [reason]` instead of leaving the field blank. If the repo has **no configured test runner**, feature-bearing units use `Test expectation: none -- no test runner configured in this repo` and name replacement verification instead of inventing a runner. **AE-link convention:** when a test scenario directly enforces an origin Acceptance Example, prefix it with `Covers AE<N>.` (or `Covers F<N> / AE<N>.`). This is sparse-by-design — most test scenarios are finer-grained than AEs and do not link. Do not force AE links onto tests that only cover lower-level implementation details.
  - **Happy path behaviors** - core functionality with expected inputs and outputs
  - **Edge cases** (when the unit has meaningful boundaries) - boundary values, empty inputs, nil/null states, concurrent access
  - **Error and failure paths** (when the unit has failure modes) - invalid input, downstream service failures, timeout behavior, permission denials
  - **Integration scenarios** (when the unit crosses layers) - behaviors that mocks alone will not prove, e.g., "creating X triggers callback Y which persists Z". Include these for any unit touching callbacks, middleware, or multi-layer interactions
- **Verification** - how an implementer should know the unit is complete, expressed as outcomes rather than shell command scripts

Every feature-bearing unit should include the test file path in `**Files:**` **when a configured test runner exists**. If none exists, do not invent test infrastructure unless that work is explicitly in scope.

When `Execution note` is absent, work uses proof-first for behavioral changes when a test runner and suitable test surface exist. Use an Execution note only to override that default (characterization-first, smoke-first, or an explicit no-test exception with replacement verification).

Do not expand units into literal `RED/GREEN/REFACTOR` substeps.

#### 3.6 Keep Planning-Time Questions and Deferred-to-Implementation Items Separate

If something is important but not knowable yet, record it explicitly under `### Deferred to Implementation` (under `## Open Questions`) rather than pretending to resolve it in the plan. Do not use the heading `Implementation-Time Unknowns` on new plans.

Examples:
- Exact method or helper names
- Final SQL or query details after touching real code
- Runtime behavior that depends on seeing actual test failures
- Refactors that may become unnecessary once implementation starts

#### 3.7 Anti-Expansion: Tangential Cleanup and Scope Creep Go to Deferred

Distinct from 3.6 (which is about *unknowns* at plan time): 3.7 is about *known but tangential* work that the agent notices while planning but that falls outside the user's confirmed scope. When research surfaces an adjacent refactor, a "while we're here" cleanup, or a scope-adjacent nice-to-have ("we could also add rate limiting"), route it to the existing `### Deferred to Follow-Up Work` subsection in Scope Boundaries (Phase 4.2 Core Plan Template), not into active Implementation Units.

The origin's scope is what the active plan executes. Everything else is deferred. This does not bias extend-versus-invent decisions inside that scope. The user's explicit ask overrides this default — if the user explicitly requested a refactor, it is in scope.

### Phase 4: Write the Plan

**NEVER CODE during this skill.** Research, decide, and write the plan — do not start implementation.

Change the amount of detail, not the boundary between planning and execution. Include a section when it has something to say. Omit a section that would only hold a placeholder.

#### 4.1 Optional sections

Add a section when it genuinely helps:
- **Alternative Approaches Considered**
- **Success Metrics**
- **Dependencies / Prerequisites**
- **Risk Analysis & Mitigation**
- **Phased Delivery**
- **Documentation Plan**
- **Operational / Rollout Notes**
- **Future Considerations** only when they materially affect current design

Do not add these as boilerplate. Include them only when they improve execution quality or stakeholder alignment.

**Alternatives Considered — what to vary.** When this section is included, alternatives must differ on *how* the work is built: architecture, sequencing, boundaries, integration pattern, rollout strategy. Tiny implementation variants (which hash function, which serialization format) belong in Key Technical Decisions, not Alternatives. Product-shape alternatives (different actors, different core outcome, different positioning) belong in `mash-brainstorm`, not here — surface them back upstream rather than re-litigating product questions during planning.

#### 4.2 Section Contract and Rendering

Compose the plan using two paired references:

- `references/plan-sections.md` — the section contract. Describes what the plan contains: the outcome the plan must enable for downstream consumers, the hard floor (Goal Capsule, Summary, Problem Frame, Requirements, Key Technical Decisions, Implementation Units, Verification Contract, Definition of Done), the include-when-material catalog (HTD, Scope Boundaries, Open Questions, System-Wide Impact, Risks & Dependencies, Acceptance Examples, Documentation/Operational Notes, Sources & Research), the agency-driven escape hatch (introduce new sections when content warrants), and the ID/content rules.
- `references/markdown-rendering.md` — how to present the sections in markdown.

The section catalog is the same regardless of format. Format-specific principles (table-vs-prose by content shape, ID prefix format, diagram rendering, etc.) live in the rendering reference.

Omit "include when material" sections that don't carry information for this specific plan. Filling a section with placeholder prose is worse than omitting it.

#### 4.3 Planning Rules

- **Horizontal rules (`---`) between top-level sections** when the plan has more than a screen of sections. A short plan does not need them.
- **All file paths must be repo-relative** — never use absolute paths like `/Users/name/Code/project/src/file.ts`. Use `src/file.ts` instead. Absolute paths make plans non-portable across machines, worktrees, and teammates. When a plan targets a different repo than the document's home, state the target repo once at the top of the plan (e.g., `**Target repo:** my-other-project`) and use repo-relative paths throughout
- Prefer path plus class/component/pattern references over brittle line numbers
- Do not include implementation code — no imports, exact method signatures, or framework-specific syntax
- Pseudo-code sketches and DSL grammars are allowed in the High-Level Technical Design section and per-unit technical design fields when they communicate design direction. Frame them explicitly as directional guidance, not implementation specification
- Mermaid diagrams are encouraged when they clarify relationships or flows that prose alone would make hard to follow — ERDs for data model changes, sequence diagrams for multi-service interactions, state diagrams for lifecycle transitions, flowcharts for complex branching logic
- Do not include git commands, commit messages, or shell choreography in Implementation Units. `## Verification Contract` **must** name real repo commands (`make test` / `make lint` when a Makefile exists).
- Do not expand implementation units into micro-step `RED/GREEN/REFACTOR` instructions
- Do not pretend an execution-time question is settled just to make the plan look complete

