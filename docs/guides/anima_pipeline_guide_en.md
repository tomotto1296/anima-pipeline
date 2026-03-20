# anima_pipeline User Guide

## Overview

anima_pipeline is a pipeline tool that takes character and scene information entered through a browser UI, optionally generates Danbooru-style prompts automatically using an LLM, and sends them to a ComfyUI Anima workflow for image generation.

---

## Requirements

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Run the server |
| requests | (pip install requests) | HTTP library (auto-installed on first run) |
| ComfyUI | 0.16.4+ | Image generation |
| Anima workflow | — | ComfyUI workflow file |
| LLM server (LM Studio, etc.) | — | Auto prompt generation (**optional**) |

---

## File Structure

Distribution package:

```
anima_pipeline/
  anima_pipeline.py              ← Main script
  start_anima_pipeline.bat       ← Windows launcher batch file
  anima_pipeline_guide_en.md     ← This file
  image_anima_preview.json       ← Anima workflow for ComfyUI (see below)
  chara/
    000_default.json             ← Default character preset (all fields empty)
  workflows/                     ← Folder for workflow JSON files (auto-created)
    image_anima_preview.json       ← Standard workflow (no LoRA)
    image_anima_preview_Lora4.json ← Workflow supporting up to 4 LoRAs
  settings/
    pipeline_config.json         ← Config (ComfyUI URL, Node IDs, etc.) — exclude from git after entering API keys
    pipeline_config.default.json ← Default config template (for git)
    ui_options.json              ← UI button options (editable)
    llm_system_prompt.txt        ← System prompt for LLM (editable)
    preset_gen_prompt.txt        ← Prompt for auto character preset generation (editable)
```

Files auto-generated after first launch (not included in distribution):

```
  settings/
    pipeline_config.json         ← Saved settings (overwritten from distribution defaults)
    extra_tags.json              ← Positive extra tag presets
    extra_tags_negative.json     ← Negative extra tag presets
    style_tags.json              ← Style tag presets
    anima_session_last.json      ← Auto-save of the last session
```

> **About `image_anima_preview.json`**
> This file is not included in the repository. Follow the steps below to export it from your ComfyUI environment and place it in the same folder as `anima_pipeline.py`.
>
> 1. Launch ComfyUI
> 2. Open the menu (top-right ≡) → "Browse Templates"
> 3. Select and load the **Anima** template
> 4. Go to menu → "Save (API Format)" and save as `image_anima_preview.json`
> 5. Place the saved file in the same folder as `anima_pipeline.py`

---

## How to Launch

### Windows
Double-click `start_anima_pipeline.bat`

> **If the .bat file opens in VS Code or another editor:** Right-click → "Open with" → "Command Prompt", or right-click → "Run as administrator".
>
> On first launch, if the `requests` library is not installed, it will be installed automatically.

### Manual launch
```bash
python anima_pipeline.py
```

After launch, open `http://localhost:7860` in your browser.

### Accessing from a smartphone or tablet (v1.4.1+)

You can access anima_pipeline from a smartphone or tablet on the same Wi-Fi network as your PC.

**Steps:**

1. Run `ipconfig` (Windows) on your PC and note the **IPv4 Address** (e.g., `192.168.1.10`)
2. Launch ComfyUI with the following arguments (`--listen` and `--enable-cors-header` are required):

```
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --lowvram --listen --enable-cors-header
```

3. Launch anima_pipeline as usual
4. Open `http://192.168.1.10:7860` in your mobile browser (use the IP from step 1)

> **Note:** Always type `http://` at the start of the address. Using `https://` will cause an SSL error.
>
> LoRA thumbnails require the ComfyUI output folder to be configured (see Settings panel).

---

## Initial Setup

Open the "▶ Settings" panel at the top of the page to review and fill in the required fields. Settings are saved to `settings/pipeline_config.json` by clicking "💾 Save Settings".

> **②③④ already have the default values for the standard Anima workflow.** Only change them if you are using a different workflow.

> **Note:** On first launch, the LLM platform is set to "None". If you want to use LLM features, select a platform in the Settings panel and click "💾 Save Settings". Settings are also auto-saved every time you click the Generate button.

### 🔴 Required

