# Global rules

## Language

- Conversational replies: Spanish. Artifacts (code, reports, memory, commit

  messages, file contents): English.

## Orchestration

- Prefer delegating to a subagent when work benefits from an isolated

  context (broad research, scoped implementation, verification, review).

  See the `orchestrate` skill for the full contract.
- Delegate by default: anything touching >3 files or needing a tool
  chain goes to a subagent. Your own tools are for targeted lookups —
  never for exploratory sweeps (`scout` owns those).
- Custom profiles: `scout` (read-only research), `tester` (verification),
  `reviewer` (diff review), `worker` (implementation).
- Subagents report via a `REPORT` block — consume only that. Long outputs
  belong in `.devin/reports/`, durable cross-session state in
  `AGENTS.md` (created only when needed).
- Background subagents cannot ask for permissions: tools not pre-approved
  in this session are auto-denied. Run write-capable subagents in the
  foreground, or pre-approve their tools first.

## Shell & fast tools

- For exploration/lookups always prefer the harness **native tools**
  (`glob`/`grep`/`read`) — they run in-process and are fastest. The shell
  tools below are for when you actually execute commands (builds, tests,
  git, pipelines); prefer them over the classic Unix originals on PATH:

  | task | use | not |
  |---|---|---|
  | search file contents | `rg` (respects .gitignore, parallel) | `grep -r` |
  | find files | `fd` | `find` |
  | structural code search/rewrite | `ast-grep` (`sg`) | `grep` on code |
  | read files | `bat` | `cat` |
  | list dirs | `eza` (`--tree --git`) | `ls`/`tree` |
  | find & replace | `sd` | `sed` |
  | JSON / YAML | `jq` / `yq` | manual parsing |
  | disk usage | `dust` / `duf` | `du`/`df` |
  | git diffs | `delta` (set as pager) | `diff` |
  | count code | `tokei` | `wc`/`cloc` |
  | benchmarks | `hyperfine` | `time` |
  | cd / fuzzy find | `zoxide` (`z`) / `fzf` | - |
  | task runner | `just` | `make` |

- These are optional — if a tool is missing, fall back to the classic
  command, or `winget install <pkg>` then use it.
- On Windows the agent shell is **Git Bash** (MSYS2). Write POSIX bash,
  never PowerShell. For multi-line or quote-heavy commands, write a `*.sh`
  file and execute it — single quotes get mangled through the launcher.

## Memory

- Before ending a task whose state must survive the session, update

  `AGENTS.md` (≤50 lines: state, decisions, pending) —

  Devin injects `AGENTS.md` every session.
