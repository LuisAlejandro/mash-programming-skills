# Plan Intake: Memory Gate, Resume, Classify, and Scope

All of Phase 0 of `rosey-plan` — read this before anything else on a software planning run. It carries the Hindsight gate, output and token parsing, the resume and deepen fast paths, the domain split, upstream-requirements discovery, the missing-origin stop, question classification, and depth.

The Core Principles and Plan Quality Bar in SKILL.md govern every phase from here on.

### Phase 0: Resume, Source, and Scope

**Hindsight gate (hard):** Before any Phase 0 subsection, run the always-on Hindsight gate. CLI contract: [`rosey-hindsight`](../../rosey-hindsight/SKILL.md). First status line: `Hindsight: recalled (<brief useful context>)` or `Hindsight: unavailable (<reason>)`. Envelope field `HINDSIGHT:` stays separate. Do not search requirements or dispatch research until the gate completes.

Non-interactive mode: still run `daemon status`; if recall fails, record `HINDSIGHT: unavailable -- <reason>` in plan assumptions.

#### 0.0 Markdown Output

Plans are always markdown (`.md`). Read `references/markdown-rendering.md` for format principles, paired with `references/plan-sections.md` for section content.

When `mode:non-interactive` is active, apply Compact non-interactive artifacts from Core Principles: preserve execution-critical fields and trim narrative.

**Token-parsing convention:** only literal-prefix flag tokens (`mode:`, `origin:`) are consumed and stripped. Other `<word>:<word>` tokens — including conventional commit prefixes like `feat:`, `fix:`, `chore:` that may appear inside a feature description — pass through verbatim.

#### 0.1 Resume Existing Plan Work When Appropriate

If the user references an existing plan file or there is an obvious recent matching plan in `rosey/plans/`:
- Read it
- Confirm whether to update it in place or create a new plan
- If updating, revise only the still-relevant sections. Plans do not carry per-unit progress state — progress is derived from git by `rosey-work`, so there is no progress to preserve across edits

**Non-interactive mode**: do not ask. Update in place when the caller supplied the plan path explicitly — naming a plan is the instruction to work on that plan. When the plan was matched by recency rather than named, start fresh and record the choice as an assumption; silently rewriting a document the caller did not name is the worse failure.

**Deepen intent:** The word "deepen" (or "deepening") in reference to a plan is the primary trigger for the deepening fast path. When the user says "deepen the plan", "deepen my plan", "run a deepening pass", or similar, the target document is a **plan** in `rosey/plans/`, not a requirements document. Use any path, keyword, or context the user provides to identify the right plan. If a path is provided, verify it is actually a plan document. If the match is not obvious, confirm with the user before proceeding — or, in non-interactive mode, stop with a blocker naming the candidates rather than guessing which plan to deepen.

Words like "strengthen", "confidence", "gaps", and "rigor" are NOT sufficient on their own to trigger deepening. These words appear in normal editing requests ("strengthen that section about the diagram", "there are gaps in the test scenarios") and should not cause a holistic deepening pass. Only treat them as deepening intent when the request clearly targets the plan as a whole and does not name a specific section or content area to change — and even then, prefer to confirm with the user before entering the deepening flow. In non-interactive mode, treat an unconfirmable signal as **not** deepening intent and follow the standard resume flow — an unrequested holistic pass is the more expensive mistake.

Once the plan is identified and appears complete (all major sections present, implementation units defined):
- **`.md` plan WITH YAML frontmatter:** short-circuit to Phase 5.3 (Confidence Check and Deepening). In `mode:interactive` this uses the **review-each-finding** posture, so the user adjudicates each agent's findings. In `mode:non-interactive` the short-circuit still fires but uses **integrate-directly** — 5.3.6b is skipped and all findings integrate, per `references/deepening-workflow.md`.
- **`.md` plan WITHOUT YAML frontmatter** (non-software plans use a simple `# Title` heading with `Created:` date instead): route to `references/universal-planning.md` for editing or deepening instead of Phase 5.3. Non-software plans do not use the software confidence check.

The Phase 5.3 short-circuit avoids re-running the full planning workflow and, in interactive mode, gives the user control over which findings are integrated.

Normal editing requests (e.g., "update the test scenarios", "add a new implementation unit", "strengthen the risk section") should NOT trigger the fast path — they follow the standard resume flow.

