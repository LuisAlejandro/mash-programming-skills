# Maintainer Guide — mash-programming-skills

## Tests

From this checkout, run `make test`. It builds the test-only image from
`Dockerfile.test` using `compose.test.yaml`, then runs disposable test containers.
`make test-image` builds the image without running tests.

There is no Docker runtime for the programming skills; the container runs
repository and `mash-parallel` tests only.

## Release

From a clean `develop`, with `git`, git-flow, `gh`, bumpversion, and a configured
GPG signing key, optionally run `make test` locally and then use
`make release-patch` (or `release-minor` / `release-major`). Run
`VERSION=<version> make undo-release` only when a rollback is needed.

`scripts/release.sh` does not run a local test preflight in this minimal profile.
It pushes `release/<version>` and waits for the complete **Push** workflow at
that exact commit before finishing git-flow and publishing the GitHub release.
The **Publish Release** workflow checks the published tag afterward. Both use
`scripts/preflight.sh` to verify version and release inputs; there is no
separate `Release Gate` job.

## CI

`.github/workflows/push.yml` runs on `develop`, `master`, and `release/**`.
Its Gate and Tests jobs must both pass on the release branch. A separate
`.github/workflows/pr.yml` has not been configured for this repository; do not
assume PR checks or branch protection are in place.
