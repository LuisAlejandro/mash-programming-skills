---
name: rosey-design-system
description: Creates an OpenDesign design-system package from a local folder through the OpenDesign daemon API, optionally applies a revision, publishes it, and copies the package to docs/design-system. Use before rosey-design-catalog when the user needs OpenDesign to produce the DESIGN.md package first.
---

# Create OpenDesign Design System Package

## Communication while using this skill

**Caveman full** for assistant status prose while this skill runs: drop articles, use fragments when clear, prefer short synonyms, and keep technical terms exact. Technical accuracy unchanged; quoted errors, code, API payloads, and command output unchanged. Drop full for security warnings, irreversible confirmations, ambiguous multi-step instructions, user confusion, required input questions, or when the user asks for normal or long-form wording.

**Artifact boundary:** Caveman full applies to chat and status prose, not copied `DESIGN.md` content, async manifests, daemon responses, generated package metadata, or validation output.

## Overview

Use this skill to create the OpenDesign design-system package that becomes input for `rosey-design-catalog`.

The workflow imports a local folder through the OpenDesign daemon, optionally applies one revision, publishes the package, copies it to `docs/design-system`, and writes an async manifest. `rosey-design-catalog` may run later and auto-discover `docs/design-system/DESIGN.md`.

## Inputs

Ask for or infer:

- `sourceDir`: required absolute path to a local folder containing `DESIGN.md`.
- `name`: optional display name for the OpenDesign design system.
- `revisionFeedback`: optional feedback to apply after import.
- `sectionTitle`: optional target section for revision feedback.
- `daemonUrl`: optional, default `http://127.0.0.1:7456`.
- `importMode`: optional, default `hybrid`.
- `openDesignProjectRoot`: optional, used to resolve `.od` when `OD_DATA_DIR` is unset.

## Workflow

### Step 1: Validate Source

The source must be an absolute directory with root `DESIGN.md`.

```bash
command -v curl >/dev/null
command -v jq >/dev/null

test "${SOURCE_DIR#/}" != "$SOURCE_DIR"
test -d "$SOURCE_DIR"
test -f "$SOURCE_DIR/DESIGN.md"

DAEMON="${DAEMON:-http://127.0.0.1:7456}"
curl -fsS --max-time 5 "$DAEMON/health" >/dev/null \
  || curl -fsS --max-time 5 "$DAEMON/api/design-systems" >/dev/null
```

Do not import folders under OpenDesign runtime data.

### Step 2: Import Local Folder

Prefer the daemon HTTP API. CLI write coverage is incomplete; use `od design-systems show` only for readback.

```bash
DAEMON="${DAEMON:-http://127.0.0.1:7456}"

DS=$(curl -fsS --max-time 30 -X POST "$DAEMON/api/design-systems/import/local" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n \
    --arg baseDir "$SOURCE_DIR" \
    --arg name "$DESIGN_SYSTEM_NAME" \
    --arg importMode "${IMPORT_MODE:-hybrid}" \
    '{
      baseDir: $baseDir,
      importMode: $importMode
    } + (if $name == "" then {} else {name: $name} end)')" \
  | jq -r '.designSystem.id')

test "$DS" != "null"
echo "Imported design system: $DS"
```

### Step 3: Apply Revision When Requested

Skip this step when `revisionFeedback` is empty. Revision jobs create pending changes; accept the `revisionId` returned by the completed job. Do not query “latest pending”, because concurrent jobs can create unrelated pending revisions.

```bash
JOB=$(curl -fsS --max-time 30 -X POST "$DAEMON/api/design-systems/$DS/revision-jobs" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n \
    --arg feedback "$REVISION_FEEDBACK" \
    --arg sectionTitle "$SECTION_TITLE" \
    '{
      feedback: $feedback
    } + (if $sectionTitle == "" then {} else {sectionTitle: $sectionTitle} end)')" \
  | jq -r '.job.id')

STATUS=queued
ATTEMPTS=0
until [ "$STATUS" = "succeeded" ] || [ "$STATUS" = "failed" ]; do
  ATTEMPTS=$((ATTEMPTS + 1))
  test "$ATTEMPTS" -le 120
  sleep 1
  STATUS=$(curl -fsS --max-time 10 "$DAEMON/api/design-systems/generation-jobs/$JOB" | jq -r .job.status)
done

JOB_JSON=$(curl -fsS --max-time 10 "$DAEMON/api/design-systems/generation-jobs/$JOB")
echo "$JOB_JSON" | jq '{status: .job.status, revisionId: .job.revisionId, error: .job.error}'

test "$STATUS" = "succeeded"

REV=$(echo "$JOB_JSON" | jq -r '.job.revisionId')

test "$REV" != "null"

curl -fsS --max-time 30 -X PATCH "$DAEMON/api/design-systems/$DS/revisions/$REV" \
  -H 'Content-Type: application/json' \
  -d '{"status":"accepted"}' | jq .
```

### Step 4: Publish

```bash
curl -fsS --max-time 30 -X PATCH "$DAEMON/api/design-systems/$DS" \
  -H 'Content-Type: application/json' \
  -d '{"status":"published"}' | jq -r '.designSystem.status'
```

Optional readback:

```bash
od design-systems show "$DS" --json | jq '.body' -r
```

### Step 5: Copy Package

User design systems live under `${OD_DATA_DIR:-<openDesignProjectRoot>/.od}/design-systems/<slug>`. The slug is the part after `user:`. This workflow intentionally removes the previous `docs/design-system` before copying the latest package.

```bash
case "$DS" in
  user:*) SLUG="${DS#user:}" ;;
  *) echo "Unsupported design-system id: $DS" >&2; exit 1 ;;
esac

if [ -n "$OD_DATA_DIR" ]; then
  OD_ROOT="$OD_DATA_DIR"
else
  test -n "$OPENDESIGN_PROJECT_ROOT"
  OD_ROOT="$OPENDESIGN_PROJECT_ROOT/.od"
fi

PACKAGE_DIR="$OD_ROOT/design-systems/$SLUG"

test -d "$PACKAGE_DIR"

rm -rf docs/design-system
mkdir -p docs/design-system
cp -R "$PACKAGE_DIR"/. docs/design-system/

test -f docs/design-system/DESIGN.md

mkdir -p docs/designs
jq -n \
  --arg designSystemId "$DS" \
  --arg sourceDir "$SOURCE_DIR" \
  --arg packageDir "$PACKAGE_DIR" \
  --arg copiedPath "docs/design-system" \
  --arg designPath "docs/design-system/DESIGN.md" \
  --arg checksum "$(shasum -a 256 docs/design-system/DESIGN.md | awk '{print $1}')" \
  --arg copiedAt "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{
    designSystemId: $designSystemId,
    sourceDir: $sourceDir,
    packageDir: $packageDir,
    copiedPath: $copiedPath,
    designPath: $designPath,
    designChecksum: $checksum,
    copiedAt: $copiedAt
  }' > docs/designs/design-system.json
```

## Handoff

After copying succeeds, report:

- OpenDesign design-system id.
- Whether revision feedback was applied.
- Copied package path: `docs/design-system`.
- Async manifest path: `docs/designs/design-system.json`.

`rosey-design-catalog` can be invoked later; it auto-discovers `docs/design-system/DESIGN.md`.
