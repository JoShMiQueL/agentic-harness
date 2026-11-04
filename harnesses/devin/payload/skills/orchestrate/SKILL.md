---
name: orchestrate
description: User's orchestration system — when and how to delegate to subagents, structured REPORT contract, disk artifacts and optional memory. Use on multi-step tasks.
triggers:
  - user
  - model
---

# Lightweight orchestration

Act as the orchestrator. Your context is scarce: delegate whatever does not
need your direct judgment and consume only condensed reports.

## Available profiles (global)

| Profile | For | Model | Writes |
|---|---|---|---|
| `scout` | Codebase exploration, architecture, research | swe-2-medium | no |
| `tester` | Running tests/lint/build and reporting | swe-2-medium | `.devin/reports/` only |
| `reviewer` | Diff reviews by severity | swe-2-high | `.devin/reports/` only |
| `worker` | Scoped implementation subtasks | swe-2-max | yes |
| `subagent_explore` / `subagent_general` | built-in fallback | router / parent | — |

## When to delegate

- Broad or uncertain investigation → `scout` (background if more work exists).
- Implementation with a clear scope → `worker`.
- Post-change verification → `tester`. Pre-merge → `reviewer`.
- Do NOT delegate: reading 1–3 files, a single command, or what you already know.
- Parallelize subagents with disjoint work; never two writing the same files.

## How to delegate (self-contained prompt)

The subagent does NOT see your conversation. Its prompt must carry: goal,
exact scope, relevant paths/files, context you already discovered, acceptance
criteria, and what to return.

## Input contract: the REPORT block

All profiles end with:

```
REPORT
status: ok | blocked | failed
summary: <max 3 lines>
artifact: <path under .devin/reports/ or none>
files: <key files>
next: <next step or none>
```

Consume only that. On `blocked`/`failed`, get details before retrying or
escalating to the user. If `artifact` points to a file, do not re-read it in
full unless needed — `summary` already condenses it.

## Disk artifacts

Long outputs live in `.devin/reports/<slug>.md` (write-capable profiles
create them; for `scout`, persist the summary yourself if worth keeping).
They act as handoff between tasks and sessions without inflating context.

## Memory (only when necessary)

- If a task will span sessions, or the user asks to remember something
  durable: create/update `.devin/memory/state.md` (≤50 lines: state,
  decisions, pending).
- A SessionStart hook injects it automatically next session. Do not create
  memory for single-session work.
