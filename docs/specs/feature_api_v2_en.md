---
render_with_liquid: false
---

# anima_pipeline API Reference (v2)

## Meta

- Status: Implemented
- Version: v2
- Last Updated: 2026-03-24
- Target release: v1.5.01 (post-refactor)

---

## Overview

v2 reflects the current routing after the `core/handlers.py` refactor.  
Keep v1 (`feature_api_v1_en.md`) as a legacy reference for the v1.4.7-era API, and use this v2 document for current behavior.

---

## Key Changes (v1 -> v2)

| v1 | v2 |
|---|---|
| `GET/POST /settings` | `GET/POST /config` |
| `POST /regenerate` | `POST /regen` |
| `POST /save_session`, `GET /last_session` | `POST/GET /session` |
| `GET /lora_thumb` | `GET /lora_thumbnail` |
| `GET /workflow_list` | `GET /workflows` |
| `GET /connection_test`, `GET /llm_connection_test` | `GET /test_connection?target=comfyui|llm` |
| `GET /gallery_images` | Operationally replaced by `GET /poll_status` + `GET /history_list` |

---

## Endpoint Reference

### Generation

#### `POST /generate`
- Runs generation (with/without LLM, multi-image, LoRA, extra tags, negative prompt, workflow selection)
- Typical inputs: `input`, `use_llm`, `width`, `height`, `fmt`, `count`, `extra_tags`, `char_direct_tags`, `prompt_prefix`, `negative_prompt`, `gen_params`, `lora_slots`, `workflow_file`, `client_id`
- Typical outputs: `comfyui_sent`, `prompt_ids`, `prompt_id`, `positive_prompt`, `pre_extra_prompt`, `final_prompt`, `negative_prompt`, `error`, `comfyui_error`

#### `POST /regen`
- Re-sends a prepared prompt to ComfyUI (re-generate flow)
- Typical inputs: `prompt`, `width`, `height`, `fmt`, `count`, `extra_tags`, `extra_note_en`, `prompt_prefix`, `negative_prompt`, `gen_params`, `lora_slots`, `workflow_file`, `client_id`
- Typical outputs: `prompt_ids`, `prompt_id`, `final_prompt`, `negative_prompt`

#### `POST /cancel`
- Interrupts generation and clears queue in ComfyUI
- Output: `{ "ok": true, "warn": "..." }` (`warn` is optional)

---

### Configuration / Status

#### `GET /config`
- Returns current config

#### `POST /config`
- Saves config
- Output: `{ "ok": true }`

#### `GET /version`
- Returns app version

#### `GET /diagnostics`
- Returns setup diagnostics
- Output: `status`, `results[]`, `summary { errors, warnings }`

#### `GET /test_connection?target=comfyui|llm`
- Connectivity test for ComfyUI or LLM
- Output: `{ "ok": boolean, "message": string }`

---

### Workflow / LoRA / Tags

#### `GET /workflows`
- Lists JSON files in `workflows/`
- Output: `{ "files": ["...json"] }`

#### `GET /lora_list`
- Returns available LoRAs

#### `GET /lora_thumbnail?name=<lora_name>`
- Serves LoRA thumbnail (`204` when not found)

#### `GET /extra_tags`, `POST /extra_tags`
#### `GET /style_tags`, `POST /style_tags`
#### `GET /neg_extra_tags`, `POST /neg_extra_tags`
#### `GET /neg_style_tags`, `POST /neg_style_tags`
- Loads/saves tag presets

---

### Presets

#### `GET /presets/<category>`
- Lists preset names in a category

#### `GET /presets/<category>/<name>`
- Loads one preset

#### `POST /presets/<category>/<name>`
- Saves one preset

#### `DELETE /presets/<category>/<name>`
- Deletes one preset

Supported categories: `chara`, `scene`, `camera`, `quality`, `lora`, `composite`, `positive`, `negative`

#### Legacy Compatibility

The following routes remain for compatibility:
- `GET /chara_list`
- `GET /chara_load?name=...`
- `POST /chara_save`
- `POST /chara_delete`

---

### Character Presets (thumbnail + generator)

#### `GET /chara_presets`
- Returns character presets (`_filename`, `_thumb_path` included)

#### `POST /chara_presets`
- Save/delete character preset (internal action-based handler)

#### `POST /chara_preset_thumb`
- Generates a character preset thumbnail from an image

#### `GET /chara_thumb?file=<preset.json>`
- Returns character preset thumbnail (WebP)

#### `GET /generate_preset?...`
- Auto-generates character preset data using Danbooru + LLM

---

### Session

#### `GET /session`
- Loads last session (`settings/anima_session_last.json`)

#### `POST /session`
- Saves last session

#### `GET /sessions`
- Lists named sessions

#### `GET /sessions/<name>`
- Loads one named session

#### `POST /sessions/<name>`
- Saves one named session (`overwrite` supported on conflict)

#### `DELETE /sessions/<name>`
- Deletes one named session

---

### History / Gallery

#### `GET /history_list?page=&per_page=&favorite=&workflow=&tag=`
- Returns history list (SQLite-backed)

#### `GET /history_detail?id=`
- Returns one history item

#### `POST /history_update`
- Updates `favorite` / `tags`

#### `POST /history_delete`
- Deletes one/all history records (`all`, `keep_favorites`)

#### `GET /poll_status?ids=<id1,id2,...>`
- Returns completion status, image paths, and queue status

---

### Binary / Utility

#### `GET /get_image?path=...`
- Serves image binary (with safe path checks)

#### `GET /open_folder?path=...`
- Opens folder via OS shell

#### `GET /logs_info`
- Returns log settings and location

#### `GET /logs_zip`
- Downloads logs as ZIP

---

### Static

#### `GET /`
#### `GET /manifest.json`
#### `GET /favicon.ico`, `GET /favicon-light.ico`, `GET /favicon-dark.ico`
#### `GET /assets/*`
#### `GET /frontend/*`

---

## HTTP Status (Typical)

| Status | Typical case |
|---|---|
| 200 | Success |
| 204 | Thumbnail not found (`/lora_thumbnail`) |
| 400 | Invalid parameters |
| 404 | Resource not found |
| 409 | Named-session save conflict |
| 500 | Internal error |

