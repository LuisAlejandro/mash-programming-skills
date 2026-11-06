# Status vocabulary

Use these strings in the status cell. Do not translate them and do not invent nearby labels (`manual`, `warning`, `error`, `pasa`, `falla`).

| Status | When to use it |
| --- | --- |
| `Pending` | Checkpoint only. The check has not run. A finalized report has no `Pending` row. |
| `Pass` | The check ran, and that check's assertion did not fail. A pass is an observation about that check. It is not a certification and it does not prove other defects are absent. |
| `Fail` | The check ran and the finding is confirmed. The row has a command and real output, or a human note for a manual check the person confirmed. |
| `Skipped` | The check does not apply. The reason is written on the row. Example: no `package-lock.json`, so npm audit does not apply. |
| `Blocked (needs human verify)` | A person must judge the check, the tool is missing, an auth wall stopped the check, or the tool returned an incomplete result. Name the remediation or the human step. Do not treat the row as a pass. |

`Blocked` alone is not a status. The status cell contains `Blocked (needs human verify)`.

## Severity

`P0` through `P3`, the same letters used by mash-qa findings, so a person can triage static and runtime reviews together.

| Source | Map |
| --- | --- |
| axe impact `critical` | `P0` |
| axe impact `serious` | `P1` |
| axe impact `moderate` | `P2` |
| axe impact `minor` | `P3` |
| ZAP risk High (riskcode 3) | `P0` |
| ZAP risk Medium (riskcode 2) | `P2` |
| ZAP risk Low (riskcode 1) | `P3` |
| ZAP risk Informational (riskcode 0) | `Skipped`, not a Fail |
| npm or pip-audit `critical` | `P0` |
| npm or pip-audit `high` | `P1` |
| npm or pip-audit `moderate` | `P2` |
| npm or pip-audit `low` | `P3` |

A hint column may name a WCAG criterion or an OWASP Top 10 category. The hint does not change the status. Leave it blank when the mapping is uncertain.

## Final status

Judge the matrix after every row is terminal:

- Any `Fail` at `P0` or `P1` → `not ready`.
- No blocking Fail, and any `Fail` at `P2` or `P3` or any `Blocked (needs human verify)` → `ready with caveats`. Name those rows.
- Every row `Pass` or `Skipped` → `ready with caveats`. State that the matrix is non-exhaustive.

Do not write a final status of compliant, certified, or safe. Never claim the target is WCAG compliant, ASVS compliant, or OWASP-safe.
