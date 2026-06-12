---
name: rosey-release
description: Create the weekly patch release for Rosey app repos by documenting closed issues in a milestone, running make release-patch, and closing the milestone. Use when publishing the current develop branch after auto-merged PRs have landed.
argument-hint: "[mode:interactive|mode:non-interactive]"
---

# Rosey Release

Publish the weekly patch release for Rosey app repositories.

This skill implements MAINTAINER release steps 7-9 for the current Rosey
workspace. It does not plan releases, implement hotfixes, open PRs, merge PRs,
or announce releases.

## Communication while using this skill

**Caveman lite** for workflow status prose while this skill runs: strip filler
and hedging; keep articles and full sentences; stay professional and tight.
Technical accuracy unchanged; commands, issue titles, GitHub output, and release
script output unchanged. Drop lite for release confirmation, destructive or
irreversible warnings, user confusion, or when the user asks for normal wording.

## Rosey Overlay

`rosey-release` is the publishing endpoint for the maintainer ritual:

- Upstream: feature work lands through `rosey-work`, `rosey-qa`,
  `rosey-pr`, or `rosey-lfg-quality`, then app PRs auto-merge into `develop`.
- Owned steps: release readiness checks, retroactive milestone documentation,
  `make release-patch`, and milestone closure.
- Downstream: none. CI pipeline babysitting is handled outside this v1 flow by
  Cursor Bugbot and existing automation.

Hard boundaries:

- App repos only. Do not run this skill in `rosey-maintainer-tools` or
  `rosey-agentic-env`; those are maintainer repositories and do not follow the
  app release ritual.
- Patch releases only. Do not infer minor or major releases from issues,
  labels, commits, or PRs.
- Do not implement hotfixes. Maintainers perform hotfixes manually.
- Do not create or update release planning artifacts. The milestone created here
  is retroactive documentation for the version being published.
- Do not pass an app name. Each repo's Makefile defines `APP_NAME ?= ...`;
  `make release-patch` passes that value to `scripts/release.sh` for the GitHub
  release title.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation. The skill may ask for
  confirmation before running the release script.
- `mode:non-interactive` — scripted or skill-to-skill execution. The skill must
  not ask blocking questions or wait for confirmations.

Strip the interaction mode token before interpreting remaining text. If no
interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

## Hindsight Gate

Before release work:

1. Read [`rosey-hindsight`](../rosey-hindsight/SKILL.md).
2. Run `uvx hindsight-embed daemon status`.
3. If available, recall release context for the current repo and weekly patch
   release.
4. If unavailable, continue and record `HINDSIGHT: unavailable` in the release
   handoff.

## Release Workflow

### 1. Resolve Repository

1. Confirm the current directory is inside a git repository.
2. Resolve the git root and repo name.
3. Stop if the repo name is `rosey-maintainer-tools` or `rosey-agentic-env`.
4. Confirm release files exist:
   - `Makefile`
   - `.bumpversion.cfg`
   - `scripts/release.sh`
5. Verify `Makefile` defines `APP_NAME`. This is informational. Do not patch the
   Makefile and do not pass `APP_NAME=...` at runtime.

### 2. Check Release Preconditions

Run and verify:

```bash
git status --short
git branch --show-current
git rev-parse --verify origin/develop
git flow version
```

Preconditions:

- Working tree must be clean.
- Current branch must be `develop`.
- `origin/develop` must exist.
- No release branch may already be in progress.
- Git flow must be available. If git flow is missing, stop with installation
  guidance. If git flow is installed but not initialized, the release script may
  initialize it.

Then sync:

```bash
git pull origin develop
```

If pull changes the tree, re-check that the working tree is clean.

Warn, but do not block, when open PRs still target `develop`:

```bash
gh pr list --base develop --state open
```

Record the count in the handoff or status output. The weekly release still
proceeds when eligible closed parent or standalone issues exist.

### 3. Compute Next Patch Version

Compute the next version without changing files:

```bash
bumpversion --dry-run --list patch
```

Extract `new_version=<version>`. The milestone name is this patch version.

Do not accept or expose `version_type:minor`, `version_type:major`,
`app_name:<name>`, positional app names, or `APP_NAME=...` overrides.

### 4. Select Issues For The Milestone

Use GitHub data to identify parent or standalone issues for the retroactive
milestone. Sub-task issues are implementation details and must not be added to
the release milestone directly.

Preferred order:

1. Use available GitHub MCP tools for milestone and issue operations when an
   enabled server supports them.
