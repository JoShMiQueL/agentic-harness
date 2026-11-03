#!/usr/bin/env python3
"""devin-agentic uninstaller - removes everything install.py laid down.

Usage: python uninstall.py [--devin-home DIR]
Removes stamped files + agentic.json and strips the managed keys
(permissions, hooks) from config.json. Restore a config.json.bak-* to fully
revert custom edits made inside the managed keys.
"""
import argparse, json, os, sys
from pathlib import Path


def default_home():
    if sys.platform == 'win32':
        return Path(os.environ['APPDATA']) / 'devin'
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'devin'


def main():
    ap = argparse.ArgumentParser(description='devin-agentic uninstaller')
    ap.add_argument('--devin-home', default=str(default_home()))
    a = ap.parse_args()
    home = Path(a.devin_home)

    stamp_path = home / 'agentic.json'
    removed = 0
    if stamp_path.is_file():
        files = json.loads(stamp_path.read_text()).get('files', {})
        for rel in files:
            p = home / rel
            if p.is_file():
                p.unlink(); removed += 1
                print(f'  - {rel}')
        stamp_path.unlink()
        print('  - agentic.json')
    else:
        print('  ! no install stamp - removing known paths')
        for rel in ['AGENTS.md', 'skills/orchestrate/SKILL.md']:
            p = home / rel
            if p.is_file():
                p.unlink(); removed += 1
                print(f'  - {rel}')

    cfg_path = home / 'config.json'
    if cfg_path.is_file():
        cfg = json.loads(cfg_path.read_text())
        for k in ('permissions', 'hooks'):
            if cfg.pop(k, None) is not None:
                print(f'  - config.json: removed "{k}"')
        cfg_path.write_text(json.dumps(cfg, indent=2) + '\n')
        baks = sorted(home.glob('config.json.bak-*'))
        if baks:
            print(f'  i to fully revert: copy "{baks[-1].name}" over config.json')

    for d in ('agents', 'skills', 'hooks'):
        p = home / d
        if p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    print(f'\nDone. {removed} file(s) removed from {home}.')


if __name__ == '__main__':
    main()
