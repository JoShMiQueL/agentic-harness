#!/usr/bin/env python3
"""agentic-harness uninstaller - removes what install.py laid down.

Usage: python uninstall.py [--harness devin|opencode|auto]
                           [--devin-home DIR] [--opencode-home DIR]
Removes stamped files + agentic.json and strips the managed keys from the
harness config file. Restore a config backup (*.bak / *.bak-*) to fully
revert edits made inside the managed keys.
"""
import argparse, json, os, sys
from pathlib import Path

HARNESSES = {
    'devin': {
        'config_file': 'config.json',
        'managed_keys': ['permissions', 'hooks'],
    },
    'opencode': {
        'config_file': 'opencode.json',
        'managed_keys': ['default_agent', 'experimental', 'permissions', 'agents'],
    },
}


def default_home(harness):
    if harness == 'devin':
        if sys.platform == 'win32':
            return Path(os.environ['APPDATA']) / 'devin'
        return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'devin'
    env = os.environ.get('OPENCODE_CONFIG_DIR')
    if env:
        return Path(env)
    return Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'opencode'


def uninstall_one(harness, home):
    print(f'==> [{harness}] {home}')
    spec = HARNESSES[harness]
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
        print('  ! no install stamp - nothing stamped to remove')

    cfg_path = home / spec['config_file']
    if cfg_path.is_file():
        cfg = json.loads(cfg_path.read_text(encoding='utf-8-sig'))
        for k in spec['managed_keys']:
            if cfg.pop(k, None) is not None:
                print(f'  - {spec["config_file"]}: removed "{k}"')
        cfg_path.write_text(json.dumps(cfg, indent=2) + '\n')
        baks = sorted(home.glob(spec['config_file'] + '.bak*'))
        if baks:
            print(f'  i to fully revert: copy "{baks[-1].name}" over {spec["config_file"]}')

    for d in ('agents', 'skills', 'hooks', 'plugins', 'commands'):
        p = home / d
        if p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    print(f'  {removed} file(s) removed.\n')


def main():
    ap = argparse.ArgumentParser(description='agentic-harness uninstaller')
    ap.add_argument('--harness', default='auto',
                    choices=['auto'] + list(HARNESSES))
    ap.add_argument('--devin-home', default=None)
    ap.add_argument('--opencode-home', default=None)
    a = ap.parse_args()

    targets = list(HARNESSES) if a.harness == 'auto' else [a.harness]
    for h in targets:
        home = Path(getattr(a, f'{h}_home', None) or default_home(h))
        if not (home / 'agentic.json').is_file() and a.harness == 'auto':
            continue  # auto: only touch harnesses that were actually installed
        uninstall_one(h, home)

    print('Done.')


if __name__ == '__main__':
    main()
