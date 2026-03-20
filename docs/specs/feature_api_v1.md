---
render_with_liquid: false
---

# anima_pipeline API仕様書

## Meta

- Status: Implemented
- Version: v1
- Last Updated: 2026-03-20
- 対象バージョン: v1.4.7（正式リリース）

---

## 概要

anima_pipeline は `http://localhost:7860` でHTTPサーバーを起動し、以下のAPIを提供します。フロントエンド（ブラウザUI）との通信はすべてJSONまたはバイナリで行われます。ComfyUIとのやり取りはサーバー側が仲介します。

---

## エンドポイント一覧

### 生成・送信系

#### `POST /generate`

UIから入力された情報を受け取り、LLMでプロンプトを生成（オプション）してComfyUIに送信します。

**Request Body（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `use_llm` | boolean | LLMを使用するかどうか |
| `charas` | array | キャラ情報の配列（後述） |
| `scene` | object | シーン・雰囲気情報 |
| `params` | object | 生成パラメータ（seed / steps / cfg / sampler / scheduler） |
| `loras` | array | LoRAスロット情報（name / strength） |
| `positive_extra` | object | ポジティブプロンプト調整情報 |
| `negative_extra` | object | ネガティブプロンプト調整情報 |
| `workflow_path` | string | ワークフローJSONのパスまたはファイル名 |
| `image_size` | string | 画像サイズ（例: `"1024x1024"`） |
| `image_format` | string | 出力フォーマット（`"png"` / `"webp"`） |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `llm_prompt` | string | LLMが生成したプロンプト（LLM使用時のみ） |
| `positive_prompt` | string | ComfyUIに送信したポジティブプロンプト |
| `negative_prompt` | string | ComfyUIに送信したネガティブプロンプト |
| `error` | string | エラー時のメッセージ |

---

#### `POST /regenerate`

直前の生成と同じプロンプトをComfyUIに再送信します。プロンプト調整欄の変更は反映されます。

**Request Body（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `positive_extra` | object | ポジティブプロンプト調整情報（再生成時に上書き） |
| `negative_extra` | object | ネガティブプロンプト調整情報（再生成時に上書き） |

**Response:** `/generate` と同形式

---

### 設定・状態系

#### `GET /settings`

現在の設定（`settings/pipeline_config.json`）を返します。

**Response（JSON）:** `pipeline_config.json` の内容そのまま

---

#### `POST /settings`

設定を保存します（`settings/pipeline_config.json` に書き込み）。

**Request Body（JSON）:** 保存したい設定フィールドを含むオブジェクト

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |

---

#### `GET /connection_test`

ComfyUIへの接続を確認します。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `python_version` | string | ComfyUI側のPythonバージョン（成功時） |
| `error` | string | エラー時のメッセージ |

---

#### `GET /llm_connection_test`

LLM APIへの接続を確認します。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `error` | string | エラー時のメッセージ |

---

### キャラプリセット系

#### `GET /chara_presets`

`chara/` フォルダ内のプリセット一覧を返します。

**Query Parameters**

| パラメータ | 型 | 説明 |
|----------|---|------|
| `_ts` | number | キャッシュバスティング用タイムスタンプ（任意） |

**Response（JSON）:** プリセット情報の配列

| フィールド | 型 | 説明 |
|-----------|---|------|
| `name` | string | プリセット名（ファイル名から拡張子を除いたもの） |
| `_thumb_path` | string \| null | サムネイルのパス（存在する場合） |

---

#### `POST /save_chara_preset`

キャラプリセットを保存します。

**Request Body（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `name` | string | プリセット名 |
| `data` | object | プリセットの内容 |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |

---

#### `POST /delete_chara_preset`

キャラプリセットを削除します。同名の `.webp` サムネイルも削除されます。

**Request Body（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `name` | string | 削除するプリセット名 |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |

---

#### `POST /chara_preset_thumb`

ギャラリー画像をもとにプリセットのサムネイルを生成します（`chara/<name>.webp` として保存）。

> **Added:** v1.4.7

**Request Body（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `preset_name` | string | サムネイルを紐付けるプリセット名 |
| `view_url` | string | サムネイルにする画像のURL（ComfyUI view URL またはローカルパス） |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `thumb_path` | string | 保存されたサムネイルのパス（成功時） |
| `error` | string | エラー時のメッセージ |

---

#### `GET /chara_thumb`

プリセットのサムネイル画像（WebP）を配信します。

> **Added:** v1.4.7

**Query Parameters**

| パラメータ | 型 | 説明 |
|----------|---|------|
| `file` | string | プリセット名（拡張子なし） |

