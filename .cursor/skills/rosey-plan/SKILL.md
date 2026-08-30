---
name: rosey-plan
description: "Create structured plans for multi-step tasks -- software features, research workflows, events, study plans, or any goal that benefits from breakdown. Also deepens existing plans with interactive sub-agent review. Use when the user says 'plan this', 'create a plan', 'how should we build', 'break this down', or when a brainstorm doc is ready for planning. Use 'deepen the plan' or 'deepening pass' for the deepening flow. For exploratory requests, prefer rosey-brainstorm first."
argument-hint: "[optional: feature description, requirements doc path, plan path to deepen, or any task to plan]"
---

# Rosey Plan

**Note: The current year is 2026.** Use this when dating plans and searching for recent documentation.

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, or when the user asks for normal or long-form wording.

`rosey-brainstorm` defines **WHAT** to build. `rosey-plan` defines **HOW** to build it. `rosey-work` executes the plan. A prior brainstorm is useful context but never required — `rosey-plan` works from any input: a requirements doc, a bug report, a feature idea, or a rough description.

**When directly invoked, always plan.** Never classify a direct invocation as "not a planning task" and abandon the workflow. If the input is unclear, ask clarifying questions or use the planning bootstrap (Phase 0.4) to establish enough context — but always stay in the planning workflow.

This workflow produces a durable implementation plan. It does **not** implement code, run tests, or learn from execution-time results. If the answer depends on changing code and seeing what happens, that belongs in `rosey-work`, not here.

## Rosey Overlay

This skill follows the Rosey-native plan workflow, with Rosey Sentrux integration:

- Input is a requirements document from `rosey-brainstorm` or a direct planning prompt. There is no separate PRD/product step.
- Plans use Implementation Units (`U1`, `U2`, ...) rather than day-by-day task groups.
- Read [`rosey-sentrux`](../rosey-sentrux/SKILL.md) before using Sentrux. Use MCP tools only; never run `sentrux scan` in the terminal.
- Produce a Sentrux topology artifact beside the plan when Sentrux is available. If unavailable, still write the plan and record `status: "unavailable"` in the topology artifact.

## Interaction Method

When asking the user a question, use the platform's blocking question tool: `AskUserQuestion` in Claude Code (call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded), `request_user_input` in Codex, `ask_user` in Gemini, `ask_user` in Pi (requires the `pi-ask-user` extension). Fall back to numbered options in chat only when no blocking tool exists in the harness or the call errors (e.g., Codex edit modes) — not because a schema load is required. Never silently skip the question.

Ask one question at a time. Prefer a concise single-select choice when natural options exist.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. The skill may ask blocking questions and present post-generation options.
- `mode:non-interactive` — scripted or skill-to-skill execution. The skill must not ask blocking questions or wait for confirmations.

Strip the interaction mode token before treating the remainder as the feature description or path. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

In non-interactive mode, make conservative assumptions from the prompt, origin document, repo research, and Sentrux context. Route unvalidated bets to `## Assumptions`, skip post-generation menus, and stop with a structured blocker when safe progress requires human judgment.

## Feature Description

<feature_description> #$ARGUMENTS </feature_description>

**If the feature description above is empty, ask the user:** "What would you like to plan? Describe the task, goal, or project you have in mind." Then wait for their response before continuing.

If the input is present but unclear or underspecified, do not abandon — ask one or two clarifying questions, or proceed to Phase 0.4's planning bootstrap to establish enough context. The goal is always to help the user plan, never to exit the workflow.

**IMPORTANT:** Use repo-relative paths everywhere in the plan (e.g., `src/models/user.rb`), never absolute paths. This applies to unit file lists, pattern references, origin links, and prose.

## Core Principles

1. **Use requirements as the source of truth** - If `rosey-brainstorm` produced a requirements document, planning should build from it rather than re-inventing behavior.
2. **Decisions, not code** - Capture approach, boundaries, files, dependencies, risks, and test scenarios. Do not pre-write implementation code or shell choreography. Pseudo-code is fine only as directional design guidance.
3. **Research before structuring** - Explore the codebase, institutional learnings, and external guidance when warranted before finalizing the plan.
4. **Right-size the artifact** - Small work gets a compact plan. Large work gets more structure. The philosophy stays the same at every depth.
5. **Separate planning from execution discovery** - Resolve planning-time questions here. Explicitly defer execution-time unknowns to implementation.
6. **Keep the plan portable** - The plan should work as a living document, review artifact, or issue body without embedding tool-specific executor instructions.
7. **Carry execution posture lightly when it matters** - Note test-first, characterization-first, or similar posture when clearly implied. Do not turn it into execution choreography.
8. **Honor user-named resources** - Treat named CLIs, MCP servers, URLs, files, docs, or artifacts as authoritative. Discover them before substituting. If unavailable, say so.
9. **Compact non-interactive artifacts** - In `mode:non-interactive`, preserve requirements traceability, Implementation Units, files, test scenarios, verification, risks, and Sentrux notes, but trim narrative setup and duplicate rationale. Interactive plans stay human-readable.

## Plan Quality Bar

Every plan should contain:
- A clear problem frame and scope boundary
- Concrete requirements traceability back to the request or origin document
- Repo-relative file paths for the work being proposed (never absolute paths — see Planning Rules)
- Explicit test file paths for feature-bearing implementation units
- Decisions with rationale, not just tasks
- Existing patterns or code references to follow
- Enumerated test scenarios for each feature-bearing unit, specific enough that an implementer knows exactly what to test without inventing coverage themselves
- Clear dependencies and sequencing

A plan is ready when an implementer can start confidently without needing the plan to write the code for them.

## Workflow

### Phase 0: Resume, Source, and Scope

**Hindsight gate (hard):** Before any Phase 0 subsection, run the gate in `.cursor/rules/hindsight-memory.mdc`. Emit `Hindsight: recalled` or `Hindsight: unavailable` in the first status message. Do not search requirements or dispatch research until the gate completes.

Non-interactive mode: still run `daemon status`; if recall fails, record `HINDSIGHT: unavailable` in plan assumptions.

#### 0.0 Markdown Output

Plans are always markdown (`.md`). Read `references/markdown-rendering.md` for format principles, paired with `references/plan-sections.md` for section content.

When `mode:non-interactive` is active, apply Compact non-interactive artifacts from Core Principles: preserve execution-critical fields and trim narrative.

**Token-parsing convention:** only literal-prefix flag tokens (`mode:`, `delegate:` where applicable) are consumed and stripped. Other `<word>:<word>` tokens — including conventional commit prefixes like `feat:`, `fix:`, `chore:` that may appear inside a feature description — pass through verbatim.

#### 0.1 Resume Existing Plan Work When Appropriate

If the user references an existing plan file or there is an obvious recent matching plan in `rosey/plans/`:
- Read it
- Confirm whether to update it in place or create a new plan
- If updating, revise only the still-relevant sections. Plans do not carry per-unit progress state — progress is derived from git by `rosey-work`, so there is no progress to preserve across edits

