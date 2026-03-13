# anima_pipeline

ブラウザUIでキャラ・シーン情報を入力 → LLM（オプション）でDanbooruプロンプトを自動生成 → ComfyUI Animaワークフローへ自動送信するパイプラインツールです。

---

## 必要なもの

- Python 3.10以上
- ComfyUI 0.16.4以上 + Animaワークフロー
- LLMサーバー（LM Studio / Gemini API など）※オプション

---

## セットアップ

### 1. ワークフローJSONを用意する

`image_anima_preview.json` はリポジトリに含まれていません。以下の手順で取得してください。

1. ComfyUIを起動
2. 右上メニュー →「Browse Templates」→ **Anima**を選択
3. メニュー →「Save (API Format)」で `image_anima_preview.json` として保存
4. `anima_pipeline.py` と同じフォルダに配置

### 2. 起動する

**Windows:** `start_anima_pipeline.bat` をダブルクリック

**その他:**
```bash
pip install requests
python anima_pipeline.py
```

ブラウザで http://localhost:7860 を開く。

### 3. 初回設定

画面上部の「▶ 設定」を開いて ComfyUI URL を確認し、「💾 設定を保存」を押す。

LLMを使う場合はプラットフォーム（LM Studio / Gemini / カスタム）を選択してURL・APIキー・モデル名を入力して保存。

---

## 主な機能

- キャラ名・作品名からDanbooruタグをLLMで自動生成
- 髪型・髪色・目・口・表情・衣装・ポーズ等をUIで細かく指定
- ポジティブ・ネガティブプロンプトの品質タグ・スタイルタグをプリセット管理
- 複数キャラ同時設定
- セッション自動保存・復元
- 生成画像のWebP変換（オプション）

---

## ファイル構成

```
anima_pipeline/
  anima_pipeline.py          ← メインスクリプト
  start_anima_pipeline.bat   ← Windows起動用
  README.md
  anima_pipeline_guide.md    ← 詳細ガイド
  image_anima_preview.json   ← ワークフローJSON（自分で用意）
  settings/
    pipeline_config.json     ← 設定ファイル（APIキーを入れたらgit管理注意）
    ui_options.json          ← UIボタン選択肢の定義
    llm_system_prompt.txt    ← LLMシステムプロンプト
```

---

## 詳細

[anima_pipeline_guide.md](anima_pipeline_guide.md) を参照してください。
