#!/usr/bin/env python3
# SessionStart hook - injects .devin/memory/state.md into agent context if present.
# Output (stdout): JSON with hookSpecificOutput.additionalContext, or nothing.
import json
import os
import sys

project_dir = os.environ.get('DEVIN_PROJECT_DIR', os.getcwd())
state = os.path.join(project_dir, '.devin', 'memory', 'state.md')
if os.path.isfile(state):
    with open(state, encoding='utf-8') as f:
        print(json.dumps({
            'hookSpecificOutput': {
                'hookEventName': 'SessionStart',
                'additionalContext': 'Persisted project memory:\n' + f.read(),
            }
        }))