**Deepen intent:** The word "deepen" (or "deepening") in reference to a plan is the primary trigger for the deepening fast path. When the user says "deepen the plan", "deepen my plan", "run a deepening pass", or similar, the target document is a **plan** in `rosey/plans/`, not a requirements document. Use any path, keyword, or context the user provides to identify the right plan. If a path is provided, verify it is actually a plan document. If the match is not obvious, confirm with the user before proceeding.

Words like "strengthen", "confidence", "gaps", and "rigor" are NOT sufficient on their own to trigger deepening. These words appear in normal editing requests ("strengthen that section about the diagram", "there are gaps in the test scenarios") and should not cause a holistic deepening pass. Only treat them as deepening intent when the request clearly targets the plan as a whole and does not name a specific section or content area to change — and even then, prefer to confirm with the user before entering the deepening flow.

Once the plan is identified and appears complete (all major sections present, implementation units defined, `status: active`):
- **`.md` plan WITH YAML frontmatter:** short-circuit to Phase 5.3 (Confidence Check and Deepening) in **interactive mode**.
- **`.md` plan WITHOUT YAML frontmatter** (non-software plans use a simple `# Title` heading with `Created:` date instead): route to `references/universal-planning.md` for editing or deepening instead of Phase 5.3. Non-software plans do not use the software confidence check.

The Phase 5.3 short-circuit avoids re-running the full planning workflow and gives the user control over which findings are integrated.

Normal editing requests (e.g., "update the test scenarios", "add a new implementation unit", "strengthen the risk section") should NOT trigger the fast path — they follow the standard resume flow.

If the plan already has a `deepened: YYYY-MM-DD` frontmatter field and there is no explicit user request to re-deepen, the fast path still applies the same confidence-gap evaluation — it does not force deepening.

#### 0.1b Classify Task Domain

If the task involves building, modifying, or architecting software (references code, repos, APIs, databases, or asks to build/modify/deploy), continue to Phase 0.2.

If the domain is genuinely ambiguous (e.g., "plan a migration" with no other context), ask the user before routing.

Otherwise, read `references/universal-planning.md` and follow that workflow instead. Skip all subsequent phases. Named tools or source links don't change this routing — they're inputs, handled per Core Principle 8.

#### 0.2 Find Upstream Requirements Document

Before asking planning questions, search `rosey/brainstorms/` for files matching `*-requirements.md`.

**Relevance criteria:** A requirements document is relevant if:
- The topic semantically matches the feature description
- It was created within the last 30 days (use judgment to override if the document is clearly still relevant or clearly stale)
- It appears to cover the same user problem or scope

If multiple source documents match, ask which one to use using the platform's blocking question tool when available (see Interaction Method). Otherwise, present numbered options in chat and wait for the user's reply before proceeding.

#### 0.3 Use the Source Document as Primary Input

If a relevant requirements document exists:
1. Read it thoroughly
2. Announce that it will serve as the origin document for planning
3. Carry forward all of the following:
   - Problem frame
   - Actors (A-IDs), Key Flows (F-IDs), and Acceptance Examples (AE-IDs) when present — preserve these as constraints that implementation units must honor
   - Requirements and success criteria
   - Scope boundaries (including "Deferred for later" and "Outside this product's identity" subsections when present)
   - Key decisions and rationale
   - Dependencies or assumptions
   - Outstanding questions, preserving whether they are blocking or deferred
4. Use the source document as the primary input to planning and research
5. Reference important carried-forward decisions in the plan with `(see origin: <source-path>)`
6. Do not silently omit source content — if the origin document discussed it, the plan must address it even if briefly. Before finalizing, scan each section of the origin document to verify nothing was dropped.

If no relevant requirements document exists, planning may proceed from the user's request directly.

#### 0.4 Planning Bootstrap (No Requirements Doc or Unclear Input)

If no relevant requirements document exists, or the input needs more structure:
- Assess whether the request is already clear enough for direct technical planning — if so, continue to Phase 0.5
- If the ambiguity is mainly product framing, user behavior, or scope definition, recommend `rosey-brainstorm` as a suggestion — but always offer to continue planning here as well
- If the user wants to continue here (or was already explicit about wanting a plan), run the planning bootstrap below

The planning bootstrap should establish:
- Problem frame
- Intended behavior
- Scope boundaries and obvious non-goals
- Success criteria
- Blocking questions or assumptions

Keep this bootstrap brief. It exists to preserve direct-entry convenience, not to replace a full brainstorm.

If the bootstrap uncovers major unresolved product questions:
- Recommend `rosey-brainstorm` again
- If the user still wants to continue, require explicit assumptions before proceeding

If the bootstrap reveals that a different workflow would serve the user better:

- **Bug-shaped prompt** (user describes broken behavior — "fix the bug where X", error message, regression, "doesn't work"). Surface `rosey-debug` as a route-out option alongside continuing with `rosey-plan` whenever the bug surface is reachable (in cwd OR named repo found at another local path). Stay in `rosey-plan` silently when the named code can't be found anywhere local — paper-planning is the only useful output for unreachable surfaces.

  **When the bug is at another local path (not cwd):**
  - Announce the target explicitly **before** any cross-repo investigation: which path will be read AND where plan outputs will land (default: target repo's `rosey/plans/`, not cwd's).
  - Default: proceed from the target repo for both investigation and plan-write. The user can interrupt to redirect (switch context, paper-plan, abandon, etc.). No location menu — the announcement makes the cross-repo nature visible, and the user can speak up if they want something unusual.
  - **After** announcing and proceeding, fire the standard rosey-debug routing menu (continue with `rosey-plan` vs switch to `rosey-debug`) — same shape as the in-cwd case. Cross-repo location and rosey-debug skill routing are orthogonal decisions; do not merge them into a single question.

  Reading code at another path is fine in principle — that's just file access. The harm to avoid is silent operation on the wrong repo, especially writing the plan doc somewhere it won't be discovered (a busyblock plan landing in `cli-printing-press/rosey/plans/` is a discoverability disaster). The announcement requirement makes the target visible; defaulting to the target repo for both investigation and outputs respects the user's stated intent (they named that repo); the orthogonal rosey-debug menu keeps the skill-choice question clean.

  The accessibility classification is conservative and may under-suggest in monorepos, dependency bugs, or after renames. Users can always invoke `/rosey-debug` manually.

  **Non-interactive mode**: skip the rosey-debug suggestion menu entirely; default to continuing with `/rosey-plan` (the explicit invocation). There is no synchronous user to resolve a route-out choice, and auto-routing to rosey-debug would change the skill mid-flight without authorization.

- **Clear task ready to execute** (known root cause, obvious fix, no architectural decisions) — suggest `rosey-work` as a faster alternative alongside continuing with planning. The user decides.

#### 0.5 Classify Outstanding Questions Before Planning

