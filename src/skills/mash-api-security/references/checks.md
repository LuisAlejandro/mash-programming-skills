# API probe

The executor is the skill-local script. It uses the Python standard library. It is Mash skill tooling, not an app start command, and not a third-party scanner.

```bash
python3 "<skill-dir>/scripts/run_api_checks.py" --self-check
python3 "<skill-dir>/scripts/run_api_checks.py" \
  --spec "$SPEC" --base "$BASE" --out "$TMP/api.json"
```

Pass `--allow-staging` only after the mash-project-review safety reference has accepted that staging origin. Never pass it for a production host. Exit `3` means the script sent no request.

`<skill-dir>` is the directory that contains this skill's `SKILL.md`.

## Spec

`spec:` wins. Otherwise the first file that exists in the project root: `openapi.json`, `openapi.yaml`, `openapi.yml`, `swagger.json`, `swagger.yaml`.

No file: do not run the probe. `api.probe` is `Blocked (needs human verify)`. Remediation: pass `spec:` pointing at an OpenAPI document. JSON is read with the standard library. YAML is read only when `python3 -c 'import yaml'` works. If it does not, the remediation is to convert the document to JSON. Do not install a parser into the app.

The script calls `--base` only. It does not call URLs in the document's `servers` array.

## Accounts

The script reads the environment. Do not put the values on the command line and do not write them in the report.

| Variable | Use |
| --- | --- |
| `MASH_REVIEW_USER_A` | Bearer token for test user A |
| `MASH_REVIEW_USER_B` | Bearer token for test user B |
| `MASH_REVIEW_USER_A_ID` | Object id owned by user A |
| `MASH_REVIEW_USER_B_ID` | Object id owned by user B |

Missing tokens still allow the unauthenticated request. Checks that need an account are `Blocked (needs human verify)` with the missing variable names. Do not invent a password. Do not try a list of passwords. Interactive mode asks once for the variables to be exported, then continues.

## What the script records

Severity and status come from the script. The mash-project-review status vocabulary is the map the script implements. Hint text is a hint, not a certification.

| Check id | Assertion |
| --- | --- |
| `api.probe` | The script finished and printed JSON |
| `api.auth.<method>.<path>` | An operation with a non-empty `security` requirement, or with no `security` at all, does not return a 2xx without credentials. `401` or `403` is `Pass`. An empty `security` array is `Skipped`, reason "spec marks security as empty" |
| `api.bola.<method>.<path>` | User B's token requesting user A's id does not receive A's object. `401`, `403`, or `404` is `Pass`. A 2xx body whose owner field is A's id is `Fail` |
| `api.mass-assignment` | A write rejects or drops privileged fields that are absent from the writable schema or marked `readOnly`: `role`, `isAdmin`, `is_admin`, `admin`, `ownerId`. No write operation is `Skipped` |
| `api.rate-limit` | Twenty sequential requests, one fixed body, no password list. One or more `429` responses is `Pass`. None is `Fail`. This is not a load test |
| `api.errors.verbose` | A malformed body `{` and one unknown id do not return a stack trace, SQL driver error, or filesystem path |
| `api.cors` | `Origin: https://evil.example` is not reflected, and `Access-Control-Allow-Origin` is not `*` |

A 2xx without credentials on a protected operation is `P0`. A confirmed object read across the two test users is `P0`. A persisted privileged field is `P0`. A reflected origin together with `Access-Control-Allow-Credentials: true` is `P0`. A `*` origin or a reflected origin without credentials is `P1`. A verbose error body is `P1`. A burst with no `429` is `P2`.

## Output

Read the JSON object between `API_JSON` and `END_API_JSON`. The same object is in `--out`. Each `checks` entry already has `command` and `output` with secrets replaced by `[redacted]`. Paste those fields. Do not paste a raw transcript that still contains a token.

ponytail: path parameters are filled from the two account ids only. A path with several different ids needs a later map. The rate burst is sequential, so a limit that trips only under concurrency is outside this check.
