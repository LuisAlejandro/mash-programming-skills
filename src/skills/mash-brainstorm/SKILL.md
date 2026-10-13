---
name: mash-brainstorm
description: 'Explore a single feature or change through collaborative dialogue, then write a right-sized requirements document. Use when the user says "let''s brainstorm" or "help me think through X", presents a vague feature request, or seems unsure about scope or direction -- even without explicitly asking to brainstorm. For an epic spanning several separately-deliverable areas, use mash-epic-frame instead.'
argument-hint: "[feature idea or problem to explore]"
---

# Mash Programming Skills Brainstorm

Brainstorming answers **WHAT** to build through collaborative dialogue; `mash-plan` then answers **HOW**. This skill does not implement code — it explores, clarifies, and documents decisions for later planning or execution. Use the current calendar year when dating artifacts.

**Outcome:** a requirements document under `.mash/brainstorms/` that planning can consume without inventing product behavior, scope boundaries, or success criteria. Every **software** run writes one — the document is the pipeline's contract with `mash-plan`, which requires it. In other workflows the artifact might be called a lightweight PRD or feature brief; in Mash Programming Skills the workflow keeps the name `brainstorm` and the artifact is a **requirements document**.

| Route | Artifact |
| --- | --- |
| Software | Always write `*-requirements.md` |
| Non-software | Stop. This skill covers software work. |
| Neither | Not a brainstorm run; answer and stop |

**Done:** Interactive: the requirements document is written, its Phase 3 checks pass, the Phase 4 menu is presented, and the selected action is executed. Non-interactive: the document is written and `MASH_BRAINSTORM_HANDOFF` is emitted, with blockers and assumptions.

**Scope floor.** This skill is for work big enough to need a durable product artifact. Small, well-understood changes belong in direct implementation, not here — there is no cheap chat-only path through this skill, and no shortcut from here to execution.

**IMPORTANT: All file references in generated documents must use repo-relative paths (e.g., `src/models/user.rb`), never absolute paths. Absolute paths break portability across machines, worktrees, and teammates.**

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

## Mash Programming Skills gates

Always-on rules; full procedures live in those guidelines — do not duplicate them here.

1. **Hindsight** before research — always-on Hindsight guideline; CLI in [`mash-hindsight`](../mash-hindsight/SKILL.md)
2. **Ponytail ladder** before adding abstractions or dependencies
3. **Docker-via-Make** for app commands and tooling

See also the always-on Mash Programming Skills workflow-gates guideline.

## Mash Programming Skills Overlay

This skill follows the Mash Programming Skills-native brainstorm workflow with Mash Programming Skills handoffs:

- Handoff target is `mash-plan`. There is no direct-to-work route: planning is not skippable.
- Do **not** create a separate PRD artifact. The requirements document is the durable product artifact for planning.
- Do **not** create a separate design doc unless the user explicitly asks for one. The requirements document should be right-sized and can include design-relevant decisions when they matter.
- When a design-to-code pipeline has already shipped the visual shell with parity aligned, use this skill for the remaining functionality only: real data sources, business logic, validation, submission, error handling, auth, routing guards, and deferred checklist items. Do not rerun design implementation for functionality work.

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
- Skip Phase 1.3 dialogue, Phase 2 approach menus, the Phase 3 file confirmation, and Phase 4 handoff menus.
- On the **software** route, a requirements document is always written — it is the only channel back to the caller. If one cannot be written safely, stop with a concise blocker. Non-software non-interactive runs return the chat summary and stop; they are not a software pipeline handoff.

**If the feature description above is empty:** In interactive mode, ask the user: "What would you like to explore? Please describe the feature, problem, or improvement you're thinking about." In non-interactive mode, stop with a blocker.

Do not proceed until you have a feature description.

## Execution Flow

Phases run in this order. Each names the files it cannot run correctly without: read them when you reach that phase, and never do its work from this table alone.

| Phase | Read first | What only those files carry |
|---|---|---|
| before anything, and for the whole run | `references/phase-0.md` | the Hindsight memory gate and what "unavailable" means; Phase 0 itself |
| before the first question, and for the whole run | `references/interaction-rules.md` | the Core Principles, and the Interaction Rules: one question per turn, the blocking-question-tool table and the resolve-by-capability rule that overrides it, when a question is genuinely open-ended, and the ask-only-decisions rule |
| 0.0–0.3 output, resume, classify, route, scope | `references/phase-0.md` | markdown output and token parsing; resume; the software / non-software / neither classification and the non-software stop; the clear-requirements fast path; the scope floor; the coherent-work gate; the unfamiliarity tripwire |
| 1 understand the idea | `references/dialogue.md` | context scan with verify-before-claiming; the grounding-scout dispatch and its lazily-created scratch path; the conflict and blindspot gates; rigor-probe firing discipline; the integration check; the six-clause Phase 1.3 exit condition |
| 1.2 pressure test | `references/product-pressure-test.md` | the gap lenses, the product-shape questions, and the questions the agent weighs privately |
| whenever a sub-agent is dispatched (1.1, 2.6) | `~/.config/mash/references/model-tiers.md` | the extraction / generation / ceiling tiers; blocking-dispatch and resolved-path rules; the degradation ladder down to inline |
| when the unfamiliarity tripwire or the mid-dialogue signal fires | `references/blindspot-pass.md` | the territory-scoped gate and its can't-evaluate guard; the offer wording; the 3–7 item decision map and how mapped decisions re-enter dialogue |
| 2–2.6 approaches and verification | `references/approaches.md` | approach generation and granularity; the anti-genericness test; the independent claim verifier |
| 3 write the requirements | `references/plan-write.md`, then `references/brainstorm-sections.md` and `references/markdown-rendering.md` | write-tight discipline; the section contract; the markdown format; the one-question confirmation of the written file |
| 4 handoff | `references/handoff.md` | the option set and its visibility conditions, per-selection dispatch, the dossier pass-through, the non-interactive `MASH_BRAINSTORM_HANDOFF` envelope, and the closing summary format |

**Read a reference on phase entry, completely.** A read made before that phase does not satisfy it, and a reference is re-read at its phase even when it is already in context.

**A required reference that cannot be read is a stop.** Never reconstruct one from memory. In interactive mode, report which file failed and why, and stop. In `mode:non-interactive`, return a structured blocker naming the unreadable path instead of stopping silently — an opaque halt is indistinguishable from a hang to an automated caller.
