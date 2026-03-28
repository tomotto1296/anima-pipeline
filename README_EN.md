# Anima Pipeline

<p align="center">
  <img src="images/hero-ui-and-result.jpg" alt="Anima Pipeline UI + Generated Image" width="800">
  <br>
  <em>Enter character name 竊・LLM auto-generates Danbooru tags 竊・One-click to stunning Anima images!</em>
</p>
Browser UI + LLM automation for the Anima workflow.

[Back to Japanese README 竊・README.md](README.md)

## 倹 Live Demo / Landing Page
- [Japanese Site](https://tomotto1296.github.io/anima-pipeline/index.html)
- [English Version](https://tomotto1296.github.io/anima-pipeline/index_en.html)
- [Try Demo (Lite)](https://tomotto1296.github.io/anima-pipeline/demo_en.html)

<p align="center">
  <img src="demo/demo-flow.gif" alt="Demo GIF" width="600">
</p>

---

## Current Version & Docs

- Current version: `v1.5.18`
- Implemented features: [docs/specs/features.md](docs/specs/features.md)
- Roadmap: [docs/updates/roadmap.md](docs/updates/roadmap.md)
- Update log: [docs/updates/Update.md](docs/updates/Update.md)

---

## Requirements

- Python 3.10 or later (not required when bundled `python_embeded/python.exe` is available)
  - If `python_embeded/python.exe` exists, launcher uses it first (Portable-style).
- ComfyUI (Anima workflow available)
  - Recommended launch option: `--listen --enable-cors-header` when using mobile clients.
- Workflow JSON
  - Four templates are bundled by default (Anima1/Anima2, with/without LoRA x4).
- LLM server (LM Studio / Gemini API, etc.) *Optional*

---

## Setup

### 1. Prepare the Workflow JSON

The repository includes four ready-to-use workflow JSON files:

- `image_anima_preview.json` (Anima1, no LoRA)
- `image_anima_preview_Lora4.json` (Anima1, LoRA x4)
- `image_anima2_preview.json` (Anima2, no LoRA)
- `image_anima2_preview_Lora4.json` (Anima2, LoRA x4)

You can use these as-is, or export your own workflow from ComfyUI:

1. Launch ComfyUI
2. Top-right menu 竊・"Browse Templates" 竊・Select **Anima**
3. Menu 竊・"Save (API Format)" and save it as `image_anima_preview.json`
4. Place it in the `workflows/` folder

> Any JSON exported from ComfyUI using "Save (API Format)" can be placed in `workflows/` and selected from the dropdown.

### 2. Launch

**Windows:** Double-click `start_anima_pipeline.bat` (installs `requests` automatically on first run)

> If the batch file opens in VS Code, right-click it and choose "Open with" 竊・"Command Prompt".

**Other platforms:**
```bash
pip install requests
python anima_pipeline.py
```

Open http://localhost:7860 in your browser.

### 3. Initial Setup

Open "笆ｶ Settings" at the top, check the ComfyUI URL, and click "沈 Save Settings".

If using an LLM, choose platform (LM Studio / Gemini / Custom), then set URL, API key, and model name.

### 4. Recommended ComfyUI Launch Option

If you want smartphone access or LoRA thumbnails, add this option when starting ComfyUI:

```
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --lowvram --listen --enable-cors-header
```

---

## Key Features (Latest)

| Status | Feature |
|---|---|
| 笘・| JA/EN split fields for character/work name (`name_en` / `series_en`) |
| 笘・| Positive/Negative preset save and load |
| 笘・| Preset hierarchy (`chara / scene / camera / quality / lora / composite`) |
| 笘・| Generation History DB (all-history UI + re-edit) |
| 笘・| Named sessions (multi-slot save/load with overwrite handling) |
| 笘・| Setup diagnostics UI (`/diagnostics`) |
| 笘・| Metadata embedding (PNG/WebP, LoRA hash metadata) |
| 笘・| OUTPUT-9: Previous-item prompt diff in history modal (Positive with toggle, Negative shown only when differences exist) |
| 笘・| LoRA injection (card-grid UI, thumbnails, up to 4 slots) |
| 笘・| Workflow switching (select from `workflows/`, auto-detect Node IDs) |
| 笘・| UI language switch (Japanese / English) |
| 笘・| Logging (save, secret masking, ZIP export) |

> For the full feature list with versions, see [docs/specs/features.md](docs/specs/features.md).

---

## Docs Structure (`docs/`)

- Guides index: [docs/guides/README.md](docs/guides/README.md)
- Specs index: [docs/specs/README.md](docs/specs/README.md)
- Update log: [docs/updates/Update.md](docs/updates/Update.md)
- Roadmap: [docs/updates/roadmap.md](docs/updates/roadmap.md)
- Release notes: `docs/release_notes/`
- Article drafts: `docs/articles/`

---

## File Structure (Current)

```text
anima_pipeline/
  anima_pipeline.py
  core/                           <- split backend modules (handlers/history/presets/etc.)
  frontend/                       <- index.html / i18n.js
  docs/
    guides/
    specs/
    updates/
    release_notes/
    articles/
  workflows/                      <- workflow JSON files
  settings/                       <- pipeline_config / ui_options / prompt settings
  presets/                        <- hierarchical presets (chara/scene/camera/quality/lora/composite)
  sessions/                       <- named sessions
  history/                        <- generation history DB
  logs/                           <- runtime logs
```

---

## Roadmap Summary

- `v1.4.8-v1.5.0`: Foundation phase (completed)
- `v1.5.1`: Daily workflow improvements (LoRA management, random preset, sharing)
- `v1.5.2`: Production phase (batch generation, queue, comparison generation)
- `v1.5.x+`: Advanced phase (LLM scoring, auto-tagging, workflow reconstruction assist)

See [docs/updates/roadmap.md](docs/updates/roadmap.md) for details.
