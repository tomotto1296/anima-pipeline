#!/usr/bin/env python3
"""Auto-bump app version when Python files are staged."""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = ROOT / "anima_pipeline.py"
VERSION_PATTERN = re.compile(r'(?m)^(\s*__version__\s*=\s*")([0-9]+(?:\.[0-9]+)*)("\s*)$')


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


def _staged_files() -> list[str]:
    out = _run_git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [line.strip() for line in out.splitlines() if line.strip()]


def _version_already_staged() -> bool:
    diff = _run_git("diff", "--cached", "--", TARGET.name)
    for line in diff.splitlines():
        if line.startswith(("+", "-")) and "__version__" in line:
            return True
    return False


def _bump_patch(version: str) -> str:
    parts = [int(p) for p in version.split(".")]
    parts[-1] += 1
    return ".".join(str(p) for p in parts)


def main() -> int:
    staged = _staged_files()
    staged_py = [p for p in staged if p.lower().endswith(".py")]
    if not staged_py:
        return 0

    if _version_already_staged():
        print("[version-bump] __version__ is already staged, skipping auto bump.")
        return 0

    text = TARGET.read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(text)
    if not match:
        print("[version-bump] __version__ declaration was not found.", file=sys.stderr)
        return 1

    old_version = match.group(2)
    new_version = _bump_patch(old_version)
    updated = VERSION_PATTERN.sub(rf'\1{new_version}\3', text, count=1)
    TARGET.write_text(updated, encoding="utf-8")

    _run_git("add", TARGET.name)
    print(f"[version-bump] {old_version} -> {new_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