| # | Setting | Default | Description |
|---|---------|---------|-------------|
| ① | Workflow JSON path (fallback) | `image_anima_preview.json` | Used when no workflow is selected in `workflows/`. Accepts a full path or just a filename. |
|   | Workflow selector (priority) | — | Select a JSON from the `workflows/` folder via dropdown. Use 🔄 to rescan. When selected, this takes priority and **Node IDs are auto-detected** (verify manually if ControlNet nodes are present). |
| ② | Positive Node ID | `11` | Standard for Anima workflow. Check for other workflows. |
| ③ | Negative Node ID | `12` | Standard for Anima workflow. Check for other workflows. |
| ④ | KSampler Node ID | `19` | ID of the KSampler node for seed/steps/cfg/sampler injection. |
| ⑤ | ComfyUI URL | `http://127.0.0.1:8188` | Only change if you modified the default. |

### 🟠 Required for LLM

Select ⑥ **LLM Platform** to expand the URL, Token, and Model Name fields.

| Platform | Description |
|----------|-------------|
| **None** | Do not use LLM. Text is entered directly. |
| **LM Studio** | Local LLM. Free and unlimited, but requires a high-end PC. |
| **Gemini** | Google Gemini API. Free tier available (API key required; no credit card needed). |
| **Custom** | Manually configure any other OpenAI-compatible API. |

> **LLM platform requirement:** The service must support an OpenAI-compatible API (`/v1/chat/completions`). Please check each service's terms, pricing, and rate limits yourself.

| # | Setting | Description |
|---|---------|-------------|
| ⑤-1 | LLM URL | Base URL for the API |
| ⑤-2 | LLM API Token | Enter only if authentication is required. Leave blank for local (LM Studio). |
| ⑤-3 | LLM Model Name | Identifier of the model to use |

### 🟢 Optional

| # | Setting | Description |
|---|---------|-------------|
| ⑦ | LLM tool integrations | Toggle Danbooru RAG / Danbooru API / DuckDuckGo ON/OFF (LM Studio only) |
| ⑧ | ComfyUI output folder | Used for WebP conversion. **Absolute path recommended** (e.g., `D:\ComfyUI_Portable\ComfyUI\output`). If left blank, auto-detection is attempted but may fail when the workflow JSON is specified by filename only. |

### 🔧 Debug

Located at the bottom of the Settings panel.

| Function | Description |
|----------|-------------|
| 🔌 ComfyUI Connection Test | Tests connectivity to ComfyUI. Displays Python version on success. |
| 🤖 LLM Connection Test | Tests connectivity to the LLM API. Verifies URL and API key. |
| 📋 Delete Character Preset | Deletes character presets (placed in Settings to prevent accidental deletion). |

---

## 💡 Recommended Workflow

**The fastest method is to type English tags directly and skip the LLM.**

1. Uncheck "Use LLM"
2. Uncheck all LLM checkboxes in the detail fields
3. Enter English tags directly and click "▶ Generate"

LLM is most useful when you want it to **automatically look up Danbooru tags from a character name or series title**.

### Input field color coding

| Color | Meaning |
|-------|---------|
| 🔵 Blue | Japanese OK (LLM will interpret and convert to English tags) |
| 🟢 Green | English only (enter Danbooru tags or English text directly) |

---

## Using a Different Workflow

To use a non-Anima workflow or a different variant:

1. Open the workflow in ComfyUI and **save it via "Save (API Format)"**
2. Update "① Workflow JSON path" to point to the new JSON
3. Update "② Positive Node ID" and "③ Negative Node ID" to match the new workflow
4. Click "💾 Save Settings"

> To find a Node ID: right-click a prompt node in ComfyUI → "Properties" → check the Node ID

---

## Basic Usage

### A. Enter Character Information

**Character Presets** (top of each character block)
- Save and recall frequently used character settings as presets.
- Stored in: `anima_pipeline/chara/` (one file per preset)
- **Save**: Save the current character block's settings under a preset name
- **Load**: Apply the selected preset to the current character block
- **🔍**: Auto-generate a preset from a character name and series using Danbooru Wiki + LLM (requires LLM setup)
  - The generation prompt is editable in `settings/preset_gen_prompt.txt`
  - If the character is not on the Wiki, LLM knowledge alone is used (generally accurate for well-known characters)
  - Recommended: review and manually edit after auto-generation, then re-save