If the origin document contains `Resolve Before Planning` or similar blocking questions:
- Review each one before proceeding
- Reclassify it into planning-owned work **only if** it is actually a technical, architectural, or research question
- Keep it as a blocker if it would change product behavior, scope, or success criteria

If true product blockers remain:
- Surface them clearly
- Ask the user, using the platform's blocking question tool when available (see Interaction Method), whether to:
  1. Resume `rosey-brainstorm` to resolve them
  2. Convert them into explicit assumptions or decisions and continue
- Do not continue planning while true blockers remain unresolved

#### 0.6 Assess Plan Depth

Classify the work into one of these plan depths:

- **Lightweight** - small, well-bounded, low ambiguity
- **Standard** - normal feature or bounded refactor with some technical decisions to document
- **Deep** - cross-cutting, strategic, high-risk, or highly ambiguous implementation work

If depth is unclear, ask one targeted question and then continue.

#### 0.7 Solo-Mode Scoping Synthesis

Surface call-outs to the user — the specific forks in scope or approach where user input materially changes the plan — so scope can be corrected **before Phase 1 research is spent**. Sub-agent dispatch (repo-research-analyst, learnings-researcher, etc.) is the expensive next step this phase guards against wasted effort on.

Fires **only in solo invocation** — when Phase 0.2 found no upstream brainstorm doc AND Phase 0.4 stayed in rosey-plan (did not route to rosey-debug, rosey-work, or universal-planning) AND Phase 0.5 cleared (no unresolved blockers) AND not on Phase 0.1 fast paths (resume normal, deepen-intent). Each guard is an explicit conditional. Skip Phase 0.7 entirely when any guard fails — brainstorm-sourced invocations defer to Phase 5.1.5 instead.

**Read `references/synthesis-summary.md` before composing the scoping synthesis.** It carries the affirmability test, keep-test criteria, detail test, summary shape budgets, granularity rules, anti-patterns, revision-vs-confirmation discipline, doc-shape routing, soft-cut behavior, self-redirect support, the worked PII compression example, and full headless-mode routing — all required for a well-shaped synthesis.

**Required gate output — do not skip; silent proceeding is not allowed.** Compose an internal three-bucket scope draft (Stated / Inferred / Out of scope — internal thinking that feeds plan-body routing at Phase 5.2, not the chat output below). Derive call-outs (specific forks where user input materially changes the plan), then emit one of the two literal templates below in chat before continuing to Phase 1.

**Synthesis is pre-plan-write.** The agent does NOT yet know how plan-write will sequence the work. Do not claim PR count ("one PR"), commit/branch shape, effort or time estimates, Implementation Unit boundaries, or exact file paths in the synthesis. The synthesis surfaces decisions knowable at THIS point — for the solo variant, that's the user's request plus the Phase 0.4 bootstrap dialogue plus the agent's own internal three-bucket draft. Phase 1 research has not happened yet and there is no upstream brainstorm; do not claim grounding from either. Plan-write produces the rest. This rule holds even when the agent has formed plan-write opinions earlier in the session — those stay internal until plan-write.

**Summary shape:** the summary is a **scope claim** — what the plan will target, what it will not — at affirm-or-redirect level. NOT an enumeration of Implementation Units. Form is prose, bullets, or mix; tier budgets are **ceilings, not targets** (Lightweight 1-3 lines; Standard up to 3-5 lines or 2-4 bullets; Deep up to 4-6 lines or 3-6 bullets). 1-2 lines per bullet, conversational not documentary. Less is correct when there isn't more to say. See reference for keep test, detail test, and source-vocabulary discipline.

**Do NOT enumerate the touch surface.** Sentences like "The touch surface is...", "This plan touches...", "The implementation reaches into..." are plan-pitch leaks. File paths, module names, directory introductions, and per-file change descriptions belong in the plan body (Implementation Units at Phase 5.2), not the synthesis. The synthesis names *what* the plan targets, not *where* the code lives.

**Pre-emit scans.** Before emitting the synthesis, scan the output:
- Bare ID references (`AE\d+`, `R\d+`, `F\d+`, `A\d+`, `U\d+`) → replace with plain names.
- File paths (`path/like.md`, `path/like.py`, etc.) → cut unless the path IS the topic of an explicit fork in the call-outs.

**Tier guard on auto-proceed:** the auto-proceed path (announce without waiting for confirmation) fires only when plan depth is **Lightweight AND zero call-outs survive**. Standard and Deep plans always fire the confirmation gate, even with zero call-outs — substance earns the checkpoint, not interaction history.

**Confirmation template (Standard/Deep regardless of call-out count, or any tier with one or more call-outs surviving):**

````text
Based on your request and our brief discussion, here's the scope I'm proposing to plan against:

[scope claim — what the plan will target, what it will not; affirm-or-redirect level; NOT an enumeration of Implementation Units]

**Call outs:** (omit this header when zero forks survived the keep test)
- [decision-level fork in 1-2 lines: name the choice and optional one-clause trade-off in parens. NO multi-sentence rationale, NO "my default is X" pitch]

Confirm and I'll proceed to research, drawing on this scope. (You can also redirect to /rosey-brainstorm if this is bigger than you initially thought — I'll stop here and load it for you.)
````

Wait for user confirmation before continuing to Phase 1.

**Auto-proceed template (Lightweight with zero call-outs only):**

````text
Planning: [1-3 line scope claim]

No open decisions to weigh in on — proceeding to research. Interrupt if I have the scope wrong.
````

Then continue to Phase 1 without a blocking question.

   **Non-interactive mode**: internal draft is composed but stage 2 (chat-time call-outs) is skipped — no synchronous user to confirm to. Continue to Phase 1 research as normal. At plan-write time (Phase 5.2), Inferred bets from the internal draft route to a `## Assumptions` section in the plan instead of Key Technical Decisions. See `references/synthesis-summary.md` Non-interactive mode for the full routing.

### Phase 1: Gather Context

#### 1.1 Local Research (Always Runs)

Prepare a concise planning context summary (a paragraph or two) to pass as input to the research agents:
- If an origin document exists, summarize the problem frame, requirements, and key decisions from that document
- Otherwise use the feature description directly
- If `STRATEGY.md` exists, read it and include the relevant pieces (target problem, approach, active tracks) in the summary so downstream research and planning decisions are anchored to product strategy

Before dispatching local research agents, read [`rosey-hindsight`](../rosey-hindsight/SKILL.md) and recall memory with the planning context summary. If the Phase 0 gate already ran, fold recall into planning context; do not skip recall unless unavailable was documented. Treat useful recall output as additional planning context, alongside but separate from `rosey/solutions/` institutional learnings. If Hindsight is unavailable or not configured, continue Phase 1 and note memory unavailability only when it materially affects the plan context.

Run these agents in parallel:

