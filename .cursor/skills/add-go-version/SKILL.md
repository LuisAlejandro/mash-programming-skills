---
name: add-go-version
description: "Add a new Go minor version to the Dockershelf packaging pipeline. Use when adding go1.26, go1.27, a new golang version, bootstrapping a new go packaging repo, registering a new go release line, or setting up new golang debian packages. Automates seed, materialize, build, publish workflow. Discovery of new upstream versions is OUT OF SCOPE."
argument-hint: 'Go minor version (e.g., 1.26)'
---

# Add Go Version to Dockershelf Pipeline

**Purpose:** Automate the complete workflow for adding a new Go minor version (e.g., go1.26) to the Dockershelf Debian packaging pipeline.

**Out of Scope:** Discovering whether a new Go version exists upstream. This skill assumes you already know which version to add.

---

## When to Use

Invoke this skill when you need to:
- Add a new Go release line (go1.26, go1.27, etc.)
- Bootstrap a new `go{MINOR}` packaging repository
- Register and build the first packages for a new Go minor version
- Set up the complete Debian packaging infrastructure for a new Go line

## Prerequisites Check

Before starting, verify:

1. **Go upstream exists:** The `release-branch.go{MINOR}` branch exists at https://github.com/golang/go
2. **Workspace setup:** You're in the `dockershelf-pipeline` directory
3. **Pipeline tools:** `go-pipeline/` exists with config and bootstrap completed
4. **Git credentials:** `DEBFULLNAME` and `DEBEMAIL` are set (in `go-pipeline/config.env` or global git config)
5. **GitHub repo ready:** Create `Dockershelf/go{MINOR}` on GitHub first

---

## Complete Workflow

### Step 1: Create the Packaging Repository

Seed from the template:

```bash
cd go-pipeline
./scripts/seed-go-repo.sh {MINOR} ../go{MINOR}
```

**Example:** For Go 1.26:
```bash
./scripts/seed-go-repo.sh 1.26 ../go1.26
```

**What this does:**
- Copies the template from `go-pipeline/templates/go-packaging/`
- Replaces `__GO_MINOR__` placeholders with the actual version
- Creates `.gitmodules` pointing to `release-branch.go{MINOR}` branch
- Registers `go/` as a 160000 gitlink (submodule pointer) at branch HEAD
- Initializes a git repo with initial commit
- Sets up staggered cron schedule for GitHub Actions

**Output:** `../go{MINOR}/` directory with complete packaging structure

### Step 2: Register in Pipeline Makefile

Edit [`go-pipeline/Makefile`](../../go-pipeline/Makefile):

```makefile
GO_VERSIONS := 1.20 1.21 1.22 1.23 1.24 1.25 {MINOR}
```

**Critical:** Add the new version to the space-separated list.

### Step 3: Initialize Go Submodule (Optional for Build)

The seed script registers `go/` as a gitlink but doesn't clone the working tree (too large). Initialize when needed:

```bash
cd ../go{MINOR}
git submodule update --init go
```

**Alternative:** Run the workspace-level init script:

```bash
cd ..
./init-go-submodules.sh
```

**Note:** You can defer this until you need to run `meta-gbp update` for version bumps. Materialize and build work without the working tree.

### Step 4: Build for Each Debian Suite

For each supported suite (trixie, unstable):

#### 4.1 Materialize

Creates the `work/` directory with upstream source + debian packaging:

```bash
cd go-pipeline
make materialize GO={MINOR} DIST=trixie
```

**What happens:**
- Downloads Go source tarball from https://go.dev/dl/
- Imports into git-buildpackage format
- Applies debian/ directory from `go{MINOR}/debiandirs/trixie/`
- Applies patches from `go{MINOR}/patches/`
- Creates `go{MINOR}/work/` ready for building

#### 4.2 Build Binary Packages

```bash
make build GO={MINOR}
```

**What happens:**
- Runs `gbp buildpackage` inside Docker builder container
- Compiles Go from source with Debian packaging
- Produces `.deb` files in `go-pipeline/dist/`

