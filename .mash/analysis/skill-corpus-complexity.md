# Skill Corpus Complexity Analysis

**Date:** 2026-10-09
**Scope:** `src/skills/` (23 skills), `src/rules/` (7 rules), `src/agents/` (33 agents), `install.sh`, `AGENTS.md`
**Method:** static inspection of the current tree. Every claim below cites a `file:line` verified against this tree.

**Question this answers:** where does the corpus get *harder to follow* — extra decisions, competing authorities, and procedures that re-run without changing the outcome. **Complexity, not size.** A long file with one linear procedure is simpler than a short file with six modes.

**Status legend:** `OPEN` not addressed · `REPORT` analysis only, no fix applied

---


## Summary

| ID | Opportunity | Class | Severity | Status |
|----|-------------|-------|----------|--------|
| C1 | Always-on rule forbids the epic chain the epic skills require | Authority conflict | High | OPEN |
| C2 | `mash-qa` is a state machine: 3 modes + quick tier + scope paths + roster + post-review router | Mode/branch fan-out | High | OPEN |
| C3 | The epic path reviews the same work three times | Redundant review | High | OPEN |
| C4 | "Shared contract before fan-out" has three owners | Split authority | Medium | OPEN |
| C5 | `mash-plan` refuses task-goal input, so `mash-parallel` invents stub requirements docs | Workaround | Medium | OPEN |
| C6 | Four front doors, none redirect to the right one | Routing | Medium | OPEN |
| C7 | `mash-ideate` writes one run configuration as prose in two places | Distributed state | Medium | OPEN |
| C8 | Hindsight gate restated in rule, skill, and per-skill phases; fingerprint `curl` exists only in the skill | Authority conflict | Medium | OPEN |
| C9 | `mash-work` runs three verification layers and says there is no precedence | Ambiguity | Medium | OPEN |
| C10 | QA and doc-review each implement the same post-review router and question-tool preload | Duplication | Medium | OPEN |
| C11 | Three agents are in the pack and named by no skill | Dead dispatch surface | Medium | OPEN |
| C12 | `mash-parallel` dispatches workers with phase names its own prompt contract does not define | Contract gap | Medium | OPEN |
| C13 | `mash-parallel` integration gate is its own test suite, and skips outside this repo | Missing gate | Medium | OPEN |
| C14 | Three personas review "complexity" in every full code review | Persona overlap | Low | OPEN |
| C15 | `mash-debug` describes a branch it cannot create | Dead path | Low | OPEN |
| C16 | "Read the reference again on phase entry" is mandatory in four skills | Ceremony | Low | OPEN |

---


## How a run actually moves

### Single-feature path

| Step | Skill | Gate |
|---|---|---|
| 1 | `mash-brainstorm` writes `*-requirements.md` | Hindsight |
| 2 | `mash-plan` consumes it, writes a plan | Hindsight, Sentrux |
| 3 | `mash-work` executes the plan, runs `mash-lint`, stops | Hindsight, Sentrux, lint |
| 4 | `mash-qa` (user invokes) | Hindsight |
| 5 | `mash-pr` (user invokes) | — |

`mash-work` does not own QA, PR, or release: "`mash-work` does **not** own QA, PR creation, merge, or release. `mash-qa`, `mash-pr`, and `mash-release` are explicit user invocations — never auto-called from this skill." (`src/skills/mash-work/SKILL.md:47`)

### Epic / parallel path

`mash-epic-frame` writes N area requirements docs and loads `mash-epic-decompose`. Decompose writes `run-inputs.json` and invokes `mash-parallel`. Parallel projects a requirements stub per task when no real doc matches, scaffolds shared contracts, plans in worktrees, stops at a human gate, then runs work / headless QA / lint per task, merges tracks, and fans out three further verifiers.

