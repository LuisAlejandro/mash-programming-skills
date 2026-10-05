---
name: rosey-dogfood
description: "Post-merge browser QA of shipped work: cluster a week's merged GitHub PRs into user journeys, drive those journeys in a real browser, judge correctness and persona experience, and write a durable dogfood report. Use when the user says dogfood, weekly QA, test this week's PRs, or browser-QA shipped work. Manual invocation only."
argument-hint: "[7d | date range | PR numbers/URLs] [target:local|staging|prod]"
---

# Dogfood

Act as a QA engineer who dogfoods **what shipped**, not the whole app.

**Outcome:** every user-visible change in the intake window has been driven in a real browser along its whole journey, judged for correctness and for how it feels to the product's personas. Findings land in a durable report. This skill does not patch `main`.

**Done:** every matrix scenario is `Pass`, `Fail`, `Skipped`, or a terminal `Blocked`; the report at `rosey/dogfood/<YYYY-MM-DD>-<window-slug>.md` is finalized against its template; chat carries a short verdict plus the file path.

This is **window-scoped**, not whole-app exploration. Merged PRs locate the change. **Journeys** are what you test. Three PRs that all touch checkout become one checkout journey, not three scripts.

**Read `references/phases.md` before Phase 0 and follow it** — it owns every phase in detail, and the run cannot be executed correctly from the phase list below.

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors, URLs, and matrix rows unchanged. Drop lite only for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, or when the user asks for normal or long-form wording.

Caveman lite applies to orchestrator chat and status. The report on disk is normal prose.

## Interaction Method

Default to the host's blocking question tool already in the current tool list (match by capability, not by a host-specific name). Presence in the current tool list is proof the tool exists; never call a user-facing question tool to discover whether it exists. If a matching tool is listed but unloaded, use the host's tool-discovery primitive to load that capability — do not search for another host's tool name. Fall back to numbered options on the host's user-visible chat surface only when no such tool is in the list or a real question call errors. Never silently skip the question.

Ask one question at a time.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. Matrix confirm and the ticket offer may fire.
- `mode:non-interactive` — scripted or skill-to-skill execution. Skip the matrix confirm and the ticket offer. Record that the matrix was unreviewed.

Strip the interaction mode token before interpreting remaining tokens. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

## Argument Parsing

Parse `$ARGUMENTS` for the following optional tokens. Strip each recognized token before interpreting the remainder as the intake.

| Token | Example | Effect |
| --- | --- | --- |
| `mode:interactive` | `mode:interactive` | Explicit default |
| `mode:non-interactive` | `mode:non-interactive` | Skip matrix confirm and ticket offer |
| `target:local` | `target:local` | Drive a local Make/Compose server (default) |
| `target:staging` | `target:staging` | Use a staging base URL; do not start a server |
| `target:prod` | `target:prod` | Use a production base URL; read-mostly, test account required |
| `port:<n>` | `port:3000` | Local listen port |
| `--port PORT` | `--port 3000` | Same as `port:<n>` |
| `url:<https://...>` | `url:https://staging.example.com` | Base URL for staging or prod |

Conflicting `target:` tokens: stop and report the conflict.

**Intake remainder** after tokens are stripped:

- Empty → last `7d` of merged PRs in this repo
- `7d`, `14d`, `30d` → trailing-day lookback
- `YYYY-MM-DD..YYYY-MM-DD` → closed date range on merge date
- PR numbers or GitHub PR URLs (`412,418,421` or `https://github.com/org/repo/pull/412`) — a pasted list always wins over a window

If the remainder is unparseable, ask one clarifying question (interactive) or stop with a blocker (non-interactive).

## Boundaries

- **PRs locate change; journeys are what you test.** Never one browser script per PR when they share a flow.
- **Window-scoped, not whole-app.** Adjacent regression is allowed. Clicking every nav item is not.
- **GitHub MCP only** for PR metadata (`search_pull_requests`, `pull_request_read` with `get` / `get_files`) and, after finalize, optional `issue_write`. Do not use the GitHub CLI.
- **Do not switch the user's checkout.** Local target is the current tree. Staging and prod need no checkout.
- **No commits, pushes, or PRs.** Fixes are a later `rosey-work` invocation or a ticket. Do not patch `main` to clear a matrix item.
- **Screenshots** go to OS temp (`mktemp -d "${TMPDIR:-/tmp}/rosey-dogfood-XXXXXX"`), never the repo root. Copy one in only to embed it in the report.
- **agent-browser** for page journeys, including in Pi. See `references/browser.md`. If it is missing, the journey is `Blocked` with the install remediation. Do not shell out to `npx` as a browser, and do not attach to the human's default Chrome profile.
- **Serve via Make / Compose**, never host `npm` / `pip` / `node` / `python`. See `references/serve.md`.
- **v1 is merged-only.** An open or draft PR in an explicit list is recorded as skipped, not driven.

This skill is not `rosey-qa`. That skill reviews code before merge. This skill drives shipped behavior.

## Artifact Root

Reports live under `<repo-root>/rosey/dogfood/`. Resolve `<repo-root>` the first time you compose any `<repo-root>/rosey/dogfood/` path, and never before. A run that composes none skips it.

- **Hardcode** the artifact root to `<repo-root>/rosey/dogfood/` (`<repo-root>` = `git rev-parse --show-toplevel`). Do not read a config file.
- **Use** that directory as the sole artifact location: create it if absent, write the report there, and never also write `dogfood-reports/` or `docs/`.

`<window-slug>` is the intake label lowercased, with every run of non-alphanumeric characters collapsed to one `-`: `7d`, `2026-09-01-2026-09-08`, or `prs-412-418-421`.

## Optional memory

Hindsight recall is **optional** and must not block the run. If `hindsight-embed daemon status` succeeds (PATH includes `${HOME}/.local/bin`), recall test-account prefs, known flaky flows, and prior dogfood outcomes for this repo. If status fails, continue. Do not treat this skill as Hindsight-gated; recall here is advisory.

## Phase order

Intake → extract → map flows → matrix → confirm → serve → execute → report.

The order is the invariant: the flow model precedes the matrix, and the matrix precedes any browser work. Each phase's conditions are in `references/phases.md` — read it before Phase 0 rather than reconstructing a phase from this line. Work one scenario at a time, judged for correctness *and* for how it feels to each persona.

**Checkpoint, not a final write.** Create the report from `references/report-template.md` as soon as the matrix exists, with every scenario at `Pending`, and update it after each scenario is judged. The task list is session-scoped; the report on disk is what a later run resumes from. An interrupted run must leave a template-shaped checkpoint, not a bare matrix.

**Terminal states.** `Blocked (needs human verify)` (OAuth, real email, payments, SMS, or a prod mutation this skill must not drive) ends that scenario, not the run: continue the rest of the matrix, and never silently re-queue a blocked scenario on this run or on resume.
