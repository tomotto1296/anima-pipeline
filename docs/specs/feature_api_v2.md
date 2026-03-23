---
render_with_liquid: false
---

# anima_pipeline API仕様書（v2）

## Meta

- Status: Implemented
- Version: v2
- Last Updated: 2026-03-24
- 対象リリース: v1.5.01（リファクタ後）

---

## 概要

v2 は、`core/handlers.py` のリファクタ後ルーティングに合わせた現行API仕様です。  
v1（`feature_api_v1.md`）は v1.4.7 時点の互換資料として残し、現行実装の参照先は本書（v2）とします。

---

## 主要な差分（v1 -> v2）

| v1 | v2 |
|---|---|
| `GET/POST /settings` | `GET/POST /config` |
| `POST /regenerate` | `POST /regen` |
| `POST /save_session`, `GET /last_session` | `POST/GET /session` |
| `GET /lora_thumb` | `GET /lora_thumbnail` |
| `GET /workflow_list` | `GET /workflows` |
| `GET /connection_test`, `GET /llm_connection_test` | `GET /test_connection?target=comfyui|llm` |
| `GET /gallery_images` | `GET /poll_status` + `GET /history_list` に統合運用 |

---

## Endpoint Reference

### Generation

#### `POST /generate`
- 生成実行（LLMあり/なし、複数枚、LoRA、追加タグ、ネガティブ、ワークフロー指定）
- 主な入力: `input`, `use_llm`, `width`, `height`, `fmt`, `count`, `extra_tags`, `char_direct_tags`, `prompt_prefix`, `negative_prompt`, `gen_params`, `lora_slots`, `workflow_file`, `client_id`
- 主な返却: `comfyui_sent`, `prompt_ids`, `prompt_id`, `positive_prompt`, `pre_extra_prompt`, `final_prompt`, `negative_prompt`, `error`, `comfyui_error`

#### `POST /regen`
- 直前プロンプトを再送（再生成）
- 主な入力: `prompt`, `width`, `height`, `fmt`, `count`, `extra_tags`, `extra_note_en`, `prompt_prefix`, `negative_prompt`, `gen_params`, `lora_slots`, `workflow_file`, `client_id`
- 主な返却: `prompt_ids`, `prompt_id`, `final_prompt`, `negative_prompt`

#### `POST /cancel`
- ComfyUI生成中断とキュークリア
- 返却: `{ "ok": true, "warn": "..." }`（`warn` は任意）

---

### Configuration / Status

#### `GET /config`
- 現在設定を返す

#### `POST /config`
- 設定保存
- 返却: `{ "ok": true }`

#### `GET /version`
- アプリバージョン返却

#### `GET /diagnostics`
- セットアップ自己診断結果を返却
- 返却: `status`, `results[]`, `summary { errors, warnings }`

#### `GET /test_connection?target=comfyui|llm`
- ComfyUI/LLM 接続テスト
- 返却: `{ "ok": boolean, "message": string }`

---

### Workflow / LoRA / Tags

#### `GET /workflows`
- `workflows/` 配下JSON一覧
- 返却: `{ "files": ["...json"] }`

#### `GET /lora_list`
- 利用可能LoRA一覧

#### `GET /lora_thumbnail?name=<lora_name>`
- LoRAサムネイル配信（未検出時は `204`）

#### `GET /extra_tags`, `POST /extra_tags`
#### `GET /style_tags`, `POST /style_tags`
#### `GET /neg_extra_tags`, `POST /neg_extra_tags`
#### `GET /neg_style_tags`, `POST /neg_style_tags`
- タグプリセット取得/保存

---

### Presets

#### `GET /presets/<category>`
- カテゴリ内プリセット名一覧取得

#### `GET /presets/<category>/<name>`
- プリセット本体取得

#### `POST /presets/<category>/<name>`
- プリセット保存

#### `DELETE /presets/<category>/<name>`
- プリセット削除

対応カテゴリ: `chara`, `scene`, `camera`, `quality`, `lora`, `composite`, `positive`, `negative`

#### Legacy Compatibility

以下は互換用の旧ルートです。
- `GET /chara_list`
- `GET /chara_load?name=...`
- `POST /chara_save`
- `POST /chara_delete`

---

### Character Presets (thumbnail + generator)

#### `GET /chara_presets`
- キャラプリセット一覧（`_filename`, `_thumb_path` を含む）

#### `POST /chara_presets`
- キャラプリセット保存/削除（内部運用アクション）

#### `POST /chara_preset_thumb`
- 指定画像からキャラプリセット用サムネイル生成

#### `GET /chara_thumb?file=<preset.json>`
- キャラプリセットサムネイル（WebP）取得

#### `GET /generate_preset?...`
- Danbooru + LLM を使ったキャラプリセット自動生成

---

### Session

#### `GET /session`
- 最終セッション取得（`settings/anima_session_last.json`）

#### `POST /session`
- 最終セッション保存

#### `GET /sessions`
- 名前付きセッション一覧

#### `GET /sessions/<name>`
- 名前付きセッション取得

#### `POST /sessions/<name>`
- 名前付きセッション保存（同名時は `overwrite` 指定可）

#### `DELETE /sessions/<name>`
- 名前付きセッション削除

---

### History / Gallery

#### `GET /history_list?page=&per_page=&favorite=&workflow=&tag=`
- 履歴一覧（SQLite）

#### `GET /history_detail?id=`
- 履歴詳細

#### `POST /history_update`
- `favorite` / `tags` 更新

#### `POST /history_delete`
- 単体削除または一括削除（`all`, `keep_favorites`）

#### `GET /poll_status?ids=<id1,id2,...>`
- 生成完了判定、画像パス、キュー情報を返却

---

### Binary / Utility

#### `GET /get_image?path=...`
- 画像バイナリ取得（安全なパス制約あり）

#### `GET /open_folder?path=...`
- フォルダをOSで開く

#### `GET /logs_info`
- ログ設定と保存先情報

#### `GET /logs_zip`
- ログZIPダウンロード

---

### Static

#### `GET /`
#### `GET /manifest.json`
#### `GET /favicon.ico`, `GET /favicon-light.ico`, `GET /favicon-dark.ico`
#### `GET /assets/*`
#### `GET /frontend/*`

---

## HTTP Status (Typical)

| Status | 典型ケース |
|---|---|
| 200 | 正常 |
| 204 | サムネイル未検出（`/lora_thumbnail`） |
| 400 | パラメータ不正 |
| 404 | リソース未検出 |
| 409 | 名前付きセッション保存時の競合 |
| 500 | 内部エラー |