Pipeline as described by the skill: "`epic (task list) → validate → per-task origin docs → scaffold (contracts-before-code) → per-task planning (worktrees, mash-plan) → sequencing → batched human gate → parallel track execution (per-task mash-plan → mash-work → mash-qa → mash-lint) → integration (local) → parallel verification → final report + run state`" (`src/skills/mash-parallel/SKILL.md:21`)

`mash-ideate` sits beside both. It generates and critiques candidate ideas and ends at a next-steps menu; it never hands off into brainstorm ("Ideation output is an evaluated candidate set; the deliverable ends with a menu of what to do next and never skips onward to planning." `src/skills/mash-ideate/SKILL.md:20`).

---

## C1. Always-on rule forbids the epic chain the epic skills require

Class: authority conflict. Severity: high. Status: OPEN

An always-on rule and two skills disagree about who may start the next pipeline stage. An agent that treats the rule as binding stops mid-epic; an agent that follows the skills violates the rule. Neither is wrong in isolation.

The rule:

    `mash-pr`, `mash-parallel`, and `mash-epic-decompose` are **explicit user invocations** — no other skill auto-calls them. If a plan is too large for one run, suggest the user invoke one of them; do not invoke it yourself.
    (`src/rules/mash-workflow-gates.mdc:23`)

What the epic skills do:

    Load the `mash-epic-decompose` skill in the current session, passing the area list ...
    **The run inputs and the run itself** — decompose emits `run-inputs.json` and invokes `mash-parallel`.
    The handoff is one-way. Framing does not wait for decompose's answer and the run does not return here.
    (`src/skills/mash-epic-frame/references/handoff.md:24`, `:34`, `:36`)

    7. **Hand off** — invoke `mash-parallel` with the file.
    (`src/skills/mash-epic-decompose/SKILL.md:89`)

The rest of the corpus is consistent with the rule. `mash-work` says "invoke `mash-parallel` explicitly rather than improvising it here" (`src/skills/mash-work/references/work-intake.md:139`) and `mash-debug` says "Never auto-invoke it" for `mash-pr` (`src/skills/mash-debug/SKILL.md:262`). `mash-plan` invoking `mash-work` is fine, because work is not on the rule's list (`src/skills/mash-plan/references/plan-handoff.md:66`).

Why it is complexity: two activation policies for one skill chain, both stated as mandatory. The agent has to remember which document wins.

Simpler workflow: one policy. Either the rule grants an exception ("invoking `mash-epic-frame` authorizes the decompose and parallel chain") or the epic skills stop after their artifact and ask the user to invoke the next stage. Both are one sentence; the current corpus is neither.

What you lose: the chain saves the user one or two invocations per epic. The stop makes the rule and the skills agree. Pick one.

## C2. `mash-qa` is a state machine, not just a review pass

Class: mode/branch fan-out. Severity: high. Status: OPEN

A run resolves three modes, a separate quick tier, scope-specific checkout rules, a dynamic reviewer roster, then a multi-stage synthesis and post-review router. Mode changes whether the tree can mutate, whether it can switch branches, which findings return, and whether a user is asked. Quick is declined for headless and report-only, and also when the adversarial gate fires.

Evidence:
- Mode table: `src/skills/mash-qa/SKILL.md:67-76`.
- Quick tier and exclusions: `src/skills/mash-qa/SKILL.md:50-65`.
- Headless prohibits checkout while PR/branch paths separately describe checkout: `src/skills/mash-qa/SKILL.md:80-96`, `:214-220`, `:263-271`.
- Full roster selection: `src/skills/mash-qa/references/persona-catalog.md:5-50`.
- Post-review router A/B/C/D and branches: `src/skills/mash-qa/references/synthesis-and-followup.md:227-284`.

Conflict: interactive PR/branch review asks the user to stash or commit and checks out a branch (`SKILL.md:220`, `:271`), while the always-on rule forbids stash, branch switching, and worktrees for `mash-qa` (`src/rules/mash-workflow-gates.mdc:17-23`).

Simpler workflow: reviews run against the current checkout or `base:<ref>`; target PR/branch reviews require an isolated checkout. Use one mode axis (interactive vs headless/report-only policy), and keep quick as roster-size selection available wherever the caller explicitly requests it.

