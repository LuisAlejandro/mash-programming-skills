---
name: rosey-lint
description: Runs lint, format, type-check, and build commands for the current repository by intelligently discovering the project's tooling (e.g., package.json scripts, Makefiles, pyproject.toml). Use when the user asks to lint or format the codebase, fix linter errors, or invokes rosey-lint.
disable-model-invocation: true
---

## Communication while using this skill

**Caveman lite** for all assistant prose while this skill runs: strip filler and hedging; keep articles and full sentences; stay professional and tight. Technical accuracy unchanged; quoted errors and code unchanged. Drop lite only for security warnings, irreversible confirmations, or when the user asks for normal or long-form wording.

# Rosey Lint & Build

## Purpose

Intelligently discover and run the formatting, linting, type-checking, and build pipelines for the current repository. This skill is language and framework agnostic. Instead of assuming commands, it inventories the repository's configuration files to determine the correct way to verify the code.

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

Always execute the discovered commands in the following order. Stop and report if any step fails, unless the step automatically fixes the issues (like `eslint --fix`).

1. **Format** (e.g., `npm run format`, `black .`, `go fmt`)
2. **Lint** (e.g., `npm run lint`, `ruff check .`, `go vet`)
3. **Typecheck** (e.g., `npm run typecheck`, `mypy .`)
4. **Build** (e.g., `npm run build`, `go build`) - Run this *after* all previous steps succeed to catch bundler/framework errors.

### 3. Missing Tools

If the repository lacks configuration for a specific step (e.g., no `typecheck` script in `package.json`), **skip that step** and briefly note it in your final report.

Do **not** install missing CLIs globally or attempt to guess commands that aren't defined in the project's configuration files (e.g., don't run `npx eslint .` if ESLint isn't in `package.json`).

### 4. Error Handling

If a command fails:
1. Attempt to fix the code automatically if the errors are obvious (e.g., fixing a typo, removing an unused import).
2. Run the command again to verify.
3. If the errors are complex or require architectural decisions, stop and ask the user how to proceed, providing the error output.

## Example Workflow

```text
User: Run rosey-lint

→ Discovering tooling...
  Found package.json. Package manager: npm.
  Found scripts: "format", "lint", "build". No "typecheck" script found.

→ Running npm run format... OK
→ Running npm run lint... OK
→ Typecheck skipped (no script defined)
→ Running npm run build... OK

All checks passed!
```