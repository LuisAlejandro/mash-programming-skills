---
name: discover-new-versions
description: 'Monitor for new major/minor versions of Node.js, Python, or Go and orchestrate the appropriate add-version skill. Use when: checking for new upstream releases, automating version discovery, planning pipeline updates, determining if node26/py3.15/go1.26 exists. Queries upstream APIs/repos to detect new release lines not yet in the pipeline. For Node.js, only even-numbered versions are considered (LTS policy).'
argument-hint: 'Optional: specific language (node, python, go) or check all'
---

# Discover New Language Versions

**Purpose:** Detect new major/minor versions of Node.js, Python, or Go that exist upstream but aren't yet registered in the Dockershelf packaging pipeline, then orchestrate the appropriate add-version skill.

**Scope:** This skill focuses on discovering NEW major/minor release lines (e.g., Node 26, Python 3.15, Go 1.26), not patch updates within existing lines. **For Node.js, only even-numbered versions are considered**, as odd-numbered versions never become LTS.

---

## When to Use

Invoke this skill when you need to:
- Check if new upstream versions have been released
- Automate periodic version discovery
- Plan pipeline expansion for new release lines
- Determine whether to add a new version before manually invoking add-node-version, add-python-version, or add-go-version
- Monitor multiple language ecosystems simultaneously

## What This Skill Does NOT Do

- **Patch version discovery:** Use `meta-gbp update` for patch bumps within existing lines
- **Build or publish:** Only discovers and plans; doesn't execute builds
- **Manual intervention:** Automatically orchestrates the add-version skill but respects prerequisites

---

## Discovery Strategy by Language

### Node.js

**Upstream source:** https://github.com/nodejs/node/branches

**Current pipeline versions:** Read from `node-pipeline/Makefile` → `NODE_VERSIONS`

**Detection logic:**
1. Query GitHub API for branches matching pattern `v{MAJOR}.x` (e.g., `v26.x`, `v28.x`)
2. Extract major version numbers from branch names
3. **Filter for even-numbered versions only** (Node.js LTS policy: only even versions become LTS)
4. Compare against `NODE_VERSIONS` in Makefile
5. New version found when branch exists, version is even, and major not in `NODE_VERSIONS`

**API endpoint:**
```bash
curl -fsSL https://api.github.com/repos/nodejs/node/branches \
  | jq -r '.[].name' \
  | grep -E '^v[0-9]+\.x$' \
  | sed 's/^v//; s/\.x$//' \
  | sort -n
```

### Python

**Upstream source:** https://github.com/python/cpython/branches

**Current pipeline versions:** Read from `python-pipeline/Makefile` → `PY_VERSIONS`

**Detection logic:**
1. Query GitHub API for branches matching pattern `{MAJOR}.{MINOR}` (e.g., `3.15`, `3.16`)
2. Filter for Python 3.x branches (exclude 2.x, main, etc.)
3. Compare against `PY_VERSIONS` in Makefile
4. New version found when branch exists but not in `PY_VERSIONS`

**API endpoint:**
```bash
curl -fsSL https://api.github.com/repos/python/cpython/branches \
  | jq -r '.[].name' \
  | grep -E '^3\.[0-9]+$' \
  | sort -V
```

### Go

**Upstream source:** https://github.com/golang/go/branches

**Current pipeline versions:** Read from `go-pipeline/Makefile` → `GO_VERSIONS`

**Detection logic:**
1. Query GitHub API for branches matching pattern `release-branch.go{MAJOR}.{MINOR}` (e.g., `release-branch.go1.26`)
2. Extract version numbers from branch names
3. Compare against `GO_VERSIONS` in Makefile
4. New version found when branch exists but not in `GO_VERSIONS`

**API endpoint:**
```bash
curl -fsSL https://api.github.com/repos/golang/go/branches \
  | jq -r '.[].name' \
  | grep -E '^release-branch\.go[0-9]+\.[0-9]+$' \
  | sed 's/^release-branch\.go//' \
  | sort -V
```

---

## Workflow

### Step 1: Read Current Pipeline State

For each language, read the current version list from the respective Makefile:

```bash
# Node.js
grep '^NODE_VERSIONS :=' node-pipeline/Makefile

# Python
grep '^PY_VERSIONS :=' python-pipeline/Makefile

# Go
grep '^GO_VERSIONS :=' go-pipeline/Makefile
```

