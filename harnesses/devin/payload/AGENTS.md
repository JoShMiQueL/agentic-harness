# Global rules

## Language

- Conversational replies: Spanish. Artifacts (code, reports, memory, commit
  messages, file contents): English.

## Orchestration

- Prefer delegating to a subagent when work benefits from an isolated
  context (broad research, scoped implementation, verification, review).
  See the `orchestrate` skill for the full contract.
- Custom profiles: `scout` (read-only research), `tester` (verification),
  `reviewer` (diff review), `worker` (implementation).
- Subagents report via a `REPORT` block — consume only that. Long outputs
  belong in `.devin/reports/`, durable cross-session state in
  `.devin/memory/state.md` (created only when needed).
- Background subagents cannot ask for permissions: tools not pre-approved
  in this session are auto-denied. Run write-capable subagents in the
  foreground, or pre-approve their tools first.

## Memory

- Before ending a task whose state must survive the session, update
  `.devin/memory/state.md` (≤50 lines: state, decisions, pending) —
  a SessionStart hook injects it next session.
