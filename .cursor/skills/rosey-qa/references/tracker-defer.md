# Tracker Detection and Defer Execution

This reference covers how Defer actions file tickets in the project's tracker. It is loaded by `SKILL.md` when Interactive mode's routing question needs to decide whether to offer option C (File tickets), when the walk-through's Defer option executes, and when the bulk-preview of option C is shown. It is also loaded by autonomous callers that need to file residual actionable findings without user prompts — see Execution Modes below.

---

## Execution Modes

Tracker-defer has two execution modes. The caller selects one; the detection, fallback chain, and ticket composition are shared.

### Interactive mode (default)

Used by `rosey-qa` Interactive mode's routing question, walk-through Defer actions, and bulk-preview option C. All user-facing prompts fire:

- Execution failures prompt with Retry on GitHub / Convert to Skip.
- Labels always name GitHub; no confirmation prompt is needed because there is only one sink.

### Non-interactive mode

Used by autonomous callers that must not prompt. All blocking questions are skipped; the fallback chain is executed silently in order. Behavior:

- No confirmation on the first generic-label Defer; proceed directly.
- On execution failure, automatically fall to the next tier without prompting. Record the failure.
- On total chain exhaustion (every tier failed or no sink available), return findings in the `no_sink` bucket so the caller can route them to another surface (e.g., inline them in a PR description).
- Return a structured result: `{ filed: [{ finding_id, tracker, url }], failed: [{ finding_id, tracker, reason }], no_sink: [{ finding_id, title, severity, file, line }] }`.

The caller decides how to surface the result to the user. The non-interactive mode treats "no sink available" as a data-producing outcome, not a prompt trigger.

---

## Sink

**GitHub Issues is the only tracker Rosey files to.** There is no tracker detection step and no named-tracker tier: the sink is GitHub Issues via GitHub MCP, or nothing. Do not read `AGENTS.md` for a `project_tracker` key, do not probe Linear/Jira/other MCP servers, and do not fall back to another tracker's CLI.

The availability output is a single flag:

```
{ sink_available }
```

- `sink_available` — `true` when GitHub MCP issue tools are loaded and responsive and the current repo has issues enabled (when the MCP exposes that metadata); `false` otherwise. Drives whether Defer is offered in Interactive mode, and drives the `no_sink` bucket in Non-interactive mode.

---

## Probe timing and caching

The availability probe runs **at most once per session** and **only when Defer execution is imminent**. Never speculatively at review start, never per-Defer, never per-walk-through-finding. The cached flag is reused for every Defer action in the same run.

Probe: verify GitHub MCP issue creation/read tools are available, and that the repository has issues enabled when the MCP exposes that metadata. Set `sink_available` from the result.

When Interactive mode's routing question is skipped entirely (R2 zero-findings case), no probe runs. A cached `sink_available = true` stays cached — do not re-probe per Defer.

---

## Label logic (Interactive mode)

The sink is always GitHub, so labels name it directly with no confidence gating and no token substitution:

- When `sink_available = true`: the routing question's option C reads `File a GitHub issue per finding without applying fixes`, and the walk-through's per-finding Defer option reads `Defer — file a GitHub issue`.
- When `sink_available = false`: option C is omitted from the routing question, option B (Defer) is omitted from the walk-through per-finding options, and the agent tells the user why in the routing question's stem.

Non-interactive mode skips label decisions entirely — it acts silently on the sink.

---

## Fallback chain

There is one sink and one fallback:

1. **GitHub Issues via GitHub MCP** — when the MCP issue tools are available and the current repo supports issues
2. **No sink** — findings remain in the review report's residual-work section (Interactive mode) or are returned in the `no_sink` bucket for the caller to route (Non-interactive mode). The agent does not re-display them through a transient surface. When GitHub Issues is unreachable, this is the correct behavior.

---

## Ticket composition

Every Defer action creates a ticket with the following content, adapted to the tracker's capabilities:

