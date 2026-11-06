# Safety

Required read before Phase 0 of mash-project-review, the mash-a11y skill, the mash-web-security skill, the mash-api-security skill, and the mash-performance skill.

The kit reviews the user's own app on a local origin or on a staging origin the user named. Production targets are refused. Never claim the target is WCAG compliant, ASVS compliant, or OWASP-safe.

## Tokens

The default target is `target:local`. `target:staging` requires `url:`.

`target:prod` and `target:production` are refusals.

A front invoked with `report:` uses the report path it was given and does not ask the staging question again. It still applies every refusal in this file. `lease:held` means the caller already holds the workspace lease.

## Origin rules

Classify the base URL host before any request:

| Host | Result |
| --- | --- |
| `localhost`, `127.0.0.1`, `::1`, `host.docker.internal`, a name ending in `.localhost`, or a name ending in `.local` | Local. Allowed when the target is local. |
| Any other host while the target is local | Refuse. Do not scan it "just this once". |
| A non-loopback IP address | Refuse in phase 1. |
| A host whose labels include `prod` or `production` | Refuse, including when the user passed `target:staging`, and including a name that also ends in `.localhost` or `.local`. |
| A public apex or a `www` host with no non-production label | Refuse. |
| A host with a non-production label: `staging`, `stage`, `stg`, `dev`, `preview`, `qa`, `test`, `sandbox`, `uat`, or `local` | Staging, and only when the target is staging and `url:` was supplied. |

Interactive staging: ask once whether to scan that exact origin, show the origin, and wait. Non-interactive staging: continue only when the host already matches the staging row. Otherwise stop.

A refusal runs no axe, no Lighthouse, no ZAP, no k6, no API probe, and no dependency audit. Do not write a scan report for a refused target. Tell the user this kit has no production target.

## Scope of tools

- axe, ZAP, k6, and the API probe run only against the resolved origin. Do not spider off-host. Do not add a second host to the scanner scope. Ignore off-host URLs if a tool reports them, and note that they were out of scope.
- Dependency audits read the project tree under review. They are not a network scan of the origin.
- Do not collect credentials for the mash-a11y skill or the mash-web-security skill, do not log into a production account, and do not paste cookies into a prompt or a report. An auth wall on those fronts is `Blocked (needs human verify)`.

## API test accounts

The mash-api-security skill is the only front that sends test-account credentials. It reads them from the environment. Do not put them on a command line and do not copy them into the report.

- `MASH_REVIEW_USER_A` and `MASH_REVIEW_USER_B` are bearer tokens for two test users on the resolved origin.
- `MASH_REVIEW_USER_A_ID` and `MASH_REVIEW_USER_B_ID` are object ids each of those users owns.

Missing variables block the checks that need them. They do not block the unauthenticated probe. Do not invent a password, do not try a password list, and do not reuse a token the user described as production.

## Load

The mash-performance skill runs one k6 smoke of 2 virtual users for 10 seconds. Do not raise that. Decline a stress test or a soak, and still run the light smoke when k6 is installed. Production remains a full refusal before k6 starts.

## Serve

When the target is local and nothing confirmed as this project is already listening, serve the app the way the mash-dogfood skill does in its `references/serve.md`, with these overrides:

- Workflow name for the lease is `project-review`.
- There is no production branch. Do not apply dogfood's read-mostly production rule here.
- Prefer Make, then Compose, per the docker-via-make rule. Do not invent a host `npm start` or a host `python` server when Make or Compose can serve the app.
- Claim `port` and `compose` with the mash-workspace helper before using them. Exit `2` means another run holds the resource. Stop and report the holder.

If the user passed `url:` to a local host, confirm the listener belongs to this project before sending traffic. An unidentified listener is a blocker, not a free server.

## Redaction and files

Follow `references/evidence.md` before writing the report. Screenshots and captures stay in the Phase 0 temp directory.
