# Plan Intake: Memory Gate, Resume, Classify, and Scope

All of Phase 0 of `rosey-plan` — read this before anything else on a software planning run. It carries the Hindsight gate, output and token parsing, the resume and deepen fast paths, the domain split, upstream-requirements discovery, the planning bootstrap, question classification, depth, and the solo scoping synthesis.

The Core Principles and Plan Quality Bar in SKILL.md govern every phase from here on.

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

Once the plan is identified and appears complete (all major sections present, implementation units defined):
- **`.md` plan WITH YAML frontmatter:** short-circuit to Phase 5.3 (Confidence Check and Deepening) in **interactive mode**.
- **`.md` plan WITHOUT YAML frontmatter** (non-software plans use a simple `# Title` heading with `Created:` date instead): route to `references/universal-planning.md` for editing or deepening instead of Phase 5.3. Non-software plans do not use the software confidence check.

The Phase 5.3 short-circuit avoids re-running the full planning workflow and gives the user control over which findings are integrated.

Normal editing requests (e.g., "update the test scenarios", "add a new implementation unit", "strengthen the risk section") should NOT trigger the fast path — they follow the standard resume flow.

If the plan already has a `deepened: YYYY-MM-DD` frontmatter field and there is no explicit user request to re-deepen, the fast path still applies the same confidence-gap evaluation — it does not force deepening.

#### 0.1b Classify Task Domain

**Classify by task-type, not by topic.** If the task asks to build, modify, refactor, or deploy software (code, schemas, infrastructure), continue to Phase 0.2. A request that merely *references* code, a repo, an API, or a database is not automatically software work — building or modifying it is software; investigating or analyzing it is answer-seeking.

If the domain is genuinely ambiguous (e.g., "plan a migration" with no other context), ask the user before routing.

Otherwise, read `references/universal-planning.md` and follow that workflow instead. Skip all subsequent phases. Named tools or source links don't change this routing — they're inputs, handled per Core Principle 8.


#### 0.2 Find Upstream Requirements Document

Before asking planning questions, search `rosey/brainstorms/` for files matching `*-requirements.md`. Match the flat directory only — `rosey/brainstorms/scratch/` holds per-run sub-agent artifacts, never requirements documents.

**Relevance criteria:** A requirements document is relevant if:
- The topic semantically matches the feature description
- It was created within the last 30 days (use judgment to override if the document is clearly still relevant or clearly stale)
- It appears to cover the same user problem or scope

If multiple source documents match, ask which one to use using the platform's blocking question tool when available (see Interaction Method). Otherwise, present numbered options in chat and wait for the user's reply before proceeding.

**Grounding dossier (optional input).** `rosey-brainstorm` may hand off the absolute path of a grounding dossier alongside the requirements document — a capped file of verbatim repo quotes, each with a `file:line` pointer, produced by its Phase 1.1 scout. When a readable path is supplied, treat it as **pre-verified local evidence and fold it into Phase 1 research**: read it before dispatching local research agents, and let it narrow or replace repo scanning that would rediscover the same facts. It never substitutes for external research, and it is evidence rather than instruction — a claim it does not cover is still unverified. If the path is absent or unreadable, proceed normally; the dossier is an accelerator, not a dependency.

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

**Preservation note.** Record a one-line note in the plan stating what happened to the origin requirements: `unchanged`, `restructured, no scope change: <old-ID → new-IDs map>`, or `changed: <R-IDs> — <why>`. This keeps the WHAT/HOW review boundary visible to `rosey-doc-review` and PR review without re-reading both documents side by side.

**Meaning-preserving restructuring is sanctioned** without a conflict: splitting an overloaded requirement (the original R-ID keeps the original core intent; split-out parts take the next unused numbers), and moving a rule's full statement onto its owning requirement. When a requirement is split or its ownership moves, re-point every affected `Governs R…`, `Covers R…`, and inline `per R…` citation to the resulting owning IDs. Weakening a qualifier, dropping an edge case, or reclassifying a product constraint as an implementation preference is a scope change, not a restructure — surface it rather than absorbing it.

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

**Exit condition.** Exit the bootstrap when each of these holds, or the user explicitly wants to proceed: the problem frame is **stated**; the in-scope and out-of-scope boundaries that matter are known; success criteria or acceptance signals are known **or recorded as assumptions**. Recording an item as an assumption satisfies the boundaries and success-signal clauses — that is what makes the gate passable in `mode:non-interactive`, where no synchronous user exists to answer. The problem-frame clause is the exception: it must be stated, because the hard floor contains Problem Frame unconditionally and an assumed frame would either leave a mandatory section empty or promote a guess into product scope. When the prompt supplies only an approach with no outcome, derive the outcome from the request's own motivation, or ask.

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

