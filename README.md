# Anima Pipeline

<p align="center">
  <img src="images/hero-ui-and-result.jpg" alt="Anima Pipeline UI + Generated Image" width="800">
  <br>
  <em>キャラクター名を入力 → LLMがDanbooruタグを自動生成 → ワンクリックで美しいAnima画像が完成！</em>
</p>
ブラウザUI + LLMでAnimaワークフローを自動化！  

[![English README](https://img.shields.io/badge/English-README-blue?logo=github)](README_EN.md)

## 🌐 Live Demo / Landing Page
- [日本語版サイト](https://tomotto1296.github.io/anima-pipeline/index.html)
- [English Version](https://tomotto1296.github.io/anima-pipeline/index_en.html)
- [Try Demo（簡易体験版）](https://tomotto1296.github.io/anima-pipeline/demo.html)

<p align="center">
  <img src="demo/demo-flow.gif" alt="Demo GIF" width="600">
</p>

---

## 現在のバージョンとドキュメント

- 現在バージョン: `v1.5.11`
- 実装済み機能一覧: [docs/specs/features.md](docs/specs/features.md)
- ロードマップ: [docs/updates/roadmap.md](docs/updates/roadmap.md)
- 更新履歴: [docs/updates/Update.md](docs/updates/Update.md)

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

## 主な機能（最新版）

| 状況 | 機能 |
|---|---|
| ☑ | キャラ名・作品名の JA/EN 分離入力（`name_en` / `series_en`） |
| ☑ | ポジティブ / ネガティブタグのプリセット保存・読込 |
| ☑ | プリセット階層化（chara / scene / camera / quality / lora / composite） |
| ☑ | 生成履歴DB（全履歴UI + 再編集） |
| ☑ | 名前付きセッション保存（複数スロット・上書き確認） |
| ☑ | セットアップ自己診断UI（`/diagnostics`） |
| ☑ | メタデータ埋め込み（PNG/WebP、LoRAハッシュ等） |
| ☑ | LoRA注入（カードグリッドUI・サムネイル表示・最大4スロット） |
| ☑ | ワークフロー切替（`workflows/` から選択・Node ID 自動検出） |
| ☑ | UI言語切替（日本語 / English） |
| ☑ | ログ機能（保存・秘匿情報マスク・ZIPエクスポート） |

> 詳細な機能一覧（バージョン付き）は [docs/specs/features.md](docs/specs/features.md) を参照してください。

---

## ドキュメント構成（docs/）

- ガイド: [docs/guides/README.md](docs/guides/README.md)
- 仕様: [docs/specs/README.md](docs/specs/README.md)
- 更新履歴: [docs/updates/Update.md](docs/updates/Update.md)
- ロードマップ: [docs/updates/roadmap.md](docs/updates/roadmap.md)
- リリースノート: `docs/release_notes/`
- 記事下書き: `docs/articles/`

---

## ファイル構成（現行）

```text
anima_pipeline/
  anima_pipeline.py
  core/                           ← サーバー/生成/履歴/プリセット等の分割モジュール
  frontend/                       ← index.html / i18n.js
  docs/
    guides/
    specs/
    updates/
    release_notes/
    articles/
  workflows/                      ← ワークフローJSONを配置
  settings/                       ← pipeline_config / ui_options / prompt設定
  presets/                        ← 階層化プリセット(chara/scene/camera/quality/lora/composite)
  sessions/                       ← 名前付きセッション保存先
  history/                        ← 生成履歴DB
  logs/                           ← 実行ログ
```

---

## ロードマップ要約

- `v1.4.8〜v1.5.0`: 基盤フェーズ（完了）
- `v1.5.1`: 日常利用強化（LoRA管理強化・ランダムプリセット・共有）
- `v1.5.2`: 量産フェーズ（一括生成・生成キュー・比較生成）
- `v1.5.x〜`: 高度化（LLM評価・自動タグ生成・再現補助）

詳細は [docs/updates/roadmap.md](docs/updates/roadmap.md) を参照してください。

## 関連記事
- note: https://note.com/rhustudio/n/nf0dc2414f852
- Qiita: https://qiita.com/RHU/items/18095cb22281cd027bc4
- zenn: https://zenn.dev/rhu/articles/4a6c315533c4e9
