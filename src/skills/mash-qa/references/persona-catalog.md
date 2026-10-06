# Persona Catalog

12 reviewer personas organized into always-on and cross-cutting conditional layers, plus Mash Programming Skills-specific agents. The orchestrator uses this catalog to select which reviewers to spawn for each review.

## Always-on (4 personas + 2 Mash Programming Skills agents)

Spawned on every review regardless of diff content.

**Persona agents (structured JSON output):**

| Persona | Agent | Focus |
|---------|-------|-------|
| `correctness` | `mash-correctness-reviewer` | Logic errors, edge cases, state bugs, error propagation, intent compliance |
| `testing` | `mash-testing-reviewer` | Coverage gaps, weak assertions, brittle tests, missing edge case tests |
| `maintainability` | `mash-maintainability-reviewer` | Structural quality, complexity deletion, 1k-line regressions, coupling, type-boundary leaks, dead code, premature abstraction |
| `ponytail` | `mash-ponytail-reviewer` | Over-engineering only: reinvented standard library, unneeded dependencies, speculative abstractions, dead flexibility, shrinkable logic. Complements maintainability; this one only hunts complexity |
| `project-standards` | `mash-project-standards-reviewer` | CLAUDE.md and AGENTS.md compliance -- frontmatter, references, naming, cross-platform portability, tool selection |

**Mash Programming Skills agents (unstructured output, synthesized separately):**

| Agent | Focus |
|-------|-------|
| `mash-agent-native-reviewer` | Verify new features are agent-accessible |
| `mash-learnings-researcher` | Search .mash/solutions/ and .mash/insights/ for past issues and durable lessons related to this PR's modules and patterns |

## Conditional (7 personas)

Spawned when the orchestrator identifies relevant patterns in the diff. The orchestrator reads the full diff and reasons about selection -- this is agent judgment, not keyword matching.

| Persona | Agent | Select when diff touches... |
|---------|-------|---------------------------|
| `security` | `mash-security-reviewer` | Auth middleware, public endpoints, user input handling, permission checks, secrets management |
| `performance` | `mash-performance-reviewer` | Database queries, ORM calls, loop-heavy data transforms, caching layers, async/concurrent code |
| `api-contract` | `mash-api-contract-reviewer` | Route definitions, serializer/interface changes, event schemas, exported type signatures, API versioning |
| `data-migration` | `mash-data-migration-reviewer` | Migration files, schema dumps (`db/schema.rb`, `structure.sql`), backfill scripts, data transformations — **not** model/query-only changes without migration artifacts |
| `reliability` | `mash-reliability-reviewer` | Error handling, retry logic, circuit breakers, timeouts, background jobs, async handlers, health checks |
| `adversarial` | `mash-adversarial-reviewer` | Diff has >=50 changed non-test, non-generated, non-lockfile lines, OR touches auth, payments, data mutations, external API integrations, or other high-risk domains |
| `previous-comments` | `mash-previous-comments-reviewer` | **PR-only AND comment-gated.** Reviewing a PR that has existing review comments or review threads from prior review rounds. Skip entirely when no PR metadata was gathered in Stage 1, OR when Stage 1's `hasPriorComments` flag is false (no `reviews` and no `comments` on the PR). |

## Mash Programming Skills Conditional Agents (migration-specific)

Spawn `mash-deployment-verification-agent` when the migration-artifact gate applies **and** the change is risky (destructive DDL, backfills, NOT NULL without default, column renames/drops). Schema drift and migration safety live in the `data-migration` persona — not separate Mash Programming Skills agents.

| Agent | Focus |
|-------|-------|
| `mash-deployment-verification-agent` | Go/No-Go deployment checklist with SQL verification queries and rollback procedures |

## Selection rules

1. **Always spawn all 5 always-on personas** plus the 2 Mash Programming Skills always-on agents — unless the quick tier is active, which runs `correctness` plus at most one conditional (see `SKILL.md`, Quick Tier).
2. **For each cross-cutting conditional persona**, the orchestrator reads the diff and decides whether the persona's domain is relevant. This is a judgment call, not a keyword match.
3. **For `data-migration`**, spawn only when the diff includes migration or schema artifacts (`db/migrate/*`, `db/schema.rb`, `db/structure.sql`, Alembic/Flyway/Liquibase paths, or explicit backfill/data-transform scripts). Do **not** spawn for model-only or query-only changes without those files.
4. **For Mash Programming Skills conditional agents**, spawn `mash-deployment-verification-agent` when the migration-artifact gate applies and the change is risky (see above).
5. **Announce the team** before spawning with a one-line justification per conditional reviewer selected.
