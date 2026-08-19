from __future__ import annotations
import argparse
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = 'upstream'
UPSTREAM_URL = 'https://github.com/Shpigford/nurb.git'
SAFE_PREFIXES = ('src/nurb/', 'tests/', 'examples/', 'skills/', 'evals/')
WINDOWS_PREFIXES = ('desktop/src-tauri/', 'desktop/scripts/', '.github/workflows/windows-')
REVIEW_PREFIXES = ('desktop/src/', 'desktop/package.json', 'desktop/package-lock.json', 'pyproject.toml', 'uv.lock')

def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def ensure_upstream() -> None:
    """Add the upstream remote when it is missing, so CI checkouts (which only
    clone origin) can still run the sync audit."""
    if UPSTREAM not in run('git', 'remote').splitlines():
        run('git', 'remote', 'add', UPSTREAM, UPSTREAM_URL)

def classify(path: str) -> str:
    if path.startswith(WINDOWS_PREFIXES): return 'WINDOWS-SPECIFIC'
    if path.startswith(SAFE_PREFIXES): return 'SAFE'
    if path.startswith(REVIEW_PREFIXES): return 'REVIEW'
    return 'REVIEW'


def safe_drift_paths(changed: list[str]) -> list[str]:
    """The SAFE-zone paths that differ from upstream. Extracted so the gate's
    decision is testable without invoking git on the live tree."""
    return [p for p in changed if classify(p) == 'SAFE']


def strict_should_fail(base_sha: str, remote_sha: str, safe_drift: list[str]) -> bool:
    """Pure-ahead means every drift hunk is the fork's own intentional
    evolution (added platform/, patched cli.py, etc.); not gating on it keeps
    fork-native work flowing. Behind or diverged against upstream while SAFE
    drifted means we are releasing on top of SAFE code we have not pulled in.
    """
    pure_ahead = base_sha == remote_sha
    return (not pure_ahead) and bool(safe_drift)

def status(strict: bool = False) -> int:
    ensure_upstream()
    run('git', 'fetch', UPSTREAM, 'main', '--prune')
    local = run('git', 'rev-parse', 'HEAD')
    remote = run('git', 'rev-parse', f'{UPSTREAM}/main')
    base = run('git', 'merge-base', 'HEAD', f'{UPSTREAM}/main')
    print(f'Local:    {local}')
    print(f'Upstream: {remote}')
    if local == remote:
        print('Status: up to date')
        return 0
    if base == local:
        count = run('git', 'rev-list', '--count', f'HEAD..{UPSTREAM}/main')
        print(f'Status: behind upstream by {count} commit(s)')
    elif base == remote:
        count = run('git', 'rev-list', '--count', f'{UPSTREAM}/main..HEAD')
        print(f'Status: fork has {count} commit(s) not in upstream')
    else:
        print('Status: histories diverged')
    changed = run('git', 'diff', '--name-only', f'HEAD..{UPSTREAM}/main').splitlines()
    groups = {'SAFE': [], 'REVIEW': [], 'WINDOWS-SPECIFIC': []}
    for path in changed:
        groups[classify(path)].append(path)
    for group, paths in groups.items():
        if paths:
            print(f'\n{group}:')
            for path in paths: print(f'  {path}')
    if strict and changed:
        # Decision lives in strict_should_fail so it can be unit-tested.
        safe_drift = safe_drift_paths(changed)
        if strict_should_fail(base, remote, safe_drift):
            print(
                f'\nstrict: {len(safe_drift)} SAFE-zone path(s) drift against '
                f'upstream while fork is behind or diverged. Merge upstream '
                f'before releasing.',
                file=__import__('sys').stderr,
            )
            for path in safe_drift:
                print(f'  - {path}', file=__import__('sys').stderr)
            return 1
    return 0

def prepare() -> int:
    branch = 'upstream-sync/' + run('git', 'rev-parse', '--short', f'{UPSTREAM}/main')
    try:
        run('git', 'switch', '-c', branch)
        print(f'Created {branch}')
    except subprocess.CalledProcessError:
        run('git', 'switch', branch)
        print(f'Switched to {branch}')
    print('Review the classified paths, then run: git merge --no-edit upstream/main')
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description='Maintain the Windows fork against upstream nurb.')
    parser.add_argument('command', choices=('status', 'prepare'))
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Exit non-zero when SAFE-zone paths differ from upstream while '
             'the fork is behind or diverged. Intended for CI; local dev '
             'leaves it off so fork-native SAFE patches do not flag.',
    )
    args = parser.parse_args()
    if args.command == 'status':
        return status(strict=args.strict)
    return prepare()

if __name__ == '__main__':
    raise SystemExit(main())
