#!/usr/bin/env python3
"""agentic-harness payload builder.

Renders harnesses/<name>/payload text files from:
  - shared/                     (templates with {{VAR}} and {{INCLUDE:...}})
  - harnesses/<name>/overlay/   (harness-specific templates, same syntax)
  - harnesses/<name>/generated/ (build.py render() hooks, e.g. agent frontmatter)

Rules:
  - {{VAR}}            -> vars from shared/vars.json + harness overlay/vars.json
  - {{INCLUDE:path}}   -> inline the file (searched overlay first, then
                          shared/, then shared/fragments/<harness>/),
                          rendered recursively; vars apply inside too
  - files under overlay/ and shared/ are copied only when referenced or when
    listed in the harness BUILD map below - generated files are NEVER
    committed; run `python build.py` after editing shared sources.

Usage: python build.py [--check]   # --check fails if payload is stale
"""
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARED = ROOT / 'shared'

INCLUDE_RE = re.compile(r'\{\{INCLUDE:([^}]+)\}\}')
VAR_RE = re.compile(r'\{\{([A-Z_]+)\}\}')


def load_vars(harness):
    v = {}
    for base in (SHARED / 'vars.json', ROOT / 'harnesses' / harness / 'overlay' / 'vars.json'):
        if base.is_file():
            v.update(json.loads(base.read_text(encoding='utf-8-sig')))
    return v


def find_include(rel, harness):
    for base in (ROOT / 'harnesses' / harness / 'overlay',
                 SHARED / 'fragments' / harness,
                 SHARED,
                 ROOT):
        p = (base / rel).resolve()
        if p.is_file():
            return p
    raise SystemExit(f'include not found: {rel} (harness={harness})')


def render(text, harness, v, seen=()):
    def sub_inc(m):
        p = find_include(m.group(1).strip(), harness)
        if p in seen:
            raise SystemExit(f'include cycle: {p}')
        return render(p.read_text(encoding='utf-8'), harness, v, seen + (p,))
    text = INCLUDE_RE.sub(sub_inc, text)
    text = VAR_RE.sub(lambda m: v.get(m.group(1), m.group(0)), text)
    if harness == 'devin':
        text = text.replace('## Available agents', '## Available profiles (global)')
    elif harness == 'opencode':
        text = text.replace('## Available agents', '## Available subagents')
    return re.sub(r'\n{3,}', '\n\n', text)


# ---------------------------------------------------------------------------
# Per-harness build maps: dest -> (source, harness) or callable
# ---------------------------------------------------------------------------

def agent_body(name, harness, v):
    src = SHARED / 'agents' / f'{name}.md'
    return render(src.read_text(encoding='utf-8'), harness, v)


def fm_opencode(name, description, mode, permission=None, temperature=None):
    lines = ['---', f'description: {description}', f'mode: {mode}']
    if temperature is not None:
        lines.append(f'temperature: {temperature}')
    if permission:
        lines.append('permission:')
        for tool, rule in permission.items():
            if isinstance(rule, dict):
                lines.append(f'  {tool}:')
                for pat, act in rule.items():
                    lines.append(f'    "{pat}": {act}' if pat != '*' else f'    "*": {act}')
            else:
                lines.append(f'  {tool}: {rule}')
    lines.append('---')
    return '\n'.join(lines) + '\n\n'


def oc_agent(name, description, permission=None):
    def gen(harness, v):
        return fm_opencode(name, description, 'subagent', permission) + agent_body(name, harness, v)
    return gen


def oc_orchestrator(harness, v):
    head = fm_opencode('orchestrator',
                       'Orchestrator - delegates scoped work to specialized subagents, '
                       'consumes only REPORT blocks, keeps its own context small.',
                       mode='primary', temperature=0.2,
                       permission={'task': 'allow'})
    v2 = dict(v, REPORT_FENCE='', REPORT_FENCE_END='', REPORT_INDENT='')
    intro = (render(SHARED.joinpath('contract.md').read_text(encoding='utf-8'), harness, v2)
             .replace('Act as the orchestrator.', 'You are the orchestrator.', 1)
             .rstrip('\n') + '\n')
    lang = ('\n## Language\n\n'
            'Conversational replies in Spanish; code, reports and file contents in\n'
            'English.\n')
    return head + intro + lang


def devin_agent(name, model, tools=None):
    def gen(harness, v):
        descs = {
            'scout': 'Read-only exploration and research. Use for understanding architecture, tracing dependencies, or answering questions without touching anything.',
            'tester': 'Runs tests, lint, typecheck and builds; reports what passes, what fails and why. Writes only into .devin/reports/.',
            'reviewer': '"Reviews diffs and code (correctness, security, style, performance). Read-only plus git diffs. Returns findings by severity."',
            'worker': 'Autonomous implementation of scoped subtasks (features, fixes, refactors). Full tool access. Use when the orchestrator delegates code changes.',
        }
        lines = ['---', f'name: {name}', f'description: {descs[name]}', f'model: {model}']
        if tools:
            lines.append('allowed-tools:')
            lines += [f'  - {t}' for t in tools]
        lines.append('---')
        return '\n'.join(lines) + '\n\n' + agent_body(name, harness, v)
    return gen


