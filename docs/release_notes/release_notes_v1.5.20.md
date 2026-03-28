# v1.5.20 Release Notes / リリースノート

Release date: 2026-03-28

## Summary / 概要

v1.5.20 introduces SHARE-1 preset bundle Export/Import and includes UI follow-up improvements for clearer generation controls, especially on mobile.

v1.5.20 は、SHARE-1 のプリセット一括 Export/Import を追加し、あわせて生成操作まわりのUIを改善したリリースです（特にモバイルでの視認性と操作性を強化）。

## Included in v1.5.20 / 反映内容

- Added `GET /presets_export` to export `chara/` and `presets/{scene,camera,quality,lora,composite}` as a single zip bundle.
- `GET /presets_export` を追加し、`chara/` と `presets/{scene,camera,quality,lora,composite}` を1つのzipとして書き出せるようにしました。
- Added `POST /presets_import` (`multipart/form-data`) with conflict detection and overwrite control (`409` on conflicts).
- `POST /presets_import`（`multipart/form-data`）を追加し、競合検出と上書き制御（競合時 `409`）に対応しました。
- Added settings-panel UI for `Export Presets` and `Import Presets`.
- Settings パネルに `Export Presets` / `Import Presets` UI を追加しました。
- Improved visual distinction between main `Generate` CTA and `Today's Mood` button.
- メインの `Generate` CTA と `Today's Mood` ボタンの視認性差を強化しました。
- Switched the `Generate` / `Today's Mood` button row to a stacked layout on mobile for readability and tap comfort.
- モバイルでは `Generate` / `Today's Mood` ボタン行を縦積みに変更し、可読性とタップしやすさを改善しました。
- Updated visible version labels to `v1.5.20` in app and docs.
- アプリ表示および主要ドキュメント上のバージョン表記を `v1.5.20` に更新しました。

## Compatibility / 互換性

- Existing settings and presets remain compatible.
- 既存の設定ファイルおよびプリセットはそのまま互換利用できます。
- Import does not overwrite conflicting presets unless overwrite is explicitly allowed.
- Import 時、上書き許可を明示しない限り競合プリセットは上書きされません。
