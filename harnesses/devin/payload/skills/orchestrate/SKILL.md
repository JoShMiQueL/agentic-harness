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
| `scout` | Codebase exploration, architecture, research | swe-2-flash-high | no |
| `tester` | Running tests/lint/build and reporting | swe-2-flash-medium | `.devin/reports/` only |
| `reviewer` | Diff reviews by severity | swe-2 | `.devin/reports/` only |
| `worker` | Scoped implementation subtasks | swe-2-flash-high | yes |

Model ids resolve through the devin-proxy wire: `swe-2*` lanes are free on
Pro+ (Flash = 3x faster, 1/5 cost — free through the promo window); any
other catalog uid needs `DEVIN_PROXY_ALLOW_PAID=1` and bills credits.
`devin-proxy models` lists the routed ids.
| `subagent_explore` / `subagent_general` | built-in fallback | router / parent | — |

Launch them with the subagent tool, foreground or background. Background
subagents cannot ask for permissions: tools not pre-approved in this session
are auto-denied — run write-capable subagents in the foreground, or
pre-approve their tools first.

## When to delegate

- Broad or uncertain investigation → `scout` (background if more work exists).
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