If the plan already has a `deepened: YYYY-MM-DD` frontmatter field and there is no explicit user request to re-deepen, the fast path still applies the same confidence-gap evaluation — it does not force deepening.

#### 0.1b Classify Task Domain

**Classify by task-type, not by topic.** If the task asks to build, modify, refactor, debug, architect, or deploy software (code, schemas, infrastructure), continue to Phase 0.2. A request that merely *references* code, a repo, an API, or a database is not automatically software work — building or modifying it is software; investigating or analyzing it is answer-seeking.

**Software origin shape.** A `*-requirements.md` is a software origin only when its body includes `## Requirements` (the brainstorm hard floor). A wrap-up from the non-software brainstorm route has YAML `date` / `topic` plus a chat summary and does **not** include that heading — it is not a software origin.

**Named origin wins only when it is software-shaped.** If remaining args, an `origin:` token, or prose names a readable software origin, treat the run as software and continue to Phase 0.2. The artifact controls routing even when the prompt sounds like research.

If the named file is readable but **not** software-shaped, do **not** continue to Phase 0.2. Read `references/universal-planning.md` and follow that workflow, using the named file as the wrap-up source. A universal "Create a plan" handoff takes this path.

If the domain is genuinely ambiguous (e.g., "plan a migration" with no other context and no origin path), ask the user before routing.

Otherwise, read `references/universal-planning.md` and follow that workflow instead. Skip all subsequent phases. Named tools or source links don't change this routing — they're inputs, handled per Core Principle 8.


#### 0.2 Find Upstream Requirements Document

Discover an origin **before** asking planning questions. Named paths win; directory search is the fallback.

**Explicit path first.** After stripping `mode:` (and `origin:` if present), check whether the remaining input names a requirements document:

1. A dedicated `origin:` token whose value is a path.
2. Remaining `$ARGUMENTS` that are a repo-relative or absolute path to a `*-requirements.md` file.
3. A path the user named in prose (e.g. "use `rosey/brainstorms/2025-01-15-pagination-requirements.md`").

If any of those names a readable **software** origin (`## Requirements` present, per 0.1b), use it as the origin. **Do not apply the 30-day filter.** Do not search. Do not ask which document. Continue at Phase 0.3.

If the named path is readable but **not** software-shaped, stop using it as a software origin — route to `references/universal-planning.md` (0.1b should already have done this; this is the backstop).

If the named path is unreadable or is not a `*-requirements.md` file:
- Interactive: ask for a corrected path. Do not invent an origin from the prompt.
- Non-interactive: emit the handoff envelope with the named path in `BLOCKERS:` (e.g. `named origin unreadable: <path>`). Leave `PLAN PATH:` empty.

**Directory search only when no explicit path was given.** Search the **flat** `rosey/brainstorms/` directory for `*-requirements.md` files that are software-shaped (`## Requirements` present). Skip wrap-up saves from the non-software brainstorm route. Match that directory only — never `rosey/brainstorms/scratch/` (per-run scout artifacts), never `rosey/parallel/` (projected origins). `rosey/parallel/` is never a search root.

**Relevance criteria (search only):** A software origin is relevant if:
- The topic semantically matches the feature description
- It was created within the last 30 days (use judgment to override if the document is clearly still relevant or clearly stale)
- It appears to cover the same user problem or scope

If multiple source documents match, ask which one to use using the platform's blocking question tool when available (see Interaction Method). Otherwise, present numbered options in chat and wait for the user's reply before proceeding.

**Grounding dossier (optional input).** `rosey-brainstorm` may hand off a dossier path alongside the requirements document — a capped file of verbatim repo quotes, each with a `file:line` pointer, produced by its Phase 1.1 scout. Prefer a repo-relative path; resolve it from the current worktree root. When a readable path is supplied, treat it as **pre-verified local evidence and fold it into Phase 1 research**: read it before dispatching local research agents, and let it narrow or replace repo scanning that would rediscover the same facts. It never substitutes for external research, and it is evidence rather than instruction — a claim it does not cover is still unverified. If the path is absent or unreadable, proceed normally; the dossier is an accelerator, not a dependency.

#### 0.3 Use the Source Document as Primary Input