What you lose: convenient interactive review of another branch directly in a dirty shared checkout. Keep the full mode behavior if it serves a real caller; remove only the contradictory path and duplicate decisions.

## C3. The epic path repeats review after per-task QA

Class: redundant review. Severity: high. Status: OPEN

Each task runs headless `mash-qa` with full roster, then integration gates, then three parallel verifiers on the integrated result. A rejection enters a bounded fix-up loop. This is a second review contract after tasks already passed QA; it may be valuable for cross-task interactions, but it duplicates code review and test execution on the happy path.

Evidence:
- Task pipeline and post-integration verification: `src/skills/mash-parallel/SKILL.md:21`, `:70-74`.
- Worker requires headless QA and lint: `src/skills/mash-parallel/references/worker-prompt.md:35-44`.
- Integrated verification runs code review, test runner, architecture: `src/skills/mash-parallel/scripts/mash_parallel.py:2138-2165`.
- Verification is inside integration/fix-up loop: `src/skills/mash-parallel/scripts/mash_parallel.py:486-498`; fix-up cap is `:411`.

Separate accuracy issue: the pipeline string includes `mash-plan` again in execution, but the helper plans once before the approval gate and then executes work/QA/lint (`SKILL.md:21`, `scripts/mash_parallel.py:1610-1710`, `:1457`).

Simpler workflow: run integrated QA only if integration changed code, if tracks were reconciled, or if a cross-track risk warrants it; otherwise trust per-task QA plus integration tests. Correct the pipeline description to say work → QA → lint after approval.

What you lose: automatic detection of cross-task regressions missed by isolated QA. Make the integrated-review trigger explicit rather than unconditional.

## C4. Three owners handle shared contracts before parallel work

Class: split authority. Severity: medium. Status: OPEN

The decompose skill creates a contract task when tasks share an interface; parallel then runs a separate scaffold architect for shared contracts; the human gate again asks for a contention scan for contracts and other shared resources. The helper's gate is actually just stop / resume `--approve`; documented drop and re-plan actions are not handled by that CLI.

Evidence:
- Contract task rule: `src/skills/mash-epic-decompose/SKILL.md:72`.
- Scaffold phase and human contention scan: `src/skills/mash-parallel/SKILL.md:66-70`.
- Helper scaffold dispatch: `src/skills/mash-parallel/scripts/mash_parallel.py:1555-1577`, `:2020-2032`.
- Human gate implementation: `src/skills/mash-parallel/scripts/mash_parallel.py:1698-1710`; only `--approve` is parsed for resume (`:2500-2523`).

Why it is complexity: contract-first is expressed as a task, an architect phase, and a human review duty. The operator must know which one actually creates the contract and whether the CLI supports the action prose offers.

Simpler workflow: designate one contract owner. Either decompose creates contract tasks and scaffold only checks/materializes them, or scaffold owns contracts and decompose does not create a duplicate task. Make gate actions match implementation, or document it as approve/abort only.

What you lose: if decompose misses a shared contract, a separate architect pass can catch it. If contract tasks are authoritative, that safety shifts to the review gate.

## C5. Parallel writes synthetic requirements docs to satisfy plan's precondition

Class: workaround. Severity: medium. Status: OPEN

`mash-plan` stops without an upstream requirements document. `mash-parallel` therefore projects every task goal into a minimal `*-requirements.md` with a generic R1, except when a matching brainstorm file exists. The synthetic document exists to satisfy a precondition; it is not validated product requirements, and the body says so.

Evidence:
- Plan stop: `src/skills/mash-plan/references/intake.md:103-137`.
- Parallel origin projection and rationale: `src/skills/mash-parallel/scripts/mash_parallel.py:2077-2132`.
- Existing brainstorm matching: `src/skills/mash-parallel/scripts/mash_parallel.py:2053-2075`.

