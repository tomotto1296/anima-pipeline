#!/usr/bin/env python3
"""Fail CI when Python files changed without __version__ bump."""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = "anima_pipeline.py"


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def _changed_files(base: str, head: str) -> list[str]:
    out = _run_git("diff", "--name-only", "--diff-filter=ACMR", base, head)
    return [line.strip() for line in out.splitlines() if line.strip()]


def _version_line_changed(base: str, head: str) -> bool:
    diff = _run_git("diff", "--", base, head, TARGET)
    for line in diff.splitlines():
        if line.startswith(("+", "-")) and "__version__" in line:
            return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Base commit SHA")
    parser.add_argument("--head", required=True, help="Head commit SHA")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files = _changed_files(args.base, args.head)
    py_files = [p for p in files if p.lower().endswith(".py")]

    if not py_files:
        print("[version-guard] No Python file changes detected.")
        return 0

    if _version_line_changed(args.base, args.head):
        print("[version-guard] __version__ change detected.")
        return 0

    print("[version-guard] Python files changed but __version__ was not updated.")
    print("[version-guard] Changed .py files:")
    for path in py_files:
        print(f"  - {path}")
    print(
        "[version-guard] Please bump anima_pipeline.py __version__ "
        "(or run pre-commit hook setup).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
