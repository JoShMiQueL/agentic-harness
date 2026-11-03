#!/usr/bin/env python3
# PreToolUse hook - hard policy, applies in every permission mode (incl. dangerous).
# Input (stdin): hook event JSON { hook_event_name, tool_name, tool_input, ... }
# Output (stdout): {"decision":"block","reason":...} to deny, nothing to allow.
import json
import re
import sys

DESTRUCTIVE = re.compile(
    r'rm\s+(-[a-zA-Z]*r|-[a-zA-Z]*f)'
    r'|Remove-Item\s+.*-Recurse'
    r'|del\s+/s\s+/q'
    r'|format\s+[a-zA-Z]:'
    r'|dd\s+if='
    r'|git\s+push\s+(-f|--force)'
    r'|git\s+reset\s+--hard'
    r'|git\s+clean\s+-[a-zA-Z]*f'
)
SECRETS = re.compile(r'\.env|id_rsa|\.pem$|\.key$|credentials\.toml$')

event = json.load(sys.stdin)
tool = event.get('tool_name', '')
inp = event.get('tool_input') or {}


def block(reason):
    print(json.dumps({'decision': 'block', 'reason': reason}))


if tool == 'exec':
    if DESTRUCTIVE.search(inp.get('command', '')):
        block('Destructive command blocked by global policy. Ask the user to run it manually.')
elif tool in ('read', 'write', 'edit', 'notebook_edit', 'notebook_read'):
    if SECRETS.search(inp.get('file_path', '')):
        block('Secret file access blocked by global policy.')