**Expected artifacts:**
- `go-pipeline/dist/golang-{MINOR}-go_{VERSION}-1+trixie1_{ARCH}.deb`
- `go-pipeline/dist/golang-{MINOR}-src_{VERSION}-1+trixie1_{ARCH}.deb`
- `go-pipeline/dist/golang-{MINOR}-doc_{VERSION}-1+trixie1_{ARCH}.deb`
- Other related packages (dbgsym, etc.)

#### 4.3 Publish to APT Repository

```bash
make publish DIST=trixie
```

**What happens:**
- Uses `reprepro` to upload `.deb` files to the Debian repository
- Updates APT repository metadata
- Makes packages available via `apt install golang-{MINOR}-go`

#### 4.4 Repeat for Unstable

```bash
make materialize GO={MINOR} DIST=unstable
make build GO={MINOR}
make publish DIST=unstable
```

### Step 5: Commit and Push

#### 5.1 Commit the new repository

```bash
cd ../go{MINOR}
git remote add origin https://github.com/Dockershelf/go{MINOR}.git
git push -u origin main
```

#### 5.2 Register as Git submodule in parent repository

**CRITICAL:** The new version repository must be registered as a Git submodule in the main dockershelf-pipeline repository.

```bash
cd ..

# Register go{MINOR} as a Git submodule
git submodule add https://github.com/Dockershelf/go{MINOR}.git go{MINOR}

# Also stage the updated submodule pointers (go-pipeline Makefile changes)
git add go-pipeline

# Commit all changes
git commit -m "Add go{MINOR} packaging repository

- Register go{MINOR} as Git submodule
- Seed go{MINOR} from template with go/ submodule pointing to release-branch.go{MINOR}
- Add {MINOR} to GO_VERSIONS in go-pipeline/Makefile"
git push origin main
```

**Why submodules?** Each version repository (go1.20, go1.21, etc.) is tracked as a Git submodule, allowing independent version control while maintaining a unified workspace structure.

### Step 6: Set Up CI/CD (Optional)

The seeded repository includes `.github/workflows/main.yml` configured for:
- Scheduled builds (cron with staggered timing)
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
| Seed repo | `./scripts/seed-go-repo.sh {MINOR} ../go{MINOR}` | `go-pipeline/` |
| Register version | Edit `GO_VERSIONS := ... {MINOR}` | `go-pipeline/Makefile` |
| Init submodule | `git submodule update --init go` | `go{MINOR}/` |
| Materialize | `make materialize GO={MINOR} DIST=trixie` | `go-pipeline/` |
| Build | `make build GO={MINOR}` | `go-pipeline/` |
| Publish | `make publish DIST=trixie` | `go-pipeline/` |
| Commit new repo | `git push -u origin main` | `go{MINOR}/` |

---

## Troubleshooting

### `seed-go-repo.sh` fails: "curl: API rate limit"

GitHub API rate limit exceeded fetching branch SHA.

**Solution:** Set `GITHUB_TOKEN` environment variable or manually provide SHA:

```bash
# Get SHA manually
SHA=$(git ls-remote https://github.com/golang/go.git refs/heads/release-branch.go{MINOR} | cut -f1)
# Edit seed script or register gitlink manually
```

### `make materialize` fails: "No such file or directory"

The `go{MINOR}/` directory doesn't exist or isn't registered in `GO_VERSIONS`.

**Solution:** 
1. Verify `../go{MINOR}/` exists
2. Check `GO_VERSIONS` in Makefile includes `{MINOR}`
3. Run `make bootstrap` to clone missing repos

### `make build` fails: "Build-Depends unsatisfied"

Builder Docker image is outdated or doesn't have required dependencies.

**Solution:** Regenerate builder images:

```bash
cd go-pipeline
make generate-dockerfiles
make build-builder-images
```

### `make publish` finds no `.deb` files

Build didn't complete or artifacts are in wrong location.

**Solution:**
1. Check `go-pipeline/dist/` for `.deb` files
2. Re-run `make build GO={MINOR}`
3. Verify build completed without errors

### Patches don't apply cleanly

Existing patches in `go{MINOR}/patches/` may not apply to new Go version.

