---
name: mash-plan
description: "Create structured plans for software work. Use when the user says 'plan this', 'create a plan', 'how should we build', 'break this down', or when a brainstorm doc is ready for planning. 'Deepen the plan' runs mash-doc-review on that plan. For exploratory requests, prefer mash-brainstorm first."
argument-hint: "[optional: feature description or requirements doc path]"
---

# Mash Programming Skills Plan

`mash-brainstorm` defines **WHAT** to build. `mash-plan` defines **HOW** to build it. `mash-work` executes the plan. Use the current calendar year when dating plans and searching recent documentation.

**An upstream requirements document is required.** The pipeline is `mash-brainstorm` → `mash-plan` → `mash-work`, and planning starts from the brainstorm's requirements document. When Phase 0.2 finds no relevant document, this skill stops at Phase 0.3b and routes to `mash-brainstorm` rather than inventing product scope from the prompt — see the missing-origin stop in `references/intake.md`.

**Outcome:** a durable plan under `.mash/plans/` that an implementer can act on without re-deciding what was already settled.

**Done:** that result is delivered **and** its handoff has fired — the Phase 5.4 menu presented and the selected action actually executed; in `mode:non-interactive`, the handoff envelope emitted. Writing the file is an intermediate milestone, not completion. Document review runs only when the user selects it from the handoff menu, or when the user asked to deepen the plan. Rendering the menu, receiving a selection, or announcing a route is not completion either — execute the selected action.

**Once an origin document is in hand, always plan.** Never classify such an invocation as "not a planning task" and abandon the workflow. If the origin leaves something unclear, ask clarifying questions — but stay in the workflow. Sanctioned stops: missing origin (0.3b), unreadable required reference, non-software stop (0.1b), or an ambiguous review target in non-interactive mode.

**Research, decide, and write the plan — never implement.** No production code, no test runs, no learning from execution-time results. Directional pseudo-code may communicate design; changing code to see what happens belongs in `mash-work`.

**IMPORTANT:** Use repo-relative paths everywhere in the plan (e.g., `src/models/user.rb`), never absolute paths. This applies to unit file lists, pattern references, origin links, and prose.

## Mash Programming Skills gates

Always-on rules; full procedures live in those guidelines — do not duplicate them here.

1. **Hindsight** before research — always-on Hindsight guideline; CLI in [`mash-hindsight`](../mash-hindsight/SKILL.md)
2. **Ponytail ladder** before adding abstractions or dependencies
3. **Docker-via-Make** for app commands and tooling

See also the always-on Mash Programming Skills workflow-gates guideline.

## Mash Programming Skills Overlay

This skill follows the Mash Programming Skills-native plan workflow, with Mash Programming Skills Sentrux integration:

- Input is a requirements document from `mash-brainstorm`. There is no separate PRD/product step.
- Plans use Implementation Units (`U1`, `U2`, ...) rather than day-by-day task groups.
- Read [`mash-sentrux`](../mash-sentrux/SKILL.md) before using Sentrux. Use MCP tools only; never run `sentrux scan` in the terminal.
- Produce a Sentrux topology artifact beside the plan when Sentrux is available. If unavailable, still write the plan and record `status: "unavailable"` in the topology artifact.

## Communication while using this skill

Caveman level, drop conditions, and what stays uncompressed are in the caveman rule.

## Interaction Method

Ask one question at a time. Prefer a concise single-select choice when natural options exist. Use the harness's blocking question tool when one exists:

| Harness | Tool | Note |
| --- | --- | --- |
| Cursor | `AskQuestion` | |
| OpenCode | `question` | |
| Claude Code | `AskUserQuestion` | Call `ToolSearch` with `select:AskUserQuestion` first if its schema is not loaded |
| Codex | `request_user_input` | Unavailable in edit modes — fall back there |
| Pi | `ask_user` | Requires the `pi-ask-user` extension |
| Gemini | `ask_user` | |
| Any other harness | match by capability | Use whatever user-input tool is in the current tool list; do not call another harness's tool name |

**Resolve by capability, not by this table.** The table is a convenience for the common harnesses, not the authority — harnesses rename tools and this list will drift. Presence in the current tool list is proof the tool exists; never call a user-facing question tool just to discover whether it exists. If a matching tool is listed but unloaded, use the host's tool-discovery primitive to load it. Fall back to numbered options in chat only when no blocking tool is in the tool list or a real call errors — not because a schema load is required. **Never silently skip the question.**

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token, and optionally one `origin:` token:

- `mode:interactive` — default for direct chat invocation. The skill may ask blocking questions and present post-generation options.
- `mode:non-interactive` — scripted or skill-to-skill execution. The skill must not ask blocking questions or wait for confirmations.

Strip `mode:` and `origin:` tokens before treating the remainder as the feature description or path. If no interaction mode token is present, set `INTERACTION_MODE=interactive`. If multiple interaction mode tokens appear, stop and report the conflict.

In non-interactive mode, make conservative assumptions from the prompt, origin document, repo research, and Sentrux context. Route unvalidated bets to `## Assumptions`, skip post-generation menus, and report anything that needs human judgment through the handoff envelope's `BLOCKERS:` field rather than stopping silently.

## Feature Description

<feature_description> #$ARGUMENTS </feature_description>

**If the feature description above is empty:** In interactive mode, ask the user: "What would you like to plan? Describe the task, goal, or project you have in mind." Then wait for their response before continuing. In `mode:non-interactive`, do not wait — emit:

```text
MASH_PLAN_HANDOFF
PLAN PATH:
FILES:
BLOCKERS: empty input; supply a requirements document path or feature description
END_MASH_PLAN_HANDOFF
```

