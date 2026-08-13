# CI npm cache (verify-only)

Dynamic generation **must not** insert `actions/cache` or GHA Docker layer cache. Report what
exists; leave it.

## Tetra (self-hosted `tetra-linux`)

Docker layers persist on the runner disk between jobs. Do **not**:

- add `actions/cache` for `~/.npm` or `node_modules` on `pr.yml` / `push.yml`
- add Buildx `cache-from` / `cache-to` `type=gha`
- replace `actions/setup-node` with `package-manager-cache: false` (valid on tetra; e.g. wholmaster)

`mkdir -p ~/.npm` is enough when Compose bind-mounts that path into the container.

## GitHub-hosted jobs

If a hosted job already restores `~/.npm` via `actions/cache`, leave it. Do not add a cache
block because this file exists. `release.yml` is repo-owned, not template-synced.

## Why this is verify-only

Adding GHA cache on tetra uploads and downloads bytes on top of a cache that already lives on
the runner. That usually costs more than it saves.

## Report

- npm / Docker cache present (Y/N)
- runner: tetra-linux or ubuntu-hosted
- caches added this pass: **none** (required)
