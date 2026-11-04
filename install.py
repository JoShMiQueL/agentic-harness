#!/usr/bin/env python3
"""agentic-harness installer - one orchestration layer, several harnesses.

Usage:
    python install.py [--harness devin|opencode|auto] [--check] [--dry-run]
                      [--devin-home DIR] [--opencode-home DIR] [--branch NAME]
                      [--set-bypass]

harnesses/<name>/payload/ maps 1:1 onto the harness data dir:
    devin:     %APPDATA%\\devin            |  ${XDG_CONFIG_HOME:-~/.config}/devin
    opencode:  ~/.config/opencode          |  $OPENCODE_CONFIG_DIR (dir form)

--harness auto (default) installs for every harness whose CLI is on PATH.
Install stamp: <home>/agentic.json (version + sha256 per file).
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, urllib.request
from pathlib import Path

REPO = 'JoShMiQueL/agentic-harness'
LEGACY_REPO = 'JoShMiQueL/devin-agentic'   # fallback while the old name redirects
SRC_ROOT = 'harnesses'

HARNESSES = {
    'devin': {
        'exe': ['devin', 'devin.exe'],
        'config_file': 'config.json',
        'managed_keys': ['permissions', 'hooks'],
        'doctor': 'doctor',
    },
    'opencode': {
        'exe': ['opencode', 'opencode.exe', 'opencode.cmd'],
        'config_file': 'opencode.json',
        'managed_keys': ['default_agent', 'subagent_depth', 'permission'],
        'doctor': None,  # `opencode debug config` is heavier; skipped
    },
}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def default_home(harness):
    if harness == 'devin':
        if sys.platform == 'win32':
            return Path(os.environ['APPDATA']) / 'devin'
        return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'devin'
    if harness == 'opencode':
        env = os.environ.get('OPENCODE_CONFIG_DIR')
        if env:
            return Path(env)
        return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'opencode'
    raise ValueError(harness)


def which_harnesses():
    found = []
    for name, spec in HARNESSES.items():
        if any(shutil.which(e) for e in spec['exe']):
            found.append(name)
    return found


def gh(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'agentic-harness'})
    return urllib.request.urlopen(req).read()


def resolve_sources(branch):
    """Return (root, [payload-relative files]) for local clone or remote repo."""
    root = Path(__file__).resolve().parent
    if (root / SRC_ROOT).is_dir():
        files = sorted(p.relative_to(root).as_posix()
                       for p in (root / SRC_ROOT).rglob('*') if p.is_file())
        return root, files + ['VERSION']

    tmp = Path(tempfile.mkdtemp(prefix='agentic-harness-'))
    last_err = None
    for repo in (REPO, LEGACY_REPO):
        try:
            sha = json.loads(gh(f'https://api.github.com/repos/{repo}/commits/{branch}'))['sha']
            tree = json.loads(gh(f'https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1'))['tree']
            paths = [i['path'] for i in tree if i['type'] == 'blob']
            files = sorted(p for p in paths if p.startswith(SRC_ROOT + '/') or p == 'VERSION')
            if not files:
                # legacy flat layout: devin-home/ at repo root
                files = sorted(p for p in paths if p.startswith('devin-home/') or p == 'VERSION')
            for f in files:
                dst = tmp / f
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(gh(f'https://raw.githubusercontent.com/{repo}/{sha}/{f}'))
            return tmp, files
        except Exception as e:  # noqa: BLE001 - report and try next remote
            last_err = e
    raise SystemExit(f'download failed: {last_err}')


def payload_files(root, files, harness):
    """Map dest-relative path -> source abs path for one harness."""
    src = f'{SRC_ROOT}/{harness}/payload'
    manifest = {}
    for f in files:
        if f.startswith(src + '/'):
            rel = f[len(src) + 1:]
        elif harness == 'devin' and f.startswith('devin-home/'):  # legacy layout
            rel = f[len('devin-home') + 1:]
        else:
            continue
        if rel != 'config.managed.json':
            manifest[rel] = root / f
    return manifest


def managed_config(root, files, harness, home):
    for f in files:
        if f.endswith(f'{harness}/payload/config.managed.json') or \
                (harness == 'devin' and f == 'devin-home/config.managed.json'):
            raw = (root / f).read_text(encoding='utf-8-sig')
            py = 'python' if sys.platform == 'win32' else 'python3'
            return json.loads(raw.replace('{{DEVIN_HOME}}', home.as_posix())
                               .replace('{{OPENCODE_HOME}}', home.as_posix())
                               .replace('{{PY}}', py))
    return {}


def install_one(harness, home, root, files, version, args):
    manifest = payload_files(root, files, harness)
    if not manifest:
        print(f'==> [{harness}] no payload in this source - skipped')
        return

    stamp_path = home / 'agentic.json'
    stamp = json.loads(stamp_path.read_text()) if stamp_path.is_file() else {}
    stamp_files = stamp.get('files', {})
    dests = set(manifest)
    orphans = [d for d in stamp_files if d not in dests and (home / d).is_file()]

    if args.check or args.dry_run:
        print(f'==> [{harness}] target: {home}')
        dirty = bool(orphans)
        for rel, src in sorted(manifest.items()):
            dst = home / rel
            if not dst.exists():
                s, dirty = 'MISSING (new in repo)', True
            elif sha256(dst) == sha256(src):
                s = 'sync'
            else:
                old = stamp_files.get(rel)
                s = 'locally-modified' if old and sha256(dst) != old else 'update-available'
                dirty = True
            if args.dry_run:
                s = 'would-create' if not dst.exists() else 'would-overwrite'
            print(f'  {rel:<44} {s}')
        for d in orphans:
            print(f'  {d:<44} removed-in-repo')
        print('  ' + ('run install to converge.\n' if dirty else 'in sync.\n'))
        return

    if stamp.get('version') == version and not orphans and all(
            (home / rel).is_file() and sha256(home / rel) == sha256(src)
            for rel, src in manifest.items()):
        print(f'==> [{harness}] already in sync (v{version})')
        return

    print(f'==> [{harness}] installing -> {home} (v{version})')
    home.mkdir(parents=True, exist_ok=True)
    for rel, src in sorted(manifest.items()):
        dst = home / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f'  + {rel}')
    for d in orphans:
        dst = home / d
        if sha256(dst) == stamp_files[d]:
            dst.unlink(); print(f'  - {d} (removed in repo)')
        else:
            shutil.move(dst, str(dst) + '.bak')
            print(f'  ! {d} removed in repo but locally modified -> .bak kept')

    spec = HARNESSES[harness]
    managed = managed_config(root, files, harness, home)
    if managed:
        cfg_path = home / spec['config_file']
        if cfg_path.is_file():
            shutil.copy2(cfg_path, str(cfg_path) + '.bak')
            cfg = json.loads(cfg_path.read_text(encoding='utf-8-sig'))
        else:
            cfg = {'$schema': 'https://opencode.ai/config.json'} if harness == 'opencode' else {'version': 1}
        for k in spec['managed_keys']:
            if k in managed:
                cfg[k] = managed[k]
        cfg_path.write_text(json.dumps(cfg, indent=2) + '\n')
        print(f'  + {spec["config_file"]}: {", ".join(k for k in spec["managed_keys"] if k in managed)} merged')

    files_hash = {rel: sha256(home / rel) for rel in manifest}
    stamp_path.write_text(json.dumps({
        'version': version, 'harness': harness,
        'installed_at': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'files': files_hash}, indent=2) + '\n')
    print(f'  + {stamp_path.name} (v{version})')


def main():
    ap = argparse.ArgumentParser(description='agentic-harness installer')
    ap.add_argument('--harness', default='auto',
                    choices=['auto'] + list(HARNESSES))
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--devin-home', default=None)
    ap.add_argument('--opencode-home', default=None)
    ap.add_argument('--branch', default='main')
    ap.add_argument('--set-bypass', action='store_true',
                    help='set DEVIN_PERMISSION_MODE=dangerous (devin only)')
    a = ap.parse_args()

    targets = list(HARNESSES) if a.harness == 'auto' else [a.harness]
    if a.harness == 'auto':
        detected = which_harnesses()
        targets = detected or targets  # no CLI found -> plan for all anyway

    root, files = resolve_sources(a.branch)
    version = (root / 'VERSION').read_text().strip()
    if a.check or a.dry_run:
        print(f'repo version : {version}')
        stamps = []
        for h in targets:
            home = Path(getattr(a, f'{h}_home', None) or default_home(h))
            sp = home / 'agentic.json'
            stamps.append(f"{h}: {json.loads(sp.read_text()).get('version', '(none)') if sp.is_file() else '(none)'}")
        print('installed    : ' + ' | '.join(stamps) + '\n')

    for h in targets:
        home = Path(getattr(a, f'{h}_home', None) or default_home(h))
        install_one(h, home, root, files, version, a)

    if a.set_bypass and 'devin' in targets:
        if sys.platform == 'win32':
            subprocess.run(['setx', 'DEVIN_PERMISSION_MODE', 'dangerous'],
                           capture_output=True)
            print('  + DEVIN_PERMISSION_MODE=dangerous (user env)')
        else:
            print('  i bypass mode: export DEVIN_PERMISSION_MODE=dangerous in your shell rc')

    if not (a.check or a.dry_run):
        print(f'\nDone. Installed for: {", ".join(targets)} (v{version})')
        if 'opencode' in targets:
            print('  i opencode: approval-free run = `opencode --auto` (agentic-guard plugin still enforces policy)')


if __name__ == '__main__':
    main()
