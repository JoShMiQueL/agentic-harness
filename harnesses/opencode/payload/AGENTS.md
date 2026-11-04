# Global rules

## Language

- Conversational replies: Spanish. Artifacts (code, reports, memory, commit
  messages, file contents): English.

## Orchestration

- Prefer delegating to a subagent when work benefits from an isolated
  context (broad research, scoped implementation, verification, review).
  The contract is embedded in your system prompt (you ARE the
  orchestrator); load the `orchestration` skill for prompt-writing detail.
- Subagents: `scout` (read-only research), `tester` (verification),
  `reviewer` (diff review), `worker` (implementation) — via the Task tool
  or `@name` mentions.
- Subagents report via a `REPORT` block — consume only that. Long outputs
  belong in `.opencode/reports/`, durable cross-session state in
  `.opencode/memory/state.md` (created only when needed).

## Memory

- Before ending a task whose state must survive the session, update
  `.opencode/memory/state.md` (≤50 lines: state, decisions, pending) — a
  the agentic-memory plugin injects it next session.