- Task rosey-repo-research-analyst(Scope: technology, architecture, patterns. {planning context summary})
- Task rosey-learnings-researcher(planning context summary)
Collect:
- Technology stack and versions (used in section 1.2 to make sharper external research decisions)
- Architectural patterns and conventions to follow
- Implementation patterns, relevant files, modules, and tests
- AGENTS.md guidance that materially affects the plan, with CLAUDE.md used only as compatibility fallback when present
- Institutional learnings from `rosey/solutions/`
- Product strategy context when `STRATEGY.md` is present — flag any plan decisions that pull away from the active tracks or the stated approach

#### 1.1b Detect Execution Posture Signals

Decide whether the plan should carry a lightweight execution posture signal.

Look for signals such as:
- The user explicitly asks for TDD, test-first, or characterization-first work
- The origin document calls for test-first implementation or exploratory hardening of legacy code
- Local research shows the target area is legacy, weakly tested, or historically fragile, suggesting characterization coverage before changing behavior

When the signal is clear, carry it forward silently in the relevant implementation units.

Ask the user only if the posture would materially change sequencing or risk and cannot be responsibly inferred.

#### 1.2 Decide on External Research

Based on the origin document, user signals, and local findings, decide **whether** external research adds value and, if so, **what kind**. Resolve this in three stages: explicit-request priority, intent classification, then the implicit signals below.

**Stage 1 — An explicit request takes precedence.** If the user prompt **or** the origin requirements document explicitly asks for external input — a signal that the answer lives outside the repo, such as competitor/prior-art comparison, "what should we borrow", "from the web", "best practices", "official docs", "alternatives to", a market scan, or naming a specific external technology to consult — external research is **required**, regardless of how strong local patterns look. The list is illustrative; key on the signal, not the exact phrase — any wording that clearly points outside the repo qualifies. The skip conditions below do **not** apply to an explicit request. The only thing that overrides it is an explicit opt-out ("no web research", "skip external research"): honor that, skip, and note it. Improvement or quality verbs ("improve", "make better") carry no external signal on their own and never trigger research by themselves.

**Stage 2 — Classify the research intent** (whenever external research will run, from Stage 1 or the implicit signals below) so Phase 1.3 routes correctly. Use this mechanical test, not a fixed phrase list:
- **Implementation-guidance** — the approach or technology is already settled; the question is *how to build it well* (best practices, version-specific docs, API constraints, known pitfalls, deprecations).
- **Landscape / option-discovery** — the question is *what options or prior art exist* (competitor scans, build-vs-buy, library/provider selection, prior art, market signals, cross-domain analogies).
- **Mixed** — both: discover an unsettled external option set first, then research the shortlisted choice for implementation guidance.

**Stage 3 — Implicit signals** decide the call when no explicit request fired.

**Read between the lines.** Pay attention to signals from the conversation so far:
- **User familiarity** — Are they pointing to specific files or patterns? They likely know the codebase well.
- **User intent** — Do they want speed or thoroughness? Exploration or execution?
- **Topic risk** — Security, payments, external APIs warrant more caution regardless of user signals.
- **Uncertainty level** — Is the approach clear or still open-ended?

**Leverage rosey-repo-research-analyst's technology context:**

The rosey-repo-research-analyst output includes a structured Technology & Infrastructure summary. Use it to make sharper external research decisions:

- If specific frameworks and versions were detected (e.g., Rails 7.2, Next.js 14, Go 1.22), pass those exact identifiers to rosey-framework-docs-researcher so it fetches version-specific documentation
- If the feature touches a technology layer the scan found well-established in the repo (e.g., existing Sidekiq jobs when planning a new background job), lean toward skipping external research -- local patterns are likely sufficient
- If the feature touches a technology layer the scan found absent or thin (e.g., no existing proto files when planning a new gRPC service), lean toward external research -- there are no local patterns to follow
- If the scan detected deployment infrastructure (Docker, K8s, serverless), note it in the planning context passed to downstream agents so they can account for deployment constraints
- If the scan detected a monorepo and scoped to a specific service, pass that service's tech context to downstream research agents -- not the aggregate of all services. If the scan surfaced the workspace map without scoping, use the feature description to identify the relevant service before proceeding with research

**Always lean toward external research when:**
- The topic is high-risk: security, payments, privacy, external APIs, migrations, compliance
- The codebase lacks relevant local patterns -- fewer than 3 direct examples of the pattern this plan needs
- Local patterns exist for an adjacent domain but not the exact one -- e.g., the codebase has HTTP clients but not webhook receivers, or has background jobs but not event-driven pub/sub. Adjacent patterns suggest the team is comfortable with the technology layer but may not know domain-specific pitfalls. When this signal is present, frame the external research query around the domain gap specifically, not the general technology
- The user is exploring unfamiliar territory
- The technology scan found the relevant layer absent or thin in the codebase
- The plan's recommendations depend on a genuinely external, **unsettled** option set — which library, provider, or approach to adopt, or what competitors and prior art do — **even when local implementation patterns are strong** (intent: landscape). Bound this implicit landscape trigger by three gates: (a) the option set genuinely lives outside the repo, (b) the decision materially shapes the plan (a KTD, dependency, or architecture choice — not an incidental detail), and (c) no settled local or team choice already exists. Improvement verbs alone never satisfy this.

**Skip external research when** (only when Stage 1 found no explicit request — an explicit request is never skipped):
- The codebase already shows a strong local pattern -- multiple direct examples (not adjacent-domain), recently touched, following current conventions
- The user already knows the intended shape
- Additional external context would add little practical value
- The technology scan found the relevant layer well-established with existing examples to follow

When an explicit request *did* fire but a settled local or team choice already exists, **narrow the research rather than skipping it** — research the current pitfalls, docs, and practices for the chosen library/pattern instead of re-surveying the whole option set.

Announce the decision and the intent briefly before continuing. Examples:
- "Your codebase has solid patterns for this. Proceeding without external research."
- "This involves payment processing, so I'll research current best practices first (implementation-guidance)."
- "You asked what to borrow from competitors, so I'll run a landscape scan first (landscape/option-discovery)."

#### 1.3 External Research (Conditional)

If Step 1.2 indicates external research is useful, dispatch by the **intent** classified in Stage 2, using the platform's subagent primitive (`Agent`/`Task` in Claude Code, `spawn_agent` in Codex, `subagent` in Pi). For `rosey-web-researcher`, pass a focus hint plus the planning context summary and do **not** pass codebase content — it operates externally.

- **Implementation-guidance** — run in parallel:
  - Task rosey-best-practices-researcher(planning context summary)
  - Task rosey-framework-docs-researcher(planning context summary, with exact frameworks/versions from Phase 1.1 where available)
- **Landscape / option-discovery** — Task rosey-web-researcher(focus hint, planning context summary). When the request targets projects on a code host (e.g., "competitors on GitHub"), name the discovery dimensions in the focus hint: project names and URLs, release recency and activity, CLI/UX shape, install path, docs and examples, plugin/extension surfaces, recurring issue themes, and license — treating star counts as a weak signal only.
- **Mixed** — **sequential, not parallel**: run `rosey-web-researcher` first to map the landscape and produce a shortlist; then run `rosey-framework-docs-researcher` and/or `rosey-best-practices-researcher` against the shortlisted technologies only when their details materially shape the plan.

