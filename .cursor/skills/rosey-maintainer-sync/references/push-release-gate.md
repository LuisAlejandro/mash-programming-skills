# Push Workflow — Whole-Run Release Gate (Manual Patch)

Static `rosey-maintain sync` does **not** write `.github/workflows/push.yml`.
Patch each repo manually so `scripts/lib.sh` `release_wait_for_branch_ci` can wait on the
**entire Push workflow** at the exact release-branch SHA.

Do **not** add a job named `Release Gate`. Release tooling discovers the workflow by name
(`Push` / `push.yml` via `RELEASE_CI_WORKFLOW`) and `--commit "$commit_sha"`.

Dynamic generation **must not** edit `push.yml`. This file is for operator/manual patches only.

## When Required

Repos with `ops-release` bundle (or any repo using `scripts/release.sh` + `release_wait_for_branch_ci`).

## Shipped `on.push.branches` (do not re-add `develop`)

Duplicate Push CI on `develop` was removed as a cost lever. Keep the shipped lists:

| Repos | `on.push.branches` |
|-------|-------------------|
| Default (agoras, spices, helpmarket, luisalejandro.org, morphile, nuncia, whol, wholmaster, wholmaster-website) | `master`, `release/**` |
| dockershelf | `release/**` only |
| agoras-actions | `develop`, `master`, `release/**` (GHCR exception) |

Do **not** add `develop` back to the nine default repos or dockershelf.

## Patch Steps

1. Ensure `release/**` is in `on.push.branches` (keep the shipped list above; do not invent `develop`):

```yaml
# default nine repos
on:
  push:
    branches: [master, "release/**"]
```

2. Ensure the Push workflow's CI jobs run on `release/**` the same way they run on `master`
   (same job names / required checks you want Gate 3 to observe).

3. Bump leftover `runs-on: ubuntu-22.04` → `ubuntu-24.04` in `push.yml` while editing (or route
   Linux jobs to `tetra-linux` for Tetra cutovers). Do not add GHA Docker `type=gha` cache on tetra.

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
