# v1.5.11 Release Notes / リリースノート

Release date: 2026-03-26

## Summary / 概要

v1.5.11 focuses on non-developer environment stability, especially for ComfyUI Portable style usage.

v1.5.11 は、ComfyUI Portable 運用に合わせた非開発環境での安定性強化を目的としたリリースです。

## Included in v1.5.11 / 反映内容

- Launcher scripts now prioritize bundled Python (`python_embeded\python.exe`) and fall back to system Python only when needed.
- 起動スクリプトは同梱Python（`python_embeded\python.exe`）を優先し、必要時のみシステムPythonへフォールバックするようにしました。
- Added Anima2 workflow templates to minimal distribution workflows.
- 最小構成配布のワークフローに Anima2 テンプレートを追加しました。
- Standardized bundled workflow set to four files:
- 同梱ワークフローを次の4ファイルに標準化しました:
  - `image_anima_preview.json`
  - `image_anima_preview_Lora4.json`
  - `image_anima2_preview.json`
  - `image_anima2_preview_Lora4.json`
- Updated visible version labels to `v1.5.11` in app and docs.
- アプリ表示およびドキュメント上のバージョン表記を `v1.5.11` に更新しました。

## Minimal Package / 最小構成ZIP

- `anima-pipeline_v1.5.11_minimal.zip` (release asset)
- `anima-pipeline_v1.5.11_minimal.zip`（リリース添付アセット）
- Download / ダウンロード: `https://github.com/tomotto1296/anima-pipeline/releases/download/v1.5.11/anima-pipeline_v1.5.11_minimal.zip`

## Compatibility / 互換性

- Existing settings and presets remain compatible.
- 既存の設定ファイルおよびプリセットはそのまま互換利用できます。
- Node IDs for bundled Anima1/Anima2 templates stay aligned with default values (`11`, `12`, `19`) in this release.
- 同梱 Anima1/Anima2 テンプレートのノードIDは、既定値（`11`, `12`, `19`）との整合を維持しています。
