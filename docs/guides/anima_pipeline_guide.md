# anima_pipeline 使い方ガイド

## 1. 概要

Anima Pipeline はブラウザUIから入力した情報を元に、必要に応じてLLMでプロンプト補助を行い、ComfyUIに送信して画像生成するツールです。

リファクタ後は `anima_pipeline.py` をエントリポイントとして、機能を `core/` と `frontend/` に分割しています。
現行版は `v1.5.20` です。

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

ヘッダーの `表示テーマ` では `端末連動 / ライト / ダーク` を切り替えできます（`端末連動` はOS設定に追従）。

`Save Settings` を押すと、個人設定は `settings/pipeline_config.local.json` に保存されます。  
共通既定値は `settings/pipeline_config.default.json` から読み込まれます。

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

### ランダム機能の使い分け（GEN-9 / INPUT-1）

- `🎲 今日の気分（GEN-9）` は生成ボタンの横にあります。
- `今日の気分（GEN-9）`:
  - 既存キャラプリセットをランダムに1件ロードします（0件時はキャラ適用をスキップ）。
  - シーン世界観 / 時間帯 / 天気（`scene_world` / `scene_tod` / `scene_weather`）もランダム適用します。
  - 適用内容のサマリーを STATUS に短時間表示します。
- `ランダム生成（INPUT-1）`:
  - キャラプリセット行の `⚀` ボタンです。
  - `ui_options` の既存選択肢（性別/年齢/髪型/髪色/瞳色/衣装）から新規ランダム適用します。
  - 適用後に保存確認ダイアログを表示し、必要ならそのままキャラプリセット保存できます。
  - 適用サマリーはSTATUSに短時間表示されます。

### ポジティブ/ネガティブプリセット（INPUT-5）

- Prompt セクション上部の Positive Preset で、ポジティブ調整状態を保存/読込/削除できます。
- Negative セクション上部の Negative Preset で、ネガティブ調整状態を保存/読込/削除できます。
- 保存対象には品質タグ・補助タグ・メモ・セーフティ系の選択状態が含まれます。
- 最後に選んだ Positive/Negative プリセットは設定に記録され、再起動後に復元されます。

### プリセット共有 zip（SHARE-1）

- `設定` パネルの `プリセット共有（zip）` に `プリセットをエクスポート` / `プリセットをインポート` ボタンがあります。
- Export では次を1つのzipとしてダウンロードします（`anima-presets_YYYY-MM-DD.zip`）。
  - `chara/*.json` / `chara/*.webp`
  - `presets/{scene,camera,quality,lora,composite}/*.json`
- Import はzipを選択して一括展開します。
- 同名ファイルが存在する場合は `409` 相当の上書き確認ダイアログを表示し、承認時のみ上書きします。
- SHARE-1の対象外:
  - `negative` / `positive` プリセット
  - `sessions/`（名前付きセッション）

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
- OUTPUT-9: 履歴モーダルに「前回との差分（Prompt）」を表示できます。
  - Positive は前回比較結果を表示し、`Show/Hide diff` トグルで開閉できます。
  - Negative は差分がある場合のみ表示され、同様にトグルで開閉できます。

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

## 10. スマホアクセス（Tailscale経由・外出先対応）

同一Wi-Fiの外からでもスマホで操作したい場合は、Tailscaleを使います。

### 事前準備（初回のみ）

1. [Tailscale](https://tailscale.com/) でアカウントを作成
2. **PC側**: Tailscaleをインストールしてログイン
3. **スマホ側**: Tailscaleアプリをインストールしてログイン（同じアカウント）
4. **ComfyUI**: 起動オプションに `--listen --enable-cors-header` を追加

   ```
   .\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --lowvram --listen --enable-cors-header
   ```

### 接続手順

1. PC上で `start_anima_pipeline - Tailscale.bat` を実行
2. コンソールに表示された URL（例: `http://100.x.x.x:7860`）をスマホで開く

   ```
   [INFO] Starting server... Open http://100.x.x.x:7860
   ```

   > Tailscaleが接続されていない場合は `[WARN] Tailscale IP not found.` と表示されます。その場合はスマホ・PCのTailscaleアプリが両方オンになっているか確認してください。

> **Tips:** Tailscaleのセットアップが済んだら、以降は `start_anima_pipeline - Tailscale.bat` を常用するのがおすすめです。同一LAN内でも問題なく動作するため、使い分けが不要になります。

---

## 11. 配布時の最小構成

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
- 個人環境の `settings/pipeline_config.local.json`

`v1.5.11` 以降の既存ユーザー向けには、差分上書き用ZIPの併配布を推奨します。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_release_zips.ps1 -Version 1.5.12 -BaseVersion 1.5.11
```

上記で次の2つが `dist/` に生成されます。

- `anima-pipeline_v<version>_minimal.zip`
- `anima-pipeline_v<version>_upgrade_from_v1.5.11.zip`

---

## 12. クイックチェック

詳細は [quick_checks_and_hooks.md](./quick_checks_and_hooks.md) を参照してください。

代表コマンド:

```bash
python scripts/check_frontend_syntax.py
python scripts/run_quick_checks.py --include-hooks-guard
```

---

## 13. 既知事項

- 起動直後の初回生成は、進捗%表示が遅れて出るケースがあります
- キャンセル直後に `Generating...` が短時間残るケースがあります

致命的ではないため、現時点では継続観察中です。

---

## 14. バージョン履歴

| バージョン | 主な変更内容 |
|-----------|------------|
| **v1.5.20** | SHARE-1: プリセット一括 Export/Import（zip）を実装。あわせて `Generate` と `今日の気分` の視認性差を強化し、モバイルでは2ボタンを縦積みに調整。 |
| **v1.5.19** | INPUT-1: ランダムキャラプリセット作成（ui_options由来の属性ランダム適用、保存確認、STATUSサマリー表示）。ランダムボタンのサイコロ表示を統一。 |
| **v1.5.18** | INPUT-6 follow-up: モバイルLoRA UIの視認性を改善（カード列数・スロット行レイアウト最適化）。 |
| **v1.5.17** | OUTPUT-9: 履歴モーダルで前回との差分ビューアを実装（Positive/Negative、トグル対応。Negativeは差分発生時のみ表示）。 |
| **v1.5.16** | GEN-9: `🎲 今日の気分` を実装（生成ボタン付近に配置、既存キャラプリセット1件 + シーン世界観/時間帯/天気のランダム適用、STATUSサマリー表示）。 |
| **v1.5.15** | UI-5: 表示テーマ切替（端末連動/ライト/ダーク）を追加。ダークモード時のコントラスト・可読性を調整（セクション背景、LoRA領域、入力欄、無効ボタン、言語トグル）。 |
| **v1.5.14** | INPUT-6: LoRA管理UI改善（検索、★お気に入り、推奨weight表示、整列順修正、設定保存API統一） |
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
