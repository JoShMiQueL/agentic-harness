"""One-off: fix mojibake + BOM in shared/ and overlay sources."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIX = {
    'â€”': '—', 'â€“': '–', 'â†’': '→', 'â‰¤': '≤', 'â€²': '′',
    'Ã¢â‚¬â€': '—', 'ï»¿': '', 'Â·': '·', 'â€¦': '…',
}

changed = []
for base in (ROOT / 'shared', ROOT / 'harnesses'):
    if not base.is_dir():
        continue
    for p in base.rglob('*'):
        if not p.is_file() or 'payload' in p.parts:
            continue
        if p.suffix not in ('.md', '.json', '.py', '.js'):
            continue
        raw = p.read_bytes()
        text = raw.decode('utf-8', 'replace')
        for bad, good in FIX.items():
            text = text.replace(bad, good)
        text = text.lstrip('﻿')
        if text.encode('utf-8') != raw:
            p.write_text(text, encoding='utf-8')
            changed.append(str(p.relative_to(ROOT)))

print('\n'.join(changed) if changed else 'nothing to fix')
