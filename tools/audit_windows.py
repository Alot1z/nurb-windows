from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {'.git', 'node_modules', 'target', '__pycache__', '.venv', 'dist', 'binaries', 'resources'}
TEXT_EXTENSIONS = {'.py', '.ts', '.tsx', '.rs', '.json', '.sh', '.toml', '.md', '.ps1'}

PATTERNS = {
    'hard-coded Unix executable': re.compile(r'(?<![\w"\'])/(?:usr/)?bin/(?:sh|bash|zsh|curl|tar|open)(?![\w-])'),
    'Unix-only launcher': re.compile(r'#!/bin/(?:sh|bash|zsh)|\.command$|\.dmg$|\.app/'),
    'Unix path assumption': re.compile(r'(?<![\w])~/\.(?:config|cache|local)|(?<![\w])/tmp/'),
    'shell=True': re.compile(r'\bshell\s*=\s*True\b'),
    'os.system': re.compile(r'\bos\.system\s*\('),
    'Unix signal API': re.compile(r'killpg|std::os::unix::process|PermissionsExt'),
}

PLATFORM_MARKERS = re.compile(r'cfg\s*\([^)]*windows|cfg!\s*\([^)]*windows|sys\.platform|os\.name|platform\.system|target_os|not\s*\([^)]*windows', re.I)


def iter_source():
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        yield path


def suspicious_lines(path: Path):
    try:
        lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    except OSError:
        return
    for index, line in enumerate(lines):
        for kind, pattern in PATTERNS.items():
            if not pattern.search(line):
                continue
            window = '\n'.join(lines[max(0, index - 3): min(len(lines), index + 4)])
            intentional = bool(PLATFORM_MARKERS.search(window))
            # Tests/docs may intentionally mention Unix behavior; report but do not fail.
            exempt = path.parts[-2:] and (('tests' in path.parts) or path.suffix.lower() in {'.md', '.sh'})
            yield kind, index + 1, line.strip(), intentional or exempt


def main() -> int:
    findings = []
    for path in iter_source():
        for kind, line_no, line, intentional in suspicious_lines(path) or ():
            findings.append((kind, path.relative_to(ROOT), line_no, line, intentional))

    real = [f for f in findings if not f[4]]
    intentional = [f for f in findings if f[4]]

    print(f'Windows audit: {len(real)} actionable finding(s), {len(intentional)} intentional/reference finding(s).')
    if real:
        print('\n[ACTIONABLE]')
        for kind, path, line_no, line, _ in real:
            print(f'{path}:{line_no}: [{kind}] {line}')
    if intentional:
        print('\n[INTENTIONAL / REFERENCE]')
        for kind, path, line_no, line, _ in intentional[:100]:
            print(f'{path}:{line_no}: [{kind}] {line}')
        if len(intentional) > 100:
            print(f'... {len(intentional) - 100} more')
    return 1 if real else 0


if __name__ == '__main__':
    raise SystemExit(main())
