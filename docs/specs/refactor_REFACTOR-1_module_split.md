# Refactor Spec: REFACTOR-1 anima_pipeline.py モジュール分割

## Meta

- Roadmap No.: REFACTOR-1
- Kind: Refactor
- Status: In Progress
- Last Updated: 2026-03-23
- Target Branch: `main`
- Related Version Range: `v1.4.8xx`

---

## 目的

単一ファイルだった `anima_pipeline.py` の責務を分離し、保守性と不具合修正速度を上げる。

### 期待効果

- UI/API/設定/ComfyUI連携の変更を局所化できる
- 文字化けやi18n不整合の修正をフロント側だけで完結できる
- GET/POSTハンドラの回帰を追いやすくなる
- 仕様書・更新ログと実装の対応を取りやすくなる

---

## スコープ

### 対象

- `anima_pipeline.py` のエントリポイント化
- `core/` への責務分離
  - `core/config.py`
  - `core/handlers.py`
  - `core/comfyui.py`
  - `core/presets.py`
  - `core/history.py`
  - `core/frontend.py`
  - `core/runtime.py`
  - `core/llm.py`
- `frontend/index.html` / `frontend/i18n.js` の外出しと修正
- Hook/Quick Check スクリプト整備

### 非対象

- 画像生成品質そのものの改善
- ComfyUI 側ワークフロー定義の全面変更
- 既存プリセット資産の構造変更

---

## 実装方針

1. `anima_pipeline.py` は起動・依存注入・サーバー起動に限定する。
2. HTTPルートは `core/handlers.py` に集約し、GET/POSTの重複処理を整理する。
3. 設定・保存系は `core/config.py` / `core/presets.py` に寄せる。
4. UI文言は `frontend/i18n.js` で置換し、`index.html` 側は最小限のマーカー運用にする。
5. 回帰防止として `scripts/run_quick_checks.py` を push 前提の検査に使う。

---

## 受け入れ条件

- `python scripts/check_frontend_syntax.py` が成功する
- `python scripts/run_quick_checks.py --include-hooks-guard` が成功する
- 以下の主要UI回帰がない
  - 言語切替で主要セクション文言が崩れない
  - 生成履歴見出しが `???` にならない
  - LoRAサムネイル取得で初回ロード時に復帰不能にならない
  - `/version`, `/extra_tags`, `/neg_extra_tags`, `/style_tags` が404にならない

---

## 既知課題（継続）

- 起動直後の初回生成時、進捗%表示がComfyUI実進捗より遅れて追従するケースあり
- キャンセル直後に `Generating...` 表示が短時間残存するケースあり

---

## 備考

本仕様は `docs/updates/Update.md` の運用ログとセットで管理する。
