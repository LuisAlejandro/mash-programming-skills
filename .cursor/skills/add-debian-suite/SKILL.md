---
name: add-debian-suite
description: "Add a new Debian suite/codename to the Dockershelf packaging pipeline (Python, Node.js, Go). Use when Debian releases a new stable, trixie becomes oldstable, adding forky, adding a new Debian distro/suite, suite transition, updating DOCKERSHELF_SUITES, regenerating builder images, or extending reprepro. Seeds debiandirs/changelogs, updates CI dists-json, APT config, and optionally shifts active targets away from the old suite. Does NOT delete packages from the APT repository."
argument-hint: 'New suite codename and optional source suite (e.g., forky from trixie)'
---

# Add Debian Suite to Dockershelf Pipeline

**Purpose:** Add a new Debian codename (e.g. `forky`) across all three language pipelines and every active packaging repo, then optionally shift CI/build targets away from the previous suite when it becomes oldstable.

**Scope:** Suite addition and target shift. Does **not** delete published APT packages.

**Out of scope:** Discovering Debian release dates. Assume the new codename is already known.

---

## When to Use

- Debian is about to release (or has released) a new stable
- Dockershelf images will target a new Debian base (e.g. `forky`)
- `trixie` (or another suite) is becoming oldstable and you need the next suite online
- You need builder images, CI `dists-json`, and APT `reprepro` updated for a new codename

## What This Skill Does

1. Seeds `debiandirs/<new>/` and `changelogs/mainline/<new>` in every active `py*`, `node*`, `go*` repo
2. Updates pipeline templates so newly seeded repos include the suite
3. Updates `DOCKERSHELF_SUITES` (Makefile defaults + `config.env.example` + local `config.env`)
4. Regenerates and builds suite builder Dockerfiles/images
5. Extends `reprepro-distributions` and deploys to the APT droplet
6. Updates CI `dists-json` in templates and every language-version `main.yml`
7. Smoke-builds and publishes packages for the new suite
8. Optionally shifts active targets (drop old suite from CI/config) without deleting APT packages

## What This Skill Does NOT Do

- Delete packages from the APT repository
- Automatically retire language versions (use `retire-version` for that)
- Change downstream Dockershelf consumer image repos (announce separately)

---

## Prerequisites

Confirm before starting:

1. **New codename known** — e.g. `forky` (argument: `{NEW}`)
2. **Source suite** — usually current stable/testing target, e.g. `trixie` (argument: `{FROM}`)
3. **Workspace** — `dockershelf-pipeline/` with sibling `py*`, `node*`, `go*` repos and `*-pipeline/` dirs
4. **Active versions** — read from each pipeline Makefile (`PY_VERSIONS`, `NODE_VERSIONS`, `GO_VERSIONS`); only touch those
5. **Maintainer identity** — `DEBFULLNAME` / `DEBEMAIL` set for changelog edits
6. **Droplet access** — SSH to deploy `conf/distributions` when extending APT

**Placeholders used below:**

| Placeholder | Meaning | Example |
|-------------|---------|---------|
| `{NEW}` | New Debian codename | `forky` |
| `{FROM}` | Suite to copy from | `trixie` |

---

## Complete Workflow

Copy this checklist and track progress:

```
Task Progress:
- [ ] Step 0: Inventory active versions and current suites
- [ ] Step 1: Seed packaging repos (debiandirs + changelogs)
- [ ] Step 2: Update pipeline templates
- [ ] Step 3: Update DOCKERSHELF_SUITES config
- [ ] Step 4: Regenerate builder Dockerfiles and images
- [ ] Step 5: Extend APT reprepro distributions
- [ ] Step 6: Update CI dists-json (templates + all version repos)
- [ ] Step 7: Materialize, build, smoke, publish for {NEW}
- [ ] Step 8: Verify
- [ ] Step 9 (optional later): Shift targets / drop {FROM}
- [ ] Step 10: Announce downstream
```

### Step 0: Inventory

```bash
cd dockershelf-pipeline

# Active versions (source of truth)
grep -E '^(PY|NODE|GO)_VERSIONS' python-pipeline/Makefile node-pipeline/Makefile go-pipeline/Makefile

# Current suites in one packaging repo
ls py3.14/debiandirs py3.14/changelogs/mainline
```

Confirm `{FROM}` exists and `{NEW}` does not yet.

### Step 1: Seed Packaging Repos

For **each** active version repo (`py3.XX`, `nodeXX`, `go1.XX`):

```bash
REPO=py3.14   # repeat for every active version
cd "$REPO"

cp -a "debiandirs/{FROM}" "debiandirs/{NEW}"
# Review Build-Depends in debiandirs/{NEW}/control and control.in if present

cp "changelogs/mainline/{FROM}" "changelogs/mainline/{NEW}"
# Edit changelogs/mainline/{NEW}:
#   - distribution field: {FROM} → {NEW}
#   - version suffix: +{FROM}N → +{NEW}1  (reset rebuild counter)
#   - add a short entry explaining the suite seed if needed

git add debiandirs/{NEW} changelogs/mainline/{NEW}
git commit -m "Add {NEW} Debian suite packaging"
# Push when ready: git push origin main
```

