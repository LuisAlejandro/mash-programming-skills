---
name: add-python-version
description: 'Add a new Python major/minor version to the Dockershelf packaging pipeline. Use when: adding py3.15, py3.16, new python version, bootstrapping new python packaging repo, registering new python release line, setting up new python debian packages. Automates seed, materialize, build, publish workflow. Discovery of new upstream versions is OUT OF SCOPE.'
argument-hint: 'Python minor version (e.g., 3.15)'
---

# Add Python Version to Dockershelf Pipeline

**Purpose:** Automate the complete workflow for adding a new Python minor version (e.g., py3.15) to the Dockershelf Debian packaging pipeline.

**Out of Scope:** Discovering whether a new Python version exists upstream. This skill assumes you already know which version to add.

---

## When to Use

Invoke this skill when you need to:
- Add a new Python release line (py3.15, py3.16, etc.)
- Bootstrap a new `py3.XX` packaging repository
- Register and build the first packages for a new Python version
- Set up the complete Debian packaging infrastructure for a new Python minor version

## Prerequisites Check

Before starting, verify:

1. **Python upstream exists:** The `{MINOR}` branch exists at https://github.com/python/cpython
2. **Workspace setup:** You're in the `dockershelf-pipeline` directory
3. **Pipeline tools:** `python-pipeline/` exists with config and bootstrap completed
4. **Git credentials:** `DEBFULLNAME` and `DEBEMAIL` are set (in `python-pipeline/config.env` or global git config)
5. **GitHub repo ready:** Create `Dockershelf/py{MINOR}` on GitHub first
6. **Source version:** Know which existing version to clone from (usually the previous minor version)

---

## Complete Workflow

### Step 1: Create the Packaging Repository

Seed from the closest existing Python version:

```bash
cd python-pipeline
./scripts/seed-py-repo.sh {MINOR} ../py{MINOR} --from {PREVIOUS_MINOR}
```

**Example:** For Python 3.15, seeding from 3.14:
```bash
./scripts/seed-py-repo.sh 3.15 ../py3.15 --from 3.14
```

**What this does:**
- Clones the previous version repository (e.g., `py3.14`)
- Performs search-replace: `python3.14` → `python3.15`, `libpython3.14` → `libpython3.15`
- Creates `.gitmodules` pointing to CPython `{MINOR}` branch
- Initializes git repo with initial commit
- **Note:** Does NOT clone cpython submodule (too large)

**Output:** `../py{MINOR}/` directory with complete packaging structure

### Step 2: Initialize CPython Submodule

Point the cpython submodule to the correct upstream branch:

```bash
cd ../py{MINOR}
git submodule update --init cpython
git -C cpython fetch origin
git -C cpython checkout {MINOR}  # e.g., "3.15"
git add cpython
```

**What happens:**
- Initializes the cpython submodule (large download)
- Checks out the appropriate Python release branch
- Registers the submodule commit

### Step 3: Update Packaging Metadata

Review and update all version references:

#### 3.1 Debian Directories

Verify `debiandirs/trixie/` and `debiandirs/unstable/` have correct version strings:
- Package names: `python{MINOR}`, `libpython{MINOR}`, etc.
- `VER=` in `debian/rules`
- `debian/control`: Maintainer, Vcs-Browser, Vcs-Git URLs

#### 3.2 Changelogs

Set initial changelog versions in both suites:
- `changelogs/mainline/trixie`: Version `{VERSION}-1+trixie1`, distribution `trixie`
- `changelogs/mainline/unstable`: Version `{VERSION}-1+unstable1`, distribution `unstable`

**Example for Python 3.15.0:**
```
python3.15 (3.15.0-1+trixie1) trixie; urgency=medium

  * Initial Python 3.15 packaging for Dockershelf

 -- Your Name <email@example.com>  Mon, 06 Jul 2026 12:00:00 +0000
```

#### 3.3 Patches

Review `patches/series`:
- Drop patches that no longer apply to the new version
- Refresh patches if needed
- Test with `gbp pq` commands

### Step 4: Commit and Push New Repository

```bash
cd ../py{MINOR}
git remote add origin https://github.com/Dockershelf/py{MINOR}.git
git push -u origin main
```

### Step 5: Register in Pipeline Makefile

Edit [`python-pipeline/Makefile`](../../python-pipeline/Makefile):

```makefile
PY_VERSIONS := 3.10 3.11 3.12 3.13 3.14 {MINOR}
```

**Critical:** Add the new version to the space-separated list.

### Step 6: Bootstrap and Verify

```bash
cd python-pipeline
make bootstrap
make list-dists  # Should show py{MINOR}: trixie unstable
```

