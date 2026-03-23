#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOCK_FILE = ROOT / '.tmp_quick_checks.lock'
DEFAULT_LOCK_STALE_SECONDS = 30 * 60
COMPILE_TARGETS = [
    'anima_pipeline.py',
    'scripts/check_frontend_syntax.py',
    'scripts/run_quick_checks.py',
    'scripts/check_version_bump.py',
    'scripts/bump_version_on_py_change.py',
    'scripts/check_hooks_guard.py',
    'core/handlers.py',
]


def run_step(title: str, cmd: list[str]) -> int:
    print(f"[CHECK] {title}", flush=True)
    print(f"        {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run quick local checks.')
    p.add_argument('--skip-compile', action='store_true')
    p.add_argument('--include-version-guard', action='store_true')
    p.add_argument('--frontend-only', action='store_true', help='Run only frontend syntax guard')
    p.add_argument('--include-hooks-guard', action='store_true', help='Validate .githooks integrity')
    p.add_argument('--no-lock', action='store_true', help='Allow concurrent quick-check runs')
    p.add_argument(
        '--lock-stale-seconds',
        type=int,
        default=DEFAULT_LOCK_STALE_SECONDS,
        help=f'Remove lock file if older than this (default: {DEFAULT_LOCK_STALE_SECONDS})',
    )
    p.add_argument('--version-base', default='HEAD~1')
    p.add_argument('--version-head', default='HEAD')
    return p.parse_args()


def _clear_stale_lock_if_needed(max_age_seconds: int) -> None:
    if not LOCK_FILE.exists():
        return
    try:
        age = time.time() - LOCK_FILE.stat().st_mtime
        if age > max_age_seconds:
            LOCK_FILE.unlink(missing_ok=True)
            print(f'[INFO] removed stale quick-check lock: {LOCK_FILE}')
    except Exception:
        # If stat/unlink fails, normal lock acquisition path will handle it.
        pass


def acquire_lock(disabled: bool, stale_seconds: int) -> int | None:
    if disabled:
        return None

    _clear_stale_lock_if_needed(max(0, stale_seconds))

    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(LOCK_FILE), flags)
    except FileExistsError:
        print(f'[NG] quick checks already running: {LOCK_FILE}')
        return -1

    os.write(fd, str(os.getpid()).encode('ascii', errors='ignore'))
    return fd


def release_lock(fd: int | None) -> None:
    if fd is None or fd < 0:
        return
    try:
        os.close(fd)
    except Exception:
        pass
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def main() -> int:
    args = parse_args()
    lock_fd = acquire_lock(args.no_lock, args.lock_stale_seconds)
    if lock_fd == -1:
        return 2

    try:
        if run_step('frontend syntax guard', [sys.executable, 'scripts/check_frontend_syntax.py']) != 0:
            return 1

        if args.frontend_only:
            print('[OK] quick checks passed (frontend-only)')
            return 0

        if not args.skip_compile:
            if run_step('python compile', [sys.executable, '-m', 'py_compile', *COMPILE_TARGETS]) != 0:
                return 1

        if args.include_hooks_guard:
            if run_step('hooks guard', [sys.executable, 'scripts/check_hooks_guard.py']) != 0:
                return 1

        if args.include_version_guard:
            if run_step(
                f'version guard ({args.version_base}..{args.version_head})',
                [
                    sys.executable,
                    'scripts/check_version_bump.py',
                    '--base',
                    args.version_base,
                    '--head',
                    args.version_head,
                ],
            ) != 0:
                return 1

        print('[OK] quick checks passed')
        return 0
    finally:
        release_lock(lock_fd)


if __name__ == '__main__':
    raise SystemExit(main())
