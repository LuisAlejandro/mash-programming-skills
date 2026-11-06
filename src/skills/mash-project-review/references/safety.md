# Safety

Required read before Phase 0 of mash-project-review, the mash-a11y skill, and the mash-web-security skill.

Phase 1 reviews the user's own app on a local origin or on a staging origin the user named. Production targets are refused. Never claim the target is WCAG compliant, ASVS compliant, or OWASP-safe.

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
| A host whose labels include `prod` or `production` | Refuse, including when the user passed `target:staging`. |
| A public apex or a `www` host with no non-production label | Refuse. |
| A host with a non-production label: `staging`, `stage`, `stg`, `dev`, `preview`, `qa`, `test`, `sandbox`, `uat`, or `local` | Staging, and only when the target is staging and `url:` was supplied. |

Interactive staging: ask once whether to scan that exact origin, show the origin, and wait. Non-interactive staging: continue only when the host already matches the staging row. Otherwise stop.

A refusal runs no axe, no Lighthouse, no ZAP, and no dependency audit. Do not write a scan report for a refused target. Tell the user phase 1 has no production target.

## Scope of tools

- axe and ZAP run only against the resolved origin. Do not spider off-host. Do not add a second host to the scanner scope. Ignore off-host URLs if a tool reports them, and note that they were out of scope.
- Dependency audits read the project tree under review. They are not a network scan of the origin.
- Do not collect credentials, do not log into a production-like account, and do not paste cookies into a prompt or a report. An auth wall is `Blocked (needs human verify)`.

## Serve

When the target is local and nothing confirmed as this project is already listening, serve the app the way the mash-dogfood skill does in its `references/serve.md`, with these overrides:

- Workflow name for the lease is `project-review`.
- There is no production branch. Do not apply dogfood's read-mostly production rule here.
- Prefer Make, then Compose, per the docker-via-make rule. Do not invent a host `npm start` or a host `python` server when Make or Compose can serve the app.
- Claim `port` and `compose` with the mash-workspace helper before using them. Exit `2` means another run holds the resource. Stop and report the holder.

If the user passed `url:` to a local host, confirm the listener belongs to this project before sending traffic. An unidentified listener is a blocker, not a free server.

## Redaction and files

Follow `references/evidence.md` before writing the report. Screenshots and captures stay in the Phase 0 temp directory.
