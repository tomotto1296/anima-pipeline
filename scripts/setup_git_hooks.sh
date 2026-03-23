#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."

dry_run=0
if [ "${1:-}" = "--dry-run" ]; then
  dry_run=1
fi

pre_commit=".githooks/pre-commit"
pre_push=".githooks/pre-push"

if [ ! -f "$pre_commit" ]; then
  echo "[git-hooks] missing $pre_commit" >&2
  exit 1
fi
if [ ! -f "$pre_push" ]; then
  echo "[git-hooks] missing $pre_push" >&2
  exit 1
fi

if [ "$dry_run" -eq 1 ]; then
  echo "[git-hooks] dry-run mode (no git config changes)"
else
  git config core.hooksPath .githooks
fi

hooks_path="$(git config --get core.hooksPath || true)"
if [ -z "$hooks_path" ]; then
  hooks_path="(unset)"
fi

if [ "$dry_run" -ne 1 ] && [ "$hooks_path" != ".githooks" ]; then
  echo "[git-hooks] unexpected core.hooksPath: $hooks_path" >&2
  exit 1
fi

echo "[git-hooks] core.hooksPath=$hooks_path"
echo "[git-hooks] pre-commit: version bump + quick checks enabled"
echo "[git-hooks] pre-push: quick checks (+ version guard + hooks guard) enabled"
