# Model Tiers and Dispatch Degradation

Read this before dispatching a sub-agent — the Phase 1.1 grounding scout or the Phase 2.6 claim verifier. Dispatch is tiered by **task shape, never by a hardcoded model name**.

- **Extraction tier** — the grounding scout: retrieval and quoting work. Use the platform's cheapest capable model when the current harness exposes a per-dispatch override. "Capable" is part of the spec — escalate to the generation tier when the repo is large or the stack unfamiliar.
- **Generation tier** — the claim verifier: evidence-driven mechanical verification. Use a mid-tier model when the harness exposes an override. If model names are unknown, omit the override and inherit rather than guessing.
- **Ceiling tier** — the dialogue itself. Questions, approaches, the synthesis, and the requirements document run in the main conversation on the orchestrator's model. Nothing is dispatched for them.

## Why tier at all

The win is **context isolation**, not cost. A sub-agent reads twenty files and returns five lines; those twenty files never enter the main conversation. That holds on every harness, including the ones with no model override at all. Cheaper models on the mechanical tiers are a bonus where available, not the point.

This matters for the degradation rule below: losing model selection costs a little money, not correctness. Losing the **read budgets and output caps** would cost the isolation, which is the actual product.

## Dispatch

Use the platform's subagent primitive (`Agent`/`Task` in Claude Code, `spawn_agent` in Codex, `subagent` in Pi, `runSubagent` in VS Code, `default.task` in OpenCode, the equivalent elsewhere). Match by capability, not by another harness's tool name. Omit the `mode` parameter so the user's configured permission settings apply.

**Dispatch blocking.** Wait for the sub-agent to return before continuing. Background dispatch exists on some harnesses (Pi's `async: true`) and is a legitimate optimization there, but it is not portable — never write a phase so that it depends on work continuing while the sub-agent runs.

**Pass resolved absolute paths.** Never pass an unresolved shell-variable string to a sub-agent; it has no access to the orchestrator's shell state.

## Degradation rule

- **No per-dispatch model selection** (Cursor, OpenCode): dispatch on the inherited model and **keep the read budgets and output caps unchanged**. Cost control then comes from structure, not tiering. Where the harness supports per-agent-definition models, that is an acceptable substitute.
- **No subagent primitive at all**: do the work inline in the main conversation — still writing the dossier to its scratch path, because downstream consumers receive that path rather than its contents, and still honoring the same budgets and caps.
- **A rejected dispatch** is classified by whether an agent launched: correct a pre-launch argument rejection once, leave capacity-limited work queued and retry when a slot frees, and send any other failure to the inline path above.

Sub-agent dispatch is never a correctness dependency. Every failure degrades to inline, and inline always completes the run.
