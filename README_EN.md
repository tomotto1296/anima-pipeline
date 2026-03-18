# anima_pipeline

This is a pipeline tool that allows you to enter character and scene information via a browser UI → automatically generate Danbooru prompts using an LLM (optional) → and automatically send them to the ComfyUI Anima workflow.
[Back to Japanese README → README.md](README.md)
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

## Main Features

- Automatically generate Danbooru tags from character names and work titles using an LLM
- Fine-tune details such as hairstyle, hair color, eyes, mouth, expressions, outfits, and poses via the UI
- LoRA injection (card grid UI, thumbnail display, up to 4 slots)
- Workflow switching (select from the `workflows/` folder)
- Preset management for quality tags and style tags in positive/negative prompts
- Simultaneous configuration of multiple characters
- Automatic session saving and restoration
- Gallery and generated image preview
- WebP conversion of generated images (optional)
- Support for smartphones and tablets (on the same Wi-Fi network)

---

## File Structure

```
anima_pipeline/
  anima_pipeline.py              ← Main script
  start_anima_pipeline.bat       ← For Windows startup
  requirements.txt               ← Dependency libraries
  README.md
  anima_pipeline_guide.md        ← Detailed guide
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

Please refer to [anima_pipeline_guide.md](anima_pipeline_guide.md).


Translated with DeepL.com (free version)