- **Deletion is done from "Character Preset Delete" inside the "▶ Settings" panel** (to prevent accidental deletion)
- `chara/000_default.json` is included as the initial preset (all fields empty)
- **LLM checkbox states are not saved in presets.** Set them manually after loading.

**Character Name / Series** (blue field — Japanese OK)
- With LLM: the LLM searches Danbooru and generates tags from the character name and series
- Without LLM: the name and series are auto-converted to `name_(series)` format and added to the prompt (English input recommended)
- For **original characters**: click the "Original" button → the Series field is disabled and all LLM checkboxes are turned OFF
- Use the "＋" button on a character block to set up multiple characters at once

**Gender / Age** (options configurable in `ui_options.json`)
- LLM checkbox ON: LLM determines the value
- LLM checkbox OFF: the selected value is converted directly to a Danbooru tag (`1girl` / `1boy`, etc.)

### B. Enter Details (Optional)

Click "＋ Details" to expand.

| Field | Description |
|-------|-------------|
| ① Hair style | Single selection from Overall / Front / Back groups. Free-text field accepts Japanese. |
| ② Hair color | Select from dropdown (25 colors). Enter other colors in free-text field in Japanese. |
| ③ Eye state | Open/closed (single), direction, and condition groups |
| ④ Eye color | Select from dropdown (20 colors). Use the "odd" button for heterochromia (set each eye individually). |
| ⑤ Mouth | Multiple selection |
| ⑥ Expression | Multiple selection |
| ⑦ Skin tone | Select from dropdown (color swatches). Enter unusual skin tones in free-text field in Japanese. |
| ⑧ Outfit | Select a category (bare / half-bare / full / top+bottom) to expand color and type options. Top and bottom are set individually. |
| ⑨ Bust | Shown for female and unknown gender only |
| ⑩–⑫ | Height / Build / Legs |
| ⑬ Accessories | Ears / Tail / Wings (single selection), Accessories (multiple) |
| ⑭ Effects | Sweat / Tears / Aura / Blood, etc. — multiple selection |
| ⑮ Action / Pose | Posture / Action / Arms & Hands / Gaze groups — multiple selection. Free-text field uses **English tags directly**. |
| ⑯ Props | Enabled by toggling "Hold". Free-text uses **English tags directly**. |
| ⑰–⑲ | Vertical framing / Horizontal framing / Camera angle |

**About LLM checkboxes**
- ON → the field value is passed to the LLM for tag generation
- OFF → the selected value is converted directly to a Danbooru tag (fast and reliable)

### C. Set Scene / Atmosphere (Optional)

Displayed as a separate block below the character(s).

| Field | Options |
|-------|---------|
| World | Everyday / Japanese / Western / Chinese / Fantasy / Sci-Fi / Ruins |
| Location | Select from Outdoor / Indoor / Special categories, or enter in free-text (blue — **Japanese OK**) |
| Time of day | Morning / Noon / Evening / Night |
| Weather | Clear / Cloudy / Rain / Snow |
| Memo (Japanese) | Atmosphere hint for the LLM. **Only applied on the first generation.** |

### D. Generation Parameters (Optional)

Adjust KSampler settings in the "▶ Generation Parameters" section.

| Setting | Description |
|---------|-------------|
| Seed | Random / Fixed / Sequential. Click 🎲 to generate a random value. |
| Steps | Sampling steps (default: 30) |
| CFG | CFG scale (default: 4) |
| Sampler | Sampler name (dropdown) |
| Scheduler | Scheduler name (dropdown) |

> Sampler and Scheduler options can be changed in `settings/ui_options.json` under `sampler_options` / `scheduler_options`.

### E. LoRA (Optional)

Configure LoRA selection and strength in the "▶ LoRA" section.

- Click 🔄 to scan ComfyUI's LoRA folder
- Up to 4 slots available. Set the LoRA file and strength (0–2) per slot.
- Empty slots are skipped
- Injects into `LoraLoader` nodes in the workflow in order
- Use a workflow that includes LoraLoader nodes (e.g., `image_anima_preview_Lora4.json`) when using LoRAs
- If there are more LoraLoader nodes than filled slots, excess nodes are bypassed (auto-disabled) before sending
- The number of LoraLoader nodes in the workflow is the effective slot limit (`image_anima_preview_Lora4.json` supports up to 4)

