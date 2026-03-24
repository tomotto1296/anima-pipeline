# Anima Pipeline

<p align="center">
  <img src="images/hero-ui-and-result.jpg" alt="Anima Pipeline UI + Generated Image" width="800">
  <br>
  <em>Enter character name → LLM auto-generates Danbooru tags → One-click to stunning Anima images!</em>
</p>
Browser UI + LLM automation for the Anima workflow.

[Back to Japanese README → README.md](README.md)

## 🌐 Live Demo / Landing Page
- [Japanese Site](https://tomotto1296.github.io/anima-pipeline/index.html)
- [English Version](https://tomotto1296.github.io/anima-pipeline/index_en.html)

<p align="center">
  <img src="demo/demo-flow.gif" alt="Demo GIF" width="600">
</p>

---

## Current Version & Docs

- Current version: `v1.5.1`
- Implemented features: [docs/specs/features.md](docs/specs/features.md)
- Roadmap: [docs/updates/roadmap.md](docs/updates/roadmap.md)
- Update log: [docs/updates/Update.md](docs/updates/Update.md)

---

## Requirements

- Python 3.10 or later
- ComfyUI 0.16.4 or later + Anima workflow
- LLM server (LM Studio / Gemini API, etc.) *Optional*

---

## Setup

### 1. Prepare the Workflow JSON

`workflows/image_anima_preview.json` is not included in the repository. Please obtain it with the steps below.

1. Launch ComfyUI
2. Top-right menu → "Browse Templates" → Select **Anima**
3. Menu → "Save (API Format)" and save it as `image_anima_preview.json`
4. Place it in the `workflows/` folder

> **You can also use your own workflow JSON.** Any JSON exported from ComfyUI using "Save (API Format)" can be placed in `workflows/` and selected from the dropdown.

### 2. Launch

**Windows:** Double-click `start_anima_pipeline.bat` (installs `requests` automatically on first run)

> If the batch file opens in VS Code, right-click it and choose "Open with" → "Command Prompt".

**Other platforms:**
```bash
pip install requests
python anima_pipeline.py
```

Open http://localhost:7860 in your browser.

### 3. Initial Setup

Open "▶ Settings" at the top, check the ComfyUI URL, and click "💾 Save Settings".

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
| ☑ | JA/EN split fields for character/work name (`name_en` / `series_en`) |
| ☑ | Positive/Negative preset save and load |
| ☑ | Preset hierarchy (`chara / scene / camera / quality / lora / composite`) |
| ☑ | Generation History DB (all-history UI + re-edit) |
| ☑ | Named sessions (multi-slot save/load with overwrite handling) |
| ☑ | Setup diagnostics UI (`/diagnostics`) |
| ☑ | Metadata embedding (PNG/WebP, LoRA hash metadata) |
| ☑ | LoRA injection (card-grid UI, thumbnails, up to 4 slots) |
| ☑ | Workflow switching (select from `workflows/`, auto-detect Node IDs) |
| ☑ | UI language switch (Japanese / English) |
| ☑ | Logging (save, secret masking, ZIP export) |

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