If the input is a path to a `*-requirements.md` file (or an `origin:` token names one), Phase 0.1b classifies it: a software origin (`## Requirements` present) continues to Phase 0.2, which uses that path; a wrap-up without that heading is a non-software stop. Do not ask which document first.

If the input is present but is not a path and is unclear or underspecified, ask one or two clarifying questions to identify which requirements document the user means. Phase 0.2 then searches for it, and Phase 0.3b stops the run when none is found.

## Core Principles

1. **Use the origin as the source of truth** - Use the origin requirements document as the source of truth. Do not reinvent behavior, scope, or success criteria. If no origin exists, stop at Phase 0.3b.
2. **Decisions, not code** - Capture approach, boundaries, files, dependencies, risks, and test scenarios. Do not pre-write implementation code or shell choreography. Pseudo-code is fine only as directional design guidance.
3. **Research before structuring** - Explore the codebase, institutional learnings, and external guidance when warranted before finalizing the plan.
4. **Right-size the artifact** - Include a section when it has something to say. The hard floor stays on every plan.
5. **Separate planning from execution discovery** - Resolve planning-time questions here. Explicitly defer execution-time unknowns to implementation.
6. **Keep the plan portable** - The plan should work as a living document, review artifact, or issue body without embedding tool-specific executor instructions.
7. **Carry execution posture lightly when it matters** - Note test-first, characterization-first, or smoke-first posture when clearly implied. Do not turn it into execution choreography.
8. **Honor user-named resources** - Treat named CLIs, MCP servers, URLs, files, docs, or artifacts as authoritative. Discover them before substituting. If unavailable, say so.
9. **Compact non-interactive artifacts** - In `mode:non-interactive`, preserve requirements traceability, Implementation Units, files, test scenarios, verification, risks, and Sentrux notes, but trim narrative setup and duplicate rationale. Interactive plans stay human-readable.

## Plan Quality Bar

Every plan should contain:
- A clear problem frame and scope boundary
- Concrete requirements traceability back to the request or origin document
- Repo-relative file paths for the work being proposed (never absolute paths)
- Explicit test file paths for feature-bearing implementation units when a configured test runner exists; otherwise `Test expectation: none -- no test runner configured in this repo` plus replacement verification
- Decisions with rationale, not just tasks
- Existing patterns or code references to follow
- Enumerated test scenarios for each feature-bearing unit, specific enough that an implementer knows exactly what to test without inventing coverage themselves
- Clear dependencies and sequencing

A plan is ready when an implementer can start confidently without needing the plan to write the code for them.

## Output Contract

Every run that reaches Phase 1 writes a durable plan under `.mash/plans/`. There is no chat-only output tier: a run either has an origin requirements document and produces a plan, or it stops at the missing-origin gate in Phase 0.3b. Small work without a plan is **direct implementation**, not `mash-work`.

## Workflow

Phases run in order unless an owner routes out or short-circuits.

**Read a reference on phase entry, completely.** A read made before that phase does not satisfy it, and a terminal owner is re-read at its step even when already in context.

**A required reference that cannot be read is a stop.** Never reconstruct one from memory. In interactive mode, report which file failed and why, and stop. In `mode:non-interactive`, emit the handoff envelope with the unreadable path named in `BLOCKERS:` instead of stopping silently — an opaque halt is indistinguishable from a hang to an automated caller.

| Phase | Read first | What only those files carry |
|---|---|---|
| 0 — memory gate, resume, classify, source, scope | `references/intake.md` | the Hindsight gate and what "unavailable" means; markdown output and token parsing; resume; the review-intent handoff to mash-doc-review; the non-software stop; upstream requirements discovery, the missing-origin stop, and the dossier input; blocking-question classification |
| 1 — gather context | `references/research.md` | when to read files inline and when to dispatch research agents; execution-direction signals; the external-research decision and its three stages; consolidation; flow analysis |
| 2–4 — resolve questions, structure, write | `references/structure.md` | planning-question classification; title and file naming; the Sentrux topology baseline; Implementation Units and stable U-IDs; high-level technical design; optional sections; planning rules |
| 4.2 — compose | `references/plan-sections.md`, then `references/markdown-rendering.md` | what the plan contains (hard floor, include-when-material catalog, ID rules); how markdown presents it |
| 5.1–5.2 — review and write | `references/final-review.md` | the pre-write checklist; write-path mechanics; the one-question confirmation of the written file |
| after the file is confirmed | `references/plan-handoff.md` | the ponytail sanity-check; final checks; the user-selected document-review option; menu rendering and per-selection routing; issue creation; the non-interactive handoff envelope |

**After the plan file is written, read `references/plan-handoff.md`.** Interactive runs read it after the user answers the file confirmation. Ponytail checks, final checks, and the Phase 5.4 menu remain part of this skill. Done means the selected Phase 5.4 action executed in interactive mode or the handoff envelope emitted in non-interactive mode. Document review is never automatic on a planning run: interactive runs offer it as a menu option, "deepen the plan" invokes it directly, and non-interactive runs skip it. Without that reference the menu renders and the run stops without firing the routed action. If the selection arrives after a user turn, reload that reference before acting.

**Phase 5.4 routing (concise; details in `references/plan-handoff.md`):**
- **Start `mash-work`** — invoke `mash-work` with the plan path now. Do not only tell the user to type the command.
- **Agent review of plan with `mash-doc-review`** — invoke `mash-doc-review` on the plan path without `mode:headless`, then return to the Phase 5.4 menu.
- **Create Issue** — follow the Issue Creation section in `references/plan-handoff.md`.
- **Done for now** — confirm the plan file is saved and stop.
