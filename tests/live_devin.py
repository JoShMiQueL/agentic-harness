#!/usr/bin/env python3
"""Live end-to-end test of the devin harness — runs the real `devin` CLI
against a sandbox data dir (never touches the real %APPDATA%\\devin usage).

Needs the real credentials file (devin auth login) — the CLI itself
authenticates; we only redirect DEVIN_DATA_DIR so agents/hooks/rules come
from the sandbox install.

Local:   python tests/live_devin.py
CI:      credentials.toml is materialized from secrets.DEVIN_CREDENTIALS_TOML
         and dropped into the sandbox before running.
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

DEVIN_CREDS_ENV = 'DEVIN_CREDENTIALS_TOML'
PROBE = 'Reply with exactly this line and nothing else: REPORT / status: ok / summary: probe / artifact: none / files: none / next: none'


def _dec(b):
    return (b or b'').decode('utf-8', 'replace') if isinstance(b, bytes) else str(b or '')


def sandbox_home():
    sb = Path(tempfile.mkdtemp(prefix='agentic-live-devin-'))
    subprocess.run([PY, str(ROOT / 'install.py'), '--harness', 'devin',
                    '--devin-home', str(sb)], check=True, capture_output=True)
    creds = os.environ.get(DEVIN_CREDS_ENV)
    if creds:  # CI: materialize from secret (secrets lose trailing newlines)
        (sb / 'credentials.toml').write_text(creds.rstrip('\n') + '\n')
    else:      # local: reuse real creds (they're per-account, not per-dir)
        real = Path(os.environ.get('APPDATA', '')) / 'devin' / 'credentials.toml'
        if not real.is_file():
            real = Path.home() / '.config' / 'devin' / 'credentials.toml'
        if real.is_file():
            shutil.copy2(real, sb / 'credentials.toml')
    return sb


def main():
    sb = sandbox_home()
    exe = shutil.which('devin') or shutil.which('devin.exe') or 'devin'
    env = dict(os.environ, DEVIN_DATA_DIR=str(sb))
    rc = '?'
    try:
        print(f'[dbg] exe={exe} sb={sb} creds={ (sb / "credentials.toml").is_file() }')
        try:
            # bytes capture: devin emits unicode that breaks cp1252 on CI
            r = subprocess.run(
                [exe, '-p', PROBE, '--permission-mode', 'auto',
                 '--respect-workspace-trust', 'false'],
                capture_output=True, env=env, cwd=ROOT,
                timeout=180, stdin=subprocess.DEVNULL)
            out = _dec(r.stdout) + _dec(r.stderr)
            rc = r.returncode
        except subprocess.TimeoutExpired as e:
            out = _dec(e.stdout) + _dec(e.stderr) + '\n[TIMEOUT]'
            rc = 'timeout'
        ok = 'status: ok' in out and 'REPORT' in out
        tail = out if os.environ.get('VERBOSE') else out[-800:]
        print(tail.encode('ascii', 'backslashreplace').decode('ascii'))
        print(f'\n{"PASS" if ok else "FAIL"} live devin probe '
              f'(exit={rc}, sandbox={sb})')
        sys.exit(0 if ok else 1)
    finally:
        if not os.environ.get('KEEP_SANDBOX'):
            shutil.rmtree(sb, ignore_errors=True)


if __name__ == '__main__':
    main()
