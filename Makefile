# >>> maintainer-tools:ops-release BEGIN
# Managed by maintainer-tools 0.4.4. Do not edit directly.

release:
	@./scripts/release.sh $${VERSION_TYPE}

release-patch:
	@./scripts/release.sh patch $${APP_NAME}

release-minor:
	@./scripts/release.sh minor $${APP_NAME}

release-major:
	@./scripts/release.sh major $${APP_NAME}



undo-release:
	@: "$${VERSION:?Set VERSION=x.y.z before running make undo-release}"
	@VERSION=$${VERSION} ./scripts/rollback.sh release
# <<< maintainer-tools:ops-release END

# Repo-owned, isolated test image; no Docker runtime is installed by this pack.
TEST_COMPOSE = docker compose -p mash-programming-skills-tests -f compose.test.yaml

.PHONY: test-image test

test-image:
	@$(TEST_COMPOSE) build tests

test: test-image
	@$(TEST_COMPOSE) run --rm --no-deps tests python3 -m pytest tests src/skills/mash-parallel/tests -q
