#!/usr/bin/env python3
"""agentic-harness local smoke tests — installs/uninstalls into a sandbox
under ./sandbox/ and never touches real harness homes.

Usage: python tests/test_e2e.py           (all tests, exit 1 on failure)
       python tests/test_e2e.py -v        (verbose)
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SANDBOX = Path(tempfile.mkdtemp(prefix='agentic-e2e-'))
PY = sys.executable
FAILURES = []


def run(*args, expect=0):
    r = subprocess.run([PY, str(ROOT / args[0]), *args[1:]],
                       capture_output=True, text=True, cwd=ROOT)
    if expect is not None and r.returncode != expect:
        raise AssertionError(
            f'{args} -> exit {r.returncode}\nstdout: {r.stdout}\nstderr: {r.stderr}')
    return r


def check(name, fn):
    try:
        fn()
        print(f'  PASS {name}')
    except Exception as e:  # noqa: BLE001
        FAILURES.append((name, e))
        print(f'  FAIL {name}: {e}')


def install(harness, home, *extra):
    return run('install.py', '--harness', harness, f'--{harness}-home', str(home), *extra)


def uninstall(harness, home):
    return run('uninstall.py', '--harness', harness, f'--{harness}-home', str(home))


# --- shared assertions -------------------------------------------------------

def fresh_install(harness):
    home = SANDBOX / harness
    r = install(harness, home)
    assert (home / 'agentic.json').is_file(), 'stamp missing'
    assert (home / 'AGENTS.md').is_file(), 'AGENTS.md missing'
    stamp = json.loads((home / 'agentic.json').read_text())
    for rel in stamp['files']:
        assert (home / rel).is_file(), f'stamped file missing: {rel}'
    return home, r


def check_sync(harness, home):
    r = install(harness, home, '--check')
    assert 'update-available' not in r.stdout and 'MISSING' not in r.stdout, \
        f'not in sync:\n{r.stdout}'


# --- tests --------------------------------------------------------------------

def t_build_check():
    run('build.py', '--check')


def t_devin_fresh_install():
    home, r = fresh_install('devin')
    assert (home / 'config.json').is_file()
    cfg = json.loads((home / 'config.json').read_text())
    assert 'permissions' in cfg and 'hooks' in cfg
    hooks = json.dumps(cfg['hooks'])
    assert str(home).replace('\\', '/') in hooks or home.as_posix() in hooks, \
        'DEVIN_HOME placeholder not resolved in hooks'


def t_opencode_fresh_install():
    home, r = fresh_install('opencode')
    cfg = json.loads((home / 'opencode.json').read_text())
    assert cfg['default_agent'] == 'orchestrator'
    assert cfg['experimental']['subagent_depth'] == 1
    assert isinstance(cfg['permissions'], list), 'permissions must be a V2 rules array'
    assert {'action': 'shell', 'resource': 'rm -rf *', 'effect': 'deny'} in cfg['permissions']
    assert 'permission' not in cfg, 'legacy v1 permission key leaked'
    assert 'subagent_depth' not in cfg, 'legacy top-level subagent_depth leaked'
    assert cfg['agents']['scout']['permissions'], 'agent-level permissions missing'
    for agent in ('orchestrator', 'scout', 'tester', 'reviewer', 'worker'):
        assert (home / 'agents' / f'{agent}.md').is_file(), agent


def t_opencode_merge_preserves():
    home = SANDBOX / 'oc-merge'
    home.mkdir(parents=True)
    (home / 'opencode.json').write_text(json.dumps({
        'provider': {'local': {'name': 'Local'}},
        'model': 'local/swe-2',
        'mcp': {'rea': {'type': 'local', 'enabled': True}},
    }))
    install('opencode', home)
    cfg = json.loads((home / 'opencode.json').read_text())
    assert cfg['provider']['local']['name'] == 'Local'
    assert cfg['model'] == 'local/swe-2'
    assert cfg['mcp']['rea']['enabled'] is True
    assert (home / 'opencode.json.bak').is_file(), 'config backup missing'


def t_reinstall_noop():
    home, _ = fresh_install('devin')
    r = install('devin', home)
    assert 'already in sync' in r.stdout, r.stdout


def t_check_reports_update():
    home, _ = fresh_install('devin')
    (home / 'AGENTS.md').write_text('tampered')
    r = install('devin', home, '--check')
    assert 'locally-modified' in r.stdout, r.stdout


def t_uninstall_clean():
    home, _ = fresh_install('devin')
    uninstall('devin', home)
    assert not (home / 'agentic.json').exists()
    assert not (home / 'AGENTS.md').exists()
    cfg = json.loads((home / 'config.json').read_text())
    assert 'permissions' not in cfg and 'hooks' not in cfg

    home, _ = fresh_install('opencode')
    uninstall('opencode', home)
    assert not (home / 'agentic.json').exists()
    cfg = json.loads((home / 'opencode.json').read_text())
    for k in ('default_agent', 'permission', 'permissions', 'subagent_depth',
              'experimental', 'agents'):
        assert k not in cfg, k


def t_dry_run_writes_nothing():
    home = SANDBOX / 'dry'
    r = install('opencode', home, '--dry-run')
    assert 'would-create' in r.stdout
    assert not home.exists() or not any(home.iterdir())


def t_agent_content_contract():
    home, _ = fresh_install('opencode')
    for agent in ('scout', 'tester', 'reviewer', 'worker'):
        body = (home / 'agents' / f'{agent}.md').read_text(encoding='utf-8')
        assert 'REPORT' in body and 'status: ok' in body, agent
        fm = body.split('---')[1]
        assert 'mode: subagent' in fm, agent
        assert 'model: devin-local/' in fm, f'{agent}: no model routed'
        assert 'permission:' not in fm, f'{agent}: legacy permission frontmatter'
    orch = (home / 'agents' / 'orchestrator.md').read_text(encoding='utf-8')
    assert 'mode: primary' in orch.split('---')[1]
    assert 'model: devin-local/' in orch.split('---')[1], 'orchestrator model missing'
    assert 'permission:' not in orch.split('---')[1], 'legacy task permission'
    assert '{{' not in orch, 'unrendered placeholder left in orchestrator'


def t_opencode_agent_models():
    home, _ = fresh_install('opencode')
    want = {
        'orchestrator': 'devin-local/swe-2',
        'scout': 'devin-local/swe-2-flash',
        'tester': 'devin-local/swe-2-flash-medium',
        'reviewer': 'devin-local/swe-2',
        'worker': 'devin-local/swe-2-flash-high',
    }
    for agent, model in want.items():
        fm = (home / 'agents' / f'{agent}.md').read_text().split('---')[1]
        assert f'model: {model}' in fm, f'{agent}: {fm}'


def t_devin_agent_models():
    home, _ = fresh_install('devin')
    want = {
        'scout': 'swe-2-flash-high',
        'tester': 'swe-2-flash-medium',
        'reviewer': 'swe-2',
        'worker': 'swe-2-flash-high',
    }
    for agent, model in want.items():
        fm = (home / 'agents' / f'{agent}.md').read_text().split('---')[1]
        assert f'model: {model}' in fm, f'{agent}: {fm}'


def t_plugin_v2_format():
    for plugin in ('agentic-guard', 'agentic-memory'):
        src = (ROOT / 'harnesses/opencode/payload/plugins'
               / f'{plugin}.js').read_text(encoding='utf-8')
        assert 'export default' in src, f'{plugin}: v2 needs a default export'
        assert 'id:' in src, f'{plugin}: default export needs an id'
        assert 'export const' not in src, f'{plugin}: v1 named export left'


def t_auto_selects_installed():
    # simulate: PATH has no CLIs on CI sandbox — just assert auto doesn't crash
    r = run('install.py', '--harness', 'auto', '--dry-run')
    assert 'devin' in r.stdout or 'opencode' in r.stdout


def main():
    tests = [(n, f) for n, f in list(globals().items())
             if n.startswith('t_') and callable(f)]
    print(f'== e2e sandbox: {SANDBOX}\n')
    for name, fn in tests:
        check(name, fn)
    shutil.rmtree(SANDBOX, ignore_errors=True)
    if FAILURES:
        print(f'\n{len(FAILURES)} failure(s)')
        sys.exit(1)
    print(f'\n{len(tests)} tests passed')


if __name__ == '__main__':
    main()
