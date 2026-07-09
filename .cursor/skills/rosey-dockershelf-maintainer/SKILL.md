---
name: rosey-dockershelf-maintainer
description: Autonomously maintains Dockershelf catalogs: discovers upstream Python, Node, and Go versions, handles Debian release rolls when a new Debian stable is released, updates shelf lists and APT-suite metadata, regenerates the tree via update.py, then commits and pushes to develop. Use for periodic Dockershelf catalog maintenance, update-shelves, Debian stable/testing rolls, or shelf version bumps before a release. LaTeX is fixed basic/full/extras only.
argument-hint: "[optional mode:check-only or explicit add/remove overrides; optional debian-release:<new-stable-codename>]"
---

# Rosey Dockershelf Maintainer

Autonomous shelf-catalog maintenance on `develop`: discover upstream runtime versions, handle Debian release rolls when live Debian suites move, apply cap policy, regenerate the tree, commit, push. **Default:** invoke with no arguments — do not ask the user which versions to add.

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

Strip the mode token before parsing optional manual overrides (`add …` / `remove …`) or optional `debian-release:<new-stable-codename>` hints. Multiple mode tokens → stop and report conflict.

**Manual overrides:** If `$ARGUMENTS` contains explicit `add` / `remove` hints, skip discovery and apply those edits to `scripts/utils.py` by hand (still honor cap + oldest-drop). Use only when overriding autonomous discovery.

**Debian release hint:** If `$ARGUMENTS` contains `debian-release:<codename>`, still verify live Debian suite metadata and APT repo readiness. Treat the hint as expected stable codename, not as proof.

## Version source of truth

| Shelf  | Manual config                                       | Live / generated                                                                                       |
| ------ | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Python | `python_suites` in `scripts/utils.py`               | Dockershelf APT `python3.X` packages; see `scripts/discover_shelf_versions.py`                         |
| Node   | `node_suites` in `scripts/utils.py`                 | Dockershelf APT `nodejs-XX` packages (even LTS majors ≥ 16)                                            |
| Go     | `go_suites` in `scripts/utils.py`                   | Dockershelf APT `golang-X.Y-go` packages; patch versions resolved from APT at regeneration             |
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
| Go     | **5**          | `go_suites`     | Drop oldest minor when adding a 6th           |
| Debian | **4 suites**   | `debian_suites` | See Debian rules below — not a sliding window |

**Cap policy (enforced by discovery script):** keep the **N newest** buildable upstream versions (N = current list length). Adding a newer release drops the oldest automatically (e.g. Node 26 in → Node 16 out).

Changing a cap (e.g. Python 5 → 6) is a **policy change** — update this table, `scripts/utils.py`, and discovery caps together in one commit.

### Debian: `sid` is permanent

- `debian_suites` in `scripts/utils.py` must **always** include `'unstable'` (Debian codename `sid`).
- **Never** remove `'unstable'` from `debian_suites` during retirement or catalog cleanup.
- Language shelves (Python, Node, Go) build **two images per runtime**: stable-suite codename + unstable-suite codename (e.g. `3.14-trixie` and `3.14-sid`, with `FROM dockershelf/debian:trixie` / `dockershelf/debian:sid`). Docker tags also expose `-stable` / `-unstable` aliases. Retiring a runtime removes both its codename dirs; **sid as a Debian base stays** for all remaining versions.
- Do not manually delete `debian/sid/` or drop sid tags from the matrix — `update.py` regenerates it from `unstable` every run.
- `oldstable`, `stable`, and `testing` codenames roll with Debian releases via `get_debian_versions()`; only **sid / unstable** is the permanent Dockershelf anchor.

### Debian release rolls

A new Debian version is a **suite promotion**, not a fifth Debian entry. When Debian promotes testing to stable:

- `oldstable` becomes the previous `stable` codename.
- `stable` becomes the previous `testing` codename.
- `testing` becomes the new codename.
- `unstable` stays `sid`.

Example: if `forky` becomes stable, `bookworm` disappears from generated Debian outputs, `trixie` becomes oldstable, `forky` becomes stable, the next codename becomes testing, and `sid` stays unstable.

Required manual inputs around a Debian release:

- `debian_suites` stays `['oldstable', 'stable', 'testing', 'unstable']`; do not add the new codename there.
- Update the Dockershelf APT scan suites from old stable codename to new stable codename in both places:
  - `DOCKERSHELF_APT_SUITES` in `scripts/discover_shelf_versions.py`
  - `dockershelf_apt_suites` in `scripts/utils.py`
- Update `scripts/build-all-images.sh` `get_debian_suite()` codename mapping so local all-image builds classify oldstable/stable/testing correctly.
- Before regenerating, verify `https://apt.dockershelf.com/dockershelf/dists/<new-stable-codename>/main/binary-amd64/Packages.gz` exists. Runtime image builds use the stable codename directly in their APT source; discovery will be incomplete until the dist exists.
- Do not change LaTeX variants. LaTeX continues `FROM dockershelf/debian:stable`; it picks up the new stable only after that tag is rebuilt and pushed.

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

```text
- [ ] 1. Branch prep (develop)
- [ ] 2. Discover upstream versions
- [ ] 3. Detect Debian release roll
- [ ] 4. Apply shelf list and Debian metadata updates
- [ ] 5. Regenerate tree
- [ ] 6. Review diff
- [ ] 7. Commit
- [ ] 8. Push develop
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

Requires network. The script:

| Shelf  | Upstream source                                      |
| ------ | ---------------------------------------------------- |
| Python | Dockershelf APT `python3.X` packages (≥ 3.10)        |
| Node   | Dockershelf APT `nodejs-XX` packages (even, ≥ 16)    |
| Go     | Dockershelf APT `golang-X.Y-go` packages             |

It scans `DOCKERSHELF_APT_SUITES`, compares upstream to `scripts/utils.py`, applies cap policy, and reports `add` / `remove` per shelf. Debian codenames are **not** discovered here.

- **All shelves `changed: false`** → continue to step 3 before deciding whether to stop.
- **Any `changed: true`** → proceed to step 3.

In `mode:interactive`, print the JSON report and wait for confirmation before step 3.

On discovery failure (network, parse error), report the error and stop — do not guess versions.

### 3. Detect Debian release roll

Always check live Debian suites before deciding “up to date”:

```bash
python3 - <<'PY'
from scripts.utils import get_debian_versions

for codename, suite in get_debian_versions():
    print(f'{suite}: {codename}')
PY
```

Compare the live `stable` codename to the first element of both Dockershelf APT suite tuples:

- `DOCKERSHELF_APT_SUITES` in `scripts/discover_shelf_versions.py`
- `dockershelf_apt_suites` in `scripts/utils.py`

If live `stable` differs, a Debian release roll is in scope. Continue even if Python/Node/Go discovery reports no changes.

For `debian-release:<codename>`, require live `stable == <codename>`. If not, stop and report that Debian has not promoted yet.

If `mode:check-only`, report the runtime discovery plus Debian suite status and stop after this step.

### 4. Apply shelf list and Debian metadata updates

**Autonomous path** (no manual overrides):

```bash
python3 -m scripts.discover_shelf_versions --apply
```

This writes recommended Python, Node, and Go lists to `scripts/utils.py`.

**Manual override path:** edit `scripts/utils.py` only (`python_suites`, `node_suites`, `go_suites`). Do not edit `scripts/config.py` or `latex_versions`.

**Debian release-roll path:** after discovery/apply, make these hand edits before regeneration:

1. In `scripts/discover_shelf_versions.py`, set `DOCKERSHELF_APT_SUITES = ('<live-stable-codename>', 'unstable')`.
2. In `scripts/utils.py`, set `dockershelf_apt_suites = ('<live-stable-codename>', 'unstable')`.
3. In `scripts/build-all-images.sh`, update `get_debian_suite()` so:
   - previous oldstable codename is removed
   - previous stable codename maps to `oldstable`
   - live stable codename maps to `stable`
   - live testing codename maps to `testing`
   - `sid` maps to `unstable`
4. Probe the new Dockershelf APT dist before regeneration:

```bash
python3 - <<'PY'
import gzip
from urllib.request import urlopen

codename = '<live-stable-codename>'
url = f'https://apt.dockershelf.com/dockershelf/dists/{codename}/main/binary-amd64/Packages.gz'
with urlopen(url, timeout=30) as response:
    gzip.decompress(response.read())
