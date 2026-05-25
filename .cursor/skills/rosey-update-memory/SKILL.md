---
name: rosey-update-memory
description: Captures git log snapshots, analyzes recent commits, updates the Memory Bank files (progress, techContext, systemPatterns), and records the new HEAD SHA. Use when the user says "Update Memory Bank" or wants the Memory Bank synced to recent git history.
---

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, or when the user asks for normal or long-form wording.

# Memory Bank Update Protocol

Execute these steps **in order** without asking for confirmation.

## Step 1 — Capture git log snapshot

Run this in the terminal to capture new commits:

```bash
bash .cursor/scripts/memory-update.sh
```

## Step 2 — Read snapshot

Read the full content of `docs/memory-bank/_diffs/recent.tmp`. If it is empty, stop and report that there are no new commits since the last update.

## Step 3 — Analyze the changes

Infer from **commit messages** (and bodies) what mattered:
- New patterns or conventions introduced
- Changes to folder structure or file organization
- New dependencies or tooling added
- Architectural decisions made
- Completed tasks or new work started

## Step 4 — Map changes to Memory Bank files

Update the files in `docs/memory-bank/`:

- **`systemPatterns.md`**: Update when you observe new coding patterns, architectural decisions, naming conventions, or structural organization.
- **`techContext.md`**: Update when you observe changes to setup, tooling, environment, dependencies, or infrastructure.
- **`progress.md`**: Update when you observe completed work, key decisions, or active/resolved blockers. Format entries by feature or ticket, summarizing the actual implementation. Keep only the "Current Status" and the last 30–60 days of history.

## Step 5 — Report what changed

Respond with a combined report listing which files were modified and why.

## Step 6 — Record HEAD (required)

Write the current `HEAD` SHA so the next capture run only includes new commits:

```bash
bash .cursor/scripts/memory-update.sh --record
```