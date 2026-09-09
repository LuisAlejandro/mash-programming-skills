# Core Principles, Interaction Rules, and Output Guidance

Read this before the first question of any brainstorm, including the non-software route.

## Core Principles

1. **Assess scope first** - Match the amount of ceremony to the size and ambiguity of the work.
2. **Be a thinking partner** - Suggest alternatives, challenge assumptions, and explore what-ifs instead of only extracting requirements.
3. **Resolve product decisions here** - User-facing behavior, scope boundaries, and success criteria belong in this workflow. Detailed implementation belongs in planning.
4. **Keep implementation out of the requirements doc by default** - Do not include libraries, schemas, endpoints, file layouts, or code-level design unless the brainstorm itself is inherently about a technical or architectural change.
5. **Right-size the artifact** - Simple work gets a compact brief; larger work gets more structure. No ceremony that does not help planning.
6. **Apply YAGNI to carrying cost, not coding effort** - Prefer simple value. Avoid speculative complexity; include low-cost polish only when easy to maintain.
7. **Do not turn coverage into decomposition** - Treat named devices, providers, and data sources as coverage requirements, not automatically as separate integration workstreams. Split them only when a shared access path cannot satisfy a named requirement. Leave connector selection to planning unless that choice materially changes product scope or behavior.
8. **Keep one coherent work unit per artifact** - When a request contains independently valuable outcomes that can be planned and delivered separately, choose one as the current focus before deep exploration. Preserve how the surrounding work is currently understood without turning tentative future areas into requirements for this document.

## Interaction Rules

These rules apply to every brainstorm, including the universal (non-software) flow routed to `references/universal-brainstorming.md`.

1. **Ask one question at a time** - Pick the single most useful question each turn.
2. **Prefer single-select multiple choice** - Use single-select when choosing one direction, one priority, or one next step.
3. **Use multi-select rarely and intentionally** - Use it only for compatible sets that can coexist. If priority matters, follow up for the primary choice.
4. **Default to the platform's blocking question tool** - Use the harness's blocking question tool when one exists:

   | Harness | Tool | Note |
   | --- | --- | --- |
   | VS Code / GitHub Copilot | `vscode_askQuestions` | Takes a `questions` array; set `multiSelect` for Rule 3 |
   | Cursor | `AskQuestion` | |
   | OpenCode | `question` | |
   | Claude Code | `AskUserQuestion` | Call `ToolSearch` with `select:AskUserQuestion` first if its schema is not loaded |
   | Codex | `request_user_input` | Unavailable in edit modes — fall back there |
   | Pi | `ask_user` | Requires the `pi-ask-user` extension |
   | Gemini | `ask_user` | |
   | Any other harness | match by capability | Use whatever user-input/elicitation tool is in the current tool list; do not call another harness's tool name |

   **Resolve by capability, not by this table.** The table is a convenience for the common harnesses, not the authority — harnesses rename tools and this list will drift. Presence in the current tool list is proof the tool exists; never call a user-facing question tool just to discover whether it exists. If a matching tool is listed but unloaded, use the host's tool-discovery primitive to load it.

   These tools include a free-text fallback (e.g., "Other"), so options scaffold the answer without confining it — well-chosen options surface dimensions the user may not have separated, and pick-plus-optional-note is lower activation energy than composing prose from scratch. This default holds for opening and elicitation questions too, not only narrowing. Fall back to numbered options in chat only when no blocking tool is in the tool list or a real call errors (e.g., Codex edit modes) — not because a schema load is required. Never silently skip the question.
5. **Use an open-ended question only when the question is genuinely open** - Drop the blocking tool only when (a) the answer is inherently narrative ("walk me through how you got here"), (b) the question is diagnostic or introspective and presented options would unintentionally influence the user's answer (e.g., "what concerns you most?" — a 4-option menu would nudge them toward those axes rather than the ones actually on their mind), or (c) you cannot write 3-4 genuinely distinct, plausibly-correct options that cover the space without padding or strawmen. The test: if you'd be straining to fill the option slots, the question is open — ask it open-ended. Rule 1 still applies: still one question per turn.
6. **Open-ended questions earn their place only when they're specific enough to elicit a substantive answer** - Apply Rule 5 silently: just ask the question, do not narrate the form choice. The question itself must give the user something concrete to anchor on. Good: *"What's the most concrete thing someone's already done about this — paid for it, built a workaround, quit a tool over it?"* (this is one of Phase 1.2's rigor probes — it earns its open-endedness by naming what counts as an answer). Too thin: *"What's your take?"* (nothing to bite into; user defaults to a one-liner that wastes the open question). Avoid (a) narrating the form choice ("the most useful question I can ask here is..."), (b) framings that imply a short answer ("briefly", "in one sentence"), (c) yes/no traps, and (d) AI-slop warmth wrappers ("take it wherever feels relevant").
7. **Ask only decisions** - A question whose answer is in the environment — the repo, the grounding scan, or another reachable source — is not put to the user. Look it up. A running lookup does not stall questions that do not depend on it. Decisions stay on the user.

## Output Guidance

- **Keep outputs concise** - Prefer short sections, brief bullets, and only enough detail to support the next decision.
- **Prioritize decision-relevant detail** - Preserve the facts, tradeoffs, and caveats needed for the next decision; trim introductions, repetition, and optional background first.
- **Use repo-relative paths** - When referencing files, use paths relative to the repo root (e.g., `src/models/user.rb`), never absolute paths. Absolute paths make documents non-portable across machines and teammates.
- **Artifact boundary** - Caveman lite applies to chat and status prose, not to requirements documents by default. Requirements remain clear enough for humans to review.
- **Compact non-interactive artifacts** - When `mode:non-interactive` is active, keep the markdown requirements lean: preserve actors, flows, acceptance examples, requirements, scope boundaries, IDs, assumptions, and blockers; trim explanatory prose, duplicate rationale, and narrative setup that downstream automation does not need.
