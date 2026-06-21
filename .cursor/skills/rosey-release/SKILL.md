---
name: rosey-release
description: Gate and publish Rosey app repo releases (patch, minor, major) by orchestrating milestone intelligence, Makefile release targets, GitHub Actions gates, PyPI checks, and release handoff.
argument-hint: "[mode:interactive|mode:non-interactive] [patch|minor|major]"
---

# Rosey Release

Gate and publish **releases** (patch, minor, major) for Rosey app repositories.

This skill implements the release portion of `MAINTAINER.rst`. It does not plan
feature work, open PRs, merge PRs, implement code, or announce releases.

## Communication while using this skill

**Caveman lite** for workflow status prose while this skill runs: strip filler
and hedging; keep articles and full sentences; stay professional and tight.
Technical accuracy unchanged; commands, issue titles, GitHub output, and release
script output unchanged. Drop lite for release confirmation, destructive or
irreversible warnings, user confusion, or when the user asks for normal wording.

## Rosey Overlay

`rosey-release` is the publishing endpoint after features land on `develop`:

- Upstream: `rosey-lfg-code` and `rosey-lfg-quality` (or `rosey-work`, `rosey-qa`,
  `rosey-pr`), then app PRs auto-merge into `develop`.
- Owned steps: release readiness checks, retroactive milestone documentation,
  `make release-*` execution, branch CI verification, Publish Release workflow
  verification, PyPI/package asset verification, milestone closure, and handoff.
- Downstream: none. This skill stops after release verification and handoff.

Hard boundaries:

- App repos only. Do not run in `rosey-maintainer-tools` or `rosey-agentic-env`.
- Patch is the default. Minor and major only when explicitly requested in
  arguments or by the user. Do not infer from issues, labels, commits, or PRs.
- Do not implement feature code.
- Do not create release planning artifacts. The milestone here is retroactive
  documentation for the version being published.
- Do not pass `APP_NAME=...`; the Makefile supplies it.
- Do not weaken, skip, or edit CI to make a release pass.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default. May ask for confirmation before running scripts.
- `mode:non-interactive` — no blocking questions or confirmations.

Strip the mode token before interpreting release type. Default `INTERACTION_MODE=interactive`.

Parse at most one release type token:

- `patch` — default. Milestone selection + `make release-patch`.
- `minor` — `make release-minor`; confirm milestone handling with user.
- `major` — `make release-major`; confirm milestone handling with user.

If no type token, set `RELEASE_TYPE=patch`. If multiple type tokens, stop and ask.

In `mode:non-interactive`:

- **Patch only** unless a release type token (`minor` or `major`) is present in `$ARGUMENTS`.
- If `minor` or `major` is requested in non-interactive mode, document milestone handling without
  blocking questions. If milestone rules cannot be satisfied automatically, emit
  `ROSEY_RELEASE_HANDOFF` with `SUCCESS: false`, `BLOCKERS:` describing the milestone gap,
  and do not run release scripts.

## Hindsight Gate

Before release work:

1. Read [`rosey-hindsight`](../rosey-hindsight/SKILL.md).
2. Run `uvx hindsight-embed@0.8.2 daemon status`.
3. If available, recall release context for the current repo.
4. If unavailable, record `HINDSIGHT: unavailable` in the handoff.

## Release Workflow

### 1. Resolve Repository

1. Confirm git repository; resolve root and repo name.
2. Stop if repo is `rosey-maintainer-tools` or `rosey-agentic-env`.
3. Confirm files exist:
   - `Makefile`, `.bumpversion.cfg`
   - `scripts/release.sh`, `scripts/lib.sh`, `scripts/rollback.sh`
   - `.github/workflows/push.yml`, `.github/workflows/release.yml`
4. Verify `Makefile` defines `APP_NAME` (informational only).

### 2. Check Preconditions

Run and verify:

```bash
git status --short
git branch --show-current
git rev-parse --verify origin/develop
command -v git docker make gh bumpversion gpg
docker info
git flow version
gh auth status
git config --get user.signingkey
gpg --list-secret-keys "$(git config --get user.signingkey)"
```

Preconditions:

- Working tree clean — no modified or untracked files (`git status --porcelain` empty).
- Host tools: `git`, `docker` (daemon running), `make`, `gh` (authenticated),
  `bumpversion`, `gpg`, `git flow`.
- GPG: `user.signingkey` set and secret key available locally.
- `origin/develop` exists.
- No in-flight `release/*` branch unless user explicitly asked to recover (use undo first).
- Current branch must be `develop`. Sync: `git pull origin develop`.

