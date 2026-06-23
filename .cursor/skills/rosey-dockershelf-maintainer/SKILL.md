---
name: rosey-dockershelf-maintainer
description: Autonomously discovers upstream Python, Node, and Go versions, updates shelf lists under cap policy, regenerates the tree via update.py, then commits and pushes to develop. Use for periodic Dockershelf catalog maintenance, update-shelves, or shelf version bumps before a release. No manual version research required unless discovery fails. LaTeX is out of scope (fixed basic/full/extras variants).
argument-hint: "[optional mode:check-only or explicit add/remove overrides]"
---

# Rosey Dockershelf Maintainer

Autonomous shelf-catalog maintenance on `develop`: discover upstream versions, apply cap policy, regenerate the tree, commit, push. **Default:** invoke with no arguments — do not ask the user which versions to add.

**Out of scope:** git-flow release/hotfix (use [`rosey-release`](../rosey-release/SKILL.md)), debugging failed image builds, Docker Hub cleanup, local full-matrix builds.

## Communication

**Caveman lite** for workflow status. Normal prose for commit messages and user-facing summaries.

## Interaction mode

Parse `$ARGUMENTS` for at most one mode token:

| Token              | Effect                                                                               |
| ------------------ | ------------------------------------------------------------------------------------ |
| `mode:autonomous`  | **Default.** Run discovery, apply changes, regenerate, commit, push without prompts. |
| `mode:check-only`  | Run discovery and report; stop before editing files (no commit/push).                |
| `mode:interactive` | Run discovery, show planned add/remove, wait for user confirmation before apply.     |

Strip the mode token before parsing optional manual overrides (`add …` / `remove …`). Multiple mode tokens → stop and report conflict.

**Manual overrides:** If `$ARGUMENTS` contains explicit `add` / `remove` hints, skip discovery and apply those edits to `scripts/utils.py` by hand (still honor cap + oldest-drop). Use only when overriding autonomous discovery.

## Version source of truth

| Shelf  | Manual config                                       | Live / generated                                                                                       |
| ------ | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Python | `python_suites` in `scripts/utils.py`               | deadsnakes PPA (≥ 3.10); see `scripts/discover_shelf_versions.py`                                      |
| Node   | `node_suites` in `scripts/utils.py`                 | nodejs.org index + NodeSource repo probe (even LTS majors ≥ 16)                                        |
| Go     | `go_suites` in `scripts/utils.py`                   | golang telemetry minors; patches at regeneration                                                       |
| Debian | `debian_suites` in `scripts/utils.py` (suite names) | Codename per suite from `deb.debian.org` via `get_debian_versions()` (imported in `scripts/config.py`) |
| LaTeX  | `latex_versions` in `scripts/config.py`             | Fixed `basic`, `full`, `extras` — do not edit in this skill                                            |

**Rules:**

- Keep each list sorted (semver for Python/Go; numeric for Node).
- Do not edit generated per-version `Dockerfile`s or workflow YAML by hand — `update.py` owns them.
- Edit `*.template` files only when changing install strategy, not for routine version bumps.

## Version caps and retirement

Dockershelf supports a **fixed maximum** of concurrent versions per **runtime** shelf. The cap equals the **current list length** in `scripts/utils.py`. When adding a version would exceed the cap, **retire the oldest** (lowest semver / lowest numeric) in the **same change**.

| Shelf  | Max concurrent | List field      | Retirement                                    |
| ------ | -------------- | --------------- | --------------------------------------------- |
| Python | **5**          | `python_suites` | Drop oldest minor when adding a 6th           |
| Node   | **5**          | `node_suites`   | Drop oldest major when adding a 6th           |
| Go     | **6**          | `go_suites`     | Drop oldest minor when adding a 7th           |
| Debian | **4 suites**   | `debian_suites` | See Debian rules below — not a sliding window |

**Cap policy (enforced by discovery script):** keep the **N newest** buildable upstream versions (N = current list length). Adding a newer release drops the oldest automatically (e.g. Node 26 in → Node 16 out).

