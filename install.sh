#!/usr/bin/env bash
# devin-agentic installer for Linux/macOS.
#   local:   ./install.sh [-d DIR] [--check] [--dry-run] [-b BRANCH]
#   remote:  curl -fsSL https://cdn.jsdelivr.net/gh/JoShMiQueL/devin-agentic@main/install.sh | bash
#
# Same semantics as install.ps1: devin-home/ maps 1:1 onto $DEVIN_HOME
# (default ${XDG_CONFIG_HOME:-~/.config}/devin), dynamic manifest,
# SHA256 install stamp, orphan cleanup, config.json merge via python3.
# Hook scripts are .ps1 — they need `pwsh` installed to actually run;
# without it hook invocations error non-blockingly.
set -euo pipefail

REPO_SLUG="JoShMiQueL/devin-agentic"
SRC_HOME="devin-home"
BRANCH="main"
CHECK=0; DRY=0
DEVIN_HOME="${XDG_CONFIG_HOME:-$HOME/.config}/devin"

while [ $# -gt 0 ]; do
  case "$1" in
    -d|--devin-home) DEVIN_HOME="$2"; shift 2 ;;
    --check)         CHECK=1; shift ;;
    --dry-run)       DRY=1; shift ;;
    -b|--branch)     BRANCH="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

step() { printf '\n==> %s\n' "$1"; }
sha256() { (sha256sum "$1" 2>/dev/null || shasum -a 256 "$1") | cut -d' ' -f1; }
py() { python3 -c "$1" "${@:2}"; }

STAMP="$DEVIN_HOME/agentic.json"

# --- Resolve source: local clone or remote download --------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "")"
REPO_ROOT="$SCRIPT_DIR"
LOCAL=0
[ -n "$SCRIPT_DIR" ] && [ -d "$SCRIPT_DIR/$SRC_HOME/agents" ] && LOCAL=1

if [ "$LOCAL" -eq 0 ]; then
  step 'Resolving remote file list'
  REPO_ROOT="${TMPDIR:-/tmp}/devin-agentic-src"
  SHA="$(curl -fsSL -H 'User-Agent: devin-agentic' "https://api.github.com/repos/$REPO_SLUG/commits/$BRANCH" | py 'import json,sys; print(json.load(sys.stdin)["sha"])')"
  BASE="https://raw.githubusercontent.com/$REPO_SLUG/$SHA"
  curl -fsSL -H 'User-Agent: devin-agentic' "https://api.github.com/repos/$REPO_SLUG/git/trees/$SHA?recursive=1" \
    | py 'import json,sys,os
for it in json.load(sys.stdin)["tree"]:
    p=it["path"]
    if it["type"]=="blob" and (p.startswith("devin-home/") or p=="VERSION"): print(p)' \
    | while read -r f; do
        mkdir -p "$REPO_ROOT/$(dirname "$f")"
        curl -fsSL "$BASE/$f" -o "$REPO_ROOT/$f"
      done
fi

VERSION="$(tr -d '[:space:]' < "$REPO_ROOT/VERSION" 2>/dev/null || echo '?')"

# --- Build manifest -----------------------------------------------------------
MANIFEST="$(mktemp)"
find "$REPO_ROOT/$SRC_HOME" -type f ! -name 'config.managed.json' | while read -r f; do
  rel="${f#$REPO_ROOT/$SRC_HOME/}"
  printf '%s\n' "$rel"
done > "$MANIFEST"
MANAGED="$REPO_ROOT/$SRC_HOME/config.managed.json"

# --- Stamp ---------------------------------------------------------------------
STAMP_FILES="$(py 'import json,os
try: d=json.load(open(os.environ["STAMP"])); [print(k) for k in d.get("files",{})]
except Exception: pass' 2>/dev/null || true)"
STAMP_VERSION="$(py 'import json,os
try: print(json.load(open(os.environ["STAMP"]))["version"])
except Exception: pass' 2>/dev/null || true)"
export STAMP

in_manifest() { grep -Fxq "$1" "$MANIFEST"; }

