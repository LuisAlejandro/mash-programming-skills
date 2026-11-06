# Project review — <slug>

> Runtime self-review of the user's own app. Generated on <YYYY-MM-DD> UTC.
> Observed checks and gaps only. Never claim the target is WCAG compliant, ASVS compliant, or OWASP-safe.

<!-- Repo-relative paths only. Build the report to this shape. -->

## Metadata

- **Front:** `<all | a11y | web-security | api-security | performance>`
- **Target:** `<local | staging>`
- **Base URL:** `<origin>`
- **Date:** `<YYYY-MM-DD>`
- **Slug:** `<slug>`
- **Report path:** `.mash/project-review/<YYYY-MM-DD>-<front>-<slug>.md`
- **Tool versions:** `<axe version, ZAP version, package-manager audit tool, agent-browser pin, k6 version, or "not run">`
- **Interaction:** interactive | non-interactive
- **Routes:** `<path list, or "homepage only">`

## Safety

- Environment: `<local origin | confirmed staging origin>`. Production targets are refused.
- Tools stayed on that origin. Dependency audits read this project tree only.
- Authorization headers, cookies, and secrets are redacted.

## Matrix

| Check id | Front | Title | Severity | Status | Hint |
| --- | --- | --- | --- | --- | --- |
| a11y.axe.scan | a11y | axe-core scan finished | P2 | Pending | hint only |
| | | | | Pass | |
| | | | | Fail | |
| | | | | Skipped | |
| | | | | Blocked (needs human verify) | |

Status values: `Pending`, `Pass`, `Fail`, `Skipped`, `Blocked (needs human verify)`. Start every row at `Pending`. The hint column is a WCAG criterion or an OWASP Top 10 category, or blank. A hint is not a certification.

## Failures

For each `Fail` row:

### <check id> — <title>

- **Symptom:** <what the tool or the person observed>
- **Expected:** <the assertion for this check>
- **Actual:** <what happened>
- **Impact:** <who is blocked or what is exposed>
- **Evidence:** <command plus real output, redacted>
- **Suggested next step:** <one concrete follow-up. Do not implement it here>

"None" when the matrix has no `Fail` rows.

## Blocked and skipped

| Check id | Status | Reason | Remediation |
| --- | --- | --- | --- |
| | Blocked (needs human verify) | | |
| | Skipped | | not applicable |

"None" when every row ran.

## Manual checklist

Used by the mash-a11y skill. Other fronts leave this section as "Not in this run."

| Check id | Title | Status | Note |
| --- | --- | --- | --- |
| | | Pending | |

## Final status

`<not ready | ready with caveats>`

Name every `P0` and `P1` Fail and every blocked row. A pass means that check's assertion held. It does not mean the app conforms to WCAG, meets ASVS, or is free of OWASP issues. The matrix is non-exhaustive.
