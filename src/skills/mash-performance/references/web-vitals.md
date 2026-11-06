# Web vitals

One Lighthouse performance category, through the chrome-devtools skill. These bands are the lab signals published by web.dev. They are review thresholds, not a certification and not field data.

| Check id | Metric | Pass | Fail `P2` | Fail `P1` |
| --- | --- | --- | --- | --- |
| `perf.lighthouse.lcp` | Largest Contentful Paint | `<= 2500` ms | `> 2500` and `<= 4000` ms | `> 4000` ms |
| `perf.lighthouse.inp` | Interaction to Next Paint | `<= 200` ms | `> 200` and `<= 500` ms | `> 500` ms |
| `perf.lighthouse.cls` | Cumulative Layout Shift | `<= 0.1` | `> 0.1` and `<= 0.25` | `> 0.25` |

Record the number the audit printed. Do not round a miss into a pass.

Lighthouse lab runs often omit Interaction to Next Paint and print Total Blocking Time instead. When INP is absent, `perf.lighthouse.inp` is `Blocked (needs human verify)`, reason "lab run did not include INP". Write the Total Blocking Time on the `perf.lighthouse.scan` note. Do not file Total Blocking Time as a pass for INP.

A missing metric other than that INP case blocks that row. Do not invent the number.