**Tool-unavailable handling.** `rosey-web-researcher` self-checks for web tools and stops if they are missing. Never block on this: if it reports research unavailable, or any researcher fails, warn and proceed, and carry the gap into Phase 1.4 so the plan records it honestly — especially when the user explicitly requested external research, where a silent skip would leave the plan looking evidence-based when it is not.

#### 1.4 Consolidate Research

Summarize:
- Relevant codebase patterns and file paths
- Relevant institutional learnings
- Organizational context from Slack conversations, if gathered (prior discussions, decisions, or domain knowledge relevant to the feature)
- External references, prior art, competitor/landscape findings, and best practices, if gathered
- Related issues, PRs, or prior art
- Any constraints that should materially shape the plan

**Land external findings in decisions, not an appendix.** Any external research that ran must surface where it changes a choice — Key Technical Decisions rationale, Alternatives, Risks, or Sources & Research — not as a detached list with no bearing on the plan. If a finding shaped nothing, it was not load-bearing; do not pad the plan with it.

**Mark whether external research was load-bearing.** Record a single internal flag: did external findings materially shape a KTD, Alternative, Scope boundary, or Risk? This flag answers only that question — it does **not** gate whether research runs (Phase 1.2 owns that decision). Phase 5.3.2 reads it to decide whether to enter a confidence-scoring pass.

**Record requested-but-unavailable.** If the user explicitly requested external research but it could not run (web tools unavailable, researcher failed), state that in the plan as an assumption or open question rather than presenting the plan as externally grounded.

#### 1.4b Reclassify Depth When Research Reveals External Contract Surfaces

If the current classification is **Lightweight** and Phase 1 research found that the work touches any of these external contract surfaces, reclassify to **Standard**:

- Environment variables consumed by external systems, CI, or other repositories
- Exported public APIs, CLI flags, or command-line interface contracts
- CI/CD configuration files (`.github/workflows/`, `Dockerfile`, deployment scripts)
- Shared types or interfaces imported by downstream consumers
- Documentation referenced by external URLs or linked from other systems

This ensures flow analysis (Phase 1.5) runs and the confidence check (Phase 5.3) applies critical-section bonuses. Announce the reclassification briefly: "Reclassifying to Standard — this change touches [environment variables / exported APIs / CI config] with external consumers."

#### 1.5 Flow and Edge-Case Analysis (Conditional)

For **Standard** or **Deep** plans, or when user flow completeness is still unclear, run:

- Task rosey-spec-flow-analyzer(planning context summary, research findings)

Use the output to:
- Identify missing edge cases, state transitions, or handoff gaps
- Tighten requirements trace or verification strategy
- Add only the flow details that materially improve the plan

### Phase 2: Resolve Planning Questions

Build a planning question list from:
- Deferred questions in the origin document
- Gaps discovered in repo or external research
- Technical decisions required to produce a useful plan

For each question, decide whether it should be:
- **Resolved during planning** - the answer is knowable from repo context, documentation, or user choice
- **Deferred to implementation** - the answer depends on code changes, runtime behavior, or execution-time discovery

Ask the user only when the answer materially affects architecture, scope, sequencing, or risk and cannot be responsibly inferred. Use the platform's blocking question tool when available (see Interaction Method).

**Do not** run tests, build the app, or probe runtime behavior in this phase. The goal is a strong plan, not partial execution.

### Phase 3: Structure the Plan

#### 3.1 Title and File Naming

- Draft a clear, searchable title using conventional format such as `feat: Add user authentication` or `fix: Prevent checkout double-submit`
- Determine the plan type: `feat`, `fix`, or `refactor`
- Build the filename following the repository convention: `rosey/plans/YYYY-MM-DD-NNN-<type>-<descriptive-name>-plan.md`
  - Create `rosey/plans/` if it does not exist
  - Check existing files for today's date to determine the next sequence number (zero-padded to 3 digits, starting at 001)
  - Keep the descriptive name concise (3-5 words) and kebab-cased
  - Examples: `2026-01-15-001-feat-user-authentication-flow-plan.md`, `2026-02-03-002-fix-checkout-race-condition-plan.md`
  - Avoid: missing sequence numbers, vague names like "new-feature", invalid characters (colons, spaces)

#### 3.2 Stakeholder and Impact Awareness

For **Standard** or **Deep** plans, briefly consider who is affected by this change — end users, developers, operations, other teams — and how that should shape the plan. For cross-cutting work, note affected parties in the System-Wide Impact section.

#### 3.2b Sentrux Topology Baseline

Before defining Implementation Units, load [`rosey-sentrux`](../rosey-sentrux/SKILL.md) and run the planning baseline:

1. Read the Sentrux MCP tool descriptors before calling tools.
2. Call MCP `scan` with the absolute workspace root.
3. Call MCP `health`.
4. Derive the dominant bottleneck/root cause and planning guidance using `rosey-sentrux`'s bottleneck mapping.
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

Each unit carries a stable plan-local **U-ID** assigned in Phase 3.5 (`U1`, `U2`, …). U-IDs survive reordering, splitting, and deletion: new units take the next unused number, gaps are fine, and existing IDs are never renumbered. This lets `rosey-work` reference units unambiguously across plan edits.

#### 3.4 High-Level Technical Design

When the plan's technical approach has shape that prose alone doesn't carry well — architecture across components, sequencing across processes, state machines, branching gates, lifecycles, quantitative comparisons — include a High-Level Technical Design section that conveys the shape. The exact form (component diagram, sequence, swim lane, flowchart, state machine, decision matrix, pseudo-code grammar, bar chart for sizing concerns) is the agent's call per artifact — pick what makes the content land fastest for the reader.

See `references/plan-sections.md` for the section catalog including HTD's "include when material" criterion. See the format-rendering reference loaded at Phase 0.0 for how visualizations render in the target format (mermaid in markdown, inline SVG in HTML — with the layout-legibility principles around halo, contrast, and label placement when in HTML).

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

Each unit is a level-3 heading carrying a stable U-ID prefix matching the format used for R/A/F/AE in requirements docs: `### U1. [Name]`. Number sequentially within the plan starting at U1. Do not render units as bulleted list items or prefix them with `- [ ]` / `- [x]` checkbox markers. List-based unit titles fragment in every standard renderer because the per-unit fields (`**Goal:**`, `**Files:**`, `**Approach:**`, etc.) are written flush-left, which terminates CommonMark list continuation and detaches the fields from the unit they describe. Headings render correctly everywhere, are the right semantic match for sections containing multi-block content, and give each unit an anchor link. The plan is a decision artifact; execution progress is derived from git by `rosey-work` rather than stored in the plan body.