**Changelog edit pattern** (example for Python):

```text
# Before (copied from trixie):
python3.14 (3.14.6-1+trixie2) trixie; urgency=medium

# After (forky seed):
python3.14 (3.14.6-1+forky1) forky; urgency=medium

  * Seed forky suite from trixie packaging.
```

Apply the same distribution + `+{NEW}1` suffix rules for Node (`nodejs-…`) and Go (`golang-…`) changelogs.

**Node note:** Ops docs may mention `changelogs/nightly/`; current repos use `changelogs/mainline/` only. Mirror whatever directories already exist for `{FROM}`.

### Step 2: Update Pipeline Templates

Keep newly seeded repos consistent. In each template tree, copy the same suite files:

```bash
# Python
cp -a python-pipeline/templates/py-packaging/debiandirs/{FROM} \
      python-pipeline/templates/py-packaging/debiandirs/{NEW}
cp python-pipeline/templates/py-packaging/changelogs/mainline/{FROM} \
   python-pipeline/templates/py-packaging/changelogs/mainline/{NEW}
# Edit template changelog distribution + +{NEW}1 suffix (placeholders OK if template uses them)

# Node
cp -a node-pipeline/templates/node-packaging/debiandirs/{FROM} \
      node-pipeline/templates/node-packaging/debiandirs/{NEW}
cp node-pipeline/templates/node-packaging/changelogs/mainline/{FROM} \
   node-pipeline/templates/node-packaging/changelogs/mainline/{NEW}

# Go
cp -a go-pipeline/templates/go-packaging/debiandirs/{FROM} \
      go-pipeline/templates/go-packaging/debiandirs/{NEW}
cp go-pipeline/templates/go-packaging/changelogs/mainline/{FROM} \
   go-pipeline/templates/go-packaging/changelogs/mainline/{NEW}
```

### Step 3: Update `DOCKERSHELF_SUITES`

During the **overlap** period (both old and new active), set:

```bash
DOCKERSHELF_SUITES={FROM} unstable {NEW}
```

Update in **all three** pipelines:

1. `{lang}-pipeline/Makefile` — `export DOCKERSHELF_SUITES ?= …`
2. `{lang}-pipeline/config.env.example`
3. `{lang}-pipeline/config.env` (local, if present)
4. Default fallbacks in `{lang}-pipeline/scripts/ci-pull-builder-images.sh` (`SUITES="${DOCKERSHELF_SUITES:-…}"`)

### Step 4: Regenerate Builder Images

For each pipeline:

```bash
cd python-pipeline   # then node-pipeline, go-pipeline
make generate-dockerfiles
make build-builder-images
# CI: push builder-images workflow so GHCR gets dockershelf-*-builder/{NEW}
```

Expect new files such as `dockerfiles/Dockerfile.{NEW}` and images `dockershelf-{lang}-builder/{NEW}`.

### Step 5: Extend APT Repository

Edit each pipeline’s `debian-repo-setup/reprepro-distributions` (keep them in sync; the droplet uses one `conf/distributions`).

Add a stanza modeled on the existing `{FROM}` block:

```text
Origin: Dockershelf
Label: Dockershelf
Suite: stable
Codename: {NEW}
Architectures: amd64 arm64 source
Components: main
Description: Dockershelf packages for Debian {NEW} (Python, Node.js, Go, …)
SignWith: SIGNWITH_KEY_ID
```

Deploy to the droplet:

```bash
# After substituting the real SignWith key id:
scp debian-repo-setup/reprepro-distributions deploy@apt.dockershelf.com:/tmp/distributions
ssh deploy@apt.dockershelf.com 'sudo cp /tmp/distributions /var/www/debian/conf/distributions'
```

Do **not** remove the `{FROM}` stanza yet if users still consume that suite.

### Step 6: Update CI `dists-json`

During overlap, include both suites:

```yaml
dists-json: '["{FROM}","unstable","{NEW}"]'
```

Update:

1. Templates:
   - `python-pipeline/templates/py-packaging/.github/workflows/main.yml`
   - `node-pipeline/templates/node-packaging/.github/workflows/main.yml`
   - `go-pipeline/templates/go-packaging/.github/workflows/main.yml`
2. Every active version repo’s `.github/workflows/main.yml`

Commit and push each language-version repo so scheduled builds pick up `{NEW}`.

### Step 7: Materialize, Build, Publish

Start with one representative version per language, then roll out.

```bash
# Python
cd python-pipeline
make list-dists
make materialize PY=3.14 DIST={NEW}
make build PY=3.14
make publish DIST={NEW}

# Node
cd ../node-pipeline
make materialize NODE=22 DIST={NEW}
make build NODE=22
make publish DIST={NEW}

# Go
cd ../go-pipeline
make materialize GO=1.25 DIST={NEW}
make build GO=1.25
make publish DIST={NEW}
```

