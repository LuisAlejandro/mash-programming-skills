# Serve

Required read at Phase 3. Produces a base URL the browser can open. Never install or run app runtimes on the host.

## Target

Read `target:` from parsed arguments. Default `local`.

### Local

1. Read the repo `Makefile`. Prefer an existing target, in this order: `make start`, `make serve`, `make serve-frontend`, `make serve-backend`. If the Makefile names a different serve target, use that name — do not invent host commands.
2. If no Make target covers it, `docker compose up` / `docker compose run` against the repo's compose file. Still never `npm run dev`, `npx`, host `node`, or host `python`.
3. **Port.** Priority: `port:<n>` / `--port PORT` → a port stated in project instructions → `PORT=` in `.env*` → Makefile / compose published port → `3000`.
4. If something already accepts connections on that port, reuse it. Do not start a second server.
5. Otherwise start the Make/Compose command in the background and poll until the port accepts connections. Do not block on a confirmation.

If Docker is required and unavailable, stop and say so. Do not fall back to host `npm`.

### Staging or prod

Do not start a server. Do not switch checkout.

Base URL: `url:<https://...>` if present. Otherwise ask once (interactive) or stop (non-interactive).

**Prod is read-mostly.** Require a test account (ask if unknown; Hindsight prefs may already name one). Scenarios that would place a real charge, email a customer, send SMS, or mutate customer data are `Blocked (needs human verify)` — do not drive them. Prefer staging when the same journeys can be exercised there.

## Base URL to Phase 4

Hand the browser a single origin: `http://localhost:<port>` or the staging/prod URL, with no trailing-path guesswork. Routes come from the matrix.
