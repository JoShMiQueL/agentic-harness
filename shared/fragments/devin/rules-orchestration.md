  See the `orchestrate` skill for the full contract.
- Custom profiles: `scout` (read-only research), `tester` (verification),
  `reviewer` (diff review), `worker` (implementation).
- Subagents report via a `REPORT` block â€” consume only that. Long outputs
  belong in `{{REPORTS_DIR}}/`, durable cross-session state in
  `{{MEMORY_STATE}}` (created only when needed).
- Background subagents cannot ask for permissions: tools not pre-approved
  in this session are auto-denied. Run write-capable subagents in the
  foreground, or pre-approve their tools first.
