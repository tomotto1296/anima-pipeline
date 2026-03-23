# Quick Checks & Hooks

## Quick checks

- Python runner:
  - `python scripts/run_quick_checks.py`
- Include version guard:
  - `python scripts/run_quick_checks.py --include-version-guard`
- Include hooks guard:
  - `python scripts/run_quick_checks.py --include-hooks-guard`
- Skip compile step:
  - `python scripts/run_quick_checks.py --skip-compile`
- Frontend only:
  - `python scripts/run_quick_checks.py --frontend-only`
- Override stale lock threshold (seconds):
  - `python scripts/run_quick_checks.py --lock-stale-seconds 600`

## Cross-platform shortcuts

- Quick checks (shell):
  - `sh scripts/run_quick_checks.sh`
- Setup git hooks (shell):
  - `sh scripts/setup_git_hooks.sh`
- Setup git hooks dry-run (shell):
  - `sh scripts/setup_git_hooks.sh --dry-run`

## Windows shortcuts

- Quick checks (Batch):
  - `scripts\run_quick_checks.bat`
- Quick checks (PowerShell):
  - `powershell -ExecutionPolicy Bypass -File scripts/run_quick_checks.ps1`
- Setup hooks (Batch):
  - `scripts\setup_git_hooks.bat`
- Setup hooks (PowerShell):
  - `powershell -ExecutionPolicy Bypass -File scripts/setup_git_hooks.ps1`
- Setup hooks dry-run (PowerShell):
  - `powershell -ExecutionPolicy Bypass -File scripts/setup_git_hooks.ps1 -DryRun`

## Git hooks

Enable hooks path, then hooks run automatically.

Current hook flow:

1. `pre-commit`
2. `scripts/bump_version_on_py_change.py`
3. `scripts/run_quick_checks.py`
4. `pre-push`
5. `scripts/run_quick_checks.py --include-version-guard --include-hooks-guard`

This ensures version bump + syntax/compile checks before commit,
and adds version/hook guard checks before push.