Simpler workflow: teach `mash-plan` two explicit origins: validated requirements doc or bounded task goal. The task-goal path records assumptions and does not pretend to be a brainstorm artifact. Parallel passes the task directly when no real origin exists.

What you lose: task-goal input has less structure than a full requirements doc. Preserve existing behavior for area docs produced by `mash-epic-frame`.

## C6. Four front doors answer the same scope-routing question

Class: routing. Severity: medium. Status: OPEN

`mash-ideate`, `mash-brainstorm`, `mash-epic-frame`, and `mash-plan` each have a different boundary:
- Ideate generates candidates, ends at a menu, and never starts planning (`src/skills/mash-ideate/SKILL.md:12-20`).
- Brainstorm detects multiple independently plannable outcomes, narrows to one, and explicitly never routes to another skill (`src/skills/mash-brainstorm/references/phase-0.md:78-90`).
- Epic-frame stops if the ask is only one outcome (`src/skills/mash-epic-frame/references/phase-0.md:30-40`).
- Plan requires an origin doc and offers brainstorm if absent (`src/skills/mash-plan/references/intake.md:103-137`).

Why it is complexity: the user or agent has to decide which of four similar entry points fits. When the scope test suggests a different path, brainstorm narrows but does not redirect; epic-frame stops; plan redirects.

Simpler workflow: one decision rule shared by descriptions and skills: settled multi-area ambition → epic-frame; one unsettled feature → brainstorm; candidate ideas → ideate; requirements doc ready → plan. Make the scope gate hand off to that route instead of repeating its own partial rule.

What you lose: brainstorm's current behavior of narrowing to one area while preserving others as contextual candidates. That can remain as the user's explicit choice, not a mandatory reroute.

## C7. Ideate computes run settings in Phase 0, then re-resolves them in Phase 2

Class: distributed state. Severity: medium. Status: OPEN

Phase 0.5 resolves focus, volume, tactical signals, `go deep`, and issue-tracker collisions. Phase 2 has a second variant matrix and fallback rules that must preserve that earlier resolution; it explicitly warns not to reread raw prompt signals. The agent carries a state machine in prose across separate references.

Evidence:
- Collision resolution and tactical dials: `src/skills/mash-ideate/references/scope-gates.md:110-135`.
- Phase 2 matrix and fallback carries prior state: `src/skills/mash-ideate/references/divergent-ideation.md:18-30`.
- Both Phase 0 gate references are mandatory even when the subject is clear: `src/skills/mash-ideate/SKILL.md:40-48`.

Simpler workflow: Phase 0 emits one `RUN_PROFILE` with selected frames, agent count, ideas per frame, read budget, and active waivers. Phase 2 consumes that profile. Put collision rules in the profile builder only.

What you lose: some inline rationale about why not to pack frames into fewer agents. Preserve the constraint and its rationale beside the one resolver.

## C8. Hindsight has overlapping authorities and an extra availability check

Class: authority conflict. Severity: medium. Status: OPEN

The always-on rule owns the gate and says check daemon status, then recall. The `mash-hindsight` skill says `daemon status` alone is insufficient: verify `/version` with `curl`, because an unrelated service can answer on the port. Skill-local sections restate Hindsight gates in multiple places. QA also calls for recall both before scope (`mash-qa/SKILL.md:166-172`) and again after scope (`:307`). This creates two availability interpretations and an extra recall decision discoverable only after loading multiple files.

Evidence:
- Gate owner and required sequence: `src/rules/hindsight-memory.mdc:18-40`.
- Port fingerprint caveat: `src/skills/mash-hindsight/SKILL.md:42-58`.
- Recall contract: `src/skills/mash-hindsight/SKILL.md:96-108`.
- Plan/work say Phase 0 recall is single use, with a deferred exception only if plan path unknown: `src/skills/mash-plan/references/research.md:16-20`; `src/skills/mash-work/references/work-intake.md:124-128`.

Current tree's gate list matches the rule frontmatter and body (brainstorm, plan, work, QA, epic-frame, release). There is no drift there now.