> Session save/restore is supported for LoRA settings as well.

### F. Positive Prompt Adjustments / Additions (Optional)

"▶ Prompt Adjustments / Additions" section. **Changes here are also applied on re-generation.**

| # | Field | Description |
|---|-------|-------------|
| ① | Era tags | Optimization tags for the Anima model (inserted at the beginning) |
| ② | Quality tags | masterpiece / score_9, etc. |
| ③ | Meta tags | highres / absurdres, etc. |
| ④ | Safety tag | safe / nsfw, etc. (single selection) |
| ⑤ | Style | @artist_name. **Can be registered as a preset.** Right-click to delete. |
| ⑥ | Extra tags | Can be registered as presets. Right-click to delete. Persisted in `settings/extra_tags.json`. |
| ⑦ | Append text (English) | English text appended directly to the end of the prompt (green field). |

### G. Negative Prompt Adjustments (Optional)

"Negative Prompt Adjustments" section (red border).

| # | Field | Notes |
|---|-------|-------|
| ① | Era tags | Shared with positive |
| ② | Quality tags | Human-based: NORMAL/LOW/WORST (default ON); Pony (default OFF) |
| ③ | Meta tags | Default OFF |
| ④ | Safety tag | Shared with positive |
| ⑤ | Style | Shared with positive |
| ⑥ | Extra tags | Negative-specific presets. Persisted in `settings/extra_tags_negative.json`. |
| ⑦ | Append text (English) | Appended directly to the end of the negative prompt |

### H. Generate

**With LLM:**
1. Confirm "Use LLM" is checked
2. Click "▶ Generate" (or press Ctrl+Enter)
3. LLM generates the prompt → sent to ComfyUI → image is generated

**Without LLM:**
1. Uncheck "Use LLM"
2. Click "▶ Generate"
3. All fields are sent directly as Danbooru tags regardless of LLM checkbox states (faster)
   - Character name and series are auto-converted to `name_(series)` format
   - Scene information (location, time of day, weather, etc.) is included automatically

After generation, the Status section displays:
- **LLM-generated positive prompt** — what the LLM produced
- **ComfyUI positive prompt sent** — the final prompt sent to ComfyUI (with copy button)
- **ComfyUI negative prompt sent** — the negative side (red text, with copy button)

---

## Gallery (Generation History)

After generation, "📷 Generation History (this session)" appears at the bottom of the page.

- Click a thumbnail to enlarge the image
- View the positive and negative prompts from the enlarged view
- "↺ Reuse Prompt" sets the prompts for re-generation mode
- "📁 Open folder" opens the image's save folder in Explorer (requires output folder setting)
- "Clear" button deletes the session's history

> The gallery is only retained within the current session. It resets on restart.

---

## Re-generation

Click "↻ Re-generate" to resend the previous prompts to ComfyUI.
Changes in the positive and negative prompt adjustment fields are reflected in re-generation.

---

## Floating Navigation

Navigation buttons displayed on the right side of the screen (when the window is wide enough). Click to smoothly scroll to each section.

| Button | Target |
|--------|--------|
| 🖼 Image | Image settings |
| ⚙ Params | Generation parameters |
| 🎭 Chara | Characters |
| 🌍 Scene | Scene / Atmosphere |
| ✨ Pos | Prompt adjustments |
| 🚫 Neg | Negative prompt adjustments |
| 📋 Status | Status / Gallery |
| ↑ TOP | Top of page |

---

## Style Tag Preset Management

Reuse artist styles across multiple characters and sessions.

1. Enter a style such as `takeuchi naoko` in the style field (green) and click "Add"
2. It is registered as a preset button (saved to `settings/style_tags.json`)
3. From then on, click the preset to toggle it ON/OFF
4. Right-click a preset to delete it

---

## Customizing Image Size

Edit `image_size_presets` in `settings/ui_options.json` to change the dropdown options.

```json
"image_size_presets": [
  {"v": "1024x1024", "label": "1024 × 1024  Square"},
  {"v": "1920x1080", "label": "1920 × 1080  Full HD Landscape"}
]
```

---

## WebP Output

