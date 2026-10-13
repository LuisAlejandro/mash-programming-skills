# Persona Catalog

12 reviewer personas organized into always-on and conditional layers, plus Mash Programming Skills agents selected by the same rules. The orchestrator uses this catalog to select which reviewers to spawn for each review. This file is the only roster.

## Always-on (5 personas)

Spawned on every full review regardless of diff content. The quick tier is the exception: `correctness` plus at most one conditional persona, and none of the Mash Programming Skills agents below.

**Persona agents (structured JSON output):**

| Persona | Agent | Focus |
|---------|-------|-------|
| `correctness` | `mash-correctness-reviewer` | Logic errors, edge cases, state bugs, error propagation, intent compliance |
| `testing` | `mash-testing-reviewer` | Coverage gaps, weak assertions, brittle tests, missing edge case tests |
| `maintainability` | `mash-maintainability-reviewer` | Structural quality, complexity deletion, 1k-line regressions, coupling, type-boundary leaks, dead code, premature abstraction |
| `ponytail` | `mash-ponytail-reviewer` | Over-engineering only: reinvented standard library, unneeded dependencies, speculative abstractions, dead flexibility, shrinkable logic. Complements maintainability; this one only hunts complexity |
| `project-standards` | `mash-project-standards-reviewer` | CLAUDE.md and AGENTS.md compliance -- frontmatter, references, naming, cross-platform portability, tool selection |

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

## Mash Programming Skills agents (unstructured output)

| Agent | Select when... |
|-------|----------------|
| `mash-agent-native-reviewer` | The diff touches UI, agent tools, or system prompts. Skip backend-only and docs-only diffs. |
| `mash-learnings-researcher` | `.mash/solutions/` or `.mash/insights/` contains at least one markdown file. Skip when both directories are missing or empty. |
| `mash-deployment-verification-agent` | The migration-artifact gate applies **and** the change is risky (destructive DDL, backfills, NOT NULL without default, column renames/drops). Schema drift and migration safety live in the `data-migration` persona. |

## Selection rules

1. **Always spawn all 5 always-on personas** — unless the quick tier is active, which runs `correctness` plus at most one conditional persona and no Mash Programming Skills agent (see `SKILL.md`, Quick Tier).
2. **For each conditional persona**, the orchestrator reads the diff and decides whether the persona's domain is relevant. This is a judgment call, not a keyword match.
3. **For `data-migration`**, spawn only when the diff includes migration or schema artifacts (`db/migrate/*`, `db/schema.rb`, `db/structure.sql`, Alembic/Flyway/Liquibase paths, or explicit backfill/data-transform scripts). Do **not** spawn for model-only or query-only changes without those files.
4. **For `mash-agent-native-reviewer`**, spawn only when the diff touches UI, agent tools, or system prompts.
5. **For `mash-learnings-researcher`**, spawn only when `.mash/solutions/` or `.mash/insights/` contains markdown. A missing directory is empty.
6. **For `mash-deployment-verification-agent`**, spawn when the migration-artifact gate applies and the change is risky (see above).
7. **Announce the team** before spawning with a one-line justification per conditional reviewer selected.
