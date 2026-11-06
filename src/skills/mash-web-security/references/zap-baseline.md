# ZAP baseline

Discovery order. Use the first one that runs. Do not invent a fourth scanner.

1. `zap-baseline.py` on `PATH`.
2. The baseline entrypoint inside the official ZAP container image `ghcr.io/zaproxy/zaproxy:stable`, and only when the host script is missing and `docker` can run that image. If the ZAP docs installed on the machine name a different official baseline image, use that image and record its name in the evidence block.
3. Otherwise the check is blocked.

Missing tool remediation, written on the row: install OWASP ZAP so `zap-baseline.py` is on `PATH`. Download: `https://www.zaproxy.org/download/`. Do not substitute Nikto, Nuclei, or a custom script.

## Commands

Host script, report JSON in the run temp directory:

```bash
zap-baseline.py -t "$BASE" -m 5 -J "$TMP/zap.json"
```

Container, local origin, Linux host network so `localhost` is the app:

```bash
docker run --rm -t --network host -v "$TMP:/zap/wrk" \
  ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t "$BASE" -m 5 -J zap.json
```

`$BASE` is the resolved origin only. Do not pass `-j` (ajax spider). Do not add config that includes another host. `-m 5` is the phase-1 minute cap.

Staging uses the same arguments. The container needs ordinary outbound network to reach a public staging host, not `--network host`, unless the staging origin is on the host loopback.

If a container run cannot open a loopback origin, retry once with the host name `host.docker.internal` in place of `localhost`, still the same local app. Record both commands. If that retry also fails, the row is `Blocked (needs human verify)`. Do not point ZAP at a different site.

## Reading the report

Prefer the JSON report. ZAP riskcode `3` is High, `2` is Medium, `1` is Low, `0` is Informational. Map those with the mash-project-review status vocabulary. If the JSON shape is not the baseline alert list, use the Markdown report (`-w`) and paste the alert lines verbatim. A parse failure is `Blocked (needs human verify)`, not a Pass.

Off-host URLs in the report are out of scope. Do not file them as findings and do not request them.

Do not pass a session cookie, an Authorization header, or a ZAP context that includes credentials. Redact the report excerpt before it enters the evidence block.
