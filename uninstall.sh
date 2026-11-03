#!/usr/bin/env bash
D=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")
python3 "$D/uninstall.py" "$@" || { echo "python3 required" >&2; exit 1; }
