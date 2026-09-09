---
name: rosey-plan
description: "Create structured plans for multi-step tasks -- software features, research workflows, events, study plans, or any goal that benefits from breakdown. Also deepens existing plans with interactive sub-agent review. Use when the user says 'plan this', 'create a plan', 'how should we build', 'break this down', or when a brainstorm doc is ready for planning. Use 'deepen the plan' or 'deepening pass' for the deepening flow. For exploratory requests, prefer rosey-brainstorm first."
argument-hint: "[optional: feature description, requirements doc path, plan path to deepen, or any task to plan]"
---

# Rosey Plan

`rosey-brainstorm` defines **WHAT** to build. `rosey-plan` defines **HOW** to build it. `rosey-work` executes the plan. A prior brainstorm is useful context but never required — `rosey-plan` works from any input: a requirements doc, a bug report, a feature idea, or a rough description. **The current year is 2026**, for dating plans and searching recent documentation.

**Outcome:** a result an implementer can act on without re-deciding what was already settled — a few sentences in chat for trivial work, or a durable plan under `rosey/plans/` when one is earned.

**Done:** that result is delivered **and** its handoff has fired — for a Durable plan, the Phase 5.4 menu presented and the selected action actually executed; in `mode:non-interactive`, the handoff envelope emitted. Writing the file, running the confidence check, and running or explicitly skipping document review are **intermediate milestones, not completion**. Rendering the menu, receiving a selection, or announcing a route is not completion either — execute the selected action.

**When directly invoked, always plan.** Never classify a direct invocation as "not a planning task" and abandon the workflow. If the input is unclear, ask clarifying questions or use the planning bootstrap (Phase 0.4) — but stay in the workflow.

**Research, decide, and write the plan — never implement.** No production code, no test runs, no learning from execution-time results. Directional pseudo-code may communicate design; changing code to see what happens belongs in `rosey-work`.

**IMPORTANT:** Use repo-relative paths everywhere in the plan (e.g., `src/models/user.rb`), never absolute paths. This applies to unit file lists, pattern references, origin links, and prose.

## Rosey Overlay

This skill follows the Rosey-native plan workflow, with Rosey Sentrux integration:

- Input is a requirements document from `rosey-brainstorm` or a direct planning prompt. There is no separate PRD/product step.
- Plans use Implementation Units (`U1`, `U2`, ...) rather than day-by-day task groups.
- Read [`rosey-sentrux`](../rosey-sentrux/SKILL.md) before using Sentrux. Use MCP tools only; never run `sentrux scan` in the terminal.
- Produce a Sentrux topology artifact beside the plan when Sentrux is available. If unavailable, still write the plan and record `status: "unavailable"` in the topology artifact.

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, or when the user asks for normal or long-form wording.

Caveman lite applies to chat and status prose, not to the plan document, which stays clear enough for humans to review.

## Interaction Method

Ask one question at a time. Prefer a concise single-select choice when natural options exist. Use the harness's blocking question tool when one exists:

| Harness | Tool | Note |
| --- | --- | --- |
| VS Code / GitHub Copilot | `vscode_askQuestions` | Takes a `questions` array |
| Cursor | `AskQuestion` | |
| OpenCode | `question` | |
| Claude Code | `AskUserQuestion` | Call `ToolSearch` with `select:AskUserQuestion` first if its schema is not loaded |
| Codex | `request_user_input` | Unavailable in edit modes — fall back there |
| Pi | `ask_user` | Requires the `pi-ask-user` extension |
| Gemini | `ask_user` | |
| Any other harness | match by capability | Use whatever user-input tool is in the current tool list; do not call another harness's tool name |

**Resolve by capability, not by this table.** The table is a convenience for the common harnesses, not the authority — harnesses rename tools and this list will drift. Presence in the current tool list is proof the tool exists; never call a user-facing question tool just to discover whether it exists. If a matching tool is listed but unloaded, use the host's tool-discovery primitive to load it. Fall back to numbered options in chat only when no blocking tool is in the tool list or a real call errors — not because a schema load is required. **Never silently skip the question.**

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. The skill may ask blocking questions and present post-generation options.
- `mode:non-interactive` — scripted or skill-to-skill execution. The skill must not ask blocking questions or wait for confirmations.

Strip the interaction mode token before treating the remainder as the feature description or path. If no interaction mode token is present, set `INTERACTION_MODE=interactive`. If multiple interaction mode tokens appear, stop and report the conflict.

In non-interactive mode, make conservative assumptions from the prompt, origin document, repo research, and Sentrux context. Route unvalidated bets to `## Assumptions`, skip post-generation menus, and report anything that needs human judgment through the handoff envelope's `BLOCKERS:` field rather than stopping silently.

## Feature Description

<feature_description> #$ARGUMENTS </feature_description>

**If the feature description above is empty, ask the user:** "What would you like to plan? Describe the task, goal, or project you have in mind." Then wait for their response before continuing.

If the input is present but unclear or underspecified, do not abandon — ask one or two clarifying questions, or proceed to Phase 0.4's planning bootstrap to establish enough context. The goal is always to help the user plan, never to exit the workflow.

## Core Principles

1. **Use requirements as the source of truth** - If `rosey-brainstorm` produced a requirements document, planning should build from it rather than re-inventing behavior.
2. **Decisions, not code** - Capture approach, boundaries, files, dependencies, risks, and test scenarios. Do not pre-write implementation code or shell choreography. Pseudo-code is fine only as directional design guidance.
3. **Research before structuring** - Explore the codebase, institutional learnings, and external guidance when warranted before finalizing the plan.
4. **Right-size the artifact** - Small work gets a compact plan, or no plan at all. Large work gets more structure. The philosophy stays the same at every depth.
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
- Explicit test file paths for feature-bearing implementation units
- Decisions with rationale, not just tasks
- Existing patterns or code references to follow
- Enumerated test scenarios for each feature-bearing unit, specific enough that an implementer knows exactly what to test without inventing coverage themselves
- Clear dependencies and sequencing

