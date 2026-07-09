# Docker Generation Rules

Apply only when the repo profile is `python` or `node`. Do not generate or rewrite Docker files for `minimal` profile repos.

## Dockerfile Defaults

- Python default base image: `dockershelf/python:3.12`
- Node default base image: `dockershelf/node:20`
- Preserve or reintroduce repo-specific system packages discovered in the existing Dockerfile, Makefile, package metadata, or docs.
- Include:

```dockerfile
ARG UID=1000
ARG GID=1000
```

- Delete an existing user and group that conflict with host UID/GID before creating the app user:

```dockerfile
RUN EXISTUSER=$(getent passwd | awk -F':' '$3 == '$UID' {print $1}') && \
    [ -n "${EXISTUSER}" ] && deluser ${EXISTUSER} || true

RUN EXISTGROUP=$(getent group | awk -F':' '$3 == '$GID' {print $1}') && \
    [ -n "${EXISTGROUP}" ] && delgroup ${EXISTGROUP} || true
```

- Create a group and user named after the repo slug:

```dockerfile
RUN groupadd -g "${GID}" <repo_user> || true
RUN useradd -u "${UID}" -g "${GID}" -ms /bin/bash <repo_user>
RUN echo "<repo_user> ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/<repo_user>
USER <repo_user>
```

- Create `/home/<repo_user>/app` and any cache directories needed by the stack.
- Set:

```dockerfile
WORKDIR /home/<repo_user>/app
CMD ["tail", "-f", "/dev/null"]
```

- Do not run the application, tests, web server, worker, package publishing, or release commands in `CMD`.
- Commands are issued through Makefile targets such as `console`, `lint`, `test`, `dist`, and release targets.

## docker-compose.yml Defaults

- Define an `app` service.
- Build from the local `Dockerfile`.
- Mount the repo source for instant updates:

```yaml
volumes:
  - .:/home/<repo_user>/app
```

- Mount relevant host caches when the stack uses them:
  - Python/pip: `~/Library/Caches/pip:/home/<repo_user>/.cache/pip`
  - npm: `~/.npm:/home/<repo_user>/.npm`
  - yarn: `~/.cache/yarn:/home/<repo_user>/.cache/yarn`
  - pnpm: `~/.local/share/pnpm/store:/home/<repo_user>/.local/share/pnpm/store`
  - Bundler/Ruby present: use a project-local or home cache that does not hide source files.
- Do not set a startup command unless it is equivalent to keeping the container idle. Prefer relying on the Dockerfile `CMD`.

## Evidence To Check

- Existing `Dockerfile`
- Existing `docker-compose.yml`
- `Makefile` Docker targets and `exec_on_docker`
- `requirements*.txt`, `pyproject.toml`, `setup.cfg`
- `package.json`, lockfiles, workspace config
- `Gemfile` / Bundler usage
- README or maintainer docs mentioning local development
