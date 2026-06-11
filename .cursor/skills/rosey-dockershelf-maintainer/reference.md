# Dockershelf shelf regeneration reference

## How `update.py` works

Entry point: `update.py` (repo root). Imports updaters from `scripts/`:

| Module | Input | Output |
|--------|-------|--------|
| `update_debian` | `debian_versions` from live Debian Release files | `debian/<codename>/Dockerfile`, debian README/matrix |
| `update_latex` | Fixed `latex_versions` (`basic`, `full`, `extras`) | `latex/<variant>/Dockerfile`, latex README/matrix |
| `update_python` | `python_versions` × stable/unstable Debian codenames | `python/<ver>-<codename>/Dockerfile`, python README/matrix |
| `update_node` | `node_versions` × stable/unstable | `node/<ver>-<codename>/Dockerfile`, node README/matrix |
| `update_go` | `go_versions` (patch from telemetry, filtered by `go_suites`) × stable/unstable | `go/<minor>-<codename>/Dockerfile`, go README/matrix |

Each updater:

1. Deletes existing version subdirs under the shelf folder
2. Recreates `Dockerfile` from `Dockerfile.template` with placeholders substituted
3. Rebuilds shelf `README.md` from `README.md.template`
4. Returns GitHub Actions matrix lines consumed by `update.py`

`update.py` then substitutes `%%MATRIX%%` into workflow templates and `%%*_TABLE%%` into root `README.md.template`.

## Stable vs unstable images

Language shelves build two variants per version:

- **Stable** — Debian codename for `stable` suite (e.g. `trixie`)
- **Unstable** — Debian codename for `unstable` suite (`sid`)

Debian shelf: `debian_suites` in `scripts/utils.py` is a **fixed** list of four suite names (`oldstable`, `stable`, `testing`, `unstable`). `get_debian_versions()` resolves each suite to its current codename at `scripts/config.py` import time (network call). Output dirs are `debian/<codename>/` (e.g. `debian/trixie/`, `debian/sid/`).

## Version caps (retirement policy)

Maximum concurrent versions per **runtime** shelf (current policy):

| Shelf | Max |
|-------|-----|
| Python | 5 |
| Node | 5 |
| Go | 6 |

When adding would exceed the cap, remove the **oldest** list entry first, then append the new one. Retirement is by **slot count**, not upstream EOL calendars.

**Debian sid is permanent:** `debian_suites` must always include `'unstable'` (`sid`). Never remove it. Retiring a Python/Node/Go version removes that runtime’s stable and sid images, but sid remains the unstable base for every other version.

## LaTeX (fixed, not catalog-managed)

- Three permanent variants: `basic`, `full`, `extras` — never add or remove in maintainer catalog work.
- `update_latex.py` always substitutes `%%BASE_IMAGE%%` with the tag `dockershelf/debian:stable` — not a codename-specific tag.
- When Debian releases a new stable, `dockershelf/debian:stable` is rebuilt and repointed when the debian matrix job pushes that tag. LaTeX `FROM dockershelf/debian:stable` is unchanged; a later LaTeX build pulls whatever that tag currently points to. Scheduled matrix jobs are parallel — debian and latex do not have an explicit depends-on in CI.
- `update.py` rewrites full LaTeX Dockerfiles each run; only the base tag line is stable across Debian promotions unless templates change.
- TeX Live / apt package versions refresh on scheduled image rebuilds, not by changing the variant list or `latex_versions`.

## Upstream discovery (`scripts/discover_shelf_versions.py`)

Autonomous catalog updates. Run from repo root:

```bash
python3 -m scripts.discover_shelf_versions          # human report
python3 -m scripts.discover_shelf_versions --json   # machine report
python3 -m scripts.discover_shelf_versions --apply  # write utils.py + extend python/build-image.sh
```

| Shelf | Source | Notes |
|-------|--------|-------|
| Python | deadsnakes PPA `Packages.gz` (jammy + noble) | Minors ≥ 3.10; extends `python/build-image.sh` on `--apply` |
| Node | nodejs.org `index.json` + NodeSource repo HEAD | Even majors ≥ 16 with a `node_N.x` repo |
| Go | golang telemetry `config.json` | All published minors; cap picks newest N |

Cap policy: `recommended = upstream_sorted[-cap:]` where `cap = len(current_list)`.

## Go patch resolution

`get_go_versions()` fetches `golang/telemetry` `config.json`, keeps the highest patch per minor listed in `go_suites`. Adding `1.26` to `go_suites` is enough; patch version is resolved at regeneration time.

## PR CI contract

`.github/workflows/pr.yml` runs `python3 update.py` on pull requests to `develop` and passes if the command exits 0. It does **not** compare regenerated output to the committed tree. Direct pushes to `develop` do not run this workflow.

## Incidental diffs on every regeneration

Even when only `python_suites` / `node_suites` / `go_suites` change:

- `debian/` — always regenerated from live Release files
- `latex/` — always regenerated (fixed three variants)
- `go/` — patch in `GO_VER_NUM` / labels may bump when golang telemetry updates

Include these in the maintainer commit when `git diff` shows them.

## What this skill does not fix

If `schedule-master` fails after catalog update due to upstream packaging (deadsnakes, go.dev tarballs, apt renames), patch `*/build-image.sh` or `Dockerfile.template` in a separate change — not part of catalog-only maintenance.
