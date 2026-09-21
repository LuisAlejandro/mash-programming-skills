---
name: rosey-lint
description: "Runs lint, format, type-check, and build commands scoped to this session's changed files by default (whole repo with --all), discovering the project's tooling (package.json scripts, Makefiles, pyproject.toml). Use when the user asks to lint or format, or invokes rosey-lint."
---

## Communication while using this skill

**Caveman ultra** for assistant status prose while this skill runs: abbreviate routine workflow words, strip conjunctions where safe, use arrows for causality, and keep one word when one word is enough. Technical accuracy unchanged; command names, code symbols, quoted errors, and command output unchanged. Drop ultra for security warnings, irreversible confirmations, complex failure explanations, user confusion, or when the user asks for normal or long-form wording.

**Output boundary:** Caveman ultra applies to chat/status prose, not raw lint output, build logs, structured failure reports, or code fixes.

# Rosey Lint & Build

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation.
- `mode:non-interactive` — scripted or skill-to-skill execution. Do not ask the user how to proceed.

Strip the interaction mode token before interpreting any remaining arguments. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

## Scope

**Default: this session's files.** Run formatting/linting on the files this session created or modified (`FILES_CHANGED`, or the working-tree diff vs `HEAD`). Type-check and build are skipped by default (whole-repo steps churn unrelated WIP); note `skipped` with a reason. If there are no session files, emit `LINT_STATUS: skipped` and stop.

**Whole repo:** pass `--all` (or the user asks for a full pass) to run the repo's standard scripts (`npm run format/lint`, `make lint`, etc.) over everything.

Prefer commands that accept a file list over whole-repo scripts; whole-repo scripts are for `--all`.

## Purpose

Intelligently discover and run the formatting, linting, type-checking, and build pipelines for this session's changed files (whole repo only with `--all`). This skill is language and framework agnostic. Instead of assuming commands, it inventories the repository's configuration files to determine the correct way to verify the code.

## Execution Steps

### 1. Tooling Inventory (Discovery)

Before running any commands, inspect the repository to determine what tools are available.

- **Node/TypeScript (`package.json`)**:
  - Read `package.json` to find the package manager (`npm`, `yarn`, `pnpm`, `bun`). Look for `packageManager` field or lockfiles (`yarn.lock`, `pnpm-lock.yaml`, etc.).
  - Inspect the `"scripts"` block for standard verification commands:
    - Formatting: `format`, `prettier`, `prettier:fix`
    - Linting: `lint`, `lint:fix`, `eslint`
    - Type-checking: `typecheck`, `check`, `tsc`
    - Building: `build`
- **Python (`pyproject.toml` / `requirements.txt` / `Makefile`)**:
  - Look for formatting and linting tools configured in `pyproject.toml` or `tox.ini` (e.g., `ruff`, `black`, `flake8`, `mypy`, `isort`).
  - Check if `pre-commit` is used (`.pre-commit-config.yaml`).
  - Determine the environment manager (`uv`, `poetry`, `pipenv`, `pip`).
- **Go (`go.mod`)**:
  - Standard commands: `go fmt ./...`, `go vet ./...`, `go build ./...`
- **Rust (`Cargo.toml`)**:
  - Standard commands: `cargo fmt`, `cargo clippy`, `cargo build`
- **Task Runners (`Makefile`, `Taskfile.yml`, `Justfile`)**:
  - If a Makefile exists, inspect it for targets like `make lint`, `make format`, `make check`, `make build`. These often wrap the underlying tools and should be preferred if present.

### 2. Execution Pipeline

If there are no session files, skip all steps and emit `LINT_STATUS: skipped`.

Otherwise execute in order, scoped to `FILES_CHANGED` (or whole-repo when `--all`). Stop and report if any step fails, unless the step automatically fixes the issues (like `eslint --fix`).

1. **Format** session files (e.g., `prettier --write <files>`, `ruff format <files>`, `gofmt -w <files>`)
2. **Lint** session files (e.g., `eslint <files>`, `ruff check <files>`, `go vet` on the touched packages)
3. **Typecheck** — session-scoped: skip unless it can be limited to the touched packages; whole-repo `tsc` / `mypy .` is skipped by default and noted
4. **Build** — skipped by default in session scope; run only on `--all` or explicit user request

### 3. Missing Tools

If the repository lacks configuration for a specific step (e.g., no `typecheck` script in `package.json`), **skip that step** and briefly note it in your final report.

Do **not** install missing CLIs globally or attempt to guess commands that aren't defined in the project's configuration files (e.g., don't run `npx eslint .` if ESLint isn't in `package.json`).

### 4. Error Handling

If a command fails:
1. Attempt to fix the code automatically if the errors are obvious (e.g., fixing a typo, removing an unused import).
2. Run the command again to verify.
3. If the errors are complex or require architectural decisions, stop and provide the error output. In interactive mode, ask the user how to proceed. In non-interactive mode, emit `LINT_HANDOFF` with `LINT_STATUS: failed` and do not prompt.

### 5. Handoff Output

In `mode:non-interactive`, emit this block before finishing (required):

```text
LINT_HANDOFF
STEPS:
- format: pass|failed|skipped
- lint: pass|failed|skipped
- typecheck: pass|failed|skipped
- build: pass|failed|skipped
LINT_STATUS: pass|failed|skipped
BLOCKERS: <none | one-line>
END_LINT_HANDOFF
```

In interactive mode, emit the same block when automation or a parent skill requests it.

## Example Workflow

```text
User: Run rosey-lint

→ Discovering tooling...
  Found package.json. Package manager: npm.
  Session files: src/foo.ts

→ prettier --write src/foo.ts... OK
→ eslint src/foo.ts... OK
→ Typecheck skipped (whole-repo tsc)
→ Build skipped (session scope)

All session checks passed!
```