---
name: orchestration
description: Orchestration contract — when and how to delegate to specialized subagents, structured REPORT input, disk artifacts and optional memory. Load on multi-step tasks.
---

# Lightweight orchestration

Act as the orchestrator. Your context is scarce: delegate whatever does not
need your direct judgment and consume only condensed reports.

## Available subagents

| Agent | For | Model | Writes |
|---|---|---|---|
| `scout` | Codebase exploration, architecture, research | devin-local/swe-2-flash | no |
| `tester` | Running tests/lint/build and reporting | devin-local/swe-2-flash-medium | `.opencode/reports/` only |
| `reviewer` | Diff reviews by severity | devin-local/swe-2 | `.opencode/reports/` only |
| `worker` | Scoped implementation subtasks | devin-local/swe-2-flash-high | yes |
| `general` / `explore` | built-in fallback | global model | — |

`devin-local/*` ids map onto the devin-proxy lanes: `swe-2*` lanes are free
on Pro+ (Flash = 3x faster, 1/5 cost); other catalog uids need
`DEVIN_PROXY_ALLOW_PAID=1` and bill credits. `devin-proxy models` lists the
routed ids.

Launch them with the Task tool (`subagent_type`) or mention `@name`.

## When to delegate

- Broad or uncertain investigation → `scout`.
- Implementation with a clear scope → `worker`.
- Post-change verification → `tester`. Pre-merge → `reviewer`.
- Do NOT delegate: reading 1–3 files, a single command, or what you already
  know. Subagent launches cost a full prompt round-trip (goal + scope + file
  contents + acceptance criteria re-stated) — on tiny edits that costs more
  than the edit itself.

## Edits: when to keep them, when to delegate

Keep it yourself when ALL of these hold:

- The change touches ≤3 files or a few dozen lines.
- You already have the relevant code in context.
- Correctness is verifiable at a glance or with one quick command.
- The edit is part of an ongoing reasoning chain (you decided it a second
  ago) — delegating would force a subagent to rebuild that reasoning.

Delegate when ANY of these hold:

- The subtask is self-contained with a clear scope (a feature, a fix, a
  refactor) — it deserves its own context and a clean REPORT.
- Doing it inline would fill your context with tool output, iterations and
  dead ends you don't need afterwards.
- Several disjoint chunks can run in parallel.
- The work needs a different tool posture (read-only research, verification)
  than your current one.

Rule of thumb: a subagent pays off when the delegated work is larger than
the prompt you'd have to write to specify it. For a one-line fix that is
almost never true — write the line yourself.
- Parallelize subagents with disjoint work; never two writing the same files.

## How to delegate (self-contained prompt)

The subagent does NOT see your conversation. Its prompt must carry: goal,
exact scope, relevant paths/files, context you already discovered, acceptance
criteria, and what to return.

## Input contract: the REPORT block

All agents end with:

```
REPORT
status: ok | blocked | failed
summary: <max 3 lines>
artifact: <path under .opencode/reports/ or none>
files: <key files>
next: <next step or none>
```

Consume only that. On `blocked`/`failed`, get details before retrying or
escalating to the user. If `artifact` points to a file, do not re-read it in
full unless needed — `summary` already condenses it.

## Disk artifacts

Long outputs live in `.opencode/reports/<slug>.md` (write-capable agents
create them; for `scout`, persist the summary yourself if worth keeping).
They act as handoff between tasks and sessions without inflating context.

## Memory (only when necessary)

- If a task will span sessions, or the user asks to remember something
  durable: create/update `.opencode/memory/state.md` (≤50 lines: state,
  decisions, pending).
- The agentic-memory plugin injects it into the system prompt
  automatically next session. Do not create memory for single-session work.