Changing a cap (e.g. Python 5 → 6) is a **policy change** — update this table, `scripts/utils.py`, and discovery caps together in one commit.

### Debian: `sid` is permanent

- `debian_suites` in `scripts/utils.py` must **always** include `'unstable'` (Debian codename `sid`).
- **Never** remove `'unstable'` from `debian_suites` during retirement or catalog cleanup.
- Language shelves (Python, Node, Go) build **two images per runtime**: stable-suite codename + unstable-suite codename (e.g. `3.14-trixie` and `3.14-sid`, with `FROM dockershelf/debian:trixie` / `dockershelf/debian:sid`). Docker tags also expose `-stable` / `-unstable` aliases. Retiring a runtime removes both its codename dirs; **sid as a Debian base stays** for all remaining versions.
- Do not manually delete `debian/sid/` or drop sid tags from the matrix — `update.py` regenerates it from `unstable` every run.
- `oldstable`, `stable`, and `testing` codenames roll with Debian releases via `get_debian_versions()`; only **sid / unstable** is the permanent Dockershelf anchor.

### LaTeX: fixed variants, passive updates

LaTeX is **not** part of add/remove maintenance in this skill.

- Always exactly three tags: `basic`, `full`, `extras` (`latex_versions` in `scripts/config.py`).
- **Do not** add, remove, or edit `latex_versions` during routine catalog work.
- `update_latex.py` always sets the base image to the tag `dockershelf/debian:stable` — never a Debian codename (e.g. not `dockershelf/debian:trixie`). Regenerating LaTeX Dockerfiles does not change that line.
- When Debian releases a new stable, the **contents** behind `dockershelf/debian:stable` are replaced when the debian shelf is rebuilt and that tag is pushed. LaTeX images pick up the new Debian on a **later** build that still `FROM dockershelf/debian:stable` (scheduled weekly rebuilds on `master`; matrix jobs run in parallel, so a single CI wave does not guarantee debian finishes before latex).
- `update.py` rewrites LaTeX Dockerfiles each run; the `FROM` line stays `dockershelf/debian:stable` unless templates change.
- Package freshness within LaTeX images also comes from those rebuilds, not from changing the variant list.

If the user asks to add/remove a LaTeX variant, stop — that is outside this skill unless they explicitly change project policy.

## Workflow

Copy and track:

```
- [ ] 1. Branch prep (develop)
- [ ] 2. Discover upstream versions
- [ ] 3. Apply shelf list updates
- [ ] 4. Regenerate tree
- [ ] 5. Review diff
- [ ] 6. Commit
- [ ] 7. Push develop
```

### 1. Branch prep

```bash
git fetch origin
git checkout develop
git pull origin develop
```

Stop if working tree has unrelated uncommitted changes unless the user explicitly wants them included.

### 2. Discover upstream versions

**Unless** `$ARGUMENTS` has manual `add` / `remove` overrides:

```bash
python3 -m pip install -r requirements.txt   # if needed
python3 -m scripts.discover_shelf_versions --json
```

Requires network (~1 min; deadsnakes PPA is slow). The script:

| Shelf  | Upstream source                                           |
| ------ | --------------------------------------------------------- |
| Python | deadsnakes PPA packages (≥ 3.10)                          |
| Node   | nodejs.org `index.json` + NodeSource `node_N.x` repo HEAD |
| Go     | golang telemetry `config.json` minors                     |

It compares upstream to `scripts/utils.py`, applies cap policy, and reports `add` / `remove` per shelf.

- **All shelves `changed: false`** and `mode:check-only` → report “up to date” and stop.
- **All shelves `changed: false`** otherwise → skip step 3, continue to step 4 (regenerate for incidental debian/go/latex drift).
- **Any `changed: true`** → proceed to step 3.

In `mode:interactive`, print the JSON report and wait for confirmation before step 3.

On discovery failure (network, parse error), report the error and stop — do not guess versions.

### 3. Apply shelf list updates

**Autonomous path** (no manual overrides):

```bash
python3 -m scripts.discover_shelf_versions --apply
```

This:

1. Writes recommended lists to `scripts/utils.py`
2. Extends `python/build-image.sh` elif chains when a new Python minor is in deadsnakes but not yet in the build script (e.g. `3.15`)

**Manual override path:** edit `scripts/utils.py` only (`python_suites`, `node_suites`, `go_suites`). Do not edit `scripts/config.py` or `latex_versions`.

**Never:** remove `'unstable'` from `debian_suites` or retire Debian sid.

### 4. Regenerate tree

**Preferred** (matches maintainer Makefile):

```bash
make update-shelves
```

Requires Docker. Builds/starts the dev container, then runs `python3 update.py` inside it.

**Fallback** (no Docker):

```bash
python3 -m pip install -r requirements.txt
python3 update.py
```

Requires network (Debian Release files, golang telemetry JSON).

`update.py` regenerates:

- `debian/`, `python/`, `node/`, `go/`, `latex/` — per-version `Dockerfile`s and shelf `README.md`
- Root `README.md` from `README.md.template`
- `.github/workflows/trigger-develop.yml`, `clean-develop.yml`, `push-master.yml`, `clean-master.yml`, `schedule-master.yml` from their `*.template` files

Re-run until exit 0. On failure, report stderr; do not commit partial regeneration.

### 5. Review diff

Confirm:

- Version list edits match intent
- New version dirs appear; removed version dirs are gone
- Workflow matrix entries match new/removed images
- Incidental `debian/` or `go/` changes are expected (codename roll-forward, Go patch bumps) — not mistaken for mistakes
- No edits outside regenerated catalog files

Optional re-run:

```bash
python3 update.py
git diff
```

PR CI only checks that `update.py` **exits 0** — it does not fail on a dirty tree. Locally, a second run may still produce diff if Go telemetry or Debian metadata changed between runs; that is normal.

### 6. Commit

Stage `scripts/utils.py`, `python/build-image.sh` (if discovery extended it), and all regenerated files. Do not stage unrelated changes or `scripts/config.py` unless edited for an unrelated reason.

**Message style** (match `HISTORY.md`):

```
Adding support for <new versions>. Removing support for <removed versions>.
```

Omit the removing clause if nothing was removed. One or two sentences, focus on why.

```bash
git add scripts/utils.py python/build-image.sh \
  debian/ python/ node/ go/ latex/ \
  README.md .github/workflows/trigger-develop.yml \
  .github/workflows/clean-develop.yml .github/workflows/push-master.yml \
  .github/workflows/clean-master.yml .github/workflows/schedule-master.yml

git commit -m "$(cat <<'EOF'
<commit message>

EOF
)"
```

Use `-S` only if the repo convention on this branch expects signed commits.

### 7. Push develop

```bash
git push origin develop
```

Report push result. `pr.yml` runs `update.py` only on **pull requests** to `develop` (exit-code check, not committed-output diff). Direct pushes to `develop` skip it — local regeneration in step 3 is mandatory. Pushing `develop` does **not** trigger image builds (`trigger-develop.yml` is manual `workflow_dispatch` only).

## Argument hints

| Pattern                              | Action                                                                        |
| ------------------------------------ | ----------------------------------------------------------------------------- |
| _(empty)_                            | Full autonomous run (discover → apply if needed → regenerate → commit → push) |
| `mode:check-only`                    | Discovery report only                                                         |
| `add python 3.15` / `remove node 16` | Skip discovery; manual override (honor cap policy)                            |
| `add latex …` / `remove latex …`     | **Reject** — LaTeX variants are fixed                                         |

## Handoff

When done, report:

- Discovery summary (upstream vs recommended; or “up to date”)
- Versions added/removed per shelf
- Regeneration method used (`make update-shelves` vs `python3 update.py`)
- Commit hash and `origin/develop` push status
- Reminder: shelf changes reach Docker Hub production tags only after [`rosey-release`](../rosey-release/SKILL.md) publishes and the release merges to `master`

## Additional resources

- Shelf regeneration details: [reference.md](reference.md)
- Release publishing (not this skill): [`rosey-release`](../rosey-release/SKILL.md)