Simpler workflow: one executable Hindsight procedure in `mash-hindsight`; the always-on rule points to it; gated skills only state their gate point. Include the fingerprint in the one procedure and define status as verified Hindsight, not generic HTTP health.

What you lose: self-contained gate instructions in skill-local references. They can remain as a pointer and outage behavior.

## C9. Work verifies the same outcome through several contracts

Class: verification ambiguity. Severity: medium. Status: OPEN

Per-unit verification runs in the implementation loop; full `mash-lint` runs at handoff; the plan's Verification Contract also runs at handoff, with instructions to carry both sets into `VERIFY:`. The handoff explicitly says there is "no precedence question" between plan-wide and per-unit verification. That negation signals a contract readers must already understand.

Evidence:
- Resolve verification commands during intake: `src/skills/mash-work/references/work-intake.md:94-107`.
- Per-unit verification and continuous checks: `src/skills/mash-work/references/implementation-loop.md:59`, `:134-140`.
- Lint, Verification Contract, and no-precedence explanation: `src/skills/mash-work/references/handoff.md:9-18`.

Simpler workflow: one verification bundle: unit checks establish completion as work proceeds; handoff runs lint and any plan-wide checks not already satisfied by lint. Emit one normalized result list, not parallel verification concepts.

What you lose: explicit distinction between per-unit and plan-wide evidence. Keep that distinction in the plan contract, but do not make it a separate decision tree when running checks.

## C10. Code review and document review repeat the same interaction machinery

Class: duplication. Severity: medium. Status: OPEN

Both `mash-qa` and `mash-doc-review` implement an interactive-vs-headless split, Claude-specific deferred `ToolSearch` preload, and a four-option routing question followed by walk-through, bulk actions, and report-only. They are separate products (code findings vs document findings), but the host question contract and routing shape are duplicated.

Evidence:
- QA preload and mode rules: `src/skills/mash-qa/SKILL.md:67-101`.
- QA four-option route and conditional validator stages: `src/skills/mash-qa/references/synthesis-and-followup.md:65-83`, `:239-284`.
- Doc-review headless contract and preload: `src/skills/mash-doc-review/SKILL.md:13-40`.
- Doc-review four-option route: `src/skills/mash-doc-review/references/walkthrough.md:9-34`.

Simpler workflow: share the interaction-method contract and tool preload. Keep review-specific mutation policy and the different meanings of defer local to each skill.

What you lose: no material behavior if shared contract remains a pointer; a shared post-review router must not blur code-fixer vs document-editor ownership.

## C11. Three agents exist without a skill dispatch path

Class: dead dispatch surface. Severity: medium. Status: OPEN

`mash-architecture-strategist`, `mash-data-integrity-guardian`, and `mash-git-history-analyzer` exist in `src/agents/`, but searches of `src/skills/` find no references to their names. The parallel integration verifier calls a generic `architecture` phase, not the architecture strategist agent. Reviewers have no defined trigger or invocation contract.

Evidence:
- Agent definitions: `src/agents/mash-architecture-strategist.md`, `src/agents/mash-data-integrity-guardian.md`, `src/agents/mash-git-history-analyzer.md`.
- QA's roster declares itself the only roster: `src/skills/mash-qa/references/persona-catalog.md:3`; it includes neither architecture strategist nor data-integrity guardian (`:10-40`).
- Parallel verifier dispatch names `code_review`, `test_runner`, `architecture`: `src/skills/mash-parallel/scripts/mash_parallel.py:2147`.

Simpler workflow: either define owners and triggers in the relevant catalog, or remove agents that have no supported caller. Do not assume the generic verifier is those agents; the driver receives only a generic phase prompt.

What you lose: a dormant specialized reviewer if removed. Wiring them in adds dispatch cost and should happen only if they serve a distinct gap.

## C12. Parallel dispatches scaffold and verify workers without phase-specific contracts

Class: contract gap. Severity: medium. Status: OPEN