**Response:** WebP バイナリ（`Content-Type: image/webp`）

---

### LoRA系

#### `GET /lora_list`

ComfyUIのLoRAフォルダをスキャンして利用可能なLoRAの一覧を返します。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `loras` | array | LoRAファイル名の配列 |

---

#### `GET /lora_thumb`

LoRAのサムネイル画像を返します。ComfyUI outputフォルダが設定されている場合に機能します。

**Query Parameters**

| パラメータ | 型 | 説明 |
|----------|---|------|
| `name` | string | LoRAファイル名 |

**Response:** 画像バイナリ

---

### ワークフロー系

#### `GET /workflow_list`

`workflows/` フォルダ内のJSONファイル一覧を返します。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `workflows` | array | ワークフローファイル名の配列 |

---

#### `GET /workflow_node_ids`

指定したワークフローJSONからPositive / Negative / KSamplerのNode IDを自動検出して返します。

**Query Parameters**

| パラメータ | 型 | 説明 |
|----------|---|------|
| `file` | string | ワークフローファイル名 |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `positive_node_id` | string | 検出されたPositiveノードのID |
| `negative_node_id` | string | 検出されたNegativeノードのID |
| `ksampler_node_id` | string | 検出されたKSamplerノードのID |

---

### セッション系

#### `POST /save_session`

現在の入力内容をJSONファイルとして保存します。

**Request Body（JSON）:** セッション全体のデータオブジェクト

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `path` | string | 保存されたファイルのパス |

---

#### `GET /last_session`

最後に自動保存されたセッション（`settings/anima_session_last.json`）を返します。

**Response（JSON）:** セッションデータオブジェクト

---

### ログ系

#### `GET /logs_info`

ログの保存場所・件数・サイズ等の情報を返します。

> **Added:** v1.4.7

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `log_dir` | string | ログ保存フォルダのパス |
| `log_level` | string | 現在のログレベル（`normal` / `debug`） |
| `retention_days` | number | ログ保持日数 |
| `file_count` | number | ログファイルの件数 |
| `total_size_bytes` | number | ログファイルの合計サイズ（バイト） |

---

#### `GET /logs_zip`

ログフォルダをZIP圧縮してダウンロードします。

> **Added:** v1.4.7

**Response:** ZIPファイル（`Content-Type: application/zip`、`Content-Disposition: attachment`）

---

### ギャラリー系

#### `GET /gallery_images`

現在のセッションのギャラリー画像一覧を返します。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `images` | array | 画像情報の配列（view_url / positive_prompt / negative_prompt を含む） |

---

## WebSocket

#### `ws://localhost:7860/ws`

ComfyUIの生成進捗をリアルタイムで受信します。

**受信メッセージ（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `type` | string | `"progress"` / `"done"` / `"error"` |
| `progress` | number | 進捗率（0〜100）。`type: "progress"` 時のみ |
| `message` | string | ステータス文言 |

---

## 設定ファイル（pipeline_config.json）の主なキー

| キー | 型 | デフォルト | 説明 |
|-----|----|----------|------|
| `comfyui_url` | string | `http://127.0.0.1:8188` | ComfyUI のURL |
| `workflow_path` | string | `image_anima_preview.json` | ワークフローJSONのパス（フォールバック） |
| `positive_node_id` | string | `11` | PositiveプロンプトノードのID |
| `negative_node_id` | string | `12` | NegativeプロンプトノードのID |
| `ksampler_node_id` | string | `19` | KSamplerノードのID |
| `llm_platform` | string | `""` | LLMプラットフォーム（`lmstudio` / `gemini` / `custom` / 空文字） |
| `llm_url` | string | `""` | LLM APIのベースURL |
| `llm_token` | string | `""` | LLM APIのトークン（マスク対象） |
| `llm_model` | string | `""` | 使用するLLMモデル名 |
| `output_folder` | string | `""` | ComfyUI outputフォルダの絶対パス |
| `console_lang` | string | `""` | コンソール表示言語（OSに追従） |
| `log_dir` | string | `logs/` | ログ保存先フォルダ |
| `log_retention_days` | number | `30` | ログ保持日数 |
| `log_level` | string | `normal` | ログレベル（`normal` / `debug`） |

---

## エラーコード早見表

| HTTPステータス | 主な原因 |
|-------------|--------|
| 200 | 正常 |
| 400 | リクエスト不正（パラメータ誤り、ワークフローノード未検出など） |
| 404 | 指定リソースが存在しない（プリセット・ワークフロー・サムネイルなど） |
| 500 | サーバー内部エラー（ComfyUI未起動、LLM接続失敗など） |
