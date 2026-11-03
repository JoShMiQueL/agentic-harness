# devin-agentic — project rules

Global orchestration layer for Devin CLI, installed into `%APPDATA%\devin\`.
This file is the project's own rules — the *payload* rules that get installed
live in `devin-home/AGENTS.md` instead.

## Layout

```
devin-home/            # payload, maps 1:1 onto %APPDATA%\devin\
├── AGENTS.md          # global rules shipped to every Devin session
├── agents/*.md        # subagent profiles (frontmatter + system prompt)
├── skills/*/(SKILL.md)
├── hooks/*.ps1        # lifecycle hook scripts
└── config.managed.json# permissions+hooks merged into user config.json
install.ps1            # installer / bootstrap / -Check sync (irm|iex ready)
uninstall.ps1          # removes installed files + hooks key
VERSION                # bumped on every shipped change
```

## Rules for working on this repo

- Conversational replies in Spanish; file contents and commits in English.
- Bump `VERSION` with every change that affects the payload or installer.
- Conventional commits.
- Hook scripts and installer must stay PowerShell 5.1 compatible — no PS7
  syntax (`??`, `?.`, `&&`/`||` operators, `ForEach-Object -Parallel`).
- NEVER commit `credentials.toml`, `.env*`, or `org_id`.
- After changing the payload, verify with `.\install.ps1` then
  `.\install.ps1 -Check` and `devin doctor`.
- The remote one-liner uses jsDelivr `@main`; raw.githubusercontent.com has
  sticky per-path caching — do not switch back.
