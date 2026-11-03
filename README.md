# devin-agentic

My personal **orchestration layer for [Devin CLI](https://docs.devin.ai/cli)**:
a global, project-agnostic multi-agent setup — subagent profiles, a delegation
contract, lifecycle hooks as external scripts, optional memory — installed once
in `%APPDATA%\devin\` and active in every project.

It replaces per-repo agent config: the orchestrator (main agent) delegates work
to specialized subagents that run in their own context and report back a
structured `REPORT` block, keeping the parent's context small.

```
%APPDATA%\devin\                     <- everything installs here, globally
├── AGENTS.md                        # global always-on rules (orchestration policy)
├── config.json                      # permissions + hooks (merged by installer)
├── agents\
│   ├── scout.md                     # read-only research          (swe-2-medium)
│   ├── tester.md                    # tests/lint/build reports    (swe-2-medium)
│   ├── reviewer.md                  # diff reviews by severity    (swe-2-high)
│   └── worker.md                    # scoped implementation       (swe-2-max)
├── skills\orchestrate\SKILL.md      # /orchestrate — full delegation contract
└── hooks\
    ├── pre-tool-guard.ps1           # PreToolUse: blocks destructive cmds + secrets
    └── session-start-memory.ps1     # SessionStart: injects .devin/memory/state.md
```

## Install

Requires [Devin CLI](https://docs.devin.ai/cli) (`devin.exe`) and PowerShell 5+.

**One-liner (remote bootstrap):**

```powershell
irm https://cdn.jsdelivr.net/gh/JoShMiQueL/devin-agentic@main/install.ps1 | iex
```

The script detects it is running from a URL, downloads the full file set to a
temp dir, then installs. No `gh` or git required.

**Alternative (clone + install):**

```powershell
gh repo clone JoShMiQueL/devin-agentic; & .\devin-agentic\install.ps1
.\install.ps1 -SetBypass   # also default every session to bypass mode
```

The installer is **idempotent**: it backs up `AGENTS.md`/`config.json` to
`*.bak-<timestamp>` before overwriting and merges only the managed keys
(`permissions`, `hooks`) — your `org_id`, credentials and model prefs survive.
Re-run it after every `git pull`.

**Uninstall:** `.\uninstall.ps1` (removes installed files + the `hooks` key;
restore a `config.json.bak-*` to fully revert).

## Updates & sync check

Every install writes a stamp at `%APPDATA%\devin\agentic.json` (version +
SHA256 of each installed file). To know whether you are in sync with the
repo, run a check:

```powershell
.\install.ps1 -Check   # from a clone
iex "& { $(irm https://cdn.jsdelivr.net/gh/JoShMiQueL/devin-agentic@main/install.ps1) } -Check"   # remote
```

Per-file statuses:

| Status | Meaning |
|---|---|
| `sync` | Installed file matches the repo |
| `update-available` | Repo changed; local untouched — run install to update |
| `locally-modified` | You edited the installed file by hand (vs. install stamp) |
| `locally-modified (+remote update pending)` | Both diverged — install will overwrite your local edit |
| `MISSING (new in repo, not installed)` | File added to the repo, not installed yet |
| `removed-in-repo` | Was installed, deleted from repo — install cleans it (`.bak` kept if locally modified) |

Workflow: `git pull` (or bump `VERSION` on GitHub) → `-Check` shows
`update-available` → run the install one-liner → back to `sync`.

## How it works

### Delegation

The global `AGENTS.md` makes delegation the default policy; the
`/orchestrate` skill (auto-discovered, shown in `<available_skills>`) carries
the full manual: which profile for what, how to write self-contained prompts,
and the memory protocol. You can also just ask in natural language:
*"use the scout subagent to map the auth flow"*.

### Report contract

Every subagent ends with a fixed block:

```
REPORT
status: ok | blocked | failed
summary: <max 3 lines>
artifact: <path under .devin/reports/ or none>
files: <key files>
next: <next step or none>
```

The orchestrator consumes only that — the subagent's transcript never enters
its context. Long outputs are written to `<repo>/.devin/reports/<slug>.md`
and referenced by path.

### Memory (optional, on demand)

For work spanning sessions, the agent maintains
`<repo>/.devin/memory/state.md` (≤50 lines). The `SessionStart` hook script
injects it automatically on the next session. Nothing is created for
single-session work.

### Hooks = hard policy

Hooks live in `hooks/*.ps1` (not inline in config) and are wired globally in
`config.json → hooks`. They fire in **every permission mode**, including
`dangerous` (verified). Each script reads the event JSON on stdin and emits
`{"decision":"block"}` on stdout to deny.

| Script | Event | Behavior |
|---|---|---|
| `pre-tool-guard.ps1` | `PreToolUse` (all tools) | `exec`: blocks `rm -rf`, `Remove-Item -Recurse`, `del /s /q`, `format`, `dd`, `git push -f`, `reset --hard`, `clean -f`. `read/write/edit`: blocks `.env*`, `id_rsa*`, `*.pem`, `*.key`, `credentials.toml` |
| `session-start-memory.ps1` | `SessionStart` | Injects `.devin/memory/state.md` as `additionalContext` if present |

### Permissions & bypass mode

`config.managed.json` ships `Read/Write/Edit/Exec(**)` in `allow` — required
so **background subagents don't auto-deny every tool** (background agents
can't prompt). The safety net is the guard script + `deny` on secret reads +
`ask` on `.env` writes.

I run `DEVIN_PERMISSION_MODE=dangerous` as a user env var (set it with
`install.ps1 -SetBypass`), so hooks are the real enforcement layer.
Per-session override: `devin --permission-mode auto`.

## Customizing (for future me)

| Want | Where |
|---|---|
| New subagent profile | `agents/<name>.md` — YAML frontmatter (`name`, `description`, `model`, `allowed-tools`, `max-nesting`) + body = system prompt. End it with the REPORT block. |
| Change a model | `model:` in the profile. Check `devin models` for slugs. Note: `subagent_general` inherits the parent's model (expensive); custom profiles don't. |
| Tune the guard | Edit the regexes in `hooks/pre-tool-guard.ps1` — no config change needed. |
| New lifecycle hook | Write `hooks/<name>.ps1`, add an entry under `"hooks"` in `config.managed.json`, re-run `install.ps1`. Events: `PreToolUse`, `PostToolUse`, `PermissionRequest`, `UserPromptSubmit`, `Stop`, `PostCompaction`, `SessionStart`, `SessionEnd`. |
| Debug hooks | `/hooks` inside a session lists loaded hooks. `devin doctor` validates agent profiles. |

## Notes

- Works on Windows (pwsh). On Linux/macOS the same layout applies under
  `~/.config/devin/` but the hook scripts would need porting from pwsh.
- NEVER commit `credentials.toml`, `.env*`, or your `org_id` — the
  `.gitignore` and `config.managed.json` (a fragment, not a full copy of
  your real config) exist precisely for that.
- Reference: [Devin CLI extensibility docs](https://docs.devin.ai/cli/extensibility),
  [subagents](https://docs.devin.ai/cli/subagents),
  [hooks](https://docs.devin.ai/cli/extensibility/hooks/overview).
