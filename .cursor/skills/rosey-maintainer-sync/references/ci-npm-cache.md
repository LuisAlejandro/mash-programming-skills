# CI npm cache (Docker-based node repos)

Use on GHA **before** `make image` / `make start` / `make dependencies`. Do **not** use `actions/setup-node` — installs run inside Docker.

## Why

`docker-compose.yml` bind-mounts `~/.npm` into the container. Restoring `~/.npm` on the runner via `actions/cache` speeds CI and avoids cold npm downloads.

## Standard block

Insert after checkout, before env vars / Docker steps:

```yaml
      - name: Restore npm cache
        uses: actions/cache@v6
        with:
          path: ~/.npm
          key: ${{ runner.os }}-npm-${{ hashFiles('package-lock.json', '**/package-lock.json') }}
          restore-keys: |
            ${{ runner.os }}-npm-

      - name: Restore node_modules cache
        uses: actions/cache@v6
        with:
          path: |
            node_modules
            */node_modules
            */*/node_modules
          key: ${{ runner.os }}-node-modules-${{ hashFiles('package-lock.json', '**/package-lock.json') }}
          restore-keys: |
            ${{ runner.os }}-node-modules-
```

## Requirements

- Commit `package-lock.json` (do not gitignore) so cache keys are stable.
- Use `npm ci` in Makefile `dependencies` when a lockfile is present.
- `release.yml`, `push.yml`, and `pr.yml`: maintained per repo (not static sync).

## Apply to

`push.yml`, `pr.yml`, and release workflow (via template sync) for node-profile repos that run quality checks through Docker.
