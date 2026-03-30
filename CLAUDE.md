# Anima Pipeline — Claude Code ガイド

## 必須ルール（すべての作業に適用）

### 実装開始の条件
- 「〇〇を実装して」と明示された場合のみ作業を開始する
- 仕様書（`docs/specs/`）を読んでも、指示があるまで実装に着手しない

### Git ルール
- **main への直接コミット禁止**。作業は必ず新規ブランチで行う
- **リモートへのプッシュ禁止**（`git push` は明示指示があるときのみ）
- **force-push 禁止**（いかなる場合も）
- `git pull` / `merge` / `rebase` は明示指示がない限り実行しない
- ブランチ命名規則: `feature/GEN-1-batch`, `fix/comfyui-timeout` など

### 作業スコープ
- タスクで明示されたファイル**のみ**変更する
- 指示にないファイルの変更・追加・削除は行わない（スコープクリープ禁止）

### 完了時のフロー
1. `git diff` を出力して変更内容を報告する
2. プッシュ・PR作成はしない
3. 「プッシュしてください」と明示されたときのみ実行する

---

## プロジェクト概要

**Anima Pipeline** — ComfyUI向けキャラクター画像生成ワークフロー自動化ツール
バージョン: v1.5.21 | サーバー: `localhost:7860`

---

## モジュール構成

```
anima_pipeline.py        ← エントリーポイント
core/
  config.py              ← 設定・ログ・センシティブデータマスク
  handlers.py            ← HTTPリクエストハンドラ（メインロジック, 127KB）
  comfyui.py             ← ComfyUI API連携・WebSocket監視
  llm.py                 ← LLMプロンプト生成
  presets.py             ← プリセット階層管理
  history.py             ← 生成履歴DB (SQLite)
  frontend.py            ← HTMLテンプレートローダー
frontend/
  index.html             ← UI（単一ファイル, ~388KB）
  i18n.js                ← 日英切替
settings/                ← JSON/TXT設定ファイル
docs/specs/              ← 機能仕様書（実装前に必ず確認）
```

---

## 仕様書一覧（実装前に該当ファイルを読むこと）

| ID | ファイル | 内容 |
|----|---------|------|
| GEN-1 | `feature_GEN-1_batch_generation.md` | バッチ生成 |
| GEN-2 | `feature_GEN-2_generation_queue.md` | 生成キュー |
| GEN-9 | `feature_GEN-9_todays_mood.md` | 今日の気分ボタン |
| INPUT-4 | `feature_INPUT-4_preset_hierarchy.md` | プリセット階層 |
| INPUT-6 | `feature_INPUT-6_lora_management.md` | LoRA管理 |
| OUTPUT-3 | `feature_OUTPUT-3_generation_history_db.md` | 履歴DB |
| OUTPUT-9 | `feature_OUTPUT-9_prompt_diff.md` | プロンプトdiff |
| SHARE-1 | `feature_SHARE-1_preset_export_import.md` | ZIP入出力 |

新機能は `docs/specs/feature_spec_template.md` をテンプレートとして使う。

---

## コンテキスト管理

- `handlers.py` (127KB) と `frontend/index.html` (~388KB) は巨大ファイル
  - 必要な関数・セクションのみ読む。ファイル全体の一括読み込みは避ける
- 複数ファイルをまたぐ調査は `Explore` サブエージェントに委ねる
- コンテキスト使用率が50%を超えたら `/compact` を実行してから継続

---

## 技術スタック

- **バックエンド**: Python 3.10+, `http.server.ThreadingHTTPServer`, `sqlite3`, `requests`
- **フロントエンド**: Vanilla HTML5/CSS3/JS（フレームワーク不使用）
- **外部API**: ComfyUI (node-based生成), Google Gemini / OpenAI / LM Studio (LLM)
- **DB**: SQLite (`history/history.db`)
- **設定**: JSON (`settings/`) + TXT (プロンプトテンプレート)