- **Title:** the merged finding's `title` (schema-capped at 10 words).
- **Body:**
  - Plain-English problem statement — reads the persona-produced `why_it_matters` from the contributing reviewer's artifact file at `rosey/qa/<run-id>/{reviewer}.json`, using the same `file + line_bucket(line, +/-3) + normalize(title)` matching headless mode uses (see SKILL.md Stage 6 detail enrichment). Falls back to the merged finding's `title`, `severity`, `file`, and `suggested_fix` (when present) when no artifact match is available — these fields are guaranteed in the merge-tier compact return.
  - Suggested fix (when present in the finding's `suggested_fix`).
  - Evidence (direct quotes from the reviewer's artifact).
  - Metadata block: `Severity: <level>`, `Confidence: <score>`, `Reviewer(s): <list>`, `Finding ID: <fingerprint>`.
- **Labels:** severity tag (`P0`, `P1`, `P2`, `P3`) and a category label sourced from the reviewer name — but only when the repo already has matching labels. Omit labels rather than creating them.
- **Length cap:** when the composed body would exceed GitHub's body length limit, truncate with `... (continued in rosey-qa run artifact: rosey/qa/<run-id>/)` and include the finding_id in both the truncated body and the metadata block so the artifact is discoverable.

The finding_id is a stable fingerprint composed as `normalize(file) + line_bucket(line, +/-3) + normalize(title)` — the same fingerprint used by the merge pipeline.

---

## Failure path

When ticket creation fails at execution (API error, auth expiry mid-session, rate limit, malformed body rejected, 4xx/5xx response):

**Interactive mode:** surface the failure inline and ask the user using the platform's blocking question tool.

Stem:
> Defer failed: GitHub returned <error summary>. How should the agent handle this finding?

Options:
- `Retry on GitHub` — re-attempt once more (useful for transient errors)
- `Convert to Skip — record the failure` — abandon this Defer, note the failure in the completion report's failure section, and continue the walk-through or bulk flow

**Non-interactive mode:** do not prompt. Record the finding in the `failed` bucket of the structured return and continue. If the sink was never available, the finding ends up in the `no_sink` bucket instead.

When GitHub issue creation fails at execution, set the cached `sink_available` to `false` for the rest of the session. Subsequent Defer actions skip straight to the failure path rather than retrying a confirmed-broken sink.

Only when `ToolSearch` explicitly returns no match or the tool call errors — or on a platform with no blocking question tool — fall back to numbered options and waiting for the user's reply (Interactive mode only).

---

## Execution behavior

| Sink | Interface | Invocation | Body format | Labels |
|---------|-----------|-------------------|-------------|--------|
| GitHub Issues | GitHub MCP issue tool | Repo defaults to the current repo. Use severity labels only when the repo already has matching labels; omit labels if unavailable. Fall back to a label-less issue on first failure. | Markdown | `P0` / `P1` / etc. when labels exist |
| No sink available | — | Interactive: Defer option omitted, findings remain in the report's residual-work section. Non-interactive: findings returned in the `no_sink` bucket for caller routing. | — | — |

When uncertain, prefer "drop with explicit user-facing notice" over "pass through silently and hope." A Defer that produces no durable artifact and no user message is data loss.

---

## Cross-platform notes

The question-tool name varies by platform. In Interactive mode, use the platform's blocking question tool (`AskUserQuestion` in Claude Code, `AskQuestion` in Cursor, `question` in OpenCode, `request_user_input` in Codex, `ask_user` in Gemini, `ask_user` in Pi (requires the `pi-ask-user` extension)). In Claude Code the tool should already be loaded from the Interactive-mode pre-load step — if it isn't, call `ToolSearch` with query `select:AskUserQuestion` now. Fall back to numbered options in chat only when the harness genuinely lacks a blocking tool — `ToolSearch` returns no match, the tool call explicitly fails, or the runtime mode does not expose it (e.g., Codex edit modes without `request_user_input`). A pending schema load is not a fallback trigger. Never silently skip the question.

Non-interactive mode is platform-agnostic: it never prompts, so the platform's question tool is not relevant.
