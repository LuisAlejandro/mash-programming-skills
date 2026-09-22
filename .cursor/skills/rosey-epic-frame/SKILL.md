---
name: rosey-epic-frame
description: "Frame an epic -- one ambition spanning several separately-deliverable work areas -- into per-area requirements documents and a parallel-aware area list. Use when the user says 'epic', describes work spanning multiple areas at once (frontend and backend together, several views, a shared contract plus its consumers), or wants an epic run through the parallel pipeline. Hands off to rosey-epic-decompose. For a single feature or change, use rosey-brainstorm instead."
argument-hint: "[the epic to frame]"
---

# Rosey Epic Frame

Framing answers **WHAT the areas are** for an epic; `/rosey-epic-decompose` then answers **how they schedule**, and `/rosey-parallel` runs them. This skill does not implement code and does not compute file footprints — it explores, clarifies, and writes one requirements document per work area. Use the current calendar year when dating artifacts.

**Pipeline position:** `rosey-epic-frame` → `rosey-epic-decompose` → `rosey-parallel`. This is the parallel-execution pipeline. It runs end to end on its own and does not route into any other workflow.

**Outcome:** N work areas, each with its own requirements document under `rosey/brainstorms/`, plus an area list carrying goals and declared dependencies. Downstream planning reads those documents as its origin, so each parallel task starts from validated product decisions rather than a projected stub.

**Done:** every area has a written requirements document, the area list is presented, and the handoff to `/rosey-epic-decompose` has fired.

**Scope floor.** This skill is for ambitions with **more than one separately-deliverable outcome**. A single feature or change does not belong here — say so and stop. There is no path through this skill that produces one document.

**IMPORTANT: All file references in generated documents must use repo-relative paths (e.g., `src/models/user.rb`), never absolute paths. Absolute paths break portability across machines.**

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, or when the user asks for normal or long-form wording.

**Artifact boundary:** Caveman lite applies to chat and status prose, not to the requirements documents, which stay clear enough for humans to review.

## Epic Description

<epic_description> #$ARGUMENTS </epic_description>

**If the epic description above is empty:** In interactive mode, ask the user: "What's the epic? Describe the ambition — what you want built, and roughly what it spans." In non-interactive mode, stop with a blocker.

Do not proceed until you have an epic description.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. Use the collaborative dialogue and question flow.
- `mode:non-interactive` — scripted or skill-to-skill execution. Do not ask blocking questions or wait for confirmation.

Strip the interaction mode token before treating the remainder as the epic description. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

**Token-parsing convention:** only literal-prefix flag tokens (`mode:`) are consumed and stripped. Other `<word>:<word>` tokens — including conventional commit prefixes like `feat:`, `fix:`, `chore:` that may appear inside an epic description — pass through verbatim.

When `INTERACTION_MODE=non-interactive`:

- Do not use blocking question tools or prompt for clarification.
- Infer conservatively from the prompt and the repo scan.
- Record material assumptions in each area's requirements document.
- Skip the Phase 2 dialogue and the Phase 4 handoff menu.
- The requirements documents are always written — they are the only channel back to the caller. If they cannot be written safely, stop with a concise blocker.

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

**Resolve by capability, not by this table.** The table is a convenience for the common harnesses, not the authority — harnesses rename tools and this list will drift. Presence in the current tool list is proof the tool exists; never call a user-facing question tool just to discover whether it exists. If a matching tool is listed but unloaded, use the host's tool-discovery primitive to load it. Fall back to numbered options in chat only when no blocking tool is in the tool list or a real call errors. **Never silently skip the question.**

## Core Principles

1. **Preserve breadth.** Every separately-deliverable outcome in the ambition survives as its own work area. Narrowing to one defeats the purpose of this skill.
2. **Slice on product seams.** An area needs its own user value and its own acceptance boundary. A named device, provider, view, or data source is not automatically an area — coverage across several of them is usually one requirement inside one area.
3. **One document per area.** N coherent requirements documents, never one document about N things. Each stands alone as a planning origin.
4. **Every area is independently verifiable.** An area that cannot be finished and checked on its own cannot be a parallel task. Merge it into the area it depends on.
5. **Declare consumption, not overlap.** A dependency means area B consumes something area A defines. Two areas touching the same file is a scheduling fact for `/rosey-epic-decompose`, not a dependency to declare here.
6. **Resolve product decisions here.** User-facing behavior, scope boundaries, and success criteria belong in this workflow. File layouts, schemas, and code structure belong downstream.
7. **Right-size the epic.** Two to five areas is the common shape. One area means this is not an epic; twenty means the seams were drawn too fine.

## Workflow

Phases run in this order. Each names the files it cannot run correctly without: read them when you reach that phase, and never do its work from this table alone.

**Read a reference on phase entry, completely.** A read made before that phase does not satisfy it, and a reference is re-read at its phase even when it is already in context.

**A required reference that cannot be read is a stop.** Never reconstruct one from memory. In interactive mode, report which file failed and why, and stop. In `mode:non-interactive`, return a structured blocker naming the unreadable path instead of stopping silently — an opaque halt is indistinguishable from a hang to an automated caller.

| Phase | Read first | What only those files carry |
|---|---|---|
| 0 — memory gate, resume, scope floor, area detection | `references/phase-0.md` | the Hindsight gate and what "unavailable" means; markdown output and token parsing; resume; the scope floor and its stop; the separable-outcome test that finds the areas |
| 1 — ground the epic | `references/dialogue.md` | the repo scan and grounding-scout dispatch with its lazily-created scratch path; verify-before-claiming; the per-area probe discipline; the cross-area integration check; the exit condition |
| whenever a sub-agent is dispatched (1.1) | `~/.config/rosey/references/model-tiers.md` | the extraction / generation / ceiling tiers; blocking-dispatch and resolved-path rules; the degradation ladder down to inline |
| 2 — draw the areas | `references/area-mapping.md` | product-seam heuristics; granularity bounds; area ids and the slug contract; dependency declaration rules; where framing stops and `rosey-epic-decompose` takes over |
| 3 — write the documents | `references/area-sections.md` | the per-area section contract and hard floor; the ID namespaces; the filename rule; the cross-area relationships section; sibling exclusion |
| 4 — handoff | `references/handoff.md` | the area table; the dispatch to `/rosey-epic-decompose`; what decompose still owns; non-interactive envelope |

## Common Pitfalls to Avoid

- **Collapsing to one area** — if the dialogue keeps merging areas until one remains, the ambition was a single feature. Stop and say so rather than producing a one-area epic.
- **Splitting on coverage** — three payment providers behind one checkout flow is one area with three requirements, not three areas.
- **Declaring file overlap as a dependency** — that is decompose's job. Over-declaring serializes work that could have run in parallel.
- **Writing file paths into requirements** — implementation detail belongs downstream. An area document names *what* the area delivers, not *where* the code lives.
- **Generic area ids** — `api` or `frontend` collide across epics in a flat namespace. Name the epic in the id.
- **Skipping the scope floor** — running a single feature through this skill produces one document and a pointless parallel run.
