#!/usr/bin/env python3
"""devin-agentic installer - cross-platform (Windows/Linux/macOS).

Usage:
    python install.py [--check] [--dry-run] [--devin-home DIR] [--branch NAME]

devin-home/ in the repo maps 1:1 onto the Devin data dir:
    Windows: %APPDATA%\\devin
    Unix:    ${XDG_CONFIG_HOME:-~/.config}/devin

Install stamp: <devin-home>/agentic.json (version + sha256 per file).
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, urllib.request
from pathlib import Path

REPO = 'JoShMiQueL/devin-agentic'
SRC = 'devin-home'


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def default_home():
    if sys.platform == 'win32':
        return Path(os.environ['APPDATA']) / 'devin'
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'devin'


def gh(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'devin-agentic'})
    return urllib.request.urlopen(req).read()


def main():
    ap = argparse.ArgumentParser(description='devin-agentic installer')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--devin-home', default=str(default_home()))
    ap.add_argument('--branch', default='main')
    a = ap.parse_args()
    home = Path(a.devin_home)

    # --- resolve sources: local clone or remote download (commit-pinned) ------
    root = Path(__file__).resolve().parent
    local = (root / SRC / 'agents').is_dir()
    if local:
        files = sorted(p.relative_to(root).as_posix() for p in (root / SRC).rglob('*') if p.is_file())
        files += ['VERSION']
    else:
        tmp = Path(tempfile.mkdtemp(prefix='devin-agentic-'))
        sha = json.loads(gh(f'https://api.github.com/repos/{REPO}/commits/{a.branch}'))['sha']
        tree = json.loads(gh(f'https://api.github.com/repos/{REPO}/git/trees/{sha}?recursive=1'))['tree']
        files = sorted(i['path'] for i in tree
                       if i['type'] == 'blob' and (i['path'].startswith(SRC + '/') or i['path'] == 'VERSION'))
        for f in files:
            dst = tmp / f
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(gh(f'https://raw.githubusercontent.com/{REPO}/{sha}/{f}'))
        root = tmp

    version = (root / 'VERSION').read_text().strip()
    manifest = {}   # dest rel -> source abs
    for f in files:
        if not f.startswith(SRC + '/'):
            continue
        rel = f[len(SRC) + 1:]
        if rel != 'config.managed.json':
            manifest[rel] = root / f

    stamp_path = home / 'agentic.json'
    stamp = json.loads(stamp_path.read_text()) if stamp_path.is_file() else {}
    stamp_files = stamp.get('files', {})
    dests = set(manifest)
    orphans = [d for d in stamp_files if d not in dests and (home / d).is_file()]

    # --- check / dry-run -------------------------------------------------------
    if a.check or a.dry_run:
        print(f"repo version : {version}\ninstalled    : {stamp.get('version','(none)')}\ntarget       : {home}\n")
        dirty = bool(orphans)
        for rel, src in sorted(manifest.items()):
            dst = home / rel
            if not dst.exists():   s, dirty = 'MISSING (new in repo)', True
            elif sha256(dst) == sha256(src): s = 'sync'
            else:
                old = stamp_files.get(rel)
                s = 'locally-modified' if old and sha256(dst) != old else 'update-available'
                dirty = True
            if a.dry_run: s = 'would-create' if not dst.exists() else 'would-overwrite'
            print(f'{rel:<42} {s}')
        for d in orphans: print(f'{d:<42} removed-in-repo')
        print('\n' + ('Run install to converge.' if dirty else 'Everything in sync.'))
        return

    # --- short-circuit: already in sync -----------------------------------------
    if stamp.get('version') == version and not orphans and all(
            (home / rel).is_file() and sha256(home / rel) == sha256(src)
            for rel, src in manifest.items()):
        print(f'Already in sync (v{version}) - nothing to do.')
        return

    # --- install ----------------------------------------------------------------
    print(f'==> Installing -> {home} (v{version})')
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

    cfg_path = home / 'config.json'
    # placeholders resolved at install time -> absolute paths per machine
    py = 'python' if sys.platform == 'win32' else 'python3'
    managed_raw = (root / SRC / 'config.managed.json').read_text()
    managed = json.loads(managed_raw.replace('{{DEVIN_HOME}}', home.as_posix()).replace('{{PY}}', py))
    if cfg_path.is_file():
        shutil.copy2(cfg_path, str(cfg_path) + '.bak')
        cfg = json.loads(cfg_path.read_text())
    else:
        cfg = {'version': 1}
    cfg['permissions'], cfg['hooks'] = managed['permissions'], managed['hooks']
    cfg_path.write_text(json.dumps(cfg, indent=2) + '\n')
    print('  + config.json: permissions + hooks merged')

    files_hash = {rel: sha256(home / rel) for rel in manifest}
    stamp_path.write_text(json.dumps({
        'version': version, 'installed_at': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'files': files_hash}, indent=2) + '\n')
    print(f'  + {stamp_path} (v{version})')

    exe = shutil.which('devin') or shutil.which('devin.exe')
    if exe:
        subprocess.run([exe, 'doctor'], check=False)
    print(f'\nDone. System installed at {home} (v{version})')


if __name__ == '__main__':
    main()
