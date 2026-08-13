# Repo Generation Prompt

Use this prompt content for each dynamic generation subagent.

## Goal

Generate common maintainer files that need repo-specific understanding. Do not commit changes.

**Do not regenerate** `MAINTAINER.md` / `MAINTAINER.rst` — static sync owns that file.

## Required Research

Inspect the repo before writing:

- package metadata (`pyproject.toml`, `setup.cfg`, `setup.py`, `package.json`, `Gemfile`)
- existing `README.*`, `CONTRIBUTING.*`, `RELEASE_DESCRIPTION.*`
- `Makefile` targets
- existing `Dockerfile` and `docker-compose.yml`
- source code references to environment variables
- existing `.env.example`, `.env.template`, `.env.sample`, `secrets.env`, or docs mentioning env vars
- existing `.bumpversion.cfg` and all version-bearing source files
- `Makefile` targets (docker lifecycle, release, preflight — repo-owned)
- `.github/workflows/pr.yml`, `push.yml` (repo-owned CI; see `workflow-generation.md`)
- `.github/dependabot.yml` (static sync when `ci-base` bundle)
- `tox.ini` and lockfiles (`yarn.lock`, `package-lock.json`)
- `Makefile` targets `image`, `dependencies`, `build`, `lint`, `format`, `test` (see `preflight-conventions.md`)
- GitHub workflows when they reveal supported runtimes, secrets, matrices, or caches

## Files To Generate

### README

- Overwrite `README.md` or `README.rst` according to the repo's existing documentation format.
- Keep content accurate to the repo's actual stack and purpose.
- Include: project summary, features or capabilities, local development, testing, release notes if relevant, and links to contribution docs for open-source repos.

### RELEASE_DESCRIPTION

- Overwrite `RELEASE_DESCRIPTION.md` or `RELEASE_DESCRIPTION.rst` according to existing docs format.
- Keep it short: one concise paragraph suitable for GitHub release descriptions.
- Describe the project, not the current diff.

### .env.example

- Overwrite `.env.example`.
- Scan source and docs for environment variables.
- Include every required or commonly referenced variable with safe placeholder values.
- Add brief comments only where helpful.
- Do not include real secrets or values from local `.env` files.

### CONTRIBUTING

- Generate only when `open_source: true`.
- Use `contributing-baseline.md`.
- Keep the structure and most wording consistent across open-source repos.
- Change only repo-specific names, URLs, setup commands, package layout, and checks.

### Docker Files

- Generate or update only when profile is `python` or `node`.
- Use `docker-generation.md`.
- Preserve necessary repo-specific dependencies discovered during research.

### .bumpversion.cfg

- Generate or overwrite when the repo uses release tooling (`ops-release` bundle).
- Use `bumpversion-generation.md`.
- Discover every file that embeds the project version and add a `[bumpversion:file:...]` section for each.
- Set `current_version` from the canonical version source in the repo.
- Add `[rosey-maintainer] post_bump_commands` when the repo needs steps after bump (e.g. monorepo `npm install`).

### tox.ini (python)

- When the repo uses tox for preflight, define `lint`, `format`, and `coverage` envs.
- `make test` must run the **coverage** env, not the multi-Python matrix (keep matrix as `test-all` or CI-only).
- **Ruff stack** (see `agoras`, `spices`): `lint` runs `ruff format --check`, `ruff check`, `pydocstyle`, `bandit`, and `pyright`; `format` runs `ruff format` plus `ruff check --fix` for unused imports. Tool config lives in `pyproject.toml` (static-sync managed).

### Makefile deduplication and preflight targets

- Use `makefile-dedup.md` and `preflight-conventions.md`.
- **Ensure** `image`, `dependencies`, `build`, `lint`, `format`, and `test` exist when profile is `python` or `node`. Implement missing targets in the repo.
- **Ensure** docker lifecycle targets (`image`, `start`, `stop`, `down`, `destroy`, `cataplum`) and release targets (`release`, `release-*`, `release-preflight`, `undo-release`) exist.
- Remove duplicate target definitions (each name at most once).
- Preserve repo-specific targets (`console`, `virtualenv`, etc.).

### GitHub Workflows (`pr.yml` CI security patch)

- When profile includes `ci-base` and `.github/workflows/pr.yml` exists, use `workflow-generation.md`.
- Run **last** after `.env.example`, Docker files, and Makefile work.
- **Do not** rewrite or create `pr.yml` / `push.yml` CI jobs. **Do not** edit `push.yml`.
- Patch existing `pr.yml` only: switch trigger to `pull_request`, remove PR-head checkout `ref:`, remove `approve`/`merge` jobs (auto-merge is static-synced in `pr-auto-merge.yml`).
- **Verify** Semgrep exists in `pr.yml` (named **Code Quality** job *or* a step in **Repository Checks**). Do **not** implement a missing named job. Do **not** extract tetra Semgrep out of **Repository Checks**.
- **Preserve** filter / `*-skip` twins / draft `if` / `timeout-minutes` / concurrency / `ready_for_review`. Do not add `workflow_dispatch`. Do not add `develop` to Push except agoras-actions.
- If `pr.yml` is missing, skip workflows and report — do not create a new workflow file.
- Do not edit `pr-auto-merge.yml`, `dependabot.yml`, `cache-cleanup.yml`, or repo-owned `release.yml`. Delete stale `keepalive.yml` if present.

### Hotfix and doc-family cleanup (when migrating fleet)

- Delete orphan `scripts/hotfix.sh` if present (no longer managed).
- Remove `hotfix` / `make hotfix` from README, CONTRIBUTING, and non-managed Makefile help lines.
- Use `make undo-release VERSION=x.y.z` and `rosey-release` instead.
- When resolved `history_file` flips extension, delete orphan siblings: `MAINTAINER.*`, `README.*`, `RELEASE_DESCRIPTION.*` in the wrong format.

## Output Summary

Return:

- files changed
- evidence used
- env vars discovered
- bumpversion files/sections configured; `[rosey-maintainer] post_bump_commands` (Y/N)
- preflight targets present (image/dependencies/build/lint/format/test Y/N); tools used for each
- Makefile duplicate targets removed
- orphan files removed (hotfix.sh, wrong-extension doc-family files) (Y/N)
- `pr.yml` patched (Y/N), trigger is `pull_request` (Y/N), approve/merge removed (Y/N), Semgrep present as named Code Quality job **or** Repository Checks step (Y/N), placement matches repo family (Y/N), cost-opt PR structure preserved (Y/N), `pr-auto-merge.yml` present from static sync (Y/N), `push.yml` untouched (Y/N), `protect-github --apply` skipped (Y/N)
- Docker assumptions
- blockers or follow-up tasks
