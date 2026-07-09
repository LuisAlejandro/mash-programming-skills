---
name: retire-version
description: 'Retire/decommission a Python, Node.js, or Go version from active maintenance. Use when: ending support for node16, py3.10, go1.20, marking version EOL, stopping automated builds, archiving repository. Disables workflows, removes from pipeline Makefile, archives GitHub repo. Does NOT delete packages from APT repository.'
argument-hint: 'Language and version (e.g., node16, py3.10, go1.20)'
---

# Retire Language Version from Dockershelf Pipeline

**Purpose:** Gracefully retire a language version from active maintenance by disabling automated builds, removing from pipeline configuration, and archiving the GitHub repository.

**Scope:** This skill handles the retirement process but does NOT delete already-published packages from the APT repository (those remain available for existing users).

---

## When to Use

Invoke this skill when you need to:
- End support for an EOL (End of Life) language version
- Stop automated builds and publishing for a version
- Archive a version repository when upstream support ends
- Remove a version from active pipeline maintenance
- Reduce CI/CD resource usage by retiring old versions

## What This Skill Does

1. **Disables GitHub Actions workflows** (stops scheduled builds)
2. **Removes version from pipeline Makefile** (excludes from bulk operations)
3. **Archives GitHub repository** (marks as read-only, shows "Archived" badge)
4. **Updates parent repository** (removes submodule pointer)
5. **Documents retirement** (adds archive notice to README)

## What This Skill Does NOT Do

- ❌ **Delete published packages** from APT repository (they remain available)
- ❌ **Delete the GitHub repository** (only archives it)
- ❌ **Delete Docker images** from GHCR (they remain available)
- ❌ **Break existing users** (all artifacts remain accessible)

---

## Complete Workflow

### Step 1: Verify Version Exists

Confirm the version repository exists and is currently active:

```bash
# Verify repository exists
cd dockershelf-pipeline
ls -d {LANG}{VERSION}  # e.g., node16, py3.10, go1.20

# Check it's in the pipeline Makefile
grep "{VERSION}" {lang}-pipeline/Makefile
```

### Step 2: Disable GitHub Actions Workflows

Prevent future scheduled builds:

**Option A: Comment out schedule trigger (preserves manual dispatch)**

Edit `.github/workflows/main.yml`:
```yaml
on:
  # schedule:
  #   - cron: '0 4 * * 4'
  workflow_dispatch:  # Keep for emergency use
    inputs:
      # ... existing inputs
```

**Option B: Delete workflow file entirely**
```bash
cd {LANG}{VERSION}
git rm .github/workflows/main.yml
git commit -m "Retire {LANG}{VERSION}: disable automated builds"
git push origin main
```

**Recommendation:** Use Option A to preserve manual rebuild capability for critical security patches.

### Step 3: Remove from Pipeline Makefile

Edit the respective pipeline Makefile to exclude the retired version:

**Node.js:**
```bash
cd node-pipeline
# Before: NODE_VERSIONS := 16 18 20 22 24
# After:  NODE_VERSIONS := 18 20 22 24
```

**Python:**
```bash
cd python-pipeline
# Before: PY_VERSIONS := 3.10 3.11 3.12 3.13 3.14
# After:  PY_VERSIONS := 3.11 3.12 3.13 3.14
```

**Go:**
```bash
cd go-pipeline
# Before: GO_VERSIONS := 1.20 1.21 1.22 1.23 1.24 1.25
# After:  GO_VERSIONS := 1.21 1.22 1.23 1.24 1.25
```

**Commit and push:**
```bash
git add Makefile
git commit -m "Retire {LANG}{VERSION}: remove from active versions list"
git push origin main
```

### Step 4: Add Archive Notice to Repository README

Update the retired version's README with a prominent notice:

```bash
cd ../{LANG}{VERSION}
```

