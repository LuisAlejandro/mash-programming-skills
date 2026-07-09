---
name: add-node-version
description: 'Add a new Node.js major version to the Dockershelf packaging pipeline. Use when: adding node26, node28, new nodejs major version, bootstrapping new node packaging repo, registering new node major line, setting up new node debian packages. Automates seed, materialize, build, publish workflow. Discovery of new upstream versions is OUT OF SCOPE.'
argument-hint: 'Node.js major version number (e.g., 26)'
---

# Add Node.js Version to Dockershelf Pipeline

**Purpose:** Automate the complete workflow for adding a new Node.js major version (e.g., node26) to the Dockershelf Debian packaging pipeline.

**Out of Scope:** Discovering whether a new Node.js version exists upstream. This skill assumes you already know which version to add.

---

## When to Use

Invoke this skill when you need to:
- Add a new Node.js major version line (node26, node28, etc.)
- Bootstrap a new `nodeXX` packaging repository
- Register and build the first packages for a new major version
- Set up the complete Debian packaging infrastructure for a new Node line

## Prerequisites Check

Before starting, verify:

1. **Node.js upstream exists:** The `v{MAJOR}.x` branch exists at https://github.com/nodejs/node
2. **Workspace setup:** You're in the `dockershelf-pipeline` directory
3. **Pipeline tools:** `node-pipeline/` exists with config and bootstrap completed
4. **Git credentials:** `DEBFULLNAME` and `DEBEMAIL` are set (in `node-pipeline/config.env` or global git config)
5. **GitHub repo ready:** Either create `Dockershelf/node{MAJOR}` on GitHub first, or plan to seed locally

---

## Complete Workflow

### Step 1: Create the Packaging Repository

Choose one approach:

#### Option A: Seed from template (recommended)

```bash
cd node-pipeline
./scripts/seed-node-repo.sh {MAJOR} ../node{MAJOR}
```

**What this does:**
- Copies the template from `node-pipeline/templates/node-packaging/`
- Replaces `__NODE_MAJOR__` placeholders with the actual version
- Creates `.gitmodules` pointing to `v{MAJOR}.x` branch
- Registers `node/` as a 160000 gitlink (submodule pointer)
- Initializes a git repo with initial commit

**Output:** `../node{MAJOR}/` directory with complete packaging structure

#### Option B: Fork from existing version

```bash
cd ..
git clone https://github.com/Dockershelf/node24.git node{MAJOR}
cd node{MAJOR}
git remote set-url origin https://github.com/Dockershelf/node{MAJOR}.git
# Then manually update version references in debian files
```

### Step 2: Register in Pipeline Makefile

Edit [`node-pipeline/Makefile`](../../node-pipeline/Makefile):

```makefile
NODE_VERSIONS := 16 18 20 22 24 {MAJOR}
```

**Critical:** Add the new version to the space-separated list.

### Step 3: Initialize Node.js Submodule (Optional for Build)

The seed script registers `node/` as a gitlink but doesn't clone the working tree (too large). Initialize when needed:

```bash
cd ../node{MAJOR}
git submodule update --init node
```

**Alternative:** Run the workspace-level init script:

```bash
cd ..
./init-node-submodules.sh
```

**Note:** You can defer this until you need to run `meta-gbp update` for version bumps. Materialize and build work without the working tree.

### Step 4: Build for Each Debian Suite

For each supported suite (trixie, unstable):

#### 4.1 Materialize

Creates the `work/` directory with upstream source + debian packaging:

```bash
cd node-pipeline
make materialize NODE={MAJOR} DIST=trixie
```

**What happens:**
- Downloads Node.js source tarball from https://go.dev/dl/
- Imports into git-buildpackage format
- Applies debian/ directory from `node{MAJOR}/debiandirs/trixie/`
- Applies patches from `node{MAJOR}/patches/`
- Creates `node{MAJOR}/work/` ready for building

#### 4.2 Build Binary Packages

```bash
make build NODE={MAJOR}
```

**What happens:**
- Runs `gbp buildpackage` inside Docker builder container
- Compiles Node.js from source with Debian packaging
- Produces `.deb` files in `node-pipeline/dist/`

**Expected artifacts:**
- `node-pipeline/dist/nodejs-{MAJOR}_{VERSION}-1+trixie1_{ARCH}.deb`
- `node-pipeline/dist/nodejs-{MAJOR}-dev_{VERSION}-1+trixie1_{ARCH}.deb`
- Other related packages (doc, dbgsym, etc.)

#### 4.3 Publish to APT Repository

```bash
make publish DIST=trixie
```

**What happens:**
- Uses `reprepro` to upload `.deb` files to the Debian repository
- Updates APT repository metadata
- Makes packages available via `apt install nodejs-{MAJOR}`

#### 4.4 Repeat for Unstable

```bash
make materialize NODE={MAJOR} DIST=unstable
make build NODE={MAJOR}
make publish DIST=unstable
```

### Step 5: Commit and Push

#### 5.1 Commit the new repository

```bash
cd ../node{MAJOR}
git remote add origin https://github.com/Dockershelf/node{MAJOR}.git
git push -u origin main
```

#### 5.2 Register as Git submodule in parent repository

**CRITICAL:** The new version repository must be registered as a Git submodule in the main dockershelf-pipeline repository.

