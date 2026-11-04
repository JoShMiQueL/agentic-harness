| Agent | For | Writes |
|---|---|---|
| `scout` | Codebase exploration, architecture, research | no |
| `tester` | Running tests/lint/build and reporting | `{{REPORTS_DIR}}/` only |
| `reviewer` | Diff reviews by severity | `{{REPORTS_DIR}}/` only |
| `worker` | Scoped implementation subtasks | yes |
| `general` / `explore` | built-in fallback | — |
