| Profile | For | Model | Writes |
|---|---|---|---|
| `scout` | Codebase exploration, architecture, research | {{MODEL_SCOUT}} | no |
| `tester` | Running tests/lint/build and reporting | {{MODEL_TESTER}} | `{{REPORTS_DIR}}/` only |
| `reviewer` | Diff reviews by severity | {{MODEL_REVIEWER}} | `{{REPORTS_DIR}}/` only |
| `worker` | Scoped implementation subtasks | {{MODEL_WORKER}} | yes |
| `subagent_explore` / `subagent_general` | built-in fallback | router / parent | — |
