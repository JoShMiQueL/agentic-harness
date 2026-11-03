# devin-agentic — project rules

Global orchestration layer for Devin CLI, installed into `%APPDATA%\devin\`
(Windows) or `~/.config/devin/` (Linux/macOS). This file is the project's own
rules — the *payload* rules that get installed live in
`devin-home/AGENTS.md` instead.

## Layout

```
devin-home/             # payload, maps 1:1 onto the devin data dir
├── AGENTS.md           # global rules shipped to every Devin session
├── agents/*.md         # subagent profiles (frontmatter + system prompt)
├── skills/*/(SKILL.md)
├── hooks/*.py          # lifecycle hook scripts (python, stdlib only)
└── config.managed.json # permissions+hooks merged into user config.json
install.py              # THE installer (--check / --dry-run / --devin-home / --set-bypass)
uninstall.py            # stamp-driven removal
install.*, uninstall.*  # .cmd/.sh/.ps1 thin shims -> require python
VERSION                 # bumped on every shipped change
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
  `DEVIN_DATA_DIR=$PWD/sandbox/devin devin doctor`.
  `--dry-run` prints the plan without writing. `sandbox/` is gitignored.
- CI (`.github/workflows/ci.yml`) runs the same install/uninstall smoke test
  on ubuntu-24.04 + windows-latest — keep it green.
- The PowerShell one-liner uses raw.githubusercontent.com (jsDelivr can serve
  .ps1 as octet-stream, which breaks `irm|iex`). cmd/bash entry points use
  jsDelivr `@main`. install.py itself resolves the commit SHA via the GitHub
  API and downloads commit-pinned files — always fresh.