# ============================ CHECK / DRY-RUN ==================================
if [ "$CHECK" -eq 1 ] || [ "$DRY" -eq 1 ]; then
  step "$([ $CHECK -eq 1 ] && echo 'Sync status' || echo 'DRY RUN - plan')"
  echo "  repo version : $VERSION"
  echo "  installed    : ${STAMP_VERSION:-(unknown - no stamp)}"
  echo "  target       : $DEVIN_HOME"
  echo
  dirty=0
  while read -r rel; do
    dst="$DEVIN_HOME/$rel"
    if [ ! -f "$dst" ]; then s='MISSING (new in repo)'; dirty=1
    elif [ "$(sha256 "$dst")" = "$(sha256 "$REPO_ROOT/$SRC_HOME/$rel")" ]; then s='sync'
    else s=$([ "$DRY" -eq 1 ] && echo 'overwrite' || echo 'update/locally-modified'); dirty=1; fi
    printf '%-42s %s\n' "$rel" "$s"
  done < "$MANIFEST"
  for d in $STAMP_FILES; do
    in_manifest "$d" || { printf '%-42s %s\n' "$d" 'removed-in-repo'; dirty=1; }
  done
  echo
  [ "$dirty" -eq 1 ] && echo 'Run install to converge.' || echo 'Everything in sync.'
  rm -f "$MANIFEST"; exit 0
fi

# ============================ INSTALL ==========================================
step "Installing -> $DEVIN_HOME (v$VERSION)"
mkdir -p "$DEVIN_HOME"
while read -r rel; do
  dst="$DEVIN_HOME/$rel"
  mkdir -p "$(dirname "$dst")"
  cp "$REPO_ROOT/$SRC_HOME/$rel" "$dst"
  echo "  + $rel"
done < "$MANIFEST"

# orphan cleanup
for d in $STAMP_FILES; do
  if ! in_manifest "$d" && [ -f "$DEVIN_HOME/$d" ]; then
    if [ "$(sha256 "$DEVIN_HOME/$d")" = "$(STAMP_FILE_KEY="$d" py 'import json,os
print(json.load(open(os.environ["STAMP"]))["files"].get(os.environ["STAMP_FILE_KEY"],""))')" ]; then
      rm -f "$DEVIN_HOME/$d"; echo "  - $d (removed in repo)"
    else
      mv "$DEVIN_HOME/$d" "$DEVIN_HOME/$d.bak-$(date +%Y%m%d-%H%M%S)"
      echo "  ! $d removed in repo but locally modified -> .bak kept"
    fi
  fi
done

step 'Merging config.json'
CFG="$DEVIN_HOME/config.json"
if python3 -c '1' >/dev/null 2>&1; then
  [ -f "$CFG" ] && cp "$CFG" "$CFG.bak-$(date +%Y%m%d-%H%M%S)"
  CFG="$CFG" MANAGED="$MANAGED" py 'import json,os
cfg_path=os.environ["CFG"]; managed=json.load(open(os.environ["MANAGED"]))
try: cfg=json.load(open(cfg_path))
except Exception: cfg={"version":1}
cfg["permissions"]=managed["permissions"]; cfg["hooks"]=managed["hooks"]
json.dump(cfg,open(cfg_path,"w"),indent=2)'
  echo '  + permissions, hooks merged (other keys untouched)'
elif [ ! -f "$CFG" ]; then
  cp "$MANAGED" "$CFG"
  echo '  + fresh config.json from managed template (no python3 to merge)'
else
  echo '  ! python3 not found - config.json merge skipped (merge permissions+hooks manually)'
fi

step 'Writing install stamp'
{
  printf '{\n  "version": "%s",\n  "installed_at": "%s",\n  "files": {\n' "$VERSION" "$(date '+%Y-%m-%d %H:%M:%S')"
  first=1
  while read -r rel; do
    [ -n "$rel" ] || continue
    [ $first -eq 0 ] && printf ',\n'; first=0
    printf '    "%s": "%s"' "$rel" "$(sha256 "$DEVIN_HOME/$rel")"
  done < "$MANIFEST"
  printf '\n  }\n}\n'
} > "$STAMP"
rm -f "$MANIFEST"
echo "  + $STAMP (v$VERSION)"

echo
printf 'Done. System installed at %s (v%s)\n' "$DEVIN_HOME" "$VERSION"
