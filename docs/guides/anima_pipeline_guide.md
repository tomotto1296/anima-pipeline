# anima_pipeline 使い方ガイド

## 1. 概要

Anima Pipeline はブラウザUIから入力した情報を元に、必要に応じてLLMでプロンプト補助を行い、ComfyUIに送信して画像生成するツールです。

リファクタ後は `anima_pipeline.py` をエントリポイントとして、機能を `core/` と `frontend/` に分割しています。

---

## 2. 動作要件

| 項目 | 推奨 |
|------|------|
| Python | 3.10 以上 |
| 依存ライブラリ | `requests`（+ 履歴サムネ利用時は `Pillow` 推奨） |
| ComfyUI | 起動済み（既定: `http://127.0.0.1:8188`） |
| ワークフローJSON | `workflows/` に最低1つ |

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

`Save Settings` で保存すると `settings/pipeline_config.json` に反映されます。

---

## 6. スマホアクセス（同一LAN）

1. PCのIPv4を確認（例: `192.168.1.103`）
2. PC上で Anima Pipeline を起動
3. スマホで `http://<PCのIPv4>:7860` を開く

接続できない場合:

- PCファイアウォールで 7860 の受信許可を確認
- URLが `https://` ではなく `http://` になっているか確認
- ComfyUI側のCORS設定（必要環境のみ）を確認

---

## 7. 配布時の最小構成

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

## 8. クイックチェック

詳細は [quick_checks_and_hooks.md](./quick_checks_and_hooks.md) を参照してください。

代表コマンド:

```bash
python scripts/check_frontend_syntax.py
python scripts/run_quick_checks.py --include-hooks-guard
```

---

## 9. 既知事項

- 起動直後の初回生成は、進捗%表示が遅れて出るケースがあります
- キャンセル直後に `Generating...` が短時間残るケースがあります

致命的ではないため、現時点では継続観察中です。
