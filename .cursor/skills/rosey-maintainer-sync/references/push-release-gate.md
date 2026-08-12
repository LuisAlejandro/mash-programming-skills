# Push Workflow — Whole-Run Release Gate (Manual Patch)

Static `rosey-maintain sync` does **not** write `.github/workflows/push.yml`.
Patch each repo manually so `scripts/lib.sh` `release_wait_for_branch_ci` can wait on the
**entire Push workflow** at the exact release-branch SHA.

Do **not** add a job named `Release Gate`. Release tooling discovers the workflow by name
(`Push` / `push.yml` via `RELEASE_CI_WORKFLOW`) and `--commit "$commit_sha"`.

## When Required

Repos with `ops-release` bundle (or any repo using `scripts/release.sh` + `release_wait_for_branch_ci`).

## Patch Steps

1. Add `release/**` to `on.push.branches` (keep existing branches):

```yaml
on:
  push:
    branches:
      - master
      - develop
      - "release/**"
```

2. Ensure the Push workflow's CI jobs run on `release/**` the same way they run on `develop`
   (same job names / required checks you want Gate 3 to observe).

3. Bump all `runs-on: ubuntu-24.04` → `ubuntu-24.04` in `push.yml` while editing (or route
   Linux jobs to `tetra-linux` for Tetra cutovers).

4. Confirm `scripts/lib.sh` waits on the whole workflow + exact SHA (synced template):

```bash
grep -E 'RELEASE_CI_WORKFLOW|--commit "\$commit_sha"|Release Gate' scripts/lib.sh
# expect: workflow + commit present; no Release Gate job name
```

## Rollback

`scripts/rollback.sh` cancels matching non-terminal **Push**, **Publish Release**, and
**Artifacts** runs for the release branch and version tag, waits for terminal status, then
deletes refs. Do not delete tags/branches before cancel-wait completes.

## Verification

```bash
grep -E 'release/\*\*' .github/workflows/push.yml
grep -E 'release_wait_for_branch_ci|release_cancel_matching_runs' scripts/lib.sh scripts/rollback.sh
```
