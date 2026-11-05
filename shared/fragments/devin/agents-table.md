| Profile | For | Model | Writes |
|---|---|---|---|
| `scout` | Codebase exploration, architecture, research | {{MODEL_SCOUT}} | no |
| `tester` | Running tests/lint/build and reporting | {{MODEL_TESTER}} | `{{REPORTS_DIR}}/` only |
| `reviewer` | Diff reviews by severity | {{MODEL_REVIEWER}} | `{{REPORTS_DIR}}/` only |
| `worker` | Scoped implementation subtasks | {{MODEL_WORKER}} | yes |

Model ids resolve through the devin-proxy wire: `swe-2*` lanes are free on
Pro+ (Flash = 3x faster, 1/5 cost — free through the promo window); any
other catalog uid needs `DEVIN_PROXY_ALLOW_PAID=1` and bills credits.
`devin-proxy models` lists the routed ids.
| `subagent_explore` / `subagent_general` | built-in fallback | router / parent | — |