2. Fall back to `gh` when MCP support is unavailable, because this release flow
   already depends on GitHub CLI for `gh release create` inside
   `scripts/release.sh`.

Resolve the release window:

1. Find the most recently closed milestone by `closed_at`.
2. Use that `closed_at` as the exclusive lower bound.
3. If no closed milestone exists, prefer the latest GitHub release or tag date as
   the lower bound.
4. If no lower bound can be resolved, stop in interactive mode and ask for the
   initial window; in non-interactive mode, stop with a blocker.

Before selecting eligible issues, close completed parent issues:

1. Find open parent feature issues. A parent feature issue is one of:
   - An issue that has sub-issues.
   - An issue with the CodeCandidates parent naming convention, such as a
     `Feature:` title, when sub-issue metadata is unavailable.
2. For each open parent, verify every linked sub-issue is closed.
3. If all linked sub-issues are closed, close the parent with:

   ```bash
   gh issue close <parent-number> --comment "All sub-tasks completed."
   ```

4. Do not close parents with open or unknown sub-issues. Do not close sub-task
   issues from this skill; PR merge via `Closes #N` owns sub-task closure.

Eligible milestone issues after that preflight:

- **Parent feature issues**: closed, `closed_at` after the lower bound, and
  identified as a parent by sub-issue metadata or `Feature:` title convention.
- **Standalone issues**: closed, `closed_at` after the lower bound, not linked
  as a sub-issue of another issue, and not a CodeCandidates `Task:` issue.
- Issue is not already assigned to a later open milestone.
- If linked PR evidence is available and shows the issue is still blocked by an
  unmerged PR, exclude it.

Issues are the source of truth. Do not use merged PRs as the primary source of
truth because one issue may need more than one PR.

Explicit exclusions:

- `Task:` sub-issues or issues linked as sub-issues of a parent.
- Open parent issues where only some children are closed.
- Issues already assigned to a later open milestone.

If no eligible issues exist, stop before creating a milestone:

```text
No eligible closed issues since <date>; skipping weekly release.
```

### 5. Create And Populate Milestone

Create a new milestone named for the next patch version.

Attach every eligible parent or standalone issue to the milestone. Do not attach
sub-task issues directly.

The milestone documents the version and the issues resolved in that version. It
is created during release and closed after release; it is not a planning
milestone.

If milestone creation or issue assignment fails after partial work:

- Do not run the release script.
- Report the partial milestone state clearly.
- Leave cleanup to the maintainer unless the corrective action is obvious and
  non-destructive.

### 6. Run The Release Script

Interactive mode:

```bash
make release-patch
```

Non-interactive mode:

```bash
NON_INTERACTIVE=true make release-patch
```

Do not run `make release-minor`, `make release-major`, `make hotfix`, or
`make release-patch APP_NAME=...`.

The Makefile passes its repo-local `APP_NAME` into `scripts/release.sh`; the
script uses it for the GitHub release title.

### 7. Verify Release

Verify:

- The command completed successfully.
- The new tag exists on the remote.
- GitHub release creation either succeeded or was skipped by the release script
  because `gh` was unavailable.
- Local branch is back on `develop` and clean.

### 8. Close Milestone

Close the milestone after successful release verification.

The release date and milestone close date should be the same date. If closing the
milestone fails after a successful release, report the release as complete but
the milestone close as a blocker for manual follow-up.

### 9. Handoff

Emit:

```text
ROSEY_RELEASE_HANDOFF
VERSION: <new patch version>
MILESTONE: <title or url>
ISSUES_INCLUDED:
- <issue number>: <title>
COMMAND:
- <make release-patch | NON_INTERACTIVE=true make release-patch>: <pass | failed>
VERIFY:
- remote tag: <pass | failed>
- GitHub release: <created | skipped | failed>
- milestone closed: <pass | failed>
BLOCKERS: <none | one-line blocker>
HINDSIGHT: <available | unavailable | skipped> -- <brief reason>
END_ROSEY_RELEASE_HANDOFF
```

If Hindsight is available, retain a concise session summary with repo, version,
milestone, included issues, command result, and blockers. Do not store secrets.

## Prohibited Behavior

- Do not create releases when no eligible issues exist.
- Do not create an empty milestone.
- Do not pass app names or override `APP_NAME`.
- Do not release from branches other than `develop`.
- Do not weaken or alter CI to make a release possible.
- Do not perform hotfixes.
- Do not run in maintainer repositories.