The loaded `worker-prompt.md` defines only plan, work, QA, and lint phases. The helper also invokes `scaffold` and `verify` through the same `_default_prompt` template. `scaffold` gets task id `__scaffold__` without task goal or origin; `verify` gets `__verify__/<verifier>` and an integrated-tip argument that is not added to prompt context. Neither phase has an instruction telling the worker what output or success means beyond harness-level "done".

Evidence:
- Template phases and contracts: `src/skills/mash-parallel/references/worker-prompt.md:17-45`.
- The same default prompt renders arbitrary phase strings: `src/skills/mash-parallel/scripts/mash_parallel.py:2347-2368`.
- Scaffold and verification use `_invoke` with those phases: `src/skills/mash-parallel/scripts/mash_parallel.py:2457-2460`.
- Verify CLI supplies tip only to `run_parallel_verification`, while driver discards it in prompt construction: `src/skills/mash-parallel/scripts/mash_parallel.py:2459-2460`, `:2587-2607`.
- Generic harness success accepts any non-empty text event: `src/skills/mash-parallel/scripts/mash_parallel.py:1217-1244`.

Why it is complexity: the orchestration graph describes important review stages, but prompt contract is only defined for four others. Agent has to infer the work from a phase label and placeholder identity.

Simpler workflow: create one compact contract for scaffold and one for integrated verification. Pass the verifier type and integrated tip explicitly. Alternatively remove these stages if they are not required; the current generic prompt is not a contract.

What you lose: none if the stages remain; removing them loses shared-contract preparation or integrated validation.

## C13. Parallel's integration gate is not a general integration test suite

Class: missing gate. Severity: medium. Status: OPEN

The doc calls integration "lint+test gates" and the integration verification phase. The code's `_default_integration_gate` runs only `src/skills/mash-parallel/tests` if that directory exists in the integration worktree; otherwise it reports a visible skip and passes. In an application repo without that exact path, the alleged integration test gate is skipped.

Evidence:
- Integration claims: `src/skills/mash-parallel/SKILL.md:72-74`.
- Exact test lookup and skip-as-success: `src/skills/mash-parallel/scripts/mash_parallel.py:413-445`.
- `integrate` calls supplied gate on merged result: `src/skills/mash-parallel/scripts/mash_parallel.py:2217-2226`.

Simpler workflow: use each task's resolved verification commands or one explicit epic-level integration command. If no project gate exists, report "not configured" distinctly from passing; do not imply app tests ran.

What you lose: the orchestrator self-test when this repo itself is the target. Keep that test as a separate self-check, not the universal integration gate.

## C14. Three full-review personas cover complexity and maintainability

Class: persona overlap. Severity: low. Status: OPEN

Every full QA run spawns maintainability and ponytail; both cover complexity deletion and abstractions. Document review separately has scope-guardian for unjustified complexity. Each has a distinctive lens, but three always-on-or-stage-level reviews can create overlapping findings and synthesis work.

Evidence:
- QA always-on roster: `src/skills/mash-qa/references/persona-catalog.md:7-16`.
- Maintainability focus overlaps complexity: `src/skills/mash-qa/references/persona-catalog.md:14`.
- Ponytail is explicitly separate but complexity-adjacent: `src/skills/mash-qa/references/persona-catalog.md:15-16`.
- Scope-guardian is in the doc-review conditional roster: `src/skills/mash-doc-review/SKILL.md:143-152`.

Simpler workflow: maintain one always-on complexity reviewer and make the second conditional on diff type/size. Keep scope-guardian document-only.

What you lose: a dedicated second opinion focused exclusively on over-engineering. Do not merge personas if the distinct findings demonstrate value.

## C15. Debug describes an unreachable branch-creation path

Class: dead path. Severity: low. Status: OPEN

Phase 3 says work in place; Phase 4 says the next move depends on whether the skill created a branch, then provides a "Pre-existing branch (skill did not create it)" flow. The branch-creation condition cannot arise in the documented implementation.