**Stability rule.** Once assigned, a U-ID is never renumbered. Reordering units leaves their IDs in place (e.g., U1, U3, U5 in their new order is correct; renumbering to U1, U2, U3 is not). Splitting a unit keeps the original U-ID on the original concept and assigns the next unused number to the new unit. Deletion leaves a gap; gaps are fine. This rule matters most during deepening (Phase 5.3), which is the most likely accidental-renumber vector.

For each unit, include:
- **Goal** - what this unit accomplishes
- **Requirements** - which requirements or success criteria it advances (cite R-IDs, and A/F/AE IDs when origin supplies them)
- **Dependencies** - what must exist first (cite by U-ID, e.g., "U1, U3")
- **Files** - repo-relative file paths to create, modify, or test (never absolute paths)
- **Approach** - key decisions, data flow, component boundaries, or integration notes
- **Execution note** - optional, only when the unit benefits from a non-default execution posture such as test-first or characterization-first
- **Technical design** - optional pseudo-code or diagram when the unit's approach is non-obvious and prose alone would leave it ambiguous. Frame explicitly as directional guidance, not implementation specification
- **Patterns to follow** - existing code or conventions to mirror
- **Test scenarios** - enumerate the specific test cases the implementer should write, right-sized to the unit's complexity and risk. Consider each category below and include scenarios from every category that applies to this unit. A simple config change may need one scenario; a payment flow may need a dozen. The quality signal is specificity — each scenario should name the input, action, and expected outcome so the implementer doesn't have to invent coverage. For units with no behavioral change (pure config, scaffolding, styling), use `Test expectation: none -- [reason]` instead of leaving the field blank. **AE-link convention:** when a test scenario directly enforces an origin Acceptance Example, prefix it with `Covers AE<N>.` (or `Covers F<N> / AE<N>.`). This is sparse-by-design — most test scenarios are finer-grained than AEs and do not link. Do not force AE links onto tests that only cover lower-level implementation details.
  - **Happy path behaviors** - core functionality with expected inputs and outputs
  - **Edge cases** (when the unit has meaningful boundaries) - boundary values, empty inputs, nil/null states, concurrent access
  - **Error and failure paths** (when the unit has failure modes) - invalid input, downstream service failures, timeout behavior, permission denials
  - **Integration scenarios** (when the unit crosses layers) - behaviors that mocks alone will not prove, e.g., "creating X triggers callback Y which persists Z". Include these for any unit touching callbacks, middleware, or multi-layer interactions
- **Verification** - how an implementer should know the unit is complete, expressed as outcomes rather than shell command scripts

Every feature-bearing unit should include the test file path in `**Files:**`.

Use `Execution note` sparingly. Good uses include:
- `Execution note: Start with a failing integration test for the request/response contract.`
- `Execution note: Add characterization coverage before modifying this legacy parser.`
- `Execution note: Implement new domain behavior test-first.`

Do not expand units into literal `RED/GREEN/REFACTOR` substeps.

#### 3.6 Keep Planning-Time and Implementation-Time Unknowns Separate

If something is important but not knowable yet, record it explicitly under deferred implementation notes rather than pretending to resolve it in the plan.

Examples:
- Exact method or helper names
- Final SQL or query details after touching real code
- Runtime behavior that depends on seeing actual test failures
- Refactors that may become unnecessary once implementation starts

#### 3.7 Anti-Expansion: Tangential Cleanup and Scope Creep Go to Deferred

Distinct from 3.6 (which is about *unknowns* at plan time): 3.7 is about *known but tangential* work that the agent notices while planning but that falls outside the user's confirmed scope. When research surfaces an adjacent refactor, a "while we're here" cleanup, or a scope-adjacent nice-to-have ("we could also add rate limiting"), route it to the existing `### Deferred to Follow-Up Work` subsection in Scope Boundaries (Phase 4.2 Core Plan Template), not into active Implementation Units.

This reinforces the synthesis discipline established at Phase 0.7 / Phase 5.1.5 — the user's confirmed scope is what the active plan executes; everything else is deferred. Does NOT impose architectural bias on extend-vs-invent decisions within confirmed scope — that judgment stays with the agent (and is surfaced via the Phase 5.1.5 synthesis when material). The user's explicit ask overrides this default — if the user explicitly requested a refactor, it's in-scope, not deferred.

### Phase 4: Write the Plan

**NEVER CODE during this skill.** Research, decide, and write the plan — do not start implementation.

Use one planning philosophy across all depths. Change the amount of detail, not the boundary between planning and execution.

#### 4.1 Plan Depth Guidance

**Lightweight**
- Keep the plan compact
- Usually 2-4 implementation units
- Omit optional sections that add little value

**Standard**
- Use the full core template, omitting optional sections (including High-Level Technical Design) that add no value for this particular work
- Usually 3-6 implementation units
- Include risks, deferred questions, and system-wide impact when relevant

**Deep**
- Use the full core template plus optional analysis sections where warranted
- Usually 4-8 implementation units
- Group units into phases when that improves clarity
- Include alternatives considered, documentation impacts, and deeper risk treatment when warranted

#### 4.1b Optional Deep Plan Extensions

For sufficiently large, risky, or cross-cutting work, add the sections that genuinely help:
- **Alternative Approaches Considered**
- **Success Metrics**
- **Dependencies / Prerequisites**
- **Risk Analysis & Mitigation**
- **Phased Delivery**
- **Documentation Plan**
- **Operational / Rollout Notes**
- **Future Considerations** only when they materially affect current design

Do not add these as boilerplate. Include them only when they improve execution quality or stakeholder alignment.

**Alternatives Considered — what to vary.** When this section is included, alternatives must differ on *how* the work is built: architecture, sequencing, boundaries, integration pattern, rollout strategy. Tiny implementation variants (which hash function, which serialization format) belong in Key Technical Decisions, not Alternatives. Product-shape alternatives (different actors, different core outcome, different positioning) belong in `rosey-brainstorm`, not here — surface them back upstream rather than re-litigating product questions during planning.

#### 4.2 Section Contract and Rendering

Compose the plan using two paired references:

- `references/plan-sections.md` — the section contract. Describes what the plan contains: the outcome the plan must enable for downstream consumers, the hard floor (Summary, Problem Frame, Requirements, KTDs, Implementation Units), the include-when-material catalog (HTD, Scope Boundaries, Open Questions, System-Wide Impact, Risks & Dependencies, Acceptance Examples, Documentation/Operational Notes, Sources & Research), the agency-driven escape hatch (introduce new sections when content warrants), and the ID/content rules.
- `references/markdown-rendering.md` — how to present the sections in markdown.

The section catalog is the same regardless of format. Format-specific principles (table-vs-prose by content shape, ID prefix format, diagram rendering, etc.) live in the rendering reference.

Omit "include when material" sections that don't carry information for this specific plan. Filling a section with placeholder prose is worse than omitting it.

#### 4.3 Planning Rules