Warn (do not block) on open PRs targeting `develop`:

```bash
gh pr list --base develop --state open
```

### 3. Compute Next Version

```bash
bumpversion --dry-run --list patch   # or minor | major
```

Extract `new_version=<version>`. Milestone name matches this version for patch flows.

### 4. Select Issues For The Milestone (patch only)

For `minor` and `major`, require user confirmation of milestone handling before
creating or changing milestones.

For `patch`, use GitHub data for parent or standalone issues (not sub-tasks).

Resolve release window:

1. Most recently closed milestone `closed_at` as exclusive lower bound.
2. Else latest GitHub release or tag date.
3. Else stop (ask in interactive mode; blocker in non-interactive).

Before selecting patch issues, close completed parent issues when all sub-issues
are closed (`gh issue close <parent> --comment "All sub-tasks completed."`).

Eligible patch issues:

- Parent features or standalone issues closed after the lower bound.
- Not sub-tasks, not `Task:` issues, not on a later open milestone.
- Exclude if blocked by unmerged PR evidence.

If no eligible issues for patch, stop:

```text
No eligible closed issues since <date>; skipping release.
```

### 5. Create And Populate Milestone

Create milestone for next version when applicable. Attach eligible issues only.
Do not run `make release-*` if milestone creation partially failed.

### 6. Run The Gated Make Target

Five gates:

| Gate | What runs | Verified by |
| --- | --- | --- |
| 1 Local preflight | `make release-preflight` | Script exit |
| 2 Branch push | `release/<version>` pushed | Remote branch |
| 3 Branch CI | Push workflow + `Release Gate` | `gh run watch` |
| 4 Tag + GH release | git-flow finish, tag, `gh release create` | Remote tag + release |
| 5 Publish verify | `release.yml` before PyPI | `gh run view` |

| Type | Interactive | Non-interactive |
| --- | --- | --- |
| `patch` | `make release-patch` | `NON_INTERACTIVE=true make release-patch` |
| `minor` | `make release-minor` | `NON_INTERACTIVE=true make release-minor` |
| `major` | `make release-major` | `NON_INTERACTIVE=true make release-major` |

### 6b. Abort and Roll Back on Failure

On any failure, **always** run `VERSION=<version> make undo-release`, halt, report
what failed, confirm rollback, and tell the user to fix on `develop` and invoke
`rosey-release` again.

### 7. Verify Branch CI And Publish Workflow

Verify: branch CI passed before tag; remote tag; GitHub release; Publish Release
workflow succeeded; `Verify release tag` before PyPI; distribution assets on
GitHub release; PyPI verification per dispatch (see below); local branch on
`develop` and clean.

**PyPI verification rules:**

- If VersionPromote dispatch lists packages (from `publish-to-pypi` in
  `.github/workflows/release.yml`), verify each listed package on PyPI and record
  `pass` or `failed` per package in the handoff `PYPI:` section.
- If dispatch says PyPI is not applicable (no `publish-to-pypi` job), set
  `PYPI: not-applicable` in the handoff and skip PyPI checks.
- Do not hardcode package names; use only the dispatch list or repo workflow discovery.

### 8. Close Milestone

Close milestone after successful verification (same date as release).

### 9. Handoff

```text
ROSEY_RELEASE_HANDOFF
VERSION: <new version>
RELEASE_TYPE: <patch | minor | major>
MILESTONE: <title or url | none>
ISSUES_INCLUDED:
- <issue number>: <title>
COMMAND:
- <make command>: <pass | failed>
PREFLIGHT: <pass | failed>
BRANCH_CI: <pass | failed>
PUBLISH_WORKFLOW: <pass | failed>
PYPI: <not-applicable | per-package lines below>
- <package-name>: <pass | failed>
GITHUB_ASSETS: <pass | failed>
VERIFY:
- remote tag: <pass | failed>
- GitHub release: <created | existed | skipped | failed>
- milestone closed: <pass | failed | not-applicable>
BLOCKERS: <none | one-line blocker>
ROLLBACK: <pass | failed | not-applicable>
HINDSIGHT: <available | unavailable | skipped> -- <brief reason>
END_ROSEY_RELEASE_HANDOFF
```

Record `ROLLBACK: pass` after successful `make undo-release`; `failed` if rollback did not complete; `not-applicable` when no release version was created.

## Prohibited Behavior

- Do not create patch releases when no eligible issues exist.
- Do not create empty milestones.
- Do not pass app names or override `APP_NAME`.
- Do not infer minor or major releases.
- Do not weaken, skip, or alter CI.
- Do not run in maintainer repositories.
