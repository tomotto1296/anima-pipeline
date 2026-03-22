# Contributing

## Version Bump Rule for Python Changes

- When a commit includes any staged `*.py` file, `anima_pipeline.py`'s `__version__` is auto-incremented by `+1` in the patch segment.
- The bump runs from the `pre-commit` hook (`.githooks/pre-commit`).
- If `__version__` is already staged manually, the auto-bump is skipped.

## One-Time Setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_git_hooks.ps1
```

or:

```powershell
git config --local core.hooksPath .githooks
```

## CI Enforcement

- GitHub Actions `Version Guard` checks pull requests and `main` pushes.
- If any `.py` file changed and `anima_pipeline.py` `__version__` did not change, CI fails.
- Local equivalent check:

```powershell
python scripts/check_version_bump.py --base <base_sha> --head <head_sha>
```
