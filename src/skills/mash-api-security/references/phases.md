# API security phases

Required read before Phase 0. Probe rules live in `references/checks.md`. Dependency commands live in `../mash-web-security/references/dependency-audit.md`. Follow that file. Do not copy its command table into this skill.

## Phase 0: Safety and report

Follow `../mash-project-review/references/safety.md`. Refuse production before any audit or probe. A refusal runs neither the dependency auditor nor the probe script.

Create the temp directory when this invocation is not already inside an orchestrated run:

```bash
mktemp -d "${TMPDIR:-/tmp}/mash-project-review-XXXXXX"
```

Create or open the report from `../mash-project-review/references/report-template.md`. Rows start at `Pending`. Leave the manual checklist section as "Not in this run."

## Phase 1: Dependency audit

Read `../mash-web-security/references/dependency-audit.md` and run every audit that applies, unless this report already has a terminal row whose check id starts with `deps.`. A terminal row is any status other than `Pending`. Do not run those auditors a second time in the same report.

A missing manifest is `Skipped` with the reason in that file. A missing auditor for a manifest that exists is `Blocked (needs human verify)` with the install remediation in that file. Do not treat a skipped ecosystem as a pass for that ecosystem.

Follow the docker-via-make rule for the project under review. Do not `npm install` or `pip install` the app's dependencies on the host while the project is in container mode.

## Phase 2: Serve

Follow the serve rules in `../mash-project-review/references/safety.md`. The probe needs an origin that accepts connections. If serve fails, or the target is staging and the origin was refused, set `api.probe` to `Blocked (needs human verify)` and skip Phase 3. Keep the dependency rows.

## Phase 3: OpenAPI probe

Read `references/checks.md` and run the skill-local script it names. Do not reimplement the probes with another client.

- Exit `3`: the script refused the host. Stop. Do not write probe rows. Tell the user this kit has no production target.
- Exit `1`, or no `API_JSON` block: `api.probe` is `Blocked (needs human verify)` with the stderr tail.
- Exit `0` and an `API_JSON` block: copy each object in `checks` to a matrix row. Keep its `id`, `severity`, `status`, `hint`, `command`, and `output`. Do not change a status the script printed.

`api.probe` with status `Pass` means the script finished. It does not mean the API is safe.

Paste an evidence block per `Fail` and per blocked probe: the exact command and the output excerpt from that object.

## Phase 4: Write the report

Update the report after each terminal row. Fill Failures, Blocked and skipped, and Final status using the mash-project-review status vocabulary.

Emit evidence blocks in chat. Release the lease when this invocation acquired it. Stop.
