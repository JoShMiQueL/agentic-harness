| Profile | For | Model | Writes |
|---|---|---|---|
| `scout` | Codebase exploration, architecture, research | swe-2-medium | no |
| `tester` | Running tests/lint/build and reporting | swe-2-medium | `{{REPORTS_DIR}}/` only |
| `reviewer` | Diff reviews by severity | swe-2-high | `{{REPORTS_DIR}}/` only |
| `worker` | Scoped implementation subtasks | swe-2-max | yes |
| `subagent_explore` / `subagent_general` | built-in fallback | router / parent | — |
