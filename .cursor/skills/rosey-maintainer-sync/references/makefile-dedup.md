# Makefile Conventions and Deduplication

Makefile docker lifecycle, release targets, and preflight wiring are **repo-owned**.
Static sync does **not** inject or rewrite Makefile sections.

## Required target groups

Every **python** or **node** fleet repo must define these targets (see `preflight-conventions.md`):

**Docker lifecycle**

- `image`, `start`, `stop`, `down`, `destroy`, `cataplum`

**Release**

- `release`, `release-patch`, `release-minor`, `release-major`, `release-preflight`, `undo-release`

**Preflight pipeline**

- `image`, `dependencies`, `build`, `format`, `lint`, `test`

After dynamic generation or migration, verify:

```bash
make -n image dependencies build format lint test
make -n release-preflight
```

## Deduplication

Remove **duplicate target names** — each target must appear at most once.

- **Pure duplicate** (same recipe or trivial wrapper) → delete the extra definition.
- **Enhanced variant** → merge into one canonical target; delete the other.

## Repo-specific targets to preserve

- `console`, `virtualenv`, `shell`
- `lint`, `test`, `coverage`, `format`, `build`, `install`
- `help`, `clean`, `clean-*`
- `update-shelves`, `dependencies` (dockershelf)
- Custom app targets and variables (`exec_on_docker`, `img_hash`, `PROJECT_NAME`, …)

## Redundant variables

Remove duplicate variable definitions that only supported removed duplicate targets
(e.g. second `all_ps_hashes`, duplicate `VERSION_TYPE` / `APP_NAME` blocks).

## Typical Makefile order

1. Shebang / `SHELL`
2. Repo variables (`exec_on_docker`, `img_hash`, release config)
3. Repo-specific targets (`help`, `clean`, `lint`, `test`, `build`, …)
4. Docker lifecycle targets
5. Docker consumers (`console`, `virtualenv`, …)
6. Release targets
7. `.PHONY`

## Verification

- `make -n help` or `make -n lint` must not error on duplicate target definitions
- Each required target name appears **at most once**
