## Edits: when to keep them, when to delegate

Keep it yourself when ALL of these hold:

- The change touches ≤3 files or a few dozen lines.
- You already have the relevant code in context.
- Correctness is verifiable at a glance or with one quick command.
- The edit is part of an ongoing reasoning chain (you decided it a
  second ago) — delegating would force a subagent to rebuild that
  reasoning.

Delegate when ANY of these hold:

- The subtask is self-contained with a clear scope (a feature, a fix, a
  refactor) — it deserves its own context and a clean REPORT.
- Doing it inline would fill your context with tool output, iterations
  and dead ends you don't need afterwards.
- Several disjoint chunks can run in parallel.
- The work needs a different tool posture (read-only research,
  verification) than your current one.

Rule of thumb: a subagent pays off when the delegated work is larger
than the prompt you'd have to write to specify it. For a one-line fix
that is almost never true — write the line yourself. Everywhere else,
bias toward delegating.
- Parallelize subagents with disjoint work; never two writing the same
  files.
