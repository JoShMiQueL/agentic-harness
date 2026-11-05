  The contract is embedded in your system prompt (you ARE the
  orchestrator); load the `orchestration` skill for prompt-writing detail.
- Subagents: `scout` (read-only research), `tester` (verification),
  `reviewer` (diff review), `worker` (implementation) â€” via the Task tool
  or `@name` mentions.
- Subagents report via a `REPORT` block â€” consume only that. Long outputs
  belong in `{{REPORTS_DIR}}/`, durable cross-session state in
  `{{MEMORY_STATE}}` (created only when needed).
