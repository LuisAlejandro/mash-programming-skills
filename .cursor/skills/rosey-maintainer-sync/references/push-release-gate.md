# Push Workflow — Release Gate (Manual Patch)

Static `rosey-maintain sync` does **not** write `.github/workflows/push.yml`. Patch each repo manually so `release.sh` Gate 3 can wait on the **Release Gate** job.

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

2. Append a terminal job after all existing CI jobs:

```yaml
  release-gate:
    name: Release Gate
    runs-on: ubuntu-24.04
    needs: [<final_ci_job>]
    steps:
      - name: Confirm all release checks passed
        run: |
          echo "Release gate passed for ${{ github.ref_name }}"
```

3. Set `needs:` to the **last** CI job in the workflow (before approve/merge if those exist in `pr.yml` only — `push.yml` typically ends with `build`, `checks`, or `finish`).

4. Bump all `runs-on: ubuntu-22.04` → `ubuntu-24.04` in `push.yml` while editing.

## Reference

Canonical full example: read-only [`Development/agoras/.github/workflows/push.yml`](file:///Users/luisalejandro/Development/agoras/.github/workflows/push.yml) (`needs: finish`).

Fleet target to update: [`rosey/agoras`](file:///Users/luisalejandro/Development/rosey/agoras) — copy/adapt from reference; do not edit the reference tree.

## Common `needs` Values

| Repo pattern | Typical final job |
|--------------|-------------------|
| agoras (full CI) | `finish` |
| dockershelf, simple matrix | `build` |
| nuncia, whol, helpmarket | `checks` or `build` |
| wholmaster (multi-job) | last job in chain |

## Verification

```bash
grep -E 'release/\*\*|release-gate' .github/workflows/push.yml
```
