# Global rules

## Language

- Conversational replies: Spanish. Artifacts (code, reports, memory, commit
  messages, file contents): English.

## Orchestration

- Prefer delegating to a subagent when work benefits from an isolated
  context (broad research, scoped implementation, verification, review).
{{INCLUDE:rules-orchestration.md}}
## Memory

- Before ending a task whose state must survive the session, update
  `{{MEMORY_STATE}}` (≤50 lines: state, decisions, pending) —
  {{MEMORY_SHORT}}.