**Output format:**
- Node: `16 18 20 22 24`
- Python: `3.10 3.11 3.12 3.13 3.14`
- Go: `1.20 1.21 1.22 1.23 1.24 1.25`

### Step 2: Query Upstream APIs

For each language, fetch branch lists from GitHub:

```bash
# Node.js branches
curl -fsSL "https://api.github.com/repos/nodejs/node/branches?per_page=100" \
  | jq -r '.[].name' \
  | grep -E '^v[0-9]+\.x$'

# Python branches
curl -fsSL "https://api.github.com/repos/python/cpython/branches?per_page=100" \
  | jq -r '.[].name' \
  | grep -E '^3\.[0-9]+$'

# Go branches
curl -fsSL "https://api.github.com/repos/golang/go/branches?per_page=100" \
  | jq -r '.[].name' \
  | grep -E '^release-branch\.go[0-9]+\.[0-9]+$'
```

**Rate limits:** GitHub API allows 60 requests/hour unauthenticated, 5000/hour with token

**Optimization:** Set `GITHUB_TOKEN` environment variable for higher limits

### Step 3: Compute Differences

For each language:
1. Parse upstream branches to extract version numbers
2. **For Node.js:** Filter to keep only even-numbered versions (divisible by 2)
3. Parse current pipeline versions from Makefile
4. Find versions in upstream but NOT in pipeline
5. Report new versions discovered

**Example output:**
```
Node.js: Found new version 26 (branch v26.x exists, even-numbered)
         Skipped version 25 (odd-numbered, not LTS)
Python: Found new version 3.15 (branch 3.15 exists)
Go: No new versions detected
```

### Step 4: Orchestrate Add-Version Skills

For each newly discovered version:

1. **Verify prerequisites:**
   - GitHub repository exists: `Dockershelf/{LANG}{VERSION}`
   - Upstream branch is active (not just created)
   - First stable release exists (check tags)

2. **Invoke appropriate skill:**
   ```
   /add-node-version 26
   /add-python-version 3.15
   /add-go-version 1.26
   ```

3. **Report summary:**
   - Versions discovered
   - Skills invoked
   - Manual steps remaining (create GitHub repos, verify builds)

### Step 5: Enforce Exactly 5 Versions Per Language

**IMPORTANT:** Each language (Node.js, Python, Go) must maintain exactly 5 active versions. This step ensures the 5-version limit by retiring excess old versions before or after adding a new version.

**Policy:** Always maintain exactly 5 active versions per language.

**Workflow for each language:**

1. **Count current versions (before adding new version):**
   ```bash
   # Node.js
   NODE_COUNT=$(echo $NODE_VERSIONS | wc -w)
   
   # Python
   PY_COUNT=$(echo $PY_VERSIONS | wc -w)
   
   # Go
   GO_COUNT=$(echo $GO_VERSIONS | wc -w)
   ```

2. **Calculate how many versions to retire:**
   ```bash
   # If we have N current versions and want to add 1 new version,
   # we need to retire (N + 1 - 5) versions to end up with exactly 5
   
   RETIRE_COUNT=$((CURRENT_COUNT + 1 - 5))
   
   # Examples:
   # - 4 versions + 1 new = 5 total → retire 0 versions
   # - 5 versions + 1 new = 6 total → retire 1 version
   # - 6 versions + 1 new = 7 total → retire 2 versions
   # - 8 versions + 1 new = 9 total → retire 4 versions
   ```

3. **Retire oldest N versions (if RETIRE_COUNT > 0):**
   ```bash
   # Get the N oldest versions (first N items in the space-separated list)
   VERSIONS_TO_RETIRE=$(echo $VERSIONS | awk "{for(i=1;i<=$RETIRE_COUNT;i++) print \$i}")
   
   # Retire each one
   for version in $VERSIONS_TO_RETIRE; do
     /retire-version {lang}$version
   done
   ```

4. **Add the new version** (using appropriate add-version skill)

5. **Verify final count is exactly 5**

**Example scenarios:**

**Scenario 1: Currently 6 versions (Go)**
```
Before: GO_VERSIONS := 1.20 1.21 1.22 1.23 1.24 1.25  (6 versions)
Action: Add Go 1.26
Retire count: 6 + 1 - 5 = 2 versions to retire

Step 1: Retire oldest 2 versions
  - /retire-version go1.20
  - /retire-version go1.21
  Result: GO_VERSIONS := 1.22 1.23 1.24 1.25  (4 versions)

Step 2: Add new version
  - /add-go-version 1.26
  Result: GO_VERSIONS := 1.22 1.23 1.24 1.25 1.26  (5 versions ✓)
```

