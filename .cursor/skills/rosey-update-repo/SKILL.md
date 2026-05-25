---
name: rosey-update-repo
description: Checks that the working tree is clean, checks out the main branch, pulls the latest changes from the remote, and then executes the rosey-update-memory skill. Use when syncing the local repository to main and refreshing the Memory Bank.
---

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, or when the user asks for normal or long-form wording.

# Update Repository

## Step 1 — Status (required)

Run:
```bash
git status --porcelain
```
If the output is NOT empty, **stop**. Tell the user the working tree is dirty and they must commit, stash, or remove changes first.

## Step 2 — Execute

In order, run:
```bash
git checkout main || git checkout master
git pull origin $(git rev-parse --abbrev-ref HEAD)
```

## Step 3 — Update Memory Bank

After the pull completes successfully, invoke the **rosey-update-memory** skill to capture git log snapshots, analyze commits, and update the `docs/memory-bank/` files.