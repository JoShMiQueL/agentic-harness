#!/usr/bin/env python3
"""Live end-to-end test of the opencode harness — `opencode run` against a
sandbox OPENCODE_CONFIG_DIR with the jailbreak proxy in front.

Needs (CI): secrets.SWE2_PROXY_REPO (owner/repo of the proxy code) and
secrets.DEVIN_CREDENTIALS_TOML (the proxy reads the CLI creds itself).
Local: reuses %APPDATA%\\devin\\credentials.toml and expects the proxy
already running on 127.0.0.1:8889 (or starts it if SWE2_PROXY_DIR is set).
"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
PROXY_URL = 'http://127.0.0.1:8889'

PROBE = 'Reply with exactly this line and nothing else: REPORT / status: ok / summary: probe / artifact: none / files: none / next: none'


def proxy_alive():
    try:
        urllib.request.urlopen(PROXY_URL + '/health', timeout=3)
        return True
    except Exception:
        return False


def start_proxy(workdir):
    """Launch the jailbreak proxy from a local checkout (SWE2_PROXY_DIR) or
    a fresh clone of SWE2_PROXY_REPO; returns (proc, dir) or raises."""
    repo = os.environ.get('SWE2_PROXY_REPO', 'funnybones69/swe2-jailbreak-proxy')
    pdir = os.environ.get('SWE2_PROXY_DIR')
    if not pdir:
        pdir = str(Path(workdir) / 'proxy')
        subprocess.run(['git', 'clone', '--depth', '1',
                        f'https://github.com/{repo}', pdir],
                       check=True, capture_output=True)
    script = Path(pdir) / 'swe2_jb_proxy.py'
    if not script.is_file():
        cand = list(Path(pdir).rglob('swe2_jb_proxy.py'))
        if cand:
            script = cand[0]
    subprocess.run([PY, '-m', 'pip', 'install', '-q', '-r',
                    str(Path(pdir) / 'requirements.txt')],
                   check=True, capture_output=True)
    env = dict(os.environ)
    creds = os.environ.get('DEVIN_CREDENTIALS_TOML')
    if creds:
        cf = Path(workdir) / 'credentials.toml'
        cf.write_text(creds)
        env['JB_SWE_CRED'] = str(cf)
    proc = subprocess.Popen([PY, str(script)], cwd=pdir, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True)
    for _ in range(60):
        if proxy_alive():
            return proc
        if proc.poll() is not None:
            raise RuntimeError(f'proxy exited early (code {proc.returncode})')
        time.sleep(1)
    proc.kill()
    raise RuntimeError('proxy did not come up')


def sandbox_home():
    sb = Path(tempfile.mkdtemp(prefix='agentic-live-oc-'))
    subprocess.run([PY, str(ROOT / 'install.py'), '--harness', 'opencode',
                    '--opencode-home', str(sb)], check=True, capture_output=True)
    # sandbox config needs the local provider wiring the real one has
    cfg_path = sb / 'opencode.json'
    cfg = json.loads(cfg_path.read_text())
    cfg['provider'] = {
        'local': {
            'npm': '@ai-sdk/openai-compatible',
            'name': 'Local',
            'options': {'baseURL': PROXY_URL + '/v1', 'apiKey': 'anything'},
            'models': {'swe-2': {'name': 'SWE-2'}},
        }
    }
    cfg['model'] = 'local/swe-2'
    cfg['small_model'] = 'local/swe-2'
    cfg_path.write_text(json.dumps(cfg, indent=2) + '\n')
    return sb


def main():
    workdir = tempfile.mkdtemp(prefix='agentic-live-wd-')
    sb = sandbox_home()
    proc = None
    try:
        if not proxy_alive():
            proc = start_proxy(workdir)
        env = dict(os.environ,
                   OPENCODE_CONFIG_DIR=str(sb))
        # isolate from project configs: run in a bare dir, no repo root
        env.pop('OPENCODE_CONFIG', None)
        env.pop('OPENCODE_CONFIG_CONTENT', None)
        exe = shutil.which('opencode') or shutil.which('opencode.cmd') or 'opencode'
        r = subprocess.run(
            [exe, 'run', '--standalone', '--auto', '--print-logs',
             '--agent', 'orchestrator', PROBE],
            capture_output=True, env=env, stdin=subprocess.DEVNULL,
            cwd=tempfile.mkdtemp(), timeout=900)  # bare cwd: no project config
        out = (r.stdout or b'').decode('utf-8', 'replace') + \
              (r.stderr or b'').decode('utf-8', 'replace')
        ok = 'status: ok' in out or 'REPORT' in out
        tail = out if os.environ.get('VERBOSE') else out[-800:]
        print(tail.encode('ascii', 'backslashreplace').decode('ascii'))
        print(f'\n{"PASS" if ok else "FAIL"} live opencode probe '
              f'(exit={r.returncode}, sandbox={sb})')
        sys.exit(0 if ok else 1)
    finally:
        if proc:
            proc.kill()
        if not os.environ.get('KEEP_SANDBOX'):
            shutil.rmtree(sb, ignore_errors=True)
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == '__main__':
    main()