Add at the top of `README.md`:
```markdown
> **⚠️ ARCHIVED: This repository has been retired**
> 
> {Language} {VERSION} reached End of Life on {DATE} and is no longer receiving updates.
> 
> - **No new builds** will be published
> - **Existing packages** remain available in the APT repository
> - **Security updates** are no longer provided
> - **For current versions**, see: https://github.com/Dockershelf/{pipeline-name}
> 
> Last build: {DATE}
```

**Commit and push:**
```bash
git add README.md
git commit -m "Add archive notice to README"
git push origin main
```

### Step 5: Archive GitHub Repository

Mark the repository as archived (read-only):

**Via GitHub CLI:**
```bash
gh repo archive Dockershelf/{LANG}{VERSION} --yes
```

**Via GitHub Web UI:**
1. Navigate to `https://github.com/Dockershelf/{LANG}{VERSION}/settings`
2. Scroll to "Danger Zone"
3. Click "Archive this repository"
4. Confirm archival

**Result:** Repository becomes read-only with "Archived" badge

### Step 6: Update Parent Repository

Remove the retired version's submodule pointer:

```bash
cd dockershelf-pipeline
git rm {LANG}{VERSION}
```

**Optional:** Keep as archived submodule reference:
```bash
# Don't remove, just document in commit message
git add {LANG}{VERSION}
git commit -m "Archive {LANG}{VERSION} submodule pointer

{Language} {VERSION} reached EOL on {DATE}.
- Workflows disabled
- Removed from {pipeline}/Makefile
- Repository archived
- Packages remain available in APT repo"
git push origin main
```

### Step 7: Announce Retirement

Communicate the retirement to users:

**Create GitHub Discussion/Issue:**
```markdown
# {Language} {VERSION} Retired

{Language} {VERSION} has been retired from the Dockershelf packaging pipeline.

## Timeline
- **EOL Date**: {DATE}
- **Last Build**: {DATE}
- **Repository Archived**: {DATE}

## What This Means
- ✅ Existing packages remain available in the APT repository
- ✅ You can continue using `apt install {package-name}`
- ❌ No new builds or security updates
- ❌ GitHub repository is now read-only

## Migration Path
Upgrade to a supported version:
- {Language} {NEXT_VERSION} (supported until {DATE})
- {Language} {LATEST_VERSION} (latest stable)

## Support Policy
Dockershelf maintains versions for N years after upstream release.
See: https://github.com/Dockershelf/dockershelf-pipeline#support-policy
```

---

## Quick Reference Commands

| Step | Command | Working Directory |
|------|---------|-------------------|
| Comment schedule | Edit `.github/workflows/main.yml`, comment `schedule:` block | `{LANG}{VERSION}/` |
| Update Makefile | Remove version from `{LANG}_VERSIONS` | `{lang}-pipeline/` |
| Add notice | Prepend archive warning to `README.md` | `{LANG}{VERSION}/` |
| Archive repo | `gh repo archive Dockershelf/{LANG}{VERSION} --yes` | Any |
| Remove submodule | `git rm {LANG}{VERSION}` | `dockershelf-pipeline/` |
| Commit parent | `git commit -m "Archive {LANG}{VERSION} submodule pointer"` | `dockershelf-pipeline/` |

---

## Examples by Language

### Retire Node.js 16

```bash
# Step 1: Disable workflow
cd node16
# Edit .github/workflows/main.yml, comment schedule
git add .github/workflows/main.yml
git commit -m "Retire node16: disable scheduled builds"
git push origin main

# Step 2: Remove from pipeline
cd ../node-pipeline
# Edit Makefile: NODE_VERSIONS := 18 20 22 24
git add Makefile
git commit -m "Retire node16: remove from active versions"
git push origin main

# Step 3: Add archive notice
cd ../node16
# Prepend archive warning to README.md
git add README.md
git commit -m "Add archive notice to README"
git push origin main

# Step 4: Archive repository
gh repo archive Dockershelf/node16 --yes

# Step 5: Update parent
cd ..
git add node16 node-pipeline
git commit -m "Retire node16: EOL Sep 2023"
git push origin main
```

### Retire Python 3.10

```bash
# Step 1: Disable workflow
cd py3.10
# Edit .github/workflows/main.yml, comment schedule
git add .github/workflows/main.yml
git commit -m "Retire py3.10: disable scheduled builds"
git push origin main

# Step 2: Remove from pipeline
cd ../python-pipeline
# Edit Makefile: PY_VERSIONS := 3.11 3.12 3.13 3.14
git add Makefile
git commit -m "Retire py3.10: remove from active versions"
git push origin main

# Step 3: Add archive notice
cd ../py3.10
# Prepend archive warning to README.md
git add README.md
git commit -m "Add archive notice to README"
git push origin main

# Step 4: Archive repository
gh repo archive Dockershelf/py3.10 --yes

# Step 5: Update parent
cd ..
git add py3.10 python-pipeline
git commit -m "Retire py3.10: approaching EOL Oct 2026"
git push origin main
```

### Retire Go 1.20

```bash
# Step 1: Disable workflow
cd go1.20
# Edit .github/workflows/main.yml, comment schedule
git add .github/workflows/main.yml
git commit -m "Retire go1.20: disable scheduled builds"
git push origin main

# Step 2: Remove from pipeline
cd ../go-pipeline
# Edit Makefile: GO_VERSIONS := 1.21 1.22 1.23 1.24 1.25
git add Makefile
git commit -m "Retire go1.20: remove from active versions"
git push origin main

# Step 3: Add archive notice
cd ../go1.20
# Prepend archive warning to README.md
git add README.md
git commit -m "Add archive notice to README"
git push origin main

# Step 4: Archive repository
gh repo archive Dockershelf/go1.20 --yes

# Step 5: Update parent
cd ..
git add go1.20 go-pipeline
git commit -m "Retire go1.20: EOL Feb 2024"
git push origin main
```

---

## Troubleshooting

### Cannot Archive: "Repository has open pull requests"

**Symptom:** GitHub refuses to archive due to open PRs

**Solution:**
1. Close or merge all open pull requests
2. Retry archive operation
3. Or: Use force flag if available via API

### Workflow Still Runs After Commenting Schedule

**Symptom:** Scheduled builds still trigger

**Solution:**
1. Verify the comment syntax (YAML comments use `#`)
2. Check for duplicate workflow files
3. Alternative: Delete workflow file entirely

### Users Complaining About Missing Packages

**Symptom:** Users report broken `apt install`

**Solution:**
- **Clarify:** Existing packages are NOT deleted from APT repository
- **Verify:** Check APT repo still has the packages
- **Document:** Emphasize in announcement that packages remain available
- **Support:** Provide migration instructions for new versions

### Accidentally Archived Wrong Repository

**Symptom:** Wrong version was archived

**Solution:**
```bash
# Unarchive via GitHub CLI
gh repo unarchive Dockershelf/{LANG}{VERSION} --yes

# Or via API
curl -X PATCH \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/Dockershelf/{LANG}{VERSION}" \
  -d '{"archived":false}'
```

### Pipeline Makefile Syntax Error After Edit

**Symptom:** `make` fails with syntax error

**Solution:**
1. Verify space-separated list format: `VERSIONS := 18 20 22`
2. No trailing commas or extra spaces
3. Test with: `make list-dists` or similar

---

## Related Skills

- **discover-new-versions:** Find new versions to add (opposite of retire)
- **add-node-version:** Add new Node.js versions
- **add-python-version:** Add new Python versions
- **add-go-version:** Add new Go versions

---

## Execution Checklist

- [ ] Verify upstream EOL status and date
- [ ] Announce retirement plan to users (1-2 weeks notice)
- [ ] Comment out or remove workflow schedule
- [ ] Remove version from pipeline Makefile
- [ ] Add archive notice to repository README
- [ ] Archive GitHub repository
- [ ] Update parent repository submodule pointer
- [ ] Post retirement announcement
- [ ] Update support policy documentation
- [ ] Monitor for user issues or questions

