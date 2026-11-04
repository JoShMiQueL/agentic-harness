# agentic-harness — project rules

Global orchestration layer for AI coding CLIs, installed per harness:
`devin` -> `%APPDATA%\devin`, `opencode` -> `~/.config/opencode`.
This file is the project's own rules — the *payload* rules that get
installed live under each `harnesses/<name>/payload/`.

## Layout

```
harnesses/<name>/payload/    # per-harness payload, maps 1:1 onto the data dir
├── AGENTS.md                # global always-on rules
├── agents/*.md              # agent profiles (frontmatter + system prompt)
├── skills/*/(SKILL.md)      # skill payloads (devin: /orchestrate, opencode: orchestration)
├── hooks/*.py               # devin lifecycle hook scripts (python, stdlib only)
├── plugins/*.js             # opencode plugin modules (ESM, no deps)
└── config.managed.json      # keys merged into the harness config file
install.py                   # installer / --check sync / --harness selector
uninstall.py                 # stamp-driven removal
install.*, uninstall.*       # .cmd/.sh/.ps1 thin shims -> require python
VERSION                      # bumped on every shipped change
```

## Harness notes

- devin: hooks are python scripts wired in `config.json → hooks`
  (placeholders `{{PY}}`, `{{DEVIN_HOME}}`). Primary agent can't be
  replaced -> delegation contract lives in the `orchestrate` skill.
- opencode: hooks are ESM plugins in `plugins/` (`tool.execute.before`,
  `experimental.chat.system.transform`); deny = `throw`. Primary agent IS
  replaceable -> `agents/orchestrator.md` + `default_agent` in managed
  config. Permissions use per-tool glob maps, last match wins.

## Rules for working on this repo

- Conversational replies in Spanish; file contents and commits in English.
- Bump `VERSION` with every change that affects a payload or installer.
- Conventional commits.
- Installer and devin hook scripts must stay Python 3.8+ compatible,
  stdlib only. Opencode plugins must be dependency-free ESM.
- NEVER commit `credentials.toml`, `.env*`, or `org_id`.
- After changing a payload, verify against a sandbox, never the real home:
  `python install.py --harness devin --devin-home ./sandbox/devin`
  `python install.py --harness opencode --opencode-home ./sandbox/oc`
  `DEVIN_DATA_DIR=$PWD/sandbox/devin devin doctor` validates devin side;
  `OPENCODE_CONFIG_DIR=$PWD/sandbox/oc opencode debug config` for opencode.
  `--dry-run` prints the plan without writing. `sandbox/` is gitignored.
- Entry points: PowerShell one-liner via raw.githubusercontent.com (jsDelivr
  can serve .ps1 as octet-stream, which breaks `irm|iex`); cmd/bash via
  jsDelivr `@main`. install.py downloads commit-pinned files via the API
  (falls back to the legacy repo name while GitHub redirects hold).
- CI (`.github/workflows/ci.yml`) runs install/uninstall smoke tests for
  BOTH harnesses on ubuntu-24.04 + windows-latest — keep it green.
