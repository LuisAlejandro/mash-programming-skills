# GitHub Workflows — Split CI and Auto-Merge

When the repo profile includes `ci-base`:

- **Static sync** writes `.github/workflows/pr-auto-merge.yml` (approve/merge after CI; API-only).
- **Repo-owned:** `.github/workflows/pr.yml` (Semgrep as a named **Code Quality** job *or* a step inside **Repository Checks**) and `.semgrepignore`.
- The dynamic phase may **patch** `.github/workflows/pr.yml` for security (trigger/checkout, remove approve/merge). It must **not** rewrite `pr.yml` or `push.yml` wholesale. It must **not** strip cost-opt structure (see Preserve below).

## Do Not Edit (static sync owns)

- `.github/workflows/pr-auto-merge.yml` — managed by static sync; do not hand-edit in app repos
- `.github/workflows/cache-cleanup.yml`
- `.github/dependabot.yml`
- Custom workflows with other names (e.g. `artifacts.yml`, GHCR publish workflows)

Keepalive workflows are no longer generated; delete stale `.github/workflows/keepalive.yml` on sync.

## Do Not Edit (repo-owned)

- `.github/workflows/push.yml` — never overwrite or regenerate
- `.github/workflows/release.yml` — each repo maintains publish/verify jobs
- Existing build/lint/test jobs in `pr.yml` — repo maintains them
- Semgrep placement in `pr.yml` (named **Code Quality** job, or a Semgrep step inside **Repository Checks**)
- `.semgrepignore`

## Goal

Run untrusted PR code in a **sandboxed** `pull_request` workflow. Auto-approve and auto-merge only **your PRs**, **Dependabot PRs**, and **Cursor automation** after CI (including Semgrep) succeeds, via a separate privileged workflow that never checks out PR code.

## Architecture

| File | Trigger | Runs PR code? |
|------|---------|---------------|
| `pr.yml` | `pull_request` only (no `workflow_dispatch`) | Yes (sandboxed; fork PRs have no repo secrets) |
| `pr.yml` → Semgrep | same workflow (named **Code Quality** job *or* a step in **Repository Checks**) | Yes (Semgrep OSS; repo-owned) |
| `pr-auto-merge.yml` | `workflow_run` after **Pull Request** (and same-SHA **E2E and User Manual** when registry `e2e_path_globs` match changed files) on `feature/**` or `dependabot/**` | **No** (GitHub API only) |

There is **no** separate `code-quality.yml` workflow.

## When To Patch `pr.yml` (dynamic phase)

Patch when **all** of:

1. Profile includes `ci-base`
2. `.github/workflows/pr.yml` exists
3. Any of: trigger is `pull_request_target`, checkout uses PR-head `ref:`, or `approve`/`merge` jobs are still present

Skip (report "pr.yml workflows untouched") when:

- No `pr.yml` exists — do not create one
- `pr.yml` already uses `pull_request`, has no approve/merge jobs, and checkouts do not force PR-head ref for privilege

## Allowed Edits In `pr.yml` (dynamic phase)

1. **`on:` trigger** — must be `pull_request` only (not `pull_request_target`, not `workflow_dispatch`).

2. **Checkout** — use default checkout (merge ref). **Remove** `ref: ${{ github.event.pull_request.head.ref }}` if present.

3. **Remove** `approve` and `merge` jobs entirely. They live in `pr-auto-merge.yml` (static sync).

Do **not** change action versions, matrices, Docker steps, caches, or terminal commands in existing CI jobs unless fixing a security issue.

## Preserve on `pr.yml` (cost-opt — do not strip)

Every fleet `pr.yml` already has this shape. Dynamic generation must leave it intact:

- hosted `filter` job and matching `*-skip` twins
- `if: github.event.pull_request.draft == false` on paid jobs
- `timeout-minutes` on jobs
- `concurrency` with `cancel-in-progress`
- `pull_request` types including `ready_for_review`
- docs filter using `git diff --name-status` (include deletes/renames)
- tetra node CI step order: `make image` → `make dependencies` → `make lint` → `make test` → `make build`

Do **not** add `workflow_dispatch` to `pr.yml`. Do **not** add `develop` to Push except **agoras-actions**. Do **not** add GHA Docker `type=gha` cache on tetra-linux. Do **not** insert `actions/cache` npm blocks on tetra (see `ci-npm-cache.md`).

## Forbidden (security)

- **`pull_request_target` for CI**
- **PR-head checkout under `pull_request_target`**
- **Approve/merge jobs in `pr.yml`**
- **Passing `secrets.GITHUB_TOKEN` or PAT into test/lint/tox env** on PR workflows

## Semgrep (repo-owned, verify-only)

Do **not** implement a missing named **Code Quality** job. Report placement; leave it where it is.

| Placement | Repos |
|-----------|-------|
| Named **Code Quality** job | agoras, agoras-actions, dockershelf, spices, luisalejandro.org |
| Semgrep step inside **Repository Checks** | helpmarket, morphile, nuncia, whol, wholmaster, wholmaster-website |

CollageLabs tetra-linux node repos keep Semgrep in **Repository Checks** for PR speed. Extracting it onto `ubuntu-24.04` slows the pipeline and changes required-check names.

Use `github.event.pull_request.base.sha` for baseline on PR workflows. Static sync does not inject Semgrep.

Do **not** run `protect-github --apply` during fleet sync. Required-check names now include **Filter** and skip twins that share display names; applying blindly is an operator decision.

## `pr-auto-merge.yml` (static sync)

Written by `rosey-maintain sync` from `templates/workflows/pr-auto-merge.yml.j2`.

Registry `overrides.e2e_path_globs` are baked into the workflow. Matching PR paths also require
a successful **E2E and User Manual** workflow run at the **same head SHA** before mutate.
Keep glob updates atomic with the app workflow paths those globs evaluate.

Do not duplicate approve/merge into `pr.yml`.

## Generation Order

Run `pr.yml` security patching **last**, after `.env.example`, Docker files, and Makefile work.

## Overwrite Policy

**Never** overwrite `pr.yml` or `push.yml` completely. Patch-only for CI trigger/checkout and removal of approve/merge jobs.

For `push.yml` release-branch CI, see `push-release-gate.md` (manual patch; whole Push workflow
at exact SHA — not a `Release Gate` job; not static sync).