**Scenario 2: Currently 5 versions (Node.js)**
```
Before: NODE_VERSIONS := 16 18 20 22 24  (5 versions)
Action: Add Node.js 26
Retire count: 5 + 1 - 5 = 1 version to retire

Step 1: Retire oldest 1 version
  - /retire-version node16
  Result: NODE_VERSIONS := 18 20 22 24  (4 versions)

Step 2: Add new version
  - /add-node-version 26
  Result: NODE_VERSIONS := 18 20 22 24 26  (5 versions ✓)
```

**Scenario 3: Currently 8 versions (hypothetical)**
```
Before: VERSIONS := v1 v2 v3 v4 v5 v6 v7 v8  (8 versions)
Action: Add v9
Retire count: 8 + 1 - 5 = 4 versions to retire

Step 1: Retire oldest 4 versions
  - /retire-version v1
  - /retire-version v2
  - /retire-version v3
  - /retire-version v4
  Result: VERSIONS := v5 v6 v7 v8  (4 versions)

Step 2: Add new version
  - /add-version v9
  Result: VERSIONS := v5 v6 v7 v8 v9  (5 versions ✓)
```

**Important notes:**
- Retirement happens BEFORE adding the new version (to avoid temporary over-limit state)
- Multiple versions may be retired in a single discovery run
- Always retire the OLDEST (first) versions in the list
- Retirement is fully automated (no manual confirmation needed)
- If any retirement fails, abort the add operation and report the error

---

## Implementation Script

Here's a reference implementation for discovery:

```bash
#!/usr/bin/env bash
# discover-new-versions.sh
set -euo pipefail

WORKSPACE="${1:-.}"
cd "$WORKSPACE"

# Read current versions
NODE_CURRENT=$(grep '^NODE_VERSIONS :=' node-pipeline/Makefile | sed 's/NODE_VERSIONS := //')
PY_CURRENT=$(grep '^PY_VERSIONS :=' python-pipeline/Makefile | sed 's/PY_VERSIONS := //')
GO_CURRENT=$(grep '^GO_VERSIONS :=' go-pipeline/Makefile | sed 's/GO_VERSIONS := //')

echo "=== Current Pipeline Versions ==="
echo "Node.js: $NODE_CURRENT"
echo "Python: $PY_CURRENT"
echo "Go: $GO_CURRENT"
echo ""

# Query upstream Node.js (even versions only - LTS policy)
echo "=== Checking Node.js upstream ==="
NODE_UPSTREAM=$(curl -fsSL "https://api.github.com/repos/nodejs/node/branches?per_page=100" \
  | jq -r '.[].name' \
  | grep -E '^v[0-9]+\.x$' \
  | sed 's/^v//; s/\.x$//' \
  | awk '$1 % 2 == 0' \
  | sort -n)
echo "Upstream branches (even-numbered only): $(echo $NODE_UPSTREAM | tr '\n' ' ')"

for ver in $NODE_UPSTREAM; do
  if ! echo " $NODE_CURRENT " | grep -q " $ver "; then
    echo "🆕 NEW: Node.js $ver (branch v${ver}.x, even-numbered)"
  fi
done
echo ""

# Query upstream Python
echo "=== Checking Python upstream ==="
PY_UPSTREAM=$(curl -fsSL "https://api.github.com/repos/python/cpython/branches?per_page=100" \
  | jq -r '.[].name' \
  | grep -E '^3\.[0-9]+$' \
  | sort -V)
echo "Upstream branches: $(echo $PY_UPSTREAM | tr '\n' ' ')"

for ver in $PY_UPSTREAM; do
  if ! echo " $PY_CURRENT " | grep -q " $ver "; then
    echo "🆕 NEW: Python $ver (branch $ver)"
  fi
done
echo ""

# Query upstream Go
echo "=== Checking Go upstream ==="
GO_UPSTREAM=$(curl -fsSL "https://api.github.com/repos/golang/go/branches?per_page=100" \
  | jq -r '.[].name' \
  | grep -E '^release-branch\.go[0-9]+\.[0-9]+$' \
  | sed 's/^release-branch\.go//' \
  | sort -V)
echo "Upstream branches: $(echo $GO_UPSTREAM | tr '\n' ' ')"

for ver in $GO_UPSTREAM; do
  if ! echo " $GO_CURRENT " | grep -q " $ver "; then
    echo "🆕 NEW: Go $ver (branch release-branch.go$ver)"
  fi
done
```

---

## Quick Reference Commands

| Task | Command |
|------|---------|
| Check Node.js versions (even only) | `curl -fsSL https://api.github.com/repos/nodejs/node/branches \| jq -r '.[].name' \| grep '^v[0-9]*\.x$' \| sed 's/^v//;s/\.x$//' \| awk '$1 % 2 == 0'` |
| Check Python versions | `curl -fsSL https://api.github.com/repos/python/cpython/branches \| jq -r '.[].name' \| grep '^3\.[0-9]*$'` |
| Check Go versions | `curl -fsSL https://api.github.com/repos/golang/go/branches \| jq -r '.[].name' \| grep '^release-branch\.go'` |
| Read pipeline Node | `grep '^NODE_VERSIONS' node-pipeline/Makefile` |
| Read pipeline Python | `grep '^PY_VERSIONS' python-pipeline/Makefile` |
| Read pipeline Go | `grep '^GO_VERSIONS' go-pipeline/Makefile` |

---

## Troubleshooting

### GitHub API Rate Limit Exceeded

**Symptom:** `API rate limit exceeded` error from curl

**Solution:** Set `GITHUB_TOKEN` environment variable:
```bash
export GITHUB_TOKEN="ghp_YourPersonalAccessToken"
```

Or use conditional headers:
```bash
HEADERS=""
if [ -n "${GITHUB_TOKEN:-}" ]; then
  HEADERS="-H 'Authorization: token $GITHUB_TOKEN'"
fi
curl -fsSL $HEADERS https://api.github.com/repos/nodejs/node/branches
```

### False Positive: Branch Exists But No Releases

**Symptom:** Discovery finds a branch but no stable releases exist yet

**Solution:** Verify tags before invoking add-version skill:
```bash
# Check if any stable release tags exist
git ls-remote https://github.com/nodejs/node.git "refs/tags/v26.*" | grep -v 'rc\|beta'
```

### Branch Naming Convention Changed

**Symptom:** Regex doesn't match new upstream branch patterns

**Solution:** Update detection regex based on upstream conventions:
- Node.js: Historically `v{MAJOR}.x`, occasionally `v{MAJOR}.x-staging`
- Python: `{MAJOR}.{MINOR}`, sometimes `{MAJOR}.{MINOR}-dev`
- Go: `release-branch.go{MAJOR}.{MINOR}`, stable pattern

### Pipeline Makefile Format Changed

**Symptom:** `grep '^NODE_VERSIONS'` returns empty

**Solution:** Adjust parsing logic to match new Makefile format

---

## Integration with Add-Version Skills

When new versions are discovered:

1. **Node.js discovery → add-node-version:**
   ```
   Discovered: Node.js 26
   Action: /add-node-version 26
   Prerequisites: Create Dockershelf/node26 GitHub repo
   ```

2. **Python discovery → add-python-version:**
   ```
   Discovered: Python 3.15
   Action: /add-python-version 3.15
   Prerequisites: Create Dockershelf/py3.15 GitHub repo, identify source version (--from 3.14)
   ```

3. **Go discovery → add-go-version:**
   ```
   Discovered: Go 1.26
   Action: /add-go-version 1.26
   Prerequisites: Create Dockershelf/go1.26 GitHub repo
   ```

---

## Automation Scenarios

### Scheduled Discovery (Weekly Check)

Create a GitHub Actions workflow in the main repo:

```yaml
name: Discover New Versions

on:
  schedule:
    - cron: '0 12 * * 1'  # Monday noon UTC
  workflow_dispatch:

jobs:
  discover:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Discover new versions
        run: |
          # Run discovery script
          bash .github/skills/discover-new-versions/scripts/discover.sh
      - name: Create issues for new versions
        if: new versions found
        run: |
          # Auto-create GitHub issues with /add-{lang}-version prompts
```

### Manual Discovery

```bash
cd dockershelf-pipeline
/discover-new-versions
```