If `mk-build-deps` fails, tune `debiandirs/{NEW}/control` Build-Depends, regenerate builders, retry.

### Step 8: Verify

```bash
make list-dists   # should list {NEW} for each version

curl -fsSL "https://apt.dockershelf.com/dockershelf/dists/{NEW}/Release" | head
```

On a `{NEW}` host (or container):

```text
deb [signed-by=…] https://apt.dockershelf.com/dockershelf {NEW} main
apt update && apt install python3.14   # or nodejs-22 / golang-1.25-go
```

### Step 9 (Optional Later): Shift Targets Away From `{FROM}`

When Dockershelf no longer builds for the old suite (e.g. `trixie` is oldstable and consumers moved):

1. Set `DOCKERSHELF_SUITES={NEW} unstable` in all three pipelines (Makefile, config examples, `ci-pull-builder-images.sh`)
2. Set CI `dists-json: '["{NEW}","unstable"]'` in templates and all version repos
3. Regenerate builders (`make generate-dockerfiles && make build-builder-images`)
4. Optionally remove `debiandirs/{FROM}` and `changelogs/mainline/{FROM}` from repos and templates
5. Leave APT packages and the `{FROM}` reprepro stanza published unless you deliberately purge later

**Key principle:** Removing a suite from `DOCKERSHELF_SUITES` and CI stops new builds. Published packages remain available.

### Step 10: Announce Downstream

Update / notify the main Dockershelf images repo:

- Shelf discovery / base image lists
- Apt sources that pin a Debian codename
- Any docs that say “we build for `trixie`”

---

## Quick Reference

| Goal | Where | Action |
|------|--------|--------|
| Seed suite packaging | each `py*` / `node*` / `go*` | `cp -a debiandirs/{FROM} debiandirs/{NEW}` + changelog |
| Keep seeds current | `*-pipeline/templates/` | Same copy + edit |
| Active suites | Makefile + `config.env*` + `ci-pull-builder-images.sh` | `DOCKERSHELF_SUITES=…` |
| Builder images | each `*-pipeline/` | `make generate-dockerfiles && make build-builder-images` |
| APT codename | `debian-repo-setup/reprepro-distributions` + droplet | Add `Codename: {NEW}` stanza |
| CI matrix | templates + each version `main.yml` | `dists-json` |
| First packages | each `*-pipeline/` | `materialize` → `build` → `publish` |
| Drop old suite | config + CI (+ optional tree cleanup) | Remove `{FROM}` from suites/dists-json |

---

## Example: Add `forky` from `trixie`

```bash
# 1) One Python line (repeat for all active py/node/go)
cd py3.14
cp -a debiandirs/trixie debiandirs/forky
cp changelogs/mainline/trixie changelogs/mainline/forky
# edit forky changelog → distribution forky, version …+forky1
git add debiandirs/forky changelogs/mainline/forky
git commit -m "Add forky Debian suite packaging"

# 2) Pipeline config (all three languages)
# DOCKERSHELF_SUITES=trixie unstable forky

# 3) Builders + APT + CI dists-json including forky

# 4) Publish
cd ../python-pipeline
make materialize PY=3.14 DIST=forky && make build PY=3.14 && make publish DIST=forky
```

Later, when dropping `trixie` builds: `DOCKERSHELF_SUITES=forky unstable` and `dists-json: '["forky","unstable"]'`.

---

## Troubleshooting

| Failure | Fix |
|---------|-----|
| `make materialize` validation fails | Every `changelogs/mainline/*` suite needs matching `debiandirs/<suite>/` |
| `mk-build-deps` / builder fails | Adjust `{NEW}` Build-Depends; regenerate builder images |
| CI still builds only old suites | Version repo `main.yml` `dists-json` not updated or not pushed |
| APT import rejects suite | Droplet `conf/distributions` missing `{NEW}` stanza / wrong `SignWith` |
| Template seeds still lack `{NEW}` | Update `*-pipeline/templates/` or new repos will miss the suite |

---

## Related Docs

- `{lang}-pipeline/docs/operations.md` — “Add a new Debian suite”
- `{lang}-pipeline/docs/ci.md` — `dists-json`, builder images
- `{lang}-pipeline/debian-repo-setup/README.md` — reprepro / droplet
- `.github/skills/retire-version/SKILL.md` — retire a language version (not a suite)
- `debian-suite-transition.md` — transition overview and checklist

---

## Execution Checklist (Summary)

- [ ] Identify `{NEW}` and `{FROM}`
- [ ] Seed all active language-version repos
- [ ] Update all three pipeline templates
- [ ] Update `DOCKERSHELF_SUITES` everywhere
- [ ] Regenerate/push builder images
- [ ] Extend and deploy reprepro distributions
- [ ] Update CI `dists-json` (templates + all version repos)
- [ ] Build and publish at least one version per language for `{NEW}`
- [ ] Verify APT `dists/{NEW}/Release`
- [ ] Announce downstream Dockershelf consumers
- [ ] (Later) Shift targets off `{FROM}` without deleting APT packages