### Step 7: Build for Each Debian Suite

For each supported suite (trixie, unstable):

#### 7.1 Materialize

Creates the `work/` directory with upstream source + debian packaging:

```bash
cd python-pipeline
make materialize PY={MINOR} DIST=trixie
```

**What happens:**
- Creates `work/` git repository
- Imports CPython source using `gbp import-orig`
- Applies debian/ directory from `py{MINOR}/debiandirs/trixie/`
- Applies patches from `py{MINOR}/patches/`
- Creates `py{MINOR}/work/` ready for building

#### 7.2 Build Binary Packages

```bash
make build PY={MINOR}
```

**What happens:**
- Runs `gbp buildpackage` inside Docker builder container
- Compiles Python from source with Debian packaging
- Produces `.deb` files in `python-pipeline/dist/`

**Expected artifacts:**
- `python-pipeline/dist/python{MINOR}_{VERSION}-1+trixie1_{ARCH}.deb`
- `python-pipeline/dist/libpython{MINOR}_{VERSION}-1+trixie1_{ARCH}.deb`
- `python-pipeline/dist/python{MINOR}-dev_{VERSION}-1+trixie1_{ARCH}.deb`
- Other related packages (doc, dbg, venv, etc.)

#### 7.3 Publish to APT Repository

```bash
make publish DIST=trixie
```

**What happens:**
- Uses `reprepro` to upload `.deb` files to the Debian repository
- Updates APT repository metadata
- Makes packages available via `apt install python{MINOR}`

#### 7.4 Repeat for Unstable

```bash
make materialize PY={MINOR} DIST=unstable
make build PY={MINOR}
make publish DIST=unstable
```

### Step 8: Register as Git Submodule in Parent Repository

**CRITICAL:** The new version repository must be registered as a Git submodule in the main dockershelf-pipeline repository.

```bash
cd ..

# Register py{MINOR} as a Git submodule
git submodule add https://github.com/Dockershelf/py{MINOR}.git py{MINOR}

# Also stage the updated submodule pointers (python-pipeline Makefile changes)
git add python-pipeline

# Commit all changes
git commit -m "Add py{MINOR} packaging repository

- Register py{MINOR} as Git submodule
- Seed py{MINOR} from py{PREVIOUS_MINOR} template with cpython submodule pointing to {MINOR} branch
- Add {MINOR} to PY_VERSIONS in python-pipeline/Makefile"
git push origin main
```

**Why submodules?** Each version repository (py3.10, py3.11, etc.) is tracked as a Git submodule, allowing independent version control while maintaining a unified workspace structure.

### Step 9: Set Up CI/CD (Optional)

The seeded repository should include `.github/workflows/main.yml` configured for:
- Scheduled builds (cron)
- Manual workflow dispatch
- Multi-architecture (amd64, arm64)
- Multi-suite (trixie, unstable)

**Verify GitHub Actions:**
1. Push triggers first build
2. Check workflow runs in GitHub UI
3. Confirm packages arrive in APT repository

---

## Quick Reference Commands

| Step | Command | Working Directory |
|------|---------|-------------------|
| Seed repo | `./scripts/seed-py-repo.sh {MINOR} ../py{MINOR} --from {PREV}` | `python-pipeline/` |
| Init submodule | `git submodule update --init cpython` | `py{MINOR}/` |
| Checkout branch | `git -C cpython checkout {MINOR}` | `py{MINOR}/` |
| Register version | Edit `PY_VERSIONS := ... {MINOR}` | `python-pipeline/Makefile` |
| Bootstrap | `make bootstrap` | `python-pipeline/` |
| Materialize | `make materialize PY={MINOR} DIST=trixie` | `python-pipeline/` |
| Build | `make build PY={MINOR}` | `python-pipeline/` |
| Publish | `make publish DIST=trixie` | `python-pipeline/` |
| Push new repo | `git push -u origin main` | `py{MINOR}/` |

---

## Troubleshooting

### `seed-py-repo.sh` fails: "repo already exists"

The target directory `../py{MINOR}/` already exists.

**Solution:** 
1. Remove or rename existing directory
2. Re-run seed script

### Submodule checkout fails: "branch not found"

The `{MINOR}` branch doesn't exist in python/cpython yet.

**Solution:**
1. Verify branch exists: `git ls-remote https://github.com/python/cpython.git | grep {MINOR}`
2. Use correct branch name (may be a release tag instead)
3. Wait for upstream CPython to create the branch

### `make materialize` fails: "No such file or directory"

