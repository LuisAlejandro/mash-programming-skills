# Handoff

Required read at the end of Phase 5. Optional ticket offer only. This skill never commits, pushes, or opens a pull request.

## After the report is finalized

Chat summary, then:

- **Zero `Fail` rows:** stop. Mention `Blocked (needs human verify)` items if any remain.
- **Interactive, one or more `Fail` rows:** ask whether to file GitHub issues. Options: one issue per Fail / one issue listing every Fail / leave them in the report.
- **Non-interactive:** skip the question. Failures stay in the report.

Decline, or no GitHub MCP write tool: leave Failures in the report and stop.

## Filing issues

GitHub MCP `issue_write` only. Read the tool descriptor first. `method: "create"` with the same `owner` / `repo` as intake.

Do not import `rosey-qa` tracker-defer. Do not probe any tracker other than GitHub. Do not assign labels unless the user named them.

**One issue per Fail**

- Title: user-visible symptom, not "Dogfood scenario 3"
- Body: report-relative path, scenario #, originating PRs, expected vs actual, evidence, suggested follow-up
- After create, paste each issue URL into that Failure's follow-up line in the report

**One issue listing every Fail**

- Title: `Dogfood <window-slug>: N failures`
- Body: table of scenario #, flow, symptom, report path
- After create, add the issue URL under Final Status

## What this skill does not do

- `git commit`, `git push`, `create_pull_request`
- Invoke `rosey-work` or `rosey-pr` unless the user explicitly asks after the offer
- Patch product code to clear a matrix row
