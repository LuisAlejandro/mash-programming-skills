# Bumpversion Generation Rules

Generate or overwrite `.bumpversion.cfg` for repos that use the release bundle (`ops-release` in profile).

The CLI only bootstraps a minimal stub when the file is missing. The LLM sync phase owns the full, repo-specific file list.

## Required `[bumpversion]` Header

Keep these settings unless the repo already uses a deliberate alternative:

```ini
[bumpversion]
current_version = <discovered version>
commit = True
tag = True
tag_name = {new_version}
```

Read `current_version` from the repo's canonical version source (see below).

## Optional `[rosey-maintainer]` Section

When a release needs repo-specific steps after `bumpversion --no-commit` (for example
`npm install` in monorepo packages), add:

```ini
[rosey-maintainer]
post_bump_commands = cd path/to/pkg && npm install && cd ../..
```

Use a **single line** after `=` (chain steps with `&&`). bumpversion cannot parse
multiline values in `.bumpversion.cfg`; indented continuation lines break `bumpversion`.

`scripts/release.sh` reads the command at runtime from `.bumpversion.cfg`. Do not
rely on registry overrides in `repos.yaml`.

## Discover Version Sources

Scan the repo and include every file that holds the project version:

| Pattern | Example search/replace |
|---------|------------------------|
| Single `__version__` in package | `search = __version__ = '{current_version}'` |
| `setup.py` / `setup.cfg` version | `version='{current_version}'` or `version = {current_version}` |
| Monorepo per-package `setup.py` | one `[bumpversion:file:...]` section per package |
| `pyproject.toml` dynamic version | usually skip unless version is literal in file |
| `package.json` | `"version": "{current_version}"` |
| README version line | match existing wording, e.g. `Current version: {current_version}` |
| Docs index | only if version string appears in tracked docs |

Use agoras `.bumpversion.cfg` as the reference for complex Python monorepos: central `version.py` plus per-package `setup.py` entries plus README files.

## Include `readme_file` from Registry Context

Always include the repo's primary readme (`README.rst` or `README.md` from `history_file` / existing docs) when it displays a version string.

Also include secondary readmes (`README.short.rst`, etc.) when they contain version placeholders.

## Do Not Include

- Files managed only by the stub template with no version string in the repo
- `rosey/maintainer-manifest.json`
- Generated lockfiles unless they embed the package version literally
- Secrets or environment files

## Overwrite Policy

Always overwrite `.bumpversion.cfg` completely. Do not append orphan sections from a stale file.

## Evidence To Check

- Existing `.bumpversion.cfg`
- `packages/*/setup.py`, root `setup.py`, `pyproject.toml`
- `*/__init__.py`, `*/version.py`, `*/_version.py`
- `package.json`, `package-lock.json` (version field only)
- `README.*`, `docs/conf.py` (Sphinx `version` / `release`)
- `.bumpversion.cfg` entries referenced in `MAINTAINER.rst` or release scripts
