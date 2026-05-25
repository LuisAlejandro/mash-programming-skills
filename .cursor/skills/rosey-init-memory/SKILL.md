---
name: rosey-init-memory
description: Bootstraps the Memory Bank for the current repository by analyzing its static architecture, dependencies, and structure, then records the baseline HEAD SHA. Use when setting up the environment for the first time or when memory-bank files are missing.
---

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, or when the user asks for normal or long-form wording.

# Initialize Memory Bank (rosey-init-memory)

## Goal

Bootstrap the `docs/memory-bank/` files for the repository by analyzing its static structure, configuration files, and dependencies. 

**CRITICAL RULE:** Do NOT use generic boilerplate like "Standard architecture" or "Unknown dependencies". You MUST base the documentation on actual files found in the repository.

## Step 1 — Structural Reconnaissance

Gather high-level context using fast shell commands and targeted file reads. 
1. **Directory Structure:** Run `ls -laR | grep ":$" | head -n 20` to understand the layout.
2. **Dependencies:** Read `package.json`, `go.mod`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, etc.
3. **Infrastructure:** Read `docker-compose.yml`, `Dockerfile`, or deployment manifests if they exist.
4. **Documentation:** Read the `README.md`.

## Step 2 — Generate `techContext.md`

Create `docs/memory-bank/techContext.md`.
- **Tech Stack:** List the specific languages, frameworks, and build tools found in Step 1.
- **Infrastructure Dependencies:** Explicitly list databases, queues, or caches found.

## Step 3 — Generate `systemPatterns.md`

Create `docs/memory-bank/systemPatterns.md`.
- Document the overarching architecture based on the folder structure.
- Document key structural conventions with actual paths.
- **FORBIDDEN:** Do not write "Follow standard conventions". You must list the actual conventions found.

## Step 4 — Generate `progress.md`

Create `docs/memory-bank/progress.md`.
Add: *"Memory Bank initialized on [Current Date]. Awaiting first incremental update."*

## Step 5 — Set the Baseline SHA

Run:
```bash
mkdir -p docs/memory-bank/_state
git rev-parse HEAD > docs/memory-bank/_state/HEAD.sha
```