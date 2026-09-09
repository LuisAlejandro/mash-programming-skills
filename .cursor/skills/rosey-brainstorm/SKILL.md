---
name: rosey-brainstorm
description: 'Explore requirements and approaches through collaborative dialogue, then write a right-sized requirements document. Use when the user says "let''s brainstorm", "what should we build", or "help me think through X", presents a vague or ambitious feature request, or seems unsure about scope or direction -- even without explicitly asking to brainstorm.'
argument-hint: "[feature idea or problem to explore]"
---

# Rosey Brainstorm

Brainstorming answers **WHAT** to build through collaborative dialogue; `/rosey-plan` then answers **HOW**. This skill does not implement code — it explores, clarifies, and documents decisions for later planning or execution. **The current year is 2026**, for dating artifacts.

**Outcome:** a right-sized result planning can consume without inventing product behavior, scope boundaries, or success criteria — a chat paragraph for Lightweight work, or a requirements document under `rosey/brainstorms/` when a file is earned. In other workflows the artifact might be called a lightweight PRD or feature brief; in Rosey the workflow keeps the name `brainstorm` and the artifact is a **requirements document**.

**Done:** that result is delivered — and, when a file was written, its Phase 3 checks pass — and Phase 4's handoff has been presented.

**IMPORTANT: All file references in generated documents must use repo-relative paths (e.g., `src/models/user.rb`), never absolute paths. Absolute paths break portability across machines, worktrees, and teammates.**

## Rosey Overlay

This skill follows the Rosey-native brainstorm workflow with Rosey handoffs and OpenDesign boundaries:

- Handoff target is `/rosey-plan`, or `/rosey-work` only when the direct-to-work gate passes.
- Do **not** create a separate PRD artifact. The requirements document is the durable product artifact for planning.
- Do **not** create a separate design doc unless the user explicitly asks for one. The requirements document should be right-sized and can include design-relevant decisions when they matter.
- After `rosey-implement-design` completes with visual parity aligned, use this skill for the remaining functionality only: real data sources, business logic, validation, submission, error handling, auth, routing guards, and deferred checklist items. Do not rerun `rosey-implement-design` for functionality work.

## Feature Description

<feature_description> #$ARGUMENTS </feature_description>

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. Use the collaborative dialogue and question flow.
- `mode:non-interactive` — scripted or skill-to-skill execution. Do not ask blocking questions or wait for confirmation.

Strip the interaction mode token before treating the remainder as the feature description. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

When `INTERACTION_MODE=non-interactive`:

- Do not use blocking question tools or prompt for clarification.
- Infer conservatively from the prompt, repo scan, and issue context supplied by the caller.
- Record material assumptions in the requirements document.
- Skip Phase 1.3 dialogue, Phase 2 approach menus, Phase 2.5 confirmation, and Phase 4 handoff menus.
- A requirements document is always written — it is the only channel back to the caller. If one cannot be written safely, stop with a concise blocker.

**If the feature description above is empty:** In interactive mode, ask the user: "What would you like to explore? Please describe the feature, problem, or improvement you're thinking about." In non-interactive mode, stop with a blocker.

Do not proceed until you have a feature description.

## Execution Flow

Phases run in this order. Each names the files it cannot run correctly without: read them when you reach that phase, and never do its work from this table alone.

| Phase | Read first | What only those files carry |
|---|---|---|
| before anything, and for the whole run — non-software route included | `references/phase-0.md` | the Caveman-lite communication rule; the Hindsight memory gate and what "unavailable" means; Phase 0 itself |
| before the first question, and for the whole run — non-software route included | `references/interaction-rules.md` | the Core Principles, and the Interaction Rules: one question per turn, the blocking-question-tool table and the resolve-by-capability rule that overrides it, when a question is genuinely open-ended, and the ask-only-decisions rule |
| 0.0–0.3 output, resume, classify, route, scope | `references/phase-0.md` | markdown output and token parsing; resume; the software / non-software / neither classification; the clear-requirements fast path; scope tiers and the Deep feature-vs-product sub-mode; the Lightweight-ends-in-chat rule; the coherent-work gate; the unfamiliarity tripwire |
| 1 understand the idea | `references/dialogue.md` | context scan with verify-before-claiming; the grounding-scout dispatch and its lazily-created scratch path; the conflict and blindspot gates; rigor-probe firing discipline; the integration check; the six-clause Phase 1.3 exit condition |
| 1.2 pressure test | `references/product-pressure-test.md` | the per-tier gap lenses and the synthesis questions the agent weighs privately |
| whenever a sub-agent is dispatched (1.1, 2.6) | `references/model-tiers.md` | the extraction / generation / ceiling tiers; blocking-dispatch and resolved-path rules; the degradation ladder down to inline |
| when the unfamiliarity tripwire or the mid-dialogue signal fires | `references/blindspot-pass.md` | the territory-scoped gate and its can't-evaluate guard; the offer wording; the 3–7 item decision map and how mapped decisions re-enter dialogue |
| 2–2.6 approaches, synthesis, verification | `references/approaches.md`, plus `references/synthesis-summary.md` before composing the synthesis | approach generation and granularity; the anti-genericness test; the Path A / Path B gate and the scoping synthesis contract; the independent claim verifier |
| 3 write the requirements | `references/plan-write.md`, then `references/brainstorm-sections.md` and `references/markdown-rendering.md` | whether a doc is warranted; write-tight discipline; the section contract; the markdown format |
| 4 handoff | `references/handoff.md` | the option set and its visibility conditions, per-selection dispatch, the dossier pass-through, and the closing summary format |

**Read a reference on phase entry, completely.** A read made before that phase does not satisfy it, and a reference is re-read at its phase even when it is already in context.

**A required reference that cannot be read is a stop.** Never reconstruct one from memory. In interactive mode, report which file failed and why, and stop. In `mode:non-interactive`, return a structured blocker naming the unreadable path instead of stopping silently — an opaque halt is indistinguishable from a hang to an automated caller.
