# Release Preflight Conventions

Repos on **python** or **node** profiles must expose six Makefile targets plus
`release-preflight`. These are **repo-owned** — static sync does not generate their bodies.

Canonical `release-preflight` chains the six steps:

```makefile
release-preflight:
	@make image
	@make dependencies
	@make build
	@make format
	@make lint
	@make test
```

`scripts/release.sh` (via `scripts/lib.sh`) runs **`make release-preflight`** once, then
**stops** if the working tree is dirty afterward (preflight must not leave uncommitted changes).

Each sub-target must exit non-zero on failure. Typical roles:

1. **`make image`** — build dev Compose image(s).
2. **`make dependencies`** — install deps in container (or no-op `@:` on Python repos
   without a separate install step).
3. **`make build`** — full production build.
4. **`make format`** — formatter (write mode OK locally; tree must be clean after full preflight).
5. **`make lint`** — style / static analysis.
6. **`make test`** — quality gate (coverage, unit tests, typecheck, etc.).

Fix formatting and lint on `develop` before `make release-*`.

## Required targets (all profiles)

| Target | Role |
|--------|------|
| `image` | Dev Compose image |
| `dependencies` | Install deps in container; Python repos may use `@:` no-op |
| `build` | Production artifact build (repo-specific) |
| `lint` | Style / static analysis |
| `format` | Formatter (write mode OK for local/PR) |
| `test` | Quality gate (coverage, unit tests, typecheck, etc.) |

## Python profile

| Target | Typical implementation |
|--------|------------------------|
| `dependencies` | `@:` when install is implicit |
| `build` | `python3 -m build` + `twine check dist/*` (monorepo: loop packages) |
| `lint` | `tox -e lint` in Docker |
| `format` | `tox -e format` in Docker |
| `test` | `tox -e coverage` in Docker |

**tox.ini** should define `lint`, `format`, and `coverage` envs when tox is the
orchestrator. Reference repos: `agoras`, `spices`.

## Node profile

| Target | Typical implementation |
|--------|------------------------|
| `dependencies` | `npm ci` / `yarn install` in container |
| `build` | `npm run build` / `yarn build`; polyglot: aggregate per stack |
| `lint` | ESLint in Docker |
| `format` | Prettier / eslint --fix in Docker |
| `test` | Jest/Vitest, `go test`, or `tsc --noEmit` |

## Semgrep (repo-owned)

When the repo uses Semgrep on PRs:

- `.github/workflows/pr.yml` must include a **Code Quality** job (or equivalent).
- `.semgrepignore` is repo-owned (not synced).

## Post-bump hooks

Put commands in `.bumpversion.cfg` under `[rosey-maintainer] post_bump_commands` — **not**
in `registry/repos.yaml`. `scripts/release.sh` reads them at runtime.

## Verification (dynamic generation / sync follow-up)

```bash
make -n image dependencies build format lint test
make -n release-preflight
```

Report blockers when any target is missing or preflight cannot run.
