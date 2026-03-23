# anima_pipeline User Guide

## 1. Overview

Anima Pipeline is a browser-based tool that can optionally use an LLM to assist prompt creation, then sends jobs to ComfyUI for image generation.

After refactoring, `anima_pipeline.py` remains the entry point, while most logic is split into `core/` and `frontend/`.

---

## 2. Requirements

| Item | Recommended |
|------|-------------|
| Python | 3.10+ |
| Dependency | `requests` (and `Pillow` recommended for history thumbnail generation) |
| ComfyUI | Running (default: `http://127.0.0.1:8188`) |
| Workflow JSON | At least one file in `workflows/` |

Install minimum dependencies:

```bash
pip install -r requirements.txt
```

---

## 3. Main Structure (Post-Refactor)

```text
anima-pipeline/
  anima_pipeline.py
  requirements.txt
  start_anima_pipeline.bat
  start_anima_pipeline - Tailscale.bat
  core/
    config.py
    handlers.py
    presets.py
    llm.py
    comfyui.py
    history.py
    frontend.py
    runtime.py
    bootstrap.py
  frontend/
    index.html
    i18n.js
  workflows/
    image_anima_preview.json  (example)
  settings/                   (auto-generated on first run)
  chara/                      (character presets)
  presets/                    (Scene/Camera/Quality/LoRA/Composite)
  assets/                     (favicon/icon/manifest resources)
```

---

## 4. How to Launch

### Windows (standard)

Run `start_anima_pipeline.bat`.

### Windows (via Tailscale)

Run `start_anima_pipeline - Tailscale.bat`.

### Direct launch

```bash
python anima_pipeline.py
```

Then open `http://localhost:7860` in your browser.

---

## 5. First-Time Settings (Important)

In `SETTINGS`, verify:

1. `Workflow JSON Path (fallback)`
2. `Select from workflows/ folder (preferred)`
3. `Positive Node ID`
4. `Negative Node ID`
5. `KSampler Node ID`
6. `ComfyUI URL`
7. `History DB Path` (default: `history/history.db`)
8. `History Thumb Dir` (default: `history/thumbs`)

Click `Save Settings` to write values into `settings/pipeline_config.json`.

---

---

## 6. Generation History (Session / All History)

- After generation, cards are added to the gallery as session history.
- The `All History` tab shows records persisted in SQLite.
- Default history storage paths:
  - `history/history.db`
  - `history/thumbs/`
- `Clear` in session history clears only session cards (DB records in `All History` remain).

## 7. Smartphone Access (Same LAN)

1. Check your PC IPv4 address (for example, `192.168.1.103`)
2. Start Anima Pipeline on the PC
3. Open `http://<PC IPv4>:7860` on your phone

If it fails:

- Confirm inbound firewall rule for port `7860`
- Confirm URL starts with `http://` (not `https://`)
- Confirm ComfyUI/CORS setup if your environment requires it

---

## 8. Minimal Distribution Set

Minimum required files:

```text
anima_pipeline.py
requirements.txt
core/*.py
frontend/index.html
frontend/i18n.js
workflows/*.json
start_anima_pipeline.bat (or any launcher you provide)
```

Recommended to include:

- `assets/icons/*`
- `manifest.json`
- `start_anima_pipeline - Tailscale.bat`

Recommended to exclude:

- `logs/`, `history/`, `__pycache__/`, `.tmp*`
- personal/local `settings/pipeline_config.json`

---

## 9. Quick Checks

See [quick_checks_and_hooks.md](./quick_checks_and_hooks.md) for full details.

Common commands:

```bash
python scripts/check_frontend_syntax.py
python scripts/run_quick_checks.py --include-hooks-guard
```

---

## 10. Known Behavior

- Right after startup, progress % can appear late on first generation
- After cancel, `Generating...` may remain for a short time

These are currently tracked as non-critical issues.
