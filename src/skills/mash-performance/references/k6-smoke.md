# k6 smoke

Host tool. Discovery is `command -v k6`. Nothing else counts. A container image, an `npx` package, or a binary downloaded into the app is not a substitute.

Missing tool remediation, written on the row: install k6 and put it on `PATH`. Download: `https://grafana.com/docs/k6/latest/set-up/install-k6/`.

## Script

Write this file into the run temp directory as `smoke.js`. Do not commit it. Do not raise `vus` or `duration`. `$BASE` is the resolved origin plus the first `path:` token, or the origin itself. The path stays on that origin.

```javascript
import http from "k6/http";
import { check } from "k6";

export const options = {
  vus: 2,
  duration: "10s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
  },
};

export default function () {
  const res = http.get(`${__ENV.BASE}`);
  check(res, { "status is 200": (r) => r.status === 200 });
}
```

## Command

```bash
k6 run -e BASE="$BASE" "$TMP/smoke.js"
```

k6 exits non-zero when a threshold fails. A crossed threshold prints the summary and exits `99`. That exit is a `Fail`, not a blocked scan. A crash before the summary is `Blocked (needs human verify)` with the stderr tail.

The duration threshold is a review signal for this smoke. It is not a service-level objective. Do not describe a pass as proof the app will hold production traffic.
