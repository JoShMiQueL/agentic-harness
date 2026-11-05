| Agent | For | Model | Writes |
|---|---|---|---|
| `scout` | Codebase exploration, architecture, research | {{MODEL_SCOUT}} | no |
| `tester` | Running tests/lint/build and reporting | {{MODEL_TESTER}} | `{{REPORTS_DIR}}/` only |
| `reviewer` | Diff reviews by severity | {{MODEL_REVIEWER}} | `{{REPORTS_DIR}}/` only |
| `worker` | Scoped implementation subtasks | {{MODEL_WORKER}} | yes |
| `general` / `explore` | built-in fallback | global model | - |

`devin-proxy/*` ids map onto the devin-proxy lanes: `swe-2*` lanes are free
on Pro+ (Flash = 3x faster, 1/5 cost); other catalog uids need
`DEVIN_PROXY_ALLOW_PAID=1` and bill credits. `devin-proxy models` lists the
routed ids.