A plan is ready when an implementer can start confidently without needing the plan to write the code for them.

## Output Contract

Resolve this gate at the start of Phase 0.6, before depth and before the scoping synthesis. Ground it with bounded inline reads of the surfaces the request names; dispatch no subagent. Select one:

- **Direct** — the work can be stated, done, and verified in one pass with no decision the user would weigh. State the change in a few sentences and offer the handoff to `rosey-work` or to the user. Nothing is written.
- **Chat brief** — bounded work with at most one decision the user would weigh and no risk surface. Deliver in chat: what changes and why, the implementation units with their files and test expectations, and one decisions line when a choice must be honored. Close by offering to hand it to `rosey-work`. Nothing is written.
- **Durable** — everything else. Continue the workflow below.

**The gate resolves only when no Phase 0.1 fast path fired and Phase 0.2 found no upstream requirements document.** A plan file that already exists, or a requirements doc someone invested a brainstorm in, is prima facie Durable work — resume, deepen, and brainstorm-sourced runs are never re-tiered.

**Durable regardless of size:**

- **`mode:non-interactive` always resolves Durable** — chat is not a channel an automated caller can read, and [`rosey-parallel`](../rosey-parallel/SKILL.md)'s `work:` phase runs against a recorded plan path.
- Wording that asks for a plan, a plan file, or an output format.
- Continuation of an existing plan's item.
- Any risk surface — authentication, payments, migrations, external contracts.
- Requests that look atomic but hide design decisions: *"add caching to this endpoint"* (TTL, invalidation, key shape, backend are all KTDs), *"migrate from package A to B"* (semantic differences create migration KTDs), *"add rate limiting"* (algorithm, scope, configurability). Genuine Direct cases look like *"fix typo in README line 47"* or *"bump dependency X to v2.3.1"*.

**When the tier is uncertain after those reads, take the heavier one.** When a read surfaces a decision the user would weigh, a risk surface, or multi-pass verification, re-resolve upward before emitting anything.

On the chat tiers nothing is written and the rest of the workflow does not run: **no file, no subagent dispatch, no Sentrux baseline, no confidence check, no document review, and no Phase 5.4 menu.** The result closes the run on its own. There is no saved chat brief — if the user wants the result preserved, that is a request for a plan: re-resolve to Durable and write one, so everything in `rosey/plans/` remains an implementation-ready plan.

## Workflow

Phases run in order unless an owner routes out or short-circuits.

**Read a reference on phase entry, completely.** A read made before that phase does not satisfy it, and a terminal owner is re-read at its step even when already in context.

**A required reference that cannot be read is a stop.** Never reconstruct one from memory. In interactive mode, report which file failed and why, and stop. In `mode:non-interactive`, emit the handoff envelope with the unreadable path named in `BLOCKERS:` instead of stopping silently — an opaque halt is indistinguishable from a hang to an automated caller.

| Phase | Read first | What only those files carry |
|---|---|---|
| 0 — memory gate, resume, classify, source, scope | `references/intake.md` | the Hindsight gate and what "unavailable" means; markdown output and token parsing; the resume and deepen fast paths; the software / non-software split; upstream requirements discovery and the dossier input; the planning bootstrap and its exit condition; blocking-question classification; depth tiers; the solo scoping synthesis. The Output Contract gate above resolves inside it, at 0.6 |
| non-software route (from 0.1b) | `references/universal-planning.md` | the domain-agnostic workflow that replaces Phases 0.2–5.1; the non-interactive hard-stop |
| 1 — gather context | `references/research.md` | local research and what Lightweight skips; execution-direction signals; the external-research decision and its three stages; consolidation; depth reclassification on external contract surfaces; flow analysis |
| 2–4 — resolve questions, structure, write | `references/structure.md` | planning-question classification; title and file naming; the Sentrux topology baseline; Implementation Units and stable U-IDs; high-level technical design; depth guidance; planning rules |
| 4.2 — compose | `references/plan-sections.md`, then `references/markdown-rendering.md` | what the plan contains (hard floor, include-when-material catalog, ID rules); how markdown presents it |
| 5.1–5.3.2 — review, write, confidence gate | `references/final-review.md` | the pre-write checklist; the brainstorm-sourced scoping synthesis; write-path mechanics and the handoff envelope; confidence classification and the deepening gate |
| 5.3.3–5.3.7 — deepening (when the gate fires) | `references/deepening-workflow.md` | confidence scoring checklists; section-to-agent dispatch; execution modes; interactive finding review; plan synthesis |
| 5.3.8–5.4 — document review and handoff | `references/plan-handoff.md` | mandatory document review and its headless default; the ponytail sanity-check; final checks; menu visibility, rendering, and per-selection routing; issue creation |
| whenever a scoping synthesis fires (0.7, 5.1.5) | `references/synthesis-summary.md` | the affirmability and keep tests; summary shape budgets; anti-patterns; the literal templates; non-interactive routing |

**STOP at 5.3.8.** Document review is mandatory for a Durable plan and its default is `mode:headless`. Read `references/plan-handoff.md` before 5.3.8 and 5.4 — without it the menu renders and the run stops without firing the routed action. If the selection arrives after a user turn, reload that reference before acting.