Evidence:
- Work in place / no branch creation: `src/skills/mash-debug/SKILL.md:218-220`.
- Branch-dependent handoff: `src/skills/mash-debug/SKILL.md:257-270`.

Simpler workflow: remove the unreachable branch test and say "after the fix, commit in place, then offer `mash-pr`." Keep the option for a user already on a pre-existing feature branch if behavior differs.

What you lose: none for the current skill path.

## C16. Four skills mandate re-reading references already in context

Class: ceremony. Severity: low. Status: OPEN

Brainstorm, plan, epic-frame, and work each say a reference read before phase entry does not count; they require reading it again even when already in context. This creates repeated reads across long workflows. The rule is tied to distributed procedure: each phase's real instructions live in separate files.

Evidence:
- `src/skills/mash-brainstorm/SKILL.md:92`.
- `src/skills/mash-epic-frame/SKILL.md:84`.
- `src/skills/mash-plan/SKILL.md:125`.
- `src/skills/mash-work/SKILL.md:86`.

Simpler workflow: phase table points at one owner; read before first use in the run. If deliberate re-reading guards against stale context, scope it to long waits or file changes rather than every phase transition.

What you lose: protection against an agent relying on an old or incomplete read after the workflow has moved on. Keep mandatory reread for genuinely mutable inputs, not static instructions.

---

## Corpus-wide complexity that is already under control

Not every long or duplicated instruction is a simplification target.

- `mash-lint` is mostly linear: inventory tooling, run format/lint/typecheck/build, return a handoff (`src/skills/mash-lint/SKILL.md:35-101`). Its phases have clear stop conditions and output contract.
- `mash-release` is a long sequence of preconditions and release gates. They mostly change whether a release is safe to continue; removing them would reduce safety, not workflow complexity.
- `mash-hindsight` has one clear CLI contract. Consolidate duplicated caller gates, not the memory behavior.
- Thin loaders (`agent-browser`, `chrome-devtools`, `cua-driver`) delegate to a specialized skill and do not add competing workflow paths.
- Caveman and ponytail explicitly define which rule owns activation and which skill owns detailed semantics (`src/rules/caveman.mdc:72-78`, `src/rules/ponytail.mdc:55-61`). That dual-file split is deliberate, not an authority conflict.

## Priority order by workflow simplification

| Rank | Opportunity | Why it ranks here |
|---|---|---|
| 1 | C1 — resolve auto-invocation policy for epic chain | Removes a direct mandatory-rule contradiction that can halt a run. |
| 2 | C2 — simplify QA entry/scope tree; fix checkout/stash conflict | Highest branch fan-out on common review path. |
| 3 | C3 — make integrated QA conditional after per-task QA | Removes work from the parallel happy path while preserving integration risk check. |
| 4 | C12 + C13 — give scaffold/verify contracts and integration gate real semantics | Existing stages currently promise more than the helper contract guarantees. |
| 5 | C4 — assign one shared-contract owner | Removes repeated planning/review responsibility and prose-vs-CLI mismatch. |
| 6 | C5 — accept task-goal origin explicitly | Deletes a workaround artifact and clarifies provenance. |
| 7 | C6 — shared routing rule for ideate/brainstorm/epic/plan | Reduces wrong-door starts and incompatible scope responses. |
| 8 | C7 — emit and consume one ideation run profile | Collapses repeated collision resolution across phases. |
| 9 | C8–C10 — consolidate shared Hindsight/question/verification contracts | Removes repeat reading and sources of drift, but mostly preserves flow. |
| 10 | C11, C14–C16 — orphan agents, overlapping persona, dead branch, rereads | Real but narrower; handle after pipeline owners agree on larger boundaries. |

The order is about agent/user path simplification, not line count or cleanup convenience. Some choices trade safety for speed and should be tested against real use before adoption.

---

**Analysis only.** No corpus changes proposed here have been applied. This document records opportunities, not a refactor plan or approval to make changes.