**Note:** When WebP format is selected, the PNG generated by ComfyUI is automatically converted to WebP immediately after generation.
**The embedded prompt and workflow data inside the PNG will be discarded after conversion.**
Use PNG format if you need to preserve workflow information.

---

## Session Save / Load

- "💾 Save Session": saves all current input as a JSON file
- "📂 Open": loads a previously saved JSON
- The last state is auto-saved to `settings/anima_session_last.json` and restored automatically on the next launch

---

## Customizing the LLM System Prompt

Directly edit `settings/llm_system_prompt.txt` to change the instructions sent to the LLM.
Changes take effect on the next generation (no restart required).

Edit `settings/preset_gen_prompt.txt` to change the instructions for auto character preset generation.
Do not remove the placeholders `{chara_name}` / `{chara_series}` / `{wiki_text}`.

---

## Customizing UI Buttons

Edit `settings/ui_options.json` to change nearly all button options.
Changes take effect after restarting the script.

Key sections:
- `image_size_presets` — image size presets
- `scene_world` / `scene_tod` / `scene_weather` — world / time of day / weather
- `gender_options` / `age_options` — gender and age
- `quality_human` / `quality_pony` / `meta_tags` — quality and meta tags with defaults
- `quality_human_neg` — negative quality tags
- `outfit_data` — outfit colors and types
- and more

---

## UI Language Switch

From v1.4.7, the UI can be switched between Japanese and English.

- On launch, the initial language is detected from the OS language (Japanese OS → Japanese UI, others → English UI)
- Use the language toggle buttons (**JA / EN**) at the top of the page to switch at any time
- The setting is saved in the browser and carried over to the next session

> **Note:** Some dynamically generated labels (such as STATUS messages) are re-rendered after switching.

---

## Logging

From v1.4.7, runtime logs are automatically saved. Useful for diagnosing issues in distributed environments.

### Storage and Default Settings

| Config key | Default | Description |
|-----------|---------|-------------|
| `log_dir` | `anima-pipeline/logs/` | Log storage folder |
| `log_retention_days` | `30` | Days to retain logs (older files are auto-deleted) |
| `log_level` | `normal` | `normal` or `debug` |

Settings can be changed in `settings/pipeline_config.json`.

### Security: Sensitive Data Masking

Values containing the following keywords are automatically masked in log output:

- `token`
- `api key`
- `authorization`
- `bearer`

### Settings Panel UI

The following controls appear at the bottom of the Settings panel:

| Control | Description |
|---------|-------------|
| LOG DIRECTORY | Path to the log storage folder |
| LOG RETENTION DAYS | Number of days to keep logs |
| LOG LEVEL | Log level (normal / debug) |
| OPEN LOGS | Open the log folder in Explorer |
| EXPORT LOGS ZIP | Download logs as a ZIP archive |

---

## Preset Thumbnail Gallery

From v1.4.7, character presets can be displayed with thumbnail images.

### Creating a Thumbnail

1. After generating an image, enlarge it in the gallery (generation history)
2. Click the "Create Preset Thumbnail" button
3. Select the target preset and confirm
4. The thumbnail is saved as `chara/<preset_name>.webp`

### Adding a Character from the Gallery

1. Expand "Preset Gallery" in the character section
2. Click a thumbnail to select a preset
3. Use the "Target" selector to choose which character slot to update
4. Click "＋ Add Character" to add a new character slot with the selected preset applied

> **Note:** "＋ Add Character" only adds a slot and **sets** the preset — it does not automatically load the preset content. Use the "Load" button separately to apply it.

- Thumbnails are loaded lazily (only when the gallery is expanded), keeping mobile initial load lightweight
- Presets without a thumbnail are not shown in the grid

---

## Troubleshooting

