# Anima Pipeline

<p align="center">
  <img src="images/hero-ui-and-result.jpg" alt="Anima Pipeline UI + Generated Image" width="800">
  <br>
  <em>キャラクター名を入力 → LLMがDanbooruタグを自動生成 → ワンクリックで美しいAnima画像が完成！</em>
</p>ブラウザUI + LLMでAnimaワークフローを自動化！  

[![English README](https://img.shields.io/badge/English-README-blue?logo=github)](README_EN.md)  

## 🌐 Live Demo / Landing Page
- [日本語版サイト](https://tomotto1296.github.io/anima-pipeline/index.html)  
- [English Version](https://tomotto1296.github.io/anima-pipeline/index_en.html)
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

## 機能一覧

| 状況 | 機能 |
|---|---|
| ☑ | キャラクター名・作品名から Danbooru タグを LLM で自動生成 |
| ☑ | 髪型・髪色・瞳・口・表情・衣装・ポーズなどを UI で細かく指定 |
| ☑ | 最大 6 キャラクターまで同時設定 |
| ☑ | キャラプリセット保存 / 読み込み / 削除 |
| ☑ | プリセットサムネイル一覧表示（v1.4.7） |
| ☑ | ギャラリー画像からサムネイル自動作成（v1.4.7） |
| ☑ | Danbooru Wiki + LLM によるプリセット自動生成 |
| ☑ | LoRA 注入（カードグリッド UI・サムネイル表示・最大 4 スロット） |
| ☑ | ワークフロー切替（`workflows/` から選択・Node ID 自動検出） |
| ☑ | 生成進捗 % 表示（WebSocket） |
| ☑ | ポジティブ / ネガティブのスタイルタグをプリセット管理 |
| ☑ | セッション自動保存と復元 |
| ☑ | ギャラリー・生成画像プレビュー・プロンプト再利用 |
| ☑ | 生成画像の WebP 変換（オプション） |
| ☑ | スマホ / タブレット対応（同一 Wi-Fi ネットワーク） |
| ☑ | UI 言語切替（日本語 / English）（v1.4.7） |
| ☑ | ログ機能（保存・マスキング・ZIP エクスポート）（v1.4.7） |

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
[English Guide → docs/guides/anima_pipeline_guide_en.md](docs/guides/anima_pipeline_guide_en.md)

## 🗺️ ロードマップ

詳細は [docs/roadmap.md](docs/roadmap.md) を参照してください。

### 近日対応予定

- プリセット階層化（キャラ / シーン / カメラ / 品質 / LoRA 構成）
- プリセット単位でネガティブタグを保存・自動切替
- 生成履歴 DB 化と再編集
- セッションに名前を付けて複数保存
- 失敗時の自己診断UI（エラー原因候補・ノード不足警告）
- LoRA 管理強化（検索・お気に入り・推奨 Weight・自動候補）
- 一括生成モード（CSV / txt → 順次生成）
- 生成キュー（追加 / 並び替え / キャンセル / 再実行）
- ランダムキャラプリセット作成
- プリセット共有（zip Export / Import）
- プロンプト差分ビューア（前回比較）

### 検討中

- 初回チュートリアルウィザード
- 画像メタデータからプロンプト復元（PNG / WebP）
- 「前回と同じキャラで続き生成」ボタン
- 比較生成モード（seed 固定で prompt / LoRA / CFG 比較）
- ワークフロー再現補助（半自動マッピング）
- 生成画像の LLM 評価・自動振り分け
- 生成画像から自動 Danbooru タグ生成
- プリセット共有（URLコード共有）

## 関連記事
- note: https://note.com/rhustudio/n/nf0dc2414f852
- Qiita: https://qiita.com/RHU/items/18095cb22281cd027bc4
- zenn https://zenn.dev/rhu/articles/4a6c315533c4e9
