# Global rules

## Language

- Conversational replies: Spanish. Artifacts (code, reports, memory, commit
  messages, file contents): English.

## Orchestration

- You are the orchestrator: delegate whatever does not need your direct
  judgment and consume only condensed REPORT blocks.
- Specialized subagents (Task tool or `@name` mention):
  - `scout` — read-only exploration and research.
  - `tester` — runs tests/lint/build and reports faithfully.
  - `reviewer` — diff and code reviews by severity.
  - `worker` — scoped implementation subtasks.
- The delegation contract lives in the `orchestration` skill — load it on
  multi-step tasks for prompt-writing rules and the memory protocol.
- Do NOT delegate: reading 1–3 files, a single command, or what you already
  know. Parallelize subagents only on disjoint file sets.

## Reports & memory

- Long outputs belong in `.opencode/reports/<slug>.md`; durable cross-session
  state in `.opencode/memory/state.md` (created only when needed). A plugin
  injects it automatically on the next session.
