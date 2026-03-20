=# anima_pipeline

# Anima Pipeline

<p align="center">
  <img src="images/hero-ui-and-result.jpg" alt="Anima Pipeline UI + Generated Image" width="800">
  <br>
  <em>キャラクター名を入力 → LLMがDanbooruタグを自動生成 → ワンクリックで美しいAnima画像が完成！</em>
</p>ブラウザUI + LLMでAnimaワークフローを自動化！  

[![English README](https://img.shields.io/badge/English-README-blue?logo=github)](README_EN.md)  

<p align="center">
  <img src="demo/demo-flow.gif" alt="Demo GIF" width="600">
</p>
---

## 必要なもの

- Python 3.10以上
- ComfyUI 0.16.4以上 + Animaワークフロー
- LLMサーバー（LM Studio / Gemini API など）※オプション

---

## セットアップ

### 1. ワークフローJSONを用意する

`workflows/image_anima_preview.json` はリポジトリに含まれていません。以下の手順で取得してください。

1. ComfyUIを起動
2. 右上メニュー →「Browse Templates」→ **Anima**を選択
3. メニュー →「Save (API Format)」で `image_anima_preview.json` として保存
4. `workflows/` フォルダに配置

> **自前ワークフローも使えます。** ComfyUIの「Save (API Format)」で出力したJSONを `workflows/` フォルダに置くとドロップダウンで選択できます。

### 2. 起動する

**Windows:** `start_anima_pipeline.bat` をダブルクリック（初回は `requests` を自動インストール）

> batファイルがVS Code等で開く場合は右クリック →「プログラムから開く」→「コマンドプロンプト」を選択してください。

**その他:**
```bash
pip install requests
python anima_pipeline.py
```

ブラウザで http://localhost:7860 を開く。

### 3. 初回設定

画面上部の「▶ 設定」を開いて ComfyUI URL を確認し、「💾 設定を保存」を押す。

LLMを使う場合はプラットフォーム（LM Studio / Gemini / カスタム）を選択してURL・APIキー・モデル名を入力して保存。

### 4. ComfyUI の起動オプション（推奨）

スマホからのアクセスやLoRAサムネイル表示を使う場合は以下のオプションを追加：

```
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --lowvram --listen --enable-cors-header
```

---

## 主な機能

- キャラ名・作品名からDanbooruタグをLLMで自動生成
- 髪型・髪色・目・口・表情・衣装・ポーズ等をUIで細かく指定
- LoRA注入（カードグリッドUI・サムネイル表示・スロット最大4つ）
- ワークフロー切り替え（workflows/フォルダから選択）
- ポジティブ・ネガティブプロンプトの品質タグ・スタイルタグをプリセット管理
- 複数キャラ同時設定
- セッション自動保存・復元
- ギャラリー・生成画像プレビュー
- 生成画像のWebP変換（オプション）
- スマホ・タブレット対応（同一Wi-Fi環境）

---

## ファイル構成

```
anima_pipeline/
  anima_pipeline.py              ← メインスクリプト
  start_anima_pipeline.bat       ← Windows起動用
  requirements.txt               ← 依存ライブラリ
  README.md
  docs/guides/anima_pipeline_guide.md  ← 詳細ガイド
  workflows/                     ← ワークフローJSONを置くフォルダ
    image_anima_preview.json     ← LoRAなし（自分で用意）
    image_anima_preview_Lora4.json ← LoRA×4対応（同梱）
  chara/
    000_default.json             ← キャラプリセット初期値
  settings/
    pipeline_config.json         ← 設定ファイル（APIキーが書き込まれるためgit管理除外推奨）
    pipeline_config.default.json ← 初期値テンプレート
    ui_options.json              ← UIボタン選択肢の定義
    llm_system_prompt.txt        ← LLMシステムプロンプト
```

---

## 📖 Detailed Guide (使い方完全ガイド)
[日本語ガイド → docs/guides/anima_pipeline_guide.md](docs/guides/anima_pipeline_guide.md)  
[English Guide → docs/guides/anima_pipeline_guide.md (Japanese only for now)](docs/guides/anima_pipeline_guide.md)

## 関連記事
- note: https://note.com/rhustudio/n/nf0dc2414f852
- Qiita: https://qiita.com/RHU/items/18095cb22281cd027bc4
- zenn https://zenn.dev/rhu/articles/4a6c315533c4e9