- **Horizontal rules (`---`) between top-level sections** in Standard and Deep plans, mirroring the `rosey-brainstorm` requirements doc convention. Improves scannability of dense plans where many H2 sections sit close together. Omit for Lightweight plans where the whole doc fits on a single screen.
- **All file paths must be repo-relative** — never use absolute paths like `/Users/name/Code/project/src/file.ts`. Use `src/file.ts` instead. Absolute paths make plans non-portable across machines, worktrees, and teammates. When a plan targets a different repo than the document's home, state the target repo once at the top of the plan (e.g., `**Target repo:** my-other-project`) and use repo-relative paths throughout
- Prefer path plus class/component/pattern references over brittle line numbers
- Do not include implementation code — no imports, exact method signatures, or framework-specific syntax
- Pseudo-code sketches and DSL grammars are allowed in the High-Level Technical Design section and per-unit technical design fields when they communicate design direction. Frame them explicitly as directional guidance, not implementation specification
- Mermaid diagrams are encouraged when they clarify relationships or flows that prose alone would make hard to follow — ERDs for data model changes, sequence diagrams for multi-service interactions, state diagrams for lifecycle transitions, flowcharts for complex branching logic
- Do not include git commands, commit messages, or exact test command recipes
- Do not expand implementation units into micro-step `RED/GREEN/REFACTOR` instructions
- Do not pretend an execution-time question is settled just to make the plan look complete

### Phase 5: Final Review, Write File, and Handoff

#### 5.1 Review Before Writing

Before finalizing, check:
- The plan does not invent product behavior that should have been defined in `rosey-brainstorm`
- If there was no origin document, the bounded planning bootstrap established enough product clarity to plan responsibly
- Every major decision is grounded in the origin document or research
- Each implementation unit is concrete, dependency-ordered, and implementation-ready
- If test-first or characterization-first posture was explicit or strongly implied, the relevant units carry it forward with a lightweight `Execution note`
- Each feature-bearing unit has test scenarios from every applicable category (happy path, edge cases, error paths, integration) — right-sized to the unit's complexity, not padded or skimped
- Test scenarios name specific inputs, actions, and expected outcomes without becoming test code
- Feature-bearing units with blank or missing test scenarios are flagged as incomplete — feature-bearing units must have actual test scenarios, not just an annotation. The `Test expectation: none -- [reason]` annotation is only valid for non-feature-bearing units (pure config, scaffolding, styling)
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

#### 5.1.5 Brainstorm-Sourced Scoping Synthesis

Surface plan-time call-outs to the user before Phase 5.2 commits the plan to disk — the latest cheap moment to catch plan-time scope errors. The brainstorm already validated WHAT to build; this phase surfaces HOW the plan will execute on the forks that matter.

Fires **only when the plan was sourced from an upstream brainstorm doc** (Phase 0.2 found a `*-requirements.md` match) AND not on Phase 0.1 fast paths (resume normal, deepen-intent). Skip Phase 5.1.5 in solo invocation — solo plans handled their synthesis in Phase 0.7.

**Read `references/synthesis-summary.md` before composing the scoping synthesis.** It carries the affirmability test, keep-test criteria, detail test, summary shape budgets, granularity rules, anti-patterns, revision-vs-confirmation discipline, doc-body reading rules, doc-shape routing, soft-cut behavior, self-redirect support, the worked PII compression example, and full headless-mode routing — all required for a well-shaped synthesis.

**Required gate output — do not skip; silent proceeding is not allowed.** Compose an internal three-bucket scope draft (Stated / Inferred / Out of scope — internal thinking that feeds plan-body routing at Phase 5.2, not the chat output below). Derive call-outs (specific forks where user input materially changes the plan), then emit one of the two literal templates below in chat before continuing to Phase 5.2.

**Synthesis is pre-plan-write.** The agent does NOT yet know how plan-write will sequence the work. Do not claim PR count ("one PR"), commit/branch shape, effort or time estimates, Implementation Unit boundaries, or exact file paths in the synthesis. The synthesis surfaces decisions knowable at THIS point (brainstorm + research + agent posture); plan-write produces the rest. This rule holds even when the agent has formed plan-write opinions earlier in the session — those stay internal until plan-write.

**Summary shape: two paragraphs.**

1. **Brainstorm-scope restatement** (1-2 sentences, prose). Restates the brainstorm's scope as orientation, in the brainstorm's own vocabulary. NOT an enumeration of Implementation Units, restated constraints, or listed acceptance examples — the user wrote those.
2. **Plan-specific scoping decisions** (prose, or bullets when multi-faceted). Scope-level commitments the agent made that the brainstorm did not: full brainstorm coverage vs. narrowed subset; adjacent refactors pulled in vs. held out; test scope at scenario level. Each item must be affirmable by the user without reading code. Form follows substance; tier budgets are **ceilings, not targets** (Lightweight 1-3 lines; Standard up to 3-5 lines or 2-4 bullets; Deep up to 4-6 lines or 3-6 bullets). 1-2 lines per bullet. Less is correct when there isn't more to say. See reference for keep test, detail test, and source-vocabulary discipline.

**Do NOT enumerate the touch surface.** Sentences like "The touch surface is...", "This plan touches...", "The implementation reaches into...", "Files modified include..." are plan-pitch leaks. File paths, module names, directory introductions, and per-file change descriptions belong in the plan body (Implementation Units at Phase 5.2), not the synthesis. The synthesis names *what* the plan targets, not *where* the code lives.

**Pre-emit scans.** Before emitting the synthesis, scan the output:
- Bare ID references (`AE\d+`, `R\d+`, `F\d+`, `A\d+`, `U\d+`) → replace with plain names.
- File paths (`path/like.md`, `path/like.py`, etc.) → cut unless the path IS the topic of an explicit fork in the call-outs.

**Tier guard on auto-proceed:** the auto-proceed path (announce without waiting for confirmation) fires only when plan depth is **Lightweight AND zero call-outs survive**. Standard and Deep plans always fire the confirmation gate, even with zero call-outs — substance earns the checkpoint, not interaction history.

**Confirmation template (Standard/Deep regardless of call-out count, or any tier with one or more call-outs surviving):**

