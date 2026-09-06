---
name: rosey-lint
description: "Runs lint, format, type-check, and build commands for this session's files by discovering the project's tooling (for example package.json scripts, Makefiles, pyproject.toml). Use when the user asks to lint or format this session's changes, or invokes rosey-lint."
---

## Communication while using this skill

**Caveman ultra** for assistant status prose while this skill runs: abbreviate routine workflow words, strip conjunctions where safe, use arrows for causality, and keep one word when one word is enough. Technical accuracy unchanged; command names, code symbols, quoted errors, and command output unchanged. Drop ultra for security warnings, irreversible confirmations, complex failure explanations, user confusion, or when the user asks for normal or long-form wording.

**Output boundary:** Caveman ultra applies to chat/status prose, not raw lint output, build logs, structured failure reports, or code fixes.

# Rosey Lint & Build (live-home)

Read `references/livehome.md` first. This is a full live-home skill: stay on `master`/`main`, no PRs, no stashes, mixed dirty files expected.

## Interaction Mode

Parse `$ARGUMENTS` for at most one interaction mode token:

- `mode:interactive` — default for direct chat invocation.
- `mode:non-interactive` — scripted or skill-to-skill execution. Do not ask the user how to proceed.

Strip the interaction mode token before interpreting any remaining arguments. If no interaction mode token is present, set `INTERACTION_MODE=interactive`.

If multiple interaction mode tokens appear, stop and report the conflict.

## Purpose

Discover and run formatting, linting, type-checking, and (when cheap) build checks **for this session's files only**. The home is mixed and dirty. Never format or lint the whole tree. Host tooling is allowed; Docker-via-Make does not apply.

If `FILES_CHANGED` is empty and this session did not create or edit files, skip the pipeline and emit `LINT_STATUS: skipped`.

## Execution Steps

### 1. Tooling Inventory (Discovery)

Before running any commands, inspect the repository to determine what tools are available. Prefer commands that accept a file list over whole-repo scripts.

- **Node/TypeScript (`package.json`)**:
  - Read `package.json` to find the package manager (`npm`, `yarn`, `pnpm`, `bun`). Look for `packageManager` field or lockfiles (`yarn.lock`, `pnpm-lock.yaml`, etc.).
  - Inspect the `"scripts"` block for standard verification commands:
    - Formatting: `format`, `prettier`, `prettier:fix`
    - Linting: `lint`, `lint:fix`, `eslint`
    - Type-checking: `typecheck`, `check`, `tsc`
    - Building: `build`
  - Prefer invoking the underlying binary with session paths (e.g. `npx prettier --write <files>`, `npx eslint <files>`) over `npm run format` / `npm run lint` when those scripts walk the whole repo.
- **Python (`pyproject.toml` / `requirements.txt` / `Makefile`)**:
  - Look for formatting and linting tools configured in `pyproject.toml` or `tox.ini` (e.g., `ruff`, `black`, `flake8`, `mypy`, `isort`).
  - Check if `pre-commit` is used (`.pre-commit-config.yaml`).
  - Determine the environment manager (`uv`, `poetry`, `pipenv`, `pip`).
  - Host `python` / `ruff` / `black` on session files is allowed.
- **Go (`go.mod`)**:
  - Session-scoped: `gofmt` / `go vet` on the packages that contain session files, not `./...` unless that is the only option and the module is small.
- **Rust (`Cargo.toml`)**:
  - Prefer package-scoped `cargo fmt` / `cargo clippy` when session files sit in one crate.
- **Task Runners (`Makefile`, `Taskfile.yml`, `Justfile`)**:
  - Use Make targets only when they can be limited to session files. Skip whole-home `make format` / `make lint` / `make build`.

### 2. Execution Pipeline

If there are no session files, skip all steps and emit `LINT_STATUS: skipped`.

Otherwise execute in order, **scoped to `FILES_CHANGED`**. Stop and report if any step fails, unless the step automatically fixes the issues (like `eslint --fix`).

1. **Format** session files (e.g., `prettier --write <files>`, `ruff format <files>`, `gofmt -w <files>`)
2. **Lint** session files (e.g., `eslint <files>`, `ruff check <files>`)
3. **Typecheck** — skip unless the typechecker can be limited to session packages without rewriting unrelated dirty files. Whole-repo `tsc` / `mypy .` is skipped by default; note `typecheck: skipped`.
4. **Build** — skip by default on a live-home. Whole-repo builds churn unrelated WIP. Note `build: skipped`. Run a build only when the user explicitly asks.

### 3. Missing Tools

If the repository lacks configuration for a specific step, **skip that step** and briefly note it in your final report.

Do **not** install missing CLIs globally. Host binaries already on `PATH` are allowed.

### 4. Error Handling

If a command fails:
1. Attempt to fix **session files** automatically if the errors are obvious (e.g., fixing a typo, removing an unused import). Do not "fix" unrelated dirty files.
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

`LINT_STATUS: skipped` is valid when this session has no files to check.

In interactive mode, emit the same block when automation or a parent skill requests it.

## Example Workflow

```text
User: Run rosey-lint

→ Session files: src/foo.ts
→ Discovering tooling...
  Found package.json. Package manager: npm.

→ prettier --write src/foo.ts... OK
→ eslint src/foo.ts... OK
→ Typecheck skipped (whole-repo tsc)
→ Build skipped (live-home)

All session checks passed!
```