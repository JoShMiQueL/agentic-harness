#!/usr/bin/env bash
# Bootstrap: requires python3 (apt/dnf/brew install python3)
D=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")
if [ -f "$D/install.py" ]; then PY="$D/install.py"; else
  PY="${TMPDIR:-/tmp}/da-install.py"
  curl -fsSL -H "Accept: application/vnd.github.raw" -H "User-Agent: devin-agentic" \
    "https://api.github.com/repos/JoShMiQueL/devin-agentic/contents/install.py" -o "$PY" || { echo "download failed" >&2; exit 1; }
fi
python3 "$PY" "$@" || { echo "python3 required - https://www.python.org/downloads/" >&2; exit 1; }
