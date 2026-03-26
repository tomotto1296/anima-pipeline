# anima_pipeline 使い方ガイド

## 1. 概要

Anima Pipeline はブラウザUIから入力した情報を元に、必要に応じてLLMでプロンプト補助を行い、ComfyUIに送信して画像生成するツールです。

リファクタ後は `anima_pipeline.py` をエントリポイントとして、機能を `core/` と `frontend/` に分割しています。

---

## 2. 動作要件

| 項目 | 推奨 |
|------|------|
| Python | 3.10 以上（`python_embeded/python.exe` がある場合はランチャーが優先使用） |
| 依存ライブラリ | `requests`（+ 履歴サムネ利用時は `Pillow` 推奨） |
| ComfyUI | 起動済み（既定: `http://127.0.0.1:8188`、モバイル利用時は `--listen --enable-cors-header` 推奨） |
| ワークフローJSON | `workflows/` に最低1つ（同梱4種: Anima1/Anima2 + LoRAあり/なし） |

`requirements.txt` の最小依存:

```bash
pip install -r requirements.txt
```

---

## 3. リファクタ後の主な構成

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
    image_anima_preview.json  (例)
  settings/                   (初回起動で自動生成)
  chara/                      (プリセット)
  presets/                    (Scene/Camera/Quality/LoRA/Composite)
  sessions/                   (名前付きセッション保存先)
  assets/                     (favicon / icon / manifest用リソース)
```

---

## 4. 起動方法

### Windows（通常）

`start_anima_pipeline.bat` を実行。

### Windows（Tailscale経由）

`start_anima_pipeline - Tailscale.bat` を実行。

### 直接起動

```bash
python anima_pipeline.py
```

起動後、ブラウザで `http://localhost:7860` を開いてください。

---

## 5. 初回設定（重要）

画面上部の `SETTINGS` セクションで以下を確認してください。

1. `Workflow JSON Path (fallback)`
2. `Select from workflows/ folder (preferred)`
3. `Positive Node ID`
4. `Negative Node ID`
5. `KSampler Node ID`
6. `ComfyUI URL`
7. `History DB Path`（既定: `history/history.db`）
8. `History Thumb Dir`（既定: `history/thumbs`）

`Save Settings` を押すと `settings/pipeline_config.json` に保存されます。

### Setup Diagnostics (SETUP-2)

Settings panel includes `Run Setup Diagnostics` to run checks at once.

- ComfyUI connection
- LLM connection (`SKIP` when not configured)
- Workflow JSON existence/parse
- `Positive/Negative/KSampler` Node ID validation
- LoRA node count
- `Output Directory` check (WebP mode)

The result panel shows `OK / WARN / ERR / SKIP`, and `WARN / ERR` rows include hints.

### プリセット階層（INPUT-4）

`PRESETS` セクションでは、次のカテゴリを独立して保存/読込/削除できます。

- `Scene`
- `Camera`
- `Quality`
- `Lora`
- `Composite`
- `Negative`
- `Positive`

既定プリセット名は次のとおりです。

- `Scene_default`
- `Camera_default`
- `Quality_default`
- `Lora_default`
- `Composite_default`

挙動の要点:

- `Composite` 読込は `snapshot` を優先して復元します（参照名より先に適用）。
- `Camera` はキャラごとの値を `all[]` で保持します。
- 複数キャラ読込時、保存データが不足するキャラは先頭のカメラ値（`posv`/`posh`/`pos_camera`）をフォールバックとして適用します。

### キャラ名・作品名の日英分離（INPUT-12）

- キャラ入力欄は Name JA / Name EN と Series JA / Series EN の4項目を扱えます。
- LLM未使用時のタグ組み立ては EN 欄を優先し、空欄の場合は JA 欄をフォールバックします。
- プリセット自動生成では、日本語のみ入力でも name_en / series_en の補完を試行します。
- キャラプリセット保存名は、JA と EN が両方ある場合 JA（EN） 形式が既定になります。

### ポジティブ/ネガティブプリセット（INPUT-5）

- Prompt セクション上部の Positive Preset で、ポジティブ調整状態を保存/読込/削除できます。
- Negative セクション上部の Negative Preset で、ネガティブ調整状態を保存/読込/削除できます。
- 保存対象には品質タグ・補助タグ・メモ・セーフティ系の選択状態が含まれます。
- 最後に選んだ Positive/Negative プリセットは設定に記録され、再起動後に復元されます。

---

## 6. 出力形式とメタデータ（OUTPUT-4）

`画像設定` の `保存形式` と `メタデータを埋め込む` で挙動を切り替えられます。

- `PNG`:
  - `parameters`（+ `prompt` / `workflow`）を保存
  - ComfyUI再読込でworkflow復元しやすい
- `WebP`:
  - Exif UserComment + XMP にメタデータ保存
  - Civitai投稿向けに軽量