**Output:**
```
🔍 Checking upstream releases...

Node.js:
  Current: 16 18 20 22 24 (5 versions)
  Upstream (even only): 16 18 20 22 24 26
  Skipped: 25 (odd-numbered, not LTS)
  🆕 NEW: 26

Python:
  Current: 3.10 3.11 3.12 3.13 3.14 (5 versions)
  Upstream: 3.10 3.11 3.12 3.13 3.14 3.15
  🆕 NEW: 3.15

Go:
  Current: 1.20 1.21 1.22 1.23 1.24 1.25 (6 versions - EXCEEDS LIMIT!)
  Upstream: 1.20 1.21 1.22 1.23 1.24 1.25 1.26
  🆕 NEW: 1.26

📋 Execution plan:

Node.js 26:
  1. Current count: 5 versions
  2. After adding 26: would be 6 versions
  3. Need to retire: 6 - 5 = 1 version
  4. Retire: node16
  5. Add: node26
  6. Final: 18 20 22 24 26 (5 versions ✓)

Python 3.15:
  1. Current count: 5 versions
  2. After adding 3.15: would be 6 versions
  3. Need to retire: 6 - 5 = 1 version
  4. Retire: py3.10
  5. Add: py3.15
  6. Final: 3.11 3.12 3.13 3.14 3.15 (5 versions ✓)

Go 1.26:
  1. Current count: 6 versions (already over limit!)
  2. After adding 1.26: would be 7 versions
  3. Need to retire: 7 - 5 = 2 versions
  4. Retire: go1.20, go1.21
  5. Add: go1.26
  6. Final: 1.22 1.23 1.24 1.25 1.26 (5 versions ✓)

Prerequisites:
- Create GitHub repos: Dockershelf/node26, Dockershelf/py3.15, Dockershelf/go1.26
```

---

## Related Skills

- **add-node-version:** Add discovered Node.js versions to pipeline
- **add-python-version:** Add discovered Python versions to pipeline
- **add-go-version:** Add discovered Go versions to pipeline
- **retire-version:** Retire old versions to maintain the 5-version limit

---

## Execution Checklist

- [ ] GitHub API access available (check rate limits)
- [ ] `jq` installed for JSON parsing
- [ ] Workspace in correct directory (dockershelf-pipeline)
- [ ] All three pipeline Makefiles readable
- [ ] Count current versions for each language
- [ ] Calculate retirement needs: (current_count + 1 - 5) versions to retire
- [ ] GitHub repos ready to be created for new versions
- [ ] Review upstream release notes before adding
- [ ] Verify oldest versions can be retired (check for breaking changes)
- [ ] Check if oldest version repositories can be archived

---

## Key Principles

1. **Detect, don't build:** This skill only discovers new versions; it doesn't create infrastructure
2. **Major/minor focus:** Targets new release lines, not patch updates within existing lines
3. **Node.js LTS policy:** Only even-numbered Node.js versions are considered (16, 18, 20, 22, 24, 26, ...) since odd versions never become LTS
4. **Exactly 5 versions:** Enforces a strict limit of exactly 5 active versions per language at all times
5. **Bulk retirement:** May retire multiple versions in a single run (e.g., if 6 versions exist, retire 2 oldest when adding 1 new)
6. **Retire-then-add:** Always retires excess old versions BEFORE adding the new version
7. **Orchestration:** Automatically calls appropriate retire-version and add-version skills when needed
8. **Prerequisites validation:** Checks that prerequisites are met before invoking downstream skills
9. **Multi-language:** Handles Node.js, Python, and Go in a single invocation
10. **API-driven:** Uses GitHub APIs rather than scraping websites
11. **Idempotent:** Safe to run repeatedly; reports only net-new versions

---

## Advanced: Version Stability Checks

Before invoking add-version skills, optionally verify version stability:

### Node.js Stability
```bash
# Check if first stable release exists
git ls-remote https://github.com/nodejs/node.git "refs/tags/v26.0.0"
```

### Python Stability
```bash
# Check if Python 3.15.0 final exists (not alpha/beta/rc)
git ls-remote https://github.com/python/cpython.git "refs/tags/v3.15.0" | grep -v 'a[0-9]\|b[0-9]\|rc[0-9]'
```

### Go Stability
```bash
# Check if go1.26.0 tag exists
git ls-remote https://github.com/golang/go.git "refs/tags/go1.26.0"
```

**Decision logic:**
- If branch exists but no stable release: Report as "upcoming" but don't auto-invoke add-version
- If stable release exists: Proceed with add-version skill invocation
