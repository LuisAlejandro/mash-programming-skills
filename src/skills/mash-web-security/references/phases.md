# Web security phases

Required read before Phase 0. Command details live in `references/zap-baseline.md` and `references/dependency-audit.md`.

## Phase 0: Safety and report

Follow `../mash-project-review/references/safety.md`. Refuse production before any audit or scan. A refusal runs neither the dependency auditor nor ZAP.

Create the temp directory when this invocation is not already inside an orchestrated run:

```bash
mktemp -d "${TMPDIR:-/tmp}/mash-project-review-XXXXXX"
```

Create or open the report from `../mash-project-review/references/report-template.md`. Rows start at `Pending`. Leave the manual checklist section as "Not in this run."

## Phase 1: Dependency audit

Read `references/dependency-audit.md` and run every audit that applies. Do this before serving the app. A missing manifest is `Skipped` with the reason in that file. A missing auditor for a manifest that exists is `Blocked (needs human verify)` with the install remediation. Do not treat a skipped ecosystem as a pass for that ecosystem.

Follow the docker-via-make rule for the project under review. In container mode, run the auditor through Make when a target exists, otherwise `docker compose run` on the service that owns the manifest. In host mode, run the host package manager. Do not `npm install` or `pip install` the app's dependencies on the host while the project is in container mode. Installing the auditor itself, when the tool is missing, is the remediation text on the blocked row — do not install it silently inside the app.

Record one `Fail` row per vulnerable package name, severity from the mash-project-review status vocabulary. When the auditor finishes and reports no vulnerabilities, one `Pass` row for that auditor (`deps.npm-audit`, `deps.pnpm-audit`, `deps.yarn-audit`, or `deps.pip-audit`).

A command that does not produce parseable output is `Blocked (needs human verify)`, not a Fail. Paste the stderr tail in the evidence block.

## Phase 2: Serve

Follow the serve rules in `../mash-project-review/references/safety.md`. ZAP needs an origin that accepts connections. If serve fails, or the target is staging and the origin was refused, set `web.zap.scan` to `Blocked (needs human verify)` and skip Phase 3. Keep the dependency rows.

## Phase 3: ZAP baseline

Read `references/zap-baseline.md` and follow the discovery order there.

- No baseline command available: `web.zap.scan` is `Blocked (needs human verify)` with the install remediation. Do not mark it `Skipped` and do not run a different scanner.
- The baseline finishes: `web.zap.scan` is `Pass`, meaning the baseline finished. Record the ZAP version in metadata.
- Each High, Medium, or Low alert is a `Fail` row `web.zap.<alert-id-or-name>`. Map risk with the status vocabulary (High → `P0`, Medium → `P2`, Low → `P3`). One row per alert name.
- Informational alerts are `Skipped` on `web.zap.info.<alert-name>`, reason "informational baseline alert". Do not promote them to Fail.
- Put an OWASP Top 10 category in the hint only when the alert clearly matches (for example a missing security header as A05 Security Misconfiguration). Leave the hint blank when unsure.

Stay on the resolved origin. Do not enable the ajax spider. Do not add hosts. Do not log in. Do not disable TLS verification to make a staging certificate succeed. A certificate failure is `Blocked (needs human verify)`.

Cap the baseline at 5 minutes. Alerts present in the report are still Fail rows. If the cap cuts the spider short, say so on `web.zap.scan` and do not describe the partial run as a complete pass: the scan row stays `Pass` only when the process finished its baseline, and becomes `Blocked (needs human verify)` when it was interrupted.

Paste an evidence block per Fail and for a blocked scan: the exact command and the alert excerpt or the stderr tail.

## Phase 4: Write the report

Update the report after each terminal row. Fill Failures, Blocked and skipped, and Final status.

Emit evidence blocks in chat. Release the lease when this invocation acquired it. Stop.
