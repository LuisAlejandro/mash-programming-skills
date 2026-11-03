# Serve

Required read at Phase 3. Produces a base URL the browser can open. Never install or run app runtimes on the host.

## Target

Read `target:` from parsed arguments. Default `local`.

### Local

1. Read the repo `Makefile`. Prefer an existing target, in this order: `make start`, `make serve`, `make serve-frontend`, `make serve-backend`. If the Makefile names a different serve target, use that name — do not invent host commands.
2. If no Make target covers it, `docker compose up` / `docker compose run` against the repo's compose file. Still never `npm run dev`, `npx`, host `node`, or host `python`.
3. **Port.** Priority: `port:<n>` / `--port PORT` → a port stated in project instructions → `PORT=` in `.env*` → Makefile / compose published port → `3000`.
4. **Claim the port before using it.** A port is machine-wide: another run's server answering on it would be dogfooded as if it were this run's build. Claim it per [`mash-workspace`](../../mash-workspace/SKILL.md):

   ```bash
   WS_HELPER="<skills>/mash-workspace/scripts/workspace.py"
   REPO="$(git rev-parse --show-toplevel)"
   RUN=$(python3 "$WS_HELPER" run start --workflow dogfood --repo "$REPO" \
         | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
   python3 "$WS_HELPER" lease acquire --run "$RUN" --kind port --key "$PORT" --repo "$REPO"
   ```

   Exit `2` means another run holds it. Stop and report the holder; do not pick a different port silently, because the matrix was built against this target. Claim the Compose project (`--kind compose`) and the browser session (`--kind browser`) the same way before starting them.
5. **Verify what answers is yours.** If something already accepts connections on the claimed port, confirm it is this repository's server before reusing it — check the Compose project name, or a known response from this build. An unidentified listener is a blocker, not a free server.
6. Otherwise start the Make/Compose command in the background and poll until the port accepts connections. Do not block on a confirmation.
7. Release every claim with `run end` when the run finishes, including after a blocker.

If Docker is required and unavailable, stop and say so. Do not fall back to host `npm`.

### Staging or prod

Do not start a server. Do not switch checkout.

Base URL: `url:<https://...>` if present. Otherwise ask once (interactive) or stop (non-interactive).

**Prod is read-mostly.** Require a test account (ask if unknown; Hindsight prefs may already name one). Scenarios that would place a real charge, email a customer, send SMS, or mutate customer data are `Blocked (needs human verify)` — do not drive them. Prefer staging when the same journeys can be exercised there.

## Base URL to Phase 4

Hand the browser a single origin: `http://localhost:<port>` or the staging/prod URL, with no trailing-path guesswork. Routes come from the matrix.
