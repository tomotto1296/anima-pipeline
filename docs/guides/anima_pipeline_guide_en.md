# anima_pipeline User Guide

## 1. Overview

Anima Pipeline is a browser-based tool that can optionally use an LLM to assist prompt creation, then sends jobs to ComfyUI for image generation.

After refactoring, `anima_pipeline.py` remains the entry point, while most logic is split into `core/` and `frontend/`.
The current release is `v1.5.20`.

---

## 2. Requirements

| Item | Recommended |
|------|-------------|
| Python | 3.10+ (launcher prioritizes `python_embeded/python.exe` when present) |
| Dependency | `requests` (and `Pillow` recommended for history thumbnail generation) |
| ComfyUI | Running (default: `http://127.0.0.1:8188`; `--listen --enable-cors-header` recommended for mobile access) |
| Workflow JSON | At least one file in `workflows/` (four templates are bundled: Anima1/Anima2 with/without LoRA x4) |

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
  sessions/                   (named session saves)
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

Use the header `Theme` selector to switch `Device / Light / Dark` (`Device` follows your OS theme setting).

Click `Save Settings` to write user-specific values into `settings/pipeline_config.local.json`.  
Shared defaults are loaded from `settings/pipeline_config.default.json`.

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

### Random Features Split (GEN-9 / INPUT-1)

- `🎲 Today's Mood (GEN-9)` is placed next to the Generate button.
- `Today's Mood (GEN-9)`:
  - Randomly loads one existing character preset (skips character apply when no presets exist).
  - Also randomizes scene world / time of day / weather (`scene_world` / `scene_tod` / `scene_weather`).
  - Shows a short applied-summary message in STATUS.
- `Random Generate (INPUT-1)`:
  - Uses the `⚀` button in the character preset row.
  - Applies a new random character setup from existing `ui_options` choices (gender/age/hairstyle/hair color/eye color/outfit).
  - Shows a save confirmation dialog after applying random values.
  - Shows a short summary in STATUS.

### Positive/Negative Presets (INPUT-5)

- Positive Preset at the top of the Prompt section can save/load/delete positive-tuning state.
- Negative Preset at the top of the Negative section can save/load/delete negative-tuning state.
- Saved state includes quality tags, helper tags, notes, and safety-related selections.
- Last selected Positive/Negative preset is persisted in settings and restored after restart.

### Preset Sharing ZIP (SHARE-1)

- In the `Settings` panel, use `Export Presets` / `Import Presets` under `Preset Sharing (zip)`.
- Export downloads a single zip (`anima-presets_YYYY-MM-DD.zip`) containing:
  - `chara/*.json` / `chara/*.webp`
  - `presets/{scene,camera,quality,lora,composite}/*.json`
- Import expands the selected zip in one operation.
- If same-name files already exist, an overwrite confirmation dialog is shown (`409`-equivalent behavior), and overwrite is applied only after confirmation.
- Out of SHARE-1 scope:
  - `negative` / `positive` presets
  - `sessions/` (named sessions)

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
- OUTPUT-9: The history modal can show a prompt diff against the previous item.
  - Positive diff is shown with a `Show/Hide diff` toggle.
  - Negative diff is shown only when a difference exists, with the same toggle behavior.

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

## 10. Smartphone Access (via Tailscale — Remote / Off-LAN)

Use Tailscale if you want to control Anima Pipeline from your phone outside your home Wi-Fi.

### One-Time Setup

1. Create an account at [Tailscale](https://tailscale.com/)
2. **PC**: Install Tailscale and sign in
3. **Smartphone**: Install the Tailscale app and sign in with the same account
4. **ComfyUI**: Add `--listen --enable-cors-header` to your launch options

   ```
   .\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --lowvram --listen --enable-cors-header
   ```

### Connecting

1. Run `start_anima_pipeline - Tailscale.bat` on your PC
2. Open the URL shown in the console on your phone (for example, `http://100.x.x.x:7860`)

   ```
   [INFO] Starting server... Open http://100.x.x.x:7860
   ```

   > If Tailscale is not connected, you will see `[WARN] Tailscale IP not found.` — check that the Tailscale app is active on both your PC and phone.

> **Tips:** Once Tailscale is set up, you can use `start_anima_pipeline - Tailscale.bat` as your default launcher. It works fine on the same LAN too, so there is no need to switch between the two scripts.

---

## 11. Minimal Distribution Set

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
- personal/local `settings/pipeline_config.local.json`

For users already on `v1.5.11`, it is recommended to ship an upgrade ZIP alongside the minimal ZIP.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_release_zips.ps1 -Version 1.5.12 -BaseVersion 1.5.11
```

This generates both files in `dist/`:

- `anima-pipeline_v<version>_minimal.zip`
- `anima-pipeline_v<version>_upgrade_from_v1.5.11.zip`

---

## 12. Quick Checks

See [quick_checks_and_hooks.md](./quick_checks_and_hooks.md) for full details.

Common commands:

```bash
python scripts/check_frontend_syntax.py
python scripts/run_quick_checks.py --include-hooks-guard
```

---

## 13. Known Behavior

- Right after startup, progress % can appear late on first generation
- After cancel, `Generating...` may remain for a short time

These are currently tracked as non-critical issues.

---

## 14. Version History

| Version | Changes |
|---------|---------|
| **v1.5.20** | SHARE-1: Implemented preset bundle Export/Import (zip). Also improved visual distinction between `Generate` and `Today's Mood`, and switched the two-button row to stacked layout on mobile. |
| **v1.5.19** | INPUT-1: random character preset generation from `ui_options` (random attribute apply + save confirmation + STATUS summary). Dice icon style was unified for random buttons. |
| **v1.5.18** | INPUT-6 follow-up: Improved mobile LoRA visibility (card columns and slot-row layout optimization). |
| **v1.5.17** | OUTPUT-9: Added previous-item prompt diff viewer in history modal (Positive/Negative with toggle support; Negative appears only when differences exist). |
| **v1.5.15** | UI-5: Added theme mode selector (Device/Light/Dark). Improved dark-mode contrast and readability (section cards, LoRA area, inputs, disabled add buttons, language toggle). |
| **v1.5.14** | INPUT-6: LoRA management UX updates (search, favorites, recommended weight display, sort-order fix, unified settings API) |
| **v1.5.0** | Module split (core/ · frontend/), generation history DB, preset hierarchy, positive/negative presets, named session save, character name JA/EN split, setup diagnostics UI |
| **v1.4.7** | UI language switch (JA/EN), logging, preset thumbnail list, allow 0 characters, BOM read fix |
| **v1.4.6** | SaveImageExtended support, /no_think added to LLM system prompt |
| **v1.4.5** | Generation progress % (WebSocket), re-generation double-insertion fixes, smartphone WS banner |
| **v1.4.4** | ExtraTag double-insertion fix, character block refactor, requests auto-install |
| **v1.4.3** | Custom workflow (API format JSON) support, Node ID auto-detection on workflow select |
| **v1.4.2** | 400 error fix for partial/no LoRA selection (LoraLoader auto-bypass) |
| **v1.4.1** | Smartphone support (major mobile UI improvements), LoRA thumbnail display, section toggles |
| **v1.4.0** | LoRA injection, workflow selection dropdown, bug fixes |
| **v1.3.0** | Gallery, generation parameters section, floating nav, scene block separation |
| **v1.2.1** | Auto preset generation (Danbooru Wiki + LLM), color dropdown |
| **v1.2.0** | Character preset feature, connection test, ComfyUI queue display |
| **v1.1.0** | Initial release |