- `メタデータを埋め込む = OFF`:
  - 画像は通常保存（メタデータなし）

運用目安:
- Civitai投稿優先: `WebP`
- ComfyUI再編集優先: `PNG`

補足:
- WebP変換に失敗した場合は PNG で保存されます。
- Civitai `Resources` 検出は、モデル/LoRAのハッシュ一致が前提です。

---

## 7. 生成履歴（セッション履歴 / 全履歴）

- 生成後、画面下部のギャラリーに セッション履歴 が追加されます。
- 全履歴 タブではSQLiteに保存された履歴を参照できます。
- 履歴DB/サムネイルの既定保存先:
  - `history/history.db`
  - `history/thumbs/`
- セッション履歴 の クリア は、セッション表示のみを消します（DBの 全履歴 は消えません）。

---

## 8. 名前付きセッション保存（OUTPUT-8）

- `SAVE SESSION` で現在の入力状態を `sessions/<n>.json` として保存できます。
- `Open` から保存済みセッションを読み込むと、主要入力欄（プロンプト・各種設定）が復元されます。
- 同名が既にある場合は確認ダイアログが表示され、`OK` で上書き、`キャンセル` で中止されます。
- セッション名はファイル名として安全な形式に正規化されます（不正文字は置換）。
- 画面の `Saved Sessions` は保存済み一覧です。`LOAD` で復元、`DELETE` で削除できます。
- 生成時に更新される `last session`（自動保存）と、`SAVE SESSION` の名前付き保存（手動保存）は別管理です。

---
## 9. スマホアクセス（同一LAN）


1. PCのIPv4を確認（例: `192.168.1.103`）
2. PC上で Anima Pipeline を起動
3. スマホで `http://<PCのIPv4>:7860` を開く

接続できない場合:

- PCファイアウォールで 7860 の受信許可を確認
- URLが `https://` ではなく `http://` になっているか確認
- ComfyUI側のCORS設定（必要環境のみ）を確認

---

## 10. 配布時の最小構成

最小構成は次の通りです。

```text
anima_pipeline.py
requirements.txt
core/*.py
frontend/index.html
frontend/i18n.js
workflows/*.json
start_anima_pipeline.bat (または任意の起動手段)
```

推奨追加:

- `assets/icons/*`
- `manifest.json`
- `start_anima_pipeline - Tailscale.bat`

配布に含めない推奨:

- `logs/`, `history/`, `__pycache__/`, `.tmp*`
- 個人環境の `settings/pipeline_config.json`

---

## 11. クイックチェック

詳細は [quick_checks_and_hooks.md](./quick_checks_and_hooks.md) を参照してください。

代表コマンド:

```bash
python scripts/check_frontend_syntax.py
python scripts/run_quick_checks.py --include-hooks-guard
```

---

## 12. 既知事項

- 起動直後の初回生成は、進捗%表示が遅れて出るケースがあります
- キャンセル直後に `Generating...` が短時間残るケースがあります

致命的ではないため、現時点では継続観察中です。

---

## 13. バージョン履歴

| バージョン | 主な変更内容 |
|-----------|------------|
| **v1.5.0** | モジュール分割（core/・frontend/）、生成履歴DB、プリセット階層化、ポジティブ/ネガティブプリセット、名前付きセッション保存、キャラ名日英分離、セットアップ診断UI |
| **v1.4.7** | UI言語切替（JA/EN）、ログ機能、プリセットサムネイル一覧、キャラ数0許可、BOM読み込み改善 |
| **v1.4.6** | SaveImageExtended対応、LLMシステムプロンプトに/no_think追加 |
| **v1.4.5** | 生成進捗%表示（WebSocket）、再生成の各種二重挿入修正、スマホWS接続バナー |
| **v1.4.4** | ExtraTag二重挿入修正、キャラブロック化、番号修正、requests自動インストール対応 |
| **v1.4.3** | 自前ワークフロー（API形式JSON）対応、ワークフロー選択時のNode ID自動検出 |
| **v1.4.2** | LoRA未選択・一部選択時の400エラー修正（LoraLoaderノード自動バイパス） |
| **v1.4.1** | スマホ対応（モバイルUI大幅改善）、LoRAサムネイル表示、各セクショントグル開閉、バージョン表示 |
| **v1.4.0** | LoRA注入、ワークフロー選択ドロップダウン、バグ修正 |
| **v1.3.0** | ギャラリー機能、生成パラメータセクション、フローティングナビ、シーンブロック独立 |
| **v1.2.1** | プリセット自動生成（Danbooru Wiki + LLM）、色選択ドロップダウン化 |
| **v1.2.0** | キャラプリセット機能、接続テスト、ComfyUIキュー表示 |
| **v1.1.0** | 初回公開 |