---

## Key Principles

1. **Graceful degradation:** Existing packages remain available
2. **Communication first:** Announce before retiring
3. **Preserve history:** Archive, don't delete
4. **Emergency access:** Keep manual workflow dispatch option
5. **Progressive workflow:** Disable → Document → Archive → Update
6. **User-centric:** Provide clear migration paths

---

## Archive Notice Template

Use this template for the repository README:

```markdown
> **⚠️ ARCHIVED: This repository has been retired**
> 
> **{Language} {VERSION}** reached End of Life on **{EOL_DATE}** and is no longer receiving updates from upstream.
> 
> ### What This Means
> - ❌ **No new builds** will be published to the Dockershelf APT repository
> - ❌ **No security updates** will be provided
> - ❌ **This repository is now read-only** (archived)
> - ✅ **Existing packages remain available** for download via `apt install`
> - ✅ **Docker images remain available** on GHCR
> 
> ### Last Build Information
> - **Last successful build:** {LAST_BUILD_DATE}
> - **Last published version:** {PACKAGE_VERSION}
> 
> ### Migration Path
> Please upgrade to a supported version:
> - **{Language} {NEXT_VERSION}** (supported until {NEXT_EOL})
> - **{Language} {LATEST_VERSION}** (latest stable, recommended)
> 
> See the [Dockershelf {Language} Pipeline](https://github.com/Dockershelf/{lang}-pipeline) for currently supported versions.
> 
> ### Support Policy
> Dockershelf follows upstream EOL schedules:
> - **Node.js:** [Release Schedule](https://github.com/nodejs/release#release-schedule)
> - **Python:** [Version Schedule](https://devguide.python.org/versions/)
> - **Go:** [Release Policy](https://go.dev/doc/devel/release)
> 
> ---
> 
> _Archived on {ARCHIVE_DATE} by the Dockershelf maintainers._
```

---

## Communication Timeline

**Recommended retirement schedule:**

| Timeline | Action |
|----------|--------|
| **EOL - 3 months** | Announce upcoming retirement, encourage migration |
| **EOL** | Add deprecation warning to README |
| **EOL + 3 months** | Comment out workflow schedule (stop new builds) |
| **EOL + 6 months** | Archive repository, remove from pipeline |
| **EOL + 12 months** | Optional: Remove from APT repository |

---

## Verification After Retirement

Confirm successful retirement:

```bash
# 1. Verify workflow disabled
gh workflow list --repo Dockershelf/{LANG}{VERSION}
# Should show "disabled" or no scheduled workflows

# 2. Verify repository archived
gh repo view Dockershelf/{LANG}{VERSION} --json isArchived
# Should return: {"isArchived": true}

# 3. Verify removed from pipeline
grep "{VERSION}" {lang}-pipeline/Makefile
# Should return nothing

# 4. Verify packages still available
curl -I https://apt.dockershelf.example/debian/pool/main/{package}
# Should return: HTTP 200 OK
```

---

## Rollback Procedure

If retirement was premature:

```bash
# 1. Unarchive repository
gh repo unarchive Dockershelf/{LANG}{VERSION} --yes

# 2. Re-enable workflow
cd {LANG}{VERSION}
# Uncomment schedule in .github/workflows/main.yml
git add .github/workflows/main.yml
git commit -m "Rollback retirement: re-enable workflows"
git push origin main

# 3. Re-add to pipeline Makefile
cd ../{lang}-pipeline
# Add version back to VERSIONS variable
git add Makefile
git commit -m "Rollback retirement: restore {VERSION} to pipeline"
git push origin main

# 4. Update parent repository
cd ..
git add {LANG}{VERSION} {lang}-pipeline
git commit -m "Rollback {LANG}{VERSION} retirement"
git push origin main
```
