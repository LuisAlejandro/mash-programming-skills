# Phase 0: Communication, Memory Gate, Resume, Classify, and Scope

Read this before anything else on every run, including the non-software route — it carries the communication rule and the memory gate as well as Phase 0 itself.

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, or when the user asks for normal or long-form wording.

## Memory gate (required check)

Before Phase 1.2 on Standard/Deep scope (before Phase 3 write on Lightweight with material scope):

1. Read [`rosey-hindsight`](../../rosey-hindsight/SKILL.md) and run `hindsight-embed daemon status` + `hindsight-embed memory recall` (prepend `~/.local/bin` to PATH; see skill) OR document `Hindsight: unavailable — <reason>`.
2. Do not write the requirements doc until step 1 completes or is explicitly marked unavailable.

"Unavailable" means CLI failed — not "I skipped it."

## Phase 0: Resume, Assess, and Route

### 0.0 Markdown Output

Requirements documents are always markdown (`.md`). Read `references/markdown-rendering.md` for format principles, paired with `references/brainstorm-sections.md` for section content.

When `mode:non-interactive` is active, apply Compact non-interactive artifacts from Output Guidance in `references/interaction-rules.md`: preserve IDs and decision-bearing content, trim narrative.

**Token-parsing convention:** only literal-prefix flag tokens (`mode:`, `delegate:` where applicable) are consumed and stripped. Other `<word>:<word>` tokens — including conventional commit prefixes like `feat:`, `fix:`, `chore:` that may appear inside a feature description — pass through verbatim.

### 0.1 Resume Existing Work When Appropriate

If the user references an existing brainstorm topic or document, or there is an obvious recent matching `*-requirements.md` file in `rosey/brainstorms/`:

- Read the document
- Confirm with the user before resuming: "Found an existing requirements doc for [topic]. Should I continue from this, or start fresh?"
- If resuming, summarize the current state briefly, continue from its existing decisions and outstanding questions, and update the existing document instead of creating a duplicate

In non-interactive mode, do not ask. Resume the matching document when the topic match is unambiguous; otherwise start fresh and record the choice as an assumption.

### 0.1b Classify Task Domain

Before proceeding to Phase 0.2, classify whether this is a software task. The key question is: **does the task involve building, modifying, or architecting software?** -- not whether the task *mentions* software topics.

**Software** (continue to Phase 0.2) -- the task references code, repositories, APIs, databases, or asks to build/modify/debug/deploy software.

**Non-software brainstorming** (route to universal brainstorming) -- BOTH conditions must be true:

- None of the software signals above are present
- The task describes something the user wants to explore, decide, or think through in a non-software domain

**Neither** (respond directly, skip all brainstorming phases) -- the input is a quick-help request, error message, factual question, or single-step task that doesn't need a brainstorm.

**If non-software brainstorming is detected:** Read `references/universal-brainstorming.md` and use those facilitation principles. Skip Phases 0.2–4 below — the **Core Principles and Interaction Rules in `references/interaction-rules.md` still apply unchanged**, including one-question-per-turn, asking only decisions the environment cannot settle, and the default to the platform's blocking question tool.

### 0.2 Assess Whether Brainstorming Is Needed

**Clear requirements indicators:**

- Specific acceptance criteria provided
- Referenced existing patterns to follow
- Described exact expected behavior
- Constrained, well-defined scope

**If requirements are already clear:**
Keep the interaction brief. Confirm understanding and present concise next-step options rather than forcing a long brainstorm. Whether a file is written is decided by the Lightweight rule in 0.3 below. Skip Phase 1.1 and 1.2 entirely — still classify tier in Phase 0.3, then go straight to Phase 1.3 or Phase 2.5 and follow `references/synthesis-summary.md`'s Path A / Path B gate exactly. Do not assume the synthesis is announce-only: a richly pre-loaded prompt classifies as Standard or Deep, which routes to Path B (full scoping synthesis + confirmation), not Path A.

### 0.3 Assess Scope

Use the feature description plus a light repo scan to classify the work:

- **Lightweight** - small, well-bounded, low ambiguity
- **Standard** - normal feature or bounded refactor with some decisions to make
- **Deep** - cross-cutting, strategic, or highly ambiguous

If the scope is unclear, ask one targeted question to disambiguate and then proceed; when it stays uncertain, take the heavier tier.

In non-interactive mode, do not ask. Classify conservatively from the supplied feature description and record the classification as an assumption when it materially affects the document.

**Lightweight ends in chat.** The result is a paragraph in the Phase 2.5 synthesis: what is being built, the one or two decisions made, and where they go next. No file is written, and the Phase 1.1 grounding scout, Phase 2's approach generation, and Phase 2.6's claim verifier do not run. A file is earned only by a decision a downstream consumer needs in IDed form, or by the user asking for one; then Phase 3 writes it from the dialogue's decisions.

This skip is **interactive-only**. In `mode:non-interactive` a file is always written — chat is not a channel the caller can read — so the scout and verifier run per their own gates and Phase 3 always produces a document. This mirrors the rule in `references/plan-write.md`.

**Deep sub-mode: feature vs product.** For Deep scope, also classify whether the brainstorm must establish product shape or inherit it:

- **Deep — feature** (default): existing product shape anchors decisions. Primary actors, core outcome, positioning, and primary flows are already established in the product or repo. The brainstorm extends or refines within that shape.
- **Deep — product**: the brainstorm must establish product shape rather than inherit it. Primary actors, core outcome, positioning against adjacent products, or primary end-to-end flows are materially unresolved. Existing code lowers the odds of product-tier but does not by itself rule it out — a half-built tool with ambiguous shape is still product-tier.

Product-tier triggers additional Phase 1.2 questions and additional sections in the requirements document. Feature-tier uses the current Deep behavior unchanged.

**Coherent-work gate.** Before entering Phase 1, check whether the request contains more than one independently plannable product outcome: each has its own user value or acceptance boundary and could be delivered without completing the others. Shared actors, one end-to-end outcome, or coverage across named devices, providers, or data sources do not by themselves justify a split — that is Core Principle 7.

When the gate finds multiple coherent areas:

1. Propose a plain-language breakdown and state only relationships supported now: which areas depend on or enable others, share a product rule, or can proceed independently.
2. Ask which one area this brainstorm should own. If the user already chose one, carry it forward instead of asking again.
3. Treat that area as the sole source of Requirements, Flows, Acceptance Examples, and Key Decisions. Other areas remain contextual candidates, not scope.
4. Preserve the current broader understanding for a **How This Work Fits Together** section in the requirements document. Mark tentative relationships as tentative; later brainstorms may revise, split, merge, or discard them.
5. Carry the boundary into the Summary: name the current area and state that the surrounding areas are not active scope.

Keep the work together when the outcomes cannot be independently useful or validated, or when separating them would force this document to invent the missing shared behavior. This gate narrows the active artifact; it does not create a parent plan or a roadmap, and it never routes to another skill.

In non-interactive mode, do not ask. Choose the area the feature description weights most heavily, record the narrowing as an explicit assumption, and note the deferred areas under Scope Boundaries.

**Unfamiliarity tripwire.** If the user signals they lack working knowledge of the domain or the territory the topic touches — "I know nothing about X", "never touched the auth modules", "I don't know what's possible / what I should be asking" — read `references/blindspot-pass.md` now. Loading here is readiness only; that reference owns when the offer fires (territory-scoped, before the first substantive question into the flagged territory), the map's shape, and how mapped decisions re-enter the dialogue. Skip the tripwire entirely in non-interactive mode — with no user to teach, flagged territory is handled as a declined offer per that reference.