```bash
cd ..

# Register node{MAJOR} as a Git submodule
git submodule add https://github.com/Dockershelf/node{MAJOR}.git node{MAJOR}

# Also stage the updated submodule pointers (node-pipeline Makefile changes)
git add node-pipeline

# Commit all changes
git commit -m "Add node{MAJOR} packaging repository

- Register node{MAJOR} as Git submodule
- Seed node{MAJOR} from template with node/ submodule pointing to v{MAJOR}.x
- Add {MAJOR} to NODE_VERSIONS in node-pipeline/Makefile"
git push origin main
```

**Why submodules?** Each version repository (node16, node18, etc.) is tracked as a Git submodule, allowing independent version control while maintaining a unified workspace structure.

### Step 6: Set Up CI/CD (Optional)

The seeded repository includes `.github/workflows/main.yml` configured for:
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
| Seed repo | `./scripts/seed-node-repo.sh {MAJOR} ../node{MAJOR}` | `node-pipeline/` |
| Register version | Edit `NODE_VERSIONS := ... {MAJOR}` | `node-pipeline/Makefile` |
| Init submodule | `git submodule update --init node` | `node{MAJOR}/` |
| Materialize | `make materialize NODE={MAJOR} DIST=trixie` | `node-pipeline/` |
| Build | `make build NODE={MAJOR}` | `node-pipeline/` |
| Publish | `make publish DIST=trixie` | `node-pipeline/` |
| Commit new repo | `git push -u origin main` | `node{MAJOR}/` |

---

## Troubleshooting

### `seed-node-repo.sh` fails: "curl: API rate limit"

GitHub API rate limit exceeded fetching branch SHA.

**Solution:** Set `GITHUB_TOKEN` environment variable or manually provide SHA:

```bash
# Get SHA manually
SHA=$(git ls-remote https://github.com/nodejs/node.git refs/heads/v{MAJOR}.x | cut -f1)
# Edit seed script or register gitlink manually
```

### `make materialize` fails: "No such file or directory"

The `node{MAJOR}/` directory doesn't exist or isn't registered in `NODE_VERSIONS`.

**Solution:** 
1. Verify `../node{MAJOR}/` exists
2. Check `NODE_VERSIONS` in Makefile includes `{MAJOR}`

### `make build` fails: "Build-Depends unsatisfied"

Builder Docker image is outdated or doesn't have required dependencies.

**Solution:** Regenerate builder images:

```bash
cd node-pipeline
make generate-dockerfiles
make build-builder-images
```

### `make publish` finds no `.deb` files

Build didn't complete or artifacts are in wrong location.

**Solution:**
1. Check `node-pipeline/dist/` for `.deb` files
2. Re-run `make build NODE={MAJOR}`
3. Verify build completed without errors

### Patches don't apply cleanly

Existing patches in `node{MAJOR}/patches/` may not apply to new Node.js version.

**Solution:**
1. Review patch failures in build log
2. Update patches or remove incompatible ones
3. Use `gbp pq` to manage patch queue:
   ```bash
   cd node{MAJOR}/work
   ../node-pipeline/tools gbp pq rebase
   ```

---

## Version Bump Workflow (Future Updates)

After the initial setup, bump to newer patch versions:

```bash
cd ../node{MAJOR}
git submodule update --init node  # if not already initialized
../node-pipeline/meta-gbp update
cd ../node-pipeline
make materialize NODE={MAJOR} DIST=trixie
make build NODE={MAJOR}
make publish DIST=trixie
```

**What `meta-gbp update` does:**
- Fetches latest from `v{MAJOR}.x` branch
- Finds newest `go{MAJOR}.Y.Z` tag
- Updates `node/` submodule pointer
- Updates `changelogs/mainline/{DIST}` with new version
- Commits the changes

---

## Related Documentation

- [Operations Manual](../../node-pipeline/docs/operations.md) — Complete operations guide
- [CI Documentation](../../node-pipeline/docs/ci.md) — GitHub Actions workflows
- [Deploy Setup](../../node-pipeline/docs/deploy-setup.md) — APT repository configuration
- [Template Structure](../../node-pipeline/templates/node-packaging/README.md) — Packaging template details

---

## Execution Checklist

Use this checklist when running the skill:

- [ ] Verify `v{MAJOR}.x` branch exists at nodejs/node
- [ ] Run seed script or clone template
- [ ] Add `{MAJOR}` to `NODE_VERSIONS` in Makefile
- [ ] Initialize node submodule (optional, can defer)
- [ ] Materialize for trixie
- [ ] Build packages
- [ ] Publish to trixie
- [ ] Repeat materialize/build/publish for unstable
- [ ] Commit node{MAJOR} repository
- [ ] Push to GitHub
- [ ] Update parent repository submodule pointer
- [ ] Verify GitHub Actions workflow runs
- [ ] Confirm packages available in APT repo

---

## Key Principles

1. **Discovery is out of scope:** This skill assumes you already know which Node.js version to add
2. **Follow the template:** The seed script handles most boilerplate; don't manually edit unless necessary
3. **Build for all suites:** Both trixie and unstable need separate materialize/build/publish cycles
4. **Gitlink vs working tree:** The `node/` submodule pointer is registered immediately, but the working tree (actual source) is cloned on-demand
5. **Progressive workflow:** Seed → Register → Materialize → Build → Publish is the canonical sequence
