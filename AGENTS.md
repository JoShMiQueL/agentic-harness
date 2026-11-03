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
├── hooks/*.py         # lifecycle hook scripts (python, stdlib only)
└── config.managed.json# permissions+hooks merged into user config.json
install.py             # installer / bootstrap / --check sync
uninstall.py           # stamp-driven removal
install.*, uninstall.* # .cmd/.sh/.ps1 thin shims -> require python
VERSION                # bumped on every shipped change
```

## Rules for working on this repo

- Conversational replies in Spanish; file contents and commits in English.
- Bump `VERSION` with every change that affects the payload or installer.
- Conventional commits.
- Installer and hook scripts must stay Python 3.8+ compatible, stdlib only
  (no third-party deps — the target machine may have nothing else).
- NEVER commit `credentials.toml`, `.env*`, or `org_id`.
- After changing the payload, verify against a sandbox, never the real home:
  `python install.py --devin-home ./sandbox/devin` then
  `DEVIN_DATA_DIR=$PWD/sandbox/devin devin doctor`. `--dry-run` prints
  the plan without writing. `sandbox/` is gitignored.
- Entry points: PowerShell one-liner via raw.githubusercontent.com (jsDelivr
  can serve .ps1 as octet-stream, which breaks `irm|iex`); cmd/bash via
  jsDelivr `@main`. install.py downloads commit-pinned files via the API —
  always fresh either way.
- CI (`.github/workflows/ci.yml`) runs the install/uninstall smoke test on
  ubuntu-24.04 + windows-latest — keep it green.