The `py{MINOR}/` directory doesn't exist or isn't registered in `PY_VERSIONS`.

**Solution:** 
1. Verify `../py{MINOR}/` exists
2. Check `PY_VERSIONS` in Makefile includes `{MINOR}`
3. Run `make bootstrap` to clone missing repos

### `make build` fails: "Build-Depends unsatisfied"

Builder Docker image is outdated or doesn't have required dependencies.

**Solution:** Regenerate builder images:

```bash
cd python-pipeline
make generate-dockerfiles
make build-builder-images
```

### `make publish` finds no `.deb` files

Build didn't complete or artifacts are in wrong location.

**Solution:**
1. Check `python-pipeline/dist/` for `.deb` files
2. Re-run `make build PY={MINOR}`
3. Verify build completed without errors

### Patches don't apply cleanly

Existing patches in `py{MINOR}/patches/` may not apply to new Python version.

**Solution:**
1. Review patch failures in build log
2. Update patches or remove incompatible ones
3. Use `gbp pq` to manage patch queue:
   ```bash
   cd py{MINOR}/work
   ../python-pipeline/tools gbp pq rebase
   ```

### Version strings still reference old version

The seed script's search-replace missed some references.

**Solution:**
1. Search for old version: `grep -r "3.14" debiandirs/ changelogs/`
2. Manually update remaining references
3. Use retarget script: `../python-pipeline/scripts/retarget-py3-control.sh`

---

## Version Bump Workflow (Future Updates)

After the initial setup, bump to newer patch versions:

```bash
cd ../py{MINOR}
git submodule update --init cpython  # if not already initialized
../python-pipeline/meta-gbp update
cd ../python-pipeline
make materialize PY={MINOR} DIST=trixie
make build PY={MINOR}
make publish DIST=trixie
```

**What `meta-gbp update` does:**
- Fetches latest from CPython `{MINOR}` branch
- Finds newest `v{MINOR}.Y` tag (e.g., `v3.15.5`)
- Updates `cpython/` submodule pointer
- Rebases patches via `gbp pq`
- Updates `changelogs/mainline/{DIST}` with new version
- Commits the changes

---

## Related Documentation

- [Operations Manual](../../python-pipeline/docs/operations.md) — Complete operations guide
- [CI Documentation](../../python-pipeline/docs/ci.md) — GitHub Actions workflows
- [Deploy Setup](../../python-pipeline/docs/deploy-setup.md) — APT repository configuration

---

## Execution Checklist

Use this checklist when running the skill:

- [ ] Verify `{MINOR}` branch exists at python/cpython
- [ ] Create GitHub repo: `Dockershelf/py{MINOR}`
- [ ] Identify source version to clone from (e.g., 3.14 for 3.15)
- [ ] Run seed script with `--from {PREVIOUS_MINOR}`
- [ ] Initialize cpython submodule
- [ ] Checkout correct CPython branch
- [ ] Update debiandirs/ metadata (control, rules)
- [ ] Set initial changelog versions for both suites
- [ ] Review and update patches/
- [ ] Commit and push py{MINOR} repository
- [ ] Add `{MINOR}` to `PY_VERSIONS` in Makefile
- [ ] Run `make bootstrap`
- [ ] Materialize for trixie
- [ ] Build packages
- [ ] Publish to trixie
- [ ] Repeat materialize/build/publish for unstable
- [ ] Update parent repository submodule pointer
- [ ] Verify GitHub Actions workflow runs
- [ ] Confirm packages available in APT repo

---

## Key Principles

1. **Discovery is out of scope:** This skill assumes you already know which Python version to add
2. **Clone from previous version:** Always seed from the most recent existing py3.XX repo
3. **Version-specific metadata:** Every reference to the old version must be updated (package names, paths, VER= variables)
4. **Build for all suites:** Both trixie and unstable need separate materialize/build/publish cycles
5. **Submodule management:** The cpython/ submodule is initialized separately from the seed script due to its size
6. **Progressive workflow:** Seed → Update metadata → Register → Materialize → Build → Publish is the canonical sequence

---

## Differences from Node.js Pipeline

Unlike the Node.js pipeline:
- **Seeding strategy:** Python clones from existing version (more complex metadata), Node seeds from template (simpler)
- **Submodule initialization:** Python requires manual checkout of branch after init, Node registers gitlink with SHA
- **Version format:** Python uses `3.15` (major.minor), Node uses `22` (major only)
- **Package complexity:** Python produces more packages (dev, venv, doc, dbg, lib), Node has simpler package set
- **Retargeting script:** Python has `retarget-py3-control.sh` for bulk updates, Node doesn't need this