print(f'OK: {url}')
PY
```

If the new APT dist is missing, stop and report the blocker. Do not regenerate language shelves against a stable codename whose Dockershelf APT packages are unavailable.

**Never:** remove `'unstable'` from `debian_suites`, retire Debian sid, or add codename literals to `debian_suites`.

### 5. Regenerate tree

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

Requires network (Debian Release files and Dockershelf APT package indexes).

`update.py` regenerates:

- `debian/`, `python/`, `node/`, `go/`, `latex/` — per-version `Dockerfile`s and shelf `README.md`
- Root `README.md` from `README.md.template`
- `.github/workflows/trigger-develop.yml`, `clean-develop.yml`, `push-master.yml`, `clean-master.yml`, `schedule-master.yml` from their `*.template` files

Re-run until exit 0. On failure, report stderr; do not commit partial regeneration.

### 6. Review diff

Confirm:

- Version list edits match intent
- New version dirs appear; removed version dirs are gone
- For Debian release rolls:
  - previous oldstable codename dirs are deleted
  - previous stable codename remains only as Debian oldstable output, not as language stable output
  - live stable codename becomes Debian stable and all Python/Node/Go stable image dirs
  - live testing codename appears under `debian/` only
  - `debian/sid/` and all runtime `*-sid` dirs remain
  - `stable` / `latest-stable` aliases now point at the live stable codename in workflow matrices and README tag tables
- Workflow matrix entries match new/removed images
- Incidental `debian/` or `go/` changes are expected (codename roll-forward, Go patch bumps) — not mistaken for mistakes
- No edits outside regenerated catalog files

Optional re-run:

```bash
python3 update.py
git diff
```

PR CI only checks that `update.py` **exits 0** — it does not fail on a dirty tree. Locally, a second run may still produce diff if Go telemetry or Debian metadata changed between runs; that is normal.

### 7. Commit

Stage `scripts/utils.py`, `scripts/discover_shelf_versions.py`, `scripts/build-all-images.sh` (only when edited for a Debian release roll), `python/build-image.sh` (if discovery extended it), and all regenerated files. Do not stage unrelated changes or `scripts/config.py` unless edited for an unrelated reason.

**Message style** (match `HISTORY.md`):

```text
Adding support for <new versions>. Removing support for <removed versions>.
```

Omit the removing clause if nothing was removed. One or two sentences, focus on why.

For Debian release rolls, prefer:

```text
Adding support for Debian <new-stable-codename>. Removing support for Debian <dropped-oldstable-codename>.
```

```bash
git add scripts/utils.py scripts/discover_shelf_versions.py \
  scripts/build-all-images.sh python/build-image.sh \
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

### 8. Push develop

```bash
git push origin develop
```

Report push result. `pr.yml` runs `update.py` only on **pull requests** to `develop` (exit-code check, not committed-output diff). Direct pushes to `develop` skip it — local regeneration in step 5 is mandatory. Pushing `develop` does **not** trigger image builds (`trigger-develop.yml` is manual `workflow_dispatch` only).

## Argument hints

| Pattern                              | Action                                                                        |
| ------------------------------------ | ----------------------------------------------------------------------------- |
| _(empty)_                            | Full autonomous run (discover → apply if needed → regenerate → commit → push) |
| `mode:check-only`                    | Discovery report only                                                         |
| `add python 3.15` / `remove node 16` | Skip discovery; manual override (honor cap policy)                            |
| `debian-release:forky`               | Verify live Debian stable is `forky`; apply Debian release-roll steps         |
| `add latex …` / `remove latex …`     | **Reject** — LaTeX variants are fixed                                         |

## Handoff

When done, report:

- Discovery summary (upstream vs recommended; or “up to date”)
- Debian suite summary (`oldstable`, `stable`, `testing`, `unstable`) and whether a release roll was applied
- Versions added/removed per shelf
- Regeneration method used (`make update-shelves` vs `python3 update.py`)
- Commit hash and `origin/develop` push status
- Reminder: shelf changes reach Docker Hub production tags only after [`rosey-release`](../rosey-release/SKILL.md) publishes and the release merges to `master`

## Additional resources

- Shelf regeneration details: [reference.md](reference.md)
- Release publishing (not this skill): [`rosey-release`](../rosey-release/SKILL.md)
