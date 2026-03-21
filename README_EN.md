# anima_pipeline
<p align="center">
  <img src="images/hero-ui-and-result.jpg" alt="Anima Pipeline UI + Generated Image" width="800">
  <br>
  <em>Enter character name → LLM auto-generates Danbooru tags → One-click to stunning Anima images!</em>

This is a pipeline tool that allows you to enter character and scene information via a browser UI → automatically generate Danbooru prompts using an LLM (optional) → and automatically send them to the ComfyUI Anima workflow.

[Back to Japanese README → README.md](README.md)

## 🌐 Live Demo / Landing Page
- [日本語版サイト](https://tomotto1296.github.io/anima-pipeline/index.html)  
- [English Version](https://tomotto1296.github.io/anima-pipeline/index_en.html)
<p align="center">
  <img src="demo/demo-flow.gif" alt="Demo GIF" width="600">
</p>
---

## Requirements

- Python 3.10 or later
- ComfyUI 0.16.4 or later + Anima workflow
- LLM server (LM Studio / Gemini API, etc.) *Optional*

---

## Setup

### 1. Prepare the Workflow JSON

`workflows/image_anima_preview.json` is not included in the repository. Please obtain it by following the steps below.

1. Launch ComfyUI
2. Top-right menu → “Browse Templates” → Select **Anima**
3. Select Menu → “Save (API Format)” and save it as `image_anima_preview.json`
4. Place it in the `workflows/` folder

> **You can also use your own workflows.** If you place the JSON exported via ComfyUI’s “Save (API Format)” in the `workflows/` folder, it will appear in the dropdown menu.

### 2. Launch

**Windows:** Double-click `start_anima_pipeline.bat` (requests will be automatically installed the first time)

> If the batch file opens in VS Code or similar, right-click → select “Open with” → “Command Prompt”.

**Other platforms:**
```bash
pip install requests
python anima_pipeline.py
```

Open http://localhost:7860 in your browser.

### 3. Initial Setup

Open “▶ Settings” at the top of the screen, verify the ComfyUI URL, and click “💾 Save Settings”.

If using an LLM, select the platform (LM Studio / Gemini / Custom), enter the URL, API key, and model name, then save.

### 4. ComfyUI Launch Options (Recommended)

If accessing from a smartphone or using LoRA thumbnail display, add the following options:

```
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --lowvram --listen --enable-cors-header
```

---

## Features

| Status | Feature |
|---|---|
| ☑ | Auto-generate Danbooru tags from character/work names with an LLM |
| ☑ | Fine-grained UI controls for hairstyle, hair color, eyes, mouth, expression, outfits, and poses |
| ☑ | Configure up to 6 characters at once |
| ☑ | Character preset save / load / delete |
| ☑ | Preset thumbnail gallery view (v1.4.7) |
| ☑ | Auto-create thumbnails from gallery images (v1.4.7) |
| ☑ | Auto-generate presets from Danbooru Wiki + LLM |
| ☑ | LoRA injection (card-grid UI, thumbnail view, up to 4 slots) |
| ☑ | Workflow switching (select from `workflows/`, auto-detect Node IDs) |
| ☑ | Live generation progress % display (WebSocket) |
| ☑ | Preset management for positive / negative style tags |
| ☑ | Automatic session save and restore |
| ☑ | Gallery, generated-image preview, and prompt reuse |
| ☑ | WebP conversion for generated images (optional) |
| ☑ | Smartphone / tablet support (same Wi-Fi network) |
| ☑ | UI language switching (Japanese / English) (v1.4.7) |
| ☑ | Logging features (save, mask sensitive data, ZIP export) (v1.4.7) |

---

## File Structure

```
anima_pipeline/
  anima_pipeline.py              ← Main script
  start_anima_pipeline.bat       ← For Windows startup
  requirements.txt               ← Dependency libraries
  README.md
  docs/guides/anima_pipeline_guide_en.md  ← Detailed guide (English)
  workflows/                     ← Folder for workflow JSON files
    image_anima_preview.json     ← No LoRA (provide your own)
    image_anima_preview_Lora4.json ← Supports 4 LoRAs (included)
  chara/
    000_default.json             ← Default character preset
  settings/
    pipeline_config.json         ← Configuration file (recommended to exclude from Git version control as it contains API keys)
    pipeline_config.default.json ← Default template
    ui_options.json              ← Definition of UI button options
    llm_system_prompt.txt        ← LLM system prompt
```

---

## Details

Please refer to [docs/guides/anima_pipeline_guide_en.md](docs/guides/anima_pipeline_guide_en.md).

---

## 🗺️ Roadmap

See [docs/roadmap.md](docs/roadmap.md) for the full list.

### Coming Soon

- Preset hierarchy (character / scene / camera / quality / LoRA composition)
- Per-preset negative-tag save and auto-switch
- Generation history DB + re-edit support
- Named session saves with multiple slots
- Self-diagnosis UI on failures (error cause hints / missing-node warnings)
- LoRA management improvements (search, favorites, recommended weight, auto-suggestions)
- Batch generation mode (CSV / txt -> sequential generation)
- Generation queue (add / reorder / cancel / rerun)
- Random character preset generation
- Preset sharing (zip Export / Import)
- Prompt diff viewer (vs previous run)

### Under Consideration

- First-run tutorial wizard
- Prompt recovery from image metadata (PNG / WebP)
- "Continue with the same character" generation button
- Comparison generation mode (fixed seed for prompt / LoRA / CFG comparisons)
- Workflow reconstruction assistance (semi-automatic mapping)
- LLM-based generated-image scoring and auto-routing
- Auto Danbooru-tag generation from generated images
- Preset sharing via URL code

