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

### Setup Diagnostics (SETUP-2)

In the Settings panel, click `Run Setup Diagnostics` to run all checks at once.

- ComfyUI connection
- LLM connection (`SKIP` when not configured)
- Workflow JSON existence/parse
- `Positive/Negative/KSampler` Node ID validation
- LoRA node count
- `Output Directory` check (WebP mode)

The result panel shows `OK / WARN / ERR / SKIP`, and `WARN / ERR` rows include hints.

### Preset Hierarchy (INPUT-4)

In `PRESETS`, the following categories can be saved/loaded/deleted independently.

- `Scene`
- `Camera`
- `Quality`
- `Lora`
- `Composite`
- `Negative`
- `Positive`

Default preset names:

- `Scene_default`
- `Camera_default`
- `Quality_default`
- `Lora_default`
- `Composite_default`

Behavior notes:

- Composite load restores from `snapshot` first (snapshot has priority over name references).
- Camera presets store per-character values in `all[]`.
- When loading for multiple characters, if some character slots are missing in saved data, the first camera values (`posv`/`posh`/`pos_camera`) are used as fallback.
### Character/Series JA-EN Split (INPUT-12)

- Character fields now support four inputs: Name JA / Name EN and Series JA / Series EN.
- When LLM is disabled, tag assembly prioritizes EN fields and falls back to JA fields when EN is empty.
- Preset auto-generation can attempt EN completion (name_en / series_en) even when only Japanese input is provided.
- Default character preset naming uses JA（EN） when both values exist.

### Positive/Negative Presets (INPUT-5)

- Positive Preset at the top of the Prompt section can save/load/delete positive-tuning state.
- Negative Preset at the top of the Negative section can save/load/delete negative-tuning state.
- Saved state includes quality tags, helper tags, notes, and safety-related selections.
- Last selected Positive/Negative preset is persisted in settings and restored after restart.

---

## 6. Output Format and Metadata (OUTPUT-4)

In `Image Settings`, you can control behavior using `Output Format` and `Embed Metadata`.

- `PNG`:
  - Saves `parameters` (plus `prompt` / `workflow`)
  - Better for ComfyUI re-import with workflow restoration
- `WebP`:
  - Saves metadata into Exif UserComment + XMP
  - Better for lightweight Civitai uploads
- `Embed Metadata = OFF`:
  - Image is saved normally without metadata

Recommended usage:
- Prioritize Civitai posting: `WebP`
- Prioritize ComfyUI re-editing: `PNG`

Notes:
- If WebP conversion fails, the image is saved as PNG.
- Civitai `Resources` detection requires model/LoRA hash matching.

---

## 7. Generation History (Session / All History)

- After generation, cards are added to the gallery as session history.
- The `All History` tab shows records persisted in SQLite.
- Default history storage paths:
  - `history/history.db`
  - `history/thumbs/`
- `Clear` in session history clears only session cards (DB records in `All History` remain).

## 8. Named Session Save (OUTPUT-8)

- Use `SAVE SESSION` to store the current input state as `sessions/<n>.json`.
- Loading from `Open` restores key input fields (prompt and major settings).
- If the same name already exists, a confirmation dialog appears: `OK` overwrites, `Cancel` aborts.
- Session names are normalized to safe file names (invalid characters are replaced).
- `Saved Sessions` shows saved entries. Use `LOAD` to restore and `DELETE` to remove.
- Auto-updated `last session` (after generation) and manual named saves (`SAVE SESSION`) are managed separately.

---
## 9. Smartphone Access (Same LAN)

1. Check your PC IPv4 address (for example, `192.168.1.103`)
2. Start Anima Pipeline on the PC
3. Open `http://<PC IPv4>:7860` on your phone

If it fails:

- Confirm inbound firewall rule for port `7860`
- Confirm URL starts with `http://` (not `https://`)
- Confirm ComfyUI/CORS setup if your environment requires it

---

## 10. Minimal Distribution Set

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

## 11. Quick Checks

See [quick_checks_and_hooks.md](./quick_checks_and_hooks.md) for full details.

Common commands:

```bash
python scripts/check_frontend_syntax.py
python scripts/run_quick_checks.py --include-hooks-guard
```

---

## 12. Known Behavior

- Right after startup, progress % can appear late on first generation
- After cancel, `Generating...` may remain for a short time

These are currently tracked as non-critical issues.