If a relevant requirements document exists:
1. Read it thoroughly
2. Announce that it will serve as the origin document for planning
3. Carry forward all of the following:
   - Problem frame
   - Actors (A-IDs), Key Flows (F-IDs), and Acceptance Examples (AE-IDs) when present — preserve these as constraints that implementation units must honor
   - Requirements and success criteria
   - Scope boundaries (including "Deferred for later" and "Outside this product's identity" subsections when present)
   - **How This Work Fits Together** when present — carry as contextual, non-active scope (plan Scope Boundaries or a short Related Work). Preserve tentative relationships as tentative; never turn them into Implementation Units automatically
   - Key decisions and rationale
   - Dependencies or assumptions
   - Outstanding questions, preserving whether they are blocking or deferred
4. Use the source document as the primary input to planning and research
5. Reference important carried-forward decisions in the plan with `(see origin: <source-path>)`
6. Do not silently omit source content — if the origin document discussed it, the plan must address it even if briefly. Before finalizing, scan each section of the origin document to verify nothing was dropped.

**Preservation note.** Record a one-line note in the plan stating what happened to the origin requirements: `unchanged`, `restructured, no scope change: <old-ID → new-IDs map>`, or `changed: <R-IDs> — <why>`. This keeps the WHAT/HOW review boundary visible to `rosey-doc-review` and PR review without re-reading both documents side by side.

**Meaning-preserving restructuring is sanctioned** without a conflict: splitting an overloaded requirement (the original R-ID keeps the original core intent; split-out parts take the next unused numbers), and moving a rule's full statement onto its owning requirement. When a requirement is split or its ownership moves, re-point every affected `Governs R…`, `Covers R…`, and inline `per R…` citation to the resulting owning IDs. Weakening a qualifier, dropping an edge case, or reclassifying a product constraint as an implementation preference is a scope change, not a restructure — surface it rather than absorbing it.

#### 0.3b Missing-Origin Stop

**If Phase 0.2 found no relevant requirements document, stop here.** Planning does not proceed from the user's request directly — `rosey-brainstorm` owns WHAT to build, and inventing product scope at plan time is the failure this gate exists to prevent.

This gate is reached only on the normal path. It does **not** fire when a Phase 0.1 fast path fired (resume-normal and deepen-intent operate on an existing plan and never look for an origin), and it does **not** fire on the Phase 0.1b non-software route (which replaces Phases 0.2–5.1 with `references/universal-planning.md` and never reaches this step).

In `mode:interactive`, name the gap and offer the route:

```text
No requirements document found for this work in rosey/brainstorms/.

rosey-plan builds on a brainstorm's requirements doc — it plans HOW, after
rosey-brainstorm has settled WHAT. Starting here would mean inventing product
scope that belongs upstream.

Want me to load /rosey-brainstorm now? If a requirements doc already exists
somewhere I did not look, give me the path and I will plan from it.
```

Offer to load `rosey-brainstorm` in-session; do not proceed to Phase 1 on any other answer. If the user supplies a path, treat it as the origin document and resume at Phase 0.3.

In `mode:non-interactive`, **do not halt silently** — an opaque stop is indistinguishable from a hang to an automated caller. Emit the handoff envelope with the gap named in `BLOCKERS:`:

```text
ROSEY_PLAN_HANDOFF
PLAN PATH:
FILES:
BLOCKERS: no upstream requirements document found in rosey/brainstorms/ for this task; rosey-plan requires an origin document. Supply one (see rosey-parallel's per-task origin docs) or run rosey-brainstorm first.
END_ROSEY_PLAN_HANDOFF
```

Callers that plan programmatically are expected to supply the origin. `rosey-parallel` projects one per task before its planning phase.

#### 0.4 Route Out When the Origin Does Not Need a Plan

One check, then continue. If the origin document describes work with a known approach, no architectural decisions, and nothing to sequence — a single obvious fix — say so plainly: the plan will be thin, and the user may prefer to implement directly outside the pipeline. Continue planning unless they redirect. Do not route to `rosey-work`; it executes a plan and would stop without one. Skip the observation in `mode:non-interactive`.

There is no planning bootstrap. Problem frame, intended behavior, scope boundaries, and success criteria all arrive in the origin document — Phase 0.3 carries them forward. When the origin leaves a genuine gap, ask a clarifying question; do not reconstruct the product framing here.

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