````text
The brainstorm scopes [1-2 sentence restatement in the brainstorm's vocabulary as orientation; NOT an enumeration of Implementation Units, constraints, or acceptance examples].

This plan [plan-specific scoping decisions: full-brainstorm coverage vs. narrowed subset; adjacent refactors in or out; test scope at scenario level. NOT PR count, sequencing, IU lists, or file paths].

**Call outs:** (omit this header when zero forks survived the keep test)
- [plan-time fork in 1-2 lines: name the choice and optional one-clause trade-off in parens. NO multi-sentence rationale, NO "my default is X" pitch]

Confirm and I'll write the plan next, drawing on the brainstorm, research, and this synthesis.
````

Wait for user confirmation before continuing to Phase 5.2.

**Auto-proceed template (Lightweight with zero call-outs only):**

````text
Planning [brief brainstorm-scope restatement] — [plan-specific shape in one clause].

No open decisions to weigh in on — proceeding to plan-write. Interrupt if I have the scope wrong.
````

Then continue to Phase 5.2 without a blocking question.

**Non-interactive mode**: internal draft is composed but stage 2 (chat-time call-outs) is skipped — no synchronous user to confirm to. Proceed to Phase 5.2 plan-write. Inferred bets from the internal draft route to a `## Assumptions` section in the plan instead of Key Technical Decisions. See `references/synthesis-summary.md` Non-interactive mode for the full routing.

#### 5.2 Write Plan File

**REQUIRED: Write the plan file to disk before presenting any options.**

Use the Write tool to save the complete plan:

```text
rosey/plans/YYYY-MM-DD-NNN-<type>-<descriptive-name>-plan.md
```

Sequence number `NNN` is derived from existing `.md` plan files in `rosey/plans/` to ensure unique daily ordering.

Compose the plan using the content from `references/plan-sections.md` and `references/markdown-rendering.md`.

Write the Sentrux topology artifact beside the plan using the same basename:

```text
rosey/plans/YYYY-MM-DD-NNN-<type>-<descriptive-name>-plan.topology.json
```

Reference this path from the plan's Architecture Baseline (Sentrux), Sources / Research, or metadata so `rosey-work` can discover it from the plan path.

Confirm (use absolute path so the reference is clickable in modern terminals):

```text
Plan written to <absolute path to plan>
```

**Non-interactive mode:** When `mode:non-interactive` is active, skip interactive questions. Make the needed choices automatically and proceed to writing the plan.

#### 5.3 Confidence Check and Deepening

After writing the plan file, automatically evaluate whether the plan needs strengthening.

**Two deepening modes:**

- **Auto mode** (default during plan generation): Runs without asking the user for approval. The user sees what is being strengthened but does not need to make a decision. Sub-agent findings are synthesized directly into the plan.
- **Interactive mode** (activated by the re-deepen fast path in Phase 0.1): The user explicitly asked to deepen an existing plan. Sub-agent findings are presented individually for review before integration. The user can accept, reject, or discuss each agent's findings. Only accepted findings are synthesized into the plan.

Interactive mode exists because on-demand deepening is a different user posture — the user already has a plan they are invested in and wants to be surgical about what changes. This applies whether the plan was generated by this skill, written by hand, or produced by another tool.

`rosey-doc-review` and this confidence check are different:
- Use the `rosey-doc-review` skill when the document needs clarity, simplification, completeness, or scope control
- This confidence check strengthens rationale, sequencing, risk treatment, and system-wide thinking when the plan is structurally sound but still needs stronger grounding

**Non-interactive mode:** This phase always runs in auto mode when `mode:non-interactive` is active. No user interaction needed.

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

If the plan already appears sufficiently grounded and neither the thin-grounding nor the load-bearing-external-research override applies, report "Confidence check passed — no sections need strengthening", then **load `references/plan-handoff.md` now and execute 5.3.8 → 5.3.9 → 5.4 in sequence**. Document review is mandatory — do not skip it because the confidence check passed. The two tools catch different classes of issues.

##### 5.3.3–5.3.7 Deepening Execution

When deepening is warranted, read `references/deepening-workflow.md` for confidence scoring checklists, section-to-agent dispatch mapping, execution mode selection, research execution, interactive finding review, and plan synthesis instructions. Execute steps 5.3.3 through 5.3.7 from that file, then return here for 5.3.8.

##### 5.3.8–5.4 Document Review, Final Checks, and Post-Generation Options

**STOP. Load `references/plan-handoff.md` now before continuing.** It carries the full instructions for 5.3.8 (document review), 5.3.9 (final checks and cleanup), and 5.4 (post-generation handoff and Issue Creation branching). **This load is non-optional** — without it, the agent renders the post-generation menu, captures the user's selection, and stops without firing the routed action. Document review at 5.3.8 runs unconditionally regardless of whether the confidence check already ran. The default mode is headless (`mode:headless`) — `safe_auto` fixes apply silently, remaining findings surface contextually above the menu, and a deeper interactive review is opt-in via free-form prompt.

After document review and final checks, print a one-line summary of the headless review state above the menu (e.g., `Doc review applied 3 fixes. 2 decisions, 1 proposed fix, 4 FYI observations remain (1 at P1).`), then present the menu. Trim and renumber options per `references/plan-handoff.md` (hide `Run deeper doc review` when there are no actionable findings). Use the platform's blocking question tool when four or fewer options remain. Never silently skip the question.

**Question:** "Plan ready at `<absolute path to plan>`. What would you like to do next?" (use absolute path so the reference is clickable in modern terminals)

**Options** (renumber after trimming; see `references/plan-handoff.md`):

1. **Start `/rosey-work`** (recommended) - Begin implementing this plan in the current session
2. **Run deeper doc review** - Walk through the remaining findings interactively (full rosey-doc-review walkthrough). Hidden when no actionable findings remain.
3. **Create Issue** - Create a tracked issue from this plan in your configured issue tracker (GitHub or Linear)
4. **Done for now** - Pause; the plan file is saved and can be resumed later

**Routing.** Act on the user's selection — do not just announce it. Elaborate sub-flows (Issue Creation tracker detection) live in `references/plan-handoff.md`.

- **Start `/rosey-work`** — Invoke the `rosey-work` skill via the platform's skill-invocation primitive (`Skill` in Claude Code, `Skill` in Codex, the equivalent on Gemini/Pi), passing the plan path as the skill argument. Do not merely tell the user to type `/rosey-work` — fire the invocation now so the plan executes in this session.
- **Run deeper doc review** — Re-invoke the `rosey-doc-review` skill on the plan path **without** `mode:headless` so the interactive routing question and walkthrough fire. After it returns, re-render this menu with refreshed counts so the user can pick a next-stage action.
- **Create Issue** — Detect the project tracker (`gh` for GitHub, `linear` for Linear) and create the issue from the plan file as described under "Issue Creation" in `references/plan-handoff.md`. After creation, display the issue URL and ask whether to proceed to `/rosey-work` via the platform's blocking question tool.
- **Done for now** — Display a brief confirmation that the plan file is saved and end the turn. Do not start follow-up work without an explicit further user prompt.

If the user types free-form prompts targeting the findings (e.g., "review", "walk through", "deep review"), route as if they picked `Run deeper doc review` — fire the skill rather than looping back to the menu. For other free-text revisions, accept the input and loop back to this menu after applying the revision.

**Completion check:** This skill is not complete until the post-generation menu above has been presented, the user has selected an action, and the inline routing for that selection has been executed. Presenting the menu and stopping at the user's selection is not completion — fire the routed action.

**Non-interactive mode exception:** When `mode:non-interactive` is active, skip the interactive menu and return control to the caller after the plan file is written, confidence check has run, and `rosey-doc-review` has run in headless mode (per `references/plan-handoff.md`).