**Solution:**
1. Review patch failures in build log
2. Update patches or remove incompatible ones
3. Use `gbp pq` to manage patch queue:
   ```bash
   cd go{MINOR}/work
   ../go-pipeline/tools gbp pq rebase
   ```

### Build fails: "cannot find package"

Go bootstrap compiler version mismatch or missing dependencies.

**Solution:**
1. Check `debian/control` Build-Depends (usually `golang-any`)
2. Verify builder image has correct Go bootstrap toolchain
3. Regenerate builder images: `make build-builder-images`

### Download fails: "404 Not Found"

The tarball for the Go version doesn't exist at https://go.dev/dl/

**Solution:**
1. Verify the version exists: `curl -I https://go.dev/dl/go{VERSION}.src.tar.gz`
2. Check if it's a prerelease (rc/beta) - adjust expectations
3. Wait for upstream to publish the release

---

## Version Bump Workflow (Future Updates)

After the initial setup, bump to newer patch versions:

```bash
cd ../go{MINOR}
git submodule update --init go  # if not already initialized
../go-pipeline/meta-gbp update
cd ../go-pipeline
make materialize GO={MINOR} DIST=trixie
make build GO={MINOR}
make publish DIST=trixie
```

**What `meta-gbp update` does:**
- Fetches latest from `release-branch.go{MINOR}` branch
- Finds newest `go{MINOR}.Y` tag
- Updates `go/` submodule pointer
- Rebases patches via `gbp pq`
- Updates `changelogs/mainline/{DIST}` with new version
- Commits the changes

---

## Related Documentation

- [Operations Manual](../../go-pipeline/docs/operations.md) — Complete operations guide
- [CI Documentation](../../go-pipeline/docs/ci.md) — GitHub Actions workflows
- [Deploy Setup](../../go-pipeline/docs/deploy-setup.md) — APT repository configuration
- [Template Structure](../../go-pipeline/templates/go-packaging/README.md) — Packaging template details

---

## Execution Checklist

Use this checklist when running the skill:

- [ ] Verify `release-branch.go{MINOR}` branch exists at golang/go
- [ ] Create GitHub repo: `Dockershelf/go{MINOR}`
- [ ] Run seed script
- [ ] Add `{MINOR}` to `GO_VERSIONS` in Makefile
- [ ] Initialize go submodule (optional, can defer)
- [ ] Materialize for trixie
- [ ] Build packages
- [ ] Publish to trixie
- [ ] Repeat materialize/build/publish for unstable
- [ ] Commit go{MINOR} repository
- [ ] Push to GitHub
- [ ] Update parent repository submodule pointer
- [ ] Verify GitHub Actions workflow runs
- [ ] Confirm packages available in APT repo

---

## Key Principles

1. **Discovery is out of scope:** This skill assumes you already know which Go version to add
2. **Follow the template:** The seed script handles most boilerplate; don't manually edit unless necessary
3. **Build for all suites:** Both trixie and unstable need separate materialize/build/publish cycles
4. **Gitlink vs working tree:** The `go/` submodule pointer is registered immediately, but the working tree (actual source) is cloned on-demand
5. **Progressive workflow:** Seed → Register → Materialize → Build → Publish is the canonical sequence
6. **Source compilation:** Unlike older pipelines, Go is compiled from source (not repackaged from precompiled binaries)

---

## Differences from Node.js and Python Pipelines

Unlike the Node.js and Python pipelines:
- **Version format:** Go uses `1.26` (major.minor), Node uses `26` (major only), Python uses `3.15` (major.minor)
- **Branch naming:** Go uses `release-branch.go{MINOR}`, Node uses `v{MAJOR}.x`, Python uses `{MINOR}` directly
- **Submodule path:** Go uses `go/`, Node uses `node/`, Python uses `cpython/`
- **Package naming:** Go uses `golang-{MINOR}-go`, Node uses `nodejs-{MAJOR}`, Python uses `python{MINOR}`
- **Build complexity:** Go requires bootstrap compiler (golang-any), more complex than Node/Python
- **Cron scheduling:** Go template uses staggered cron times (10:35, 10:40, etc.) to spread CI load
- **Template placeholders:** Go uses `__GO_MINOR__` and `__GO_MINOR_DIR__` patterns for replacement
