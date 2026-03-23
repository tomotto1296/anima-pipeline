#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / '.githooks'


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding='utf-8', errors='replace')


def main() -> int:
    failed = False

    pre_commit = HOOKS / 'pre-commit'
    pre_push = HOOKS / 'pre-push'

    if not pre_commit.exists():
        print('[NG] missing .githooks/pre-commit')
        failed = True
    if not pre_push.exists():
        print('[NG] missing .githooks/pre-push')
        failed = True

    if failed:
        return 1

    pc = _read(pre_commit)
    pp = _read(pre_push)

    pc_required = [
        'scripts/bump_version_on_py_change.py',
        'scripts/run_quick_checks.py',
    ]
    for snip in pc_required:
        if snip not in pc:
            print(f'[NG] pre-commit missing: {snip}')
            failed = True

    pp_required = [
        'scripts/run_quick_checks.py --include-version-guard',
    ]
    for snip in pp_required:
        if snip not in pp:
            print(f'[NG] pre-push missing: {snip}')
            failed = True

    if failed:
        return 1

    print('[OK] git hooks guard passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