| Symptom | What to check |
|---------|--------------|
| .bat file opens in VS Code or another editor | Right-click → "Open with" → "Command Prompt" |
| `No module named 'requests'` error | Run `pip install requests`, or right-click the .bat → "Run as administrator" |
| Not sent to ComfyUI | Verify ComfyUI URL and workflow JSON path |
| "Positive node XXX not found" on custom workflow | Make sure you exported using "Save (API Format)". Auto-resolved from v1.4.3+. |
| Negative prompt not applied | Check that "③ Negative Node ID" is set correctly |
| LLM not responding | Make sure the LLM server is running. Verify model name and URL. |
| Image not displayed / WebP conversion fails | Enter an absolute path for ComfyUI output folder. Auto-detection may fail when the workflow JSON is specified by filename only. |
| MCP tools not working | Check the MCP plugin on the LLM server side, or disable tool integrations in Settings. |
| Session restore is off | Old session files are auto-converted to the new format. If issues persist, a page reload should fix it. |
| LoRA thumbnails not showing | Set the ComfyUI output folder in Settings. Also requires `--listen --enable-cors-header` in ComfyUI launch args. |
| Gallery images not showing from smartphone | ComfyUI must be launched with the `--listen` argument. |
| LLM outputs long thinking text / slow response | See "About Qwen3 thinking output" below. |
| Generated image is all white / full of noise | LLM thinking text may be mixing into the prompt. See "About Qwen3 thinking output" below. |
| UI language won't switch / partial switch | Reload the page. Dynamically generated labels are re-rendered after the next generation action. |
| `ui_options.json` load error (BOM-related) | Resave the file as UTF-8 without BOM. BOM-mixed files are handled from v1.4.7+. |
| Logs not being saved | Verify that the `log_dir` path in `settings/pipeline_config.json` is correct. The folder is created automatically if it does not exist. |

### About Qwen3 thinking output

Qwen3.5 and similar "thinking" models may output lengthy reasoning text before generating the actual prompt, causing slowdowns or text contamination.

**Symptoms:**
- Text like "The user wants me to generate..." appears in the LLM-generated positive prompt
- Generated image is all white or full of noise
- Response is extremely slow

These are caused by Qwen3-series thinking text mixing into the prompt. Fix using one of the methods below.

**Recommended fix (LM Studio):**

Add the following at the top of the "Template" setting in LM Studio's bottom-right panel to disable thinking output:

{% raw %}
```
{%- set enable_thinking = false %}
```
{% endraw %}

This is the most reliable fix as it disables thinking at the model level.

**System prompt fix:**

Add the following at the beginning of `settings/llm_system_prompt.txt` and `settings/preset_gen_prompt.txt`:

```
/no_think
Answer immediately. Do not deliberate.
```

**llama.cpp (including LM Studio) launch argument fix:**

```
--reasoning-budget 256
```

Limits the number of thinking tokens and improves response speed.

### LLM API Error Codes

| Code | Cause | Fix |
|------|-------|-----|
| **400** Bad Request | Wrong model name, or unsupported parameter sent to the API | Check model name. Outside LM Studio, MCP tool integrations may be the cause — try disabling them in Settings. |
| **401** Unauthorized | API key missing or invalid | Enter the correct API key in the Token field and save. |
| **404** Not Found | Model does not exist, or the URL is wrong | Re-check model name and URL. |
| **429** Too Many Requests | Rate limit reached | Wait and retry. If the free-tier limit is exhausted, wait until the next day or switch to a different model. |
| **500** / **503** | Temporary server-side error | Wait and retry. |

---

## Version History

| Version | Summary |
|---------|---------|
| **v1.4.7** | UI language switch (JA/EN), logging system, preset thumbnail gallery, allow 0 characters, BOM read improvement |
| **v1.4.6** | SaveImageExtended support, /no_think added to LLM system prompt |
| **v1.4.5** | Generation progress % display (WebSocket), fixes for duplicate insertions on re-gen, mobile WS connection banner |
| **v1.4.4** | ExtraTag duplicate insertion fix, character block redesign, numbering fix, auto-install of requests |
| **v1.4.3** | Custom workflow (API format JSON) support, auto Node ID detection on workflow select |
| **v1.4.2** | Fixed 400 error when no LoRA / partial LoRA selected (LoraLoader node auto-bypass) |
| **v1.4.1** | Mobile support (major mobile UI overhaul), LoRA thumbnails, section toggles, version display, location tag English fix, code cleanup |
| **v1.4.0** | LoRA injection, workflow selection dropdown, bug fixes |
| **v1.3.0** | Gallery feature, generation parameters section, floating navigation, scene block independence |
| **v1.2.1** | Auto preset generation (Danbooru Wiki + LLM), color dropdowns |
| **v1.2.0** | Character preset feature, connection test, ComfyUI queue display |
| **v1.1.0** | Initial release |