def skill_doc(harness, v, title):
    body = render(SHARED.joinpath('contract.md').read_text(encoding='utf-8'), harness, v)
    return (f'# {title}\n\n' + body).rstrip('\n') + '\n'


READ_TOOLS = ['read', 'grep', 'find_file_by_name', 'web_search', 'webfetch']

BUILD = {
    'devin': {
        'AGENTS.md': ('global-rules.md', 'shared'),
        'skills/orchestrate/SKILL.md': ('orchestrate.md', 'overlay'),
        # model slugs come from vars so they can match whatever proxy is live
        'agents/scout.md': lambda h, v: devin_agent('scout', v['MODEL_SCOUT'], READ_TOOLS)(h, v),
        'agents/tester.md': lambda h, v: devin_agent('tester', v['MODEL_TESTER'], READ_TOOLS[:3] + ['exec', 'write'])(h, v),
        'agents/reviewer.md': lambda h, v: devin_agent('reviewer', v['MODEL_REVIEWER'], READ_TOOLS[:3] + ['exec', 'write'])(h, v),
        'agents/worker.md': lambda h, v: devin_agent('worker', v['MODEL_WORKER'])(h, v),
    },
    'opencode': {
        'AGENTS.md': ('global-rules.md', 'shared'),
        'skills/orchestration/SKILL.md': lambda h, v: (
            '---\nname: orchestration\n'
            'description: Orchestration contract — when and how to delegate to '
            'specialized subagents, structured REPORT input, disk artifacts and '
            'optional memory. Load on multi-step tasks.\n---\n\n'
            + skill_doc(h, v, 'Lightweight orchestration')),
        'agents/orchestrator.md': oc_orchestrator,
        'agents/scout.md': oc_agent('scout',
            'Read-only exploration and research. Use for understanding architecture, tracing dependencies, or answering questions without touching anything.',
            {'edit': 'deny', 'bash': 'deny', 'write': 'deny', 'todowrite': 'deny'}),
        'agents/tester.md': oc_agent('tester',
            'Runs tests, lint, typecheck and builds; reports what passes, what fails and why. Writes only into .opencode/reports/.',
            {'edit': {'*': 'deny', '.opencode/reports/*': 'allow'}}),
        'agents/reviewer.md': oc_agent('reviewer',
            'Reviews diffs and code (correctness, security, style, performance). Read-only plus git diffs. Returns findings by severity.',
            {'edit': {'*': 'deny', '.opencode/reports/*': 'allow'},
             'bash': {'*': 'deny', 'git *': 'allow'}}),
        'agents/worker.md': oc_agent('worker',
            'Autonomous implementation of scoped subtasks (features, fixes, refactors). Full tool access. Use when the orchestrator delegates code changes.'),
    },
}

# static payload files that pass through untouched (hooks, plugins, configs)
STATIC_DIRS = ('hooks', 'plugins')


def build(harness):
    payload = ROOT / 'harnesses' / harness / 'payload'
    overlay = ROOT / 'harnesses' / harness / 'overlay'
    v = load_vars(harness)
    out = {}

    for dest, spec in BUILD[harness].items():
        if callable(spec):
            out[dest] = spec(harness, v)
        else:
            rel, base = spec
            src = (SHARED if base == 'shared' else overlay) / rel
            out[dest] = render(src.read_text(encoding='utf-8'), harness, v)

    # payload statics (hooks, plugins, managed config) pass through
    for p in payload.rglob('*') if payload.is_dir() else []:
        if not p.is_file():
            continue
        rel = p.relative_to(payload).as_posix()
        if rel.startswith(STATIC_DIRS) or rel == 'config.managed.json':
            out[rel] = p.read_bytes()

    for rel, content in list(out.items()):  # normalize: single trailing newline
        if not isinstance(content, bytes):
            out[rel] = content.rstrip('\n') + '\n'
    return out


def main():
    check = '--check' in sys.argv
    stale = []
    for harness in BUILD:
        want = build(harness)
        payload = ROOT / 'harnesses' / harness / 'payload'
        have = {p.relative_to(payload).as_posix(): p.read_bytes()
                for p in payload.rglob('*') if p.is_file()}
        for rel, content in sorted(want.items()):
            data = content if isinstance(content, bytes) else content.encode('utf-8')
            cur = have.pop(rel, None)
            if check:
                if cur != data:
                    stale.append(f'{harness}/{rel}')
            else:
                if cur != data:
                    dst = payload / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(data)
                    print(f'  + {harness}/{rel}')
        for rel in sorted(have):  # files in payload no longer generated
            if rel.startswith(STATIC_DIRS) or rel == 'config.managed.json':
                continue
            if check:
                stale.append(f'{harness}/{rel} (orphan)')
            else:
                (payload / rel).unlink()
                print(f'  - {harness}/{rel} (orphan removed)')
    if check:
        if stale:
            print('stale payload - run `python build.py`:\n  ' + '\n  '.join(stale))
            sys.exit(1)
        print('payload in sync with sources')
    else:
        print('build done')


if __name__ == '__main__':
    main()
