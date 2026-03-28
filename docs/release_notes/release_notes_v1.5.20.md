# v1.5.20 Release Notes / リリースノート

Release date: 2026-03-28

## Summary / 概要

v1.5.20 introduces SHARE-1 preset bundle Export/Import and includes UI follow-up improvements for clearer generation controls, especially on mobile.

v1.5.20 は、SHARE-1 のプリセット一括 Export/Import を追加し、あわせて生成操作まわりの UI を改善したリリースです（特にモバイルでの視認性と操作性を強化）。

## Included in v1.5.20 / v1.5.20 の反映内容

- Added `GET /presets_export` to export `chara/` and `presets/{scene,camera,quality,lora,composite}` as a single zip bundle.
- `GET /presets_export` を追加し、`chara/` と `presets/{scene,camera,quality,lora,composite}` を 1 つの zip として書き出せるようにしました。
- Added `POST /presets_import` (`multipart/form-data`) with conflict detection and overwrite control (`409` on conflicts).
- `POST /presets_import`（`multipart/form-data`）を追加し、競合検出と上書き制御（競合時 `409`）に対応しました。
- Added settings panel UI for `Export Presets` and `Import Presets`.
- Settings パネルに `Export Presets` / `Import Presets` UI を追加しました。
- Improved visual distinction between main `Generate` CTA and `Today's Mood` button.
- メインの `Generate` CTA と `Today's Mood` ボタンの視認性差を強化しました。
- Switched the `Generate` / `Today's Mood` button row to a stacked layout on mobile for readability and tap comfort.
- モバイルでは `Generate` / `Today's Mood` ボタン行を縦積みに変更し、可読性とタップしやすさを改善しました。
- Updated visible version labels to `v1.5.20` in app and docs.
- アプリ表示および主要ドキュメント上のバージョン表記を `v1.5.20` に更新しました。

## Cumulative Updates Since v1.5.11 (v1.5.12-v1.5.19) / v1.5.11 以降の累積更新（v1.5.12-v1.5.19）

- v1.5.12: Synchronized release version labels and improved frontend syntax check temporary-file handling.
- v1.5.12: リリース版表記を同期し、フロントエンド構文チェック時の一時ファイル挙動を改善しました。
- v1.5.13-v1.5.14 (INPUT-6): Added LoRA search, favorites, recommended weight persistence, favorites-first sorting, and i18n/spec alignment.
- v1.5.13-v1.5.14（INPUT-6）: LoRA 検索・お気に入り・推奨 weight 保存・お気に入り先頭ソート・i18n/仕様整合を実装しました。
- v1.5.15 (UI-5): Added theme mode (`Device / Light / Dark`) and tuned dark-theme contrast/readability.
- v1.5.15（UI-5）: テーマ切替（`Device / Light / Dark`）を追加し、ダークテーマ時のコントラストと可読性を改善しました。
- v1.5.16 (GEN-9): Added `Today's Mood` random apply flow and guard behavior.
- v1.5.16（GEN-9）: `Today's Mood` のランダム適用フローとガード挙動を追加しました。
- v1.5.17 (OUTPUT-9): Added previous-item prompt diff viewer/toggle in history modal (Positive and conditional Negative).
- v1.5.17（OUTPUT-9）: 履歴モーダルに前回との差分ビューア/トグルを追加しました（Positive と差分時のみの Negative）。
- v1.5.18: Improved mobile LoRA UI layout and visibility.
- v1.5.18: モバイル LoRA UI のレイアウトと視認性を改善しました。
- v1.5.19 (INPUT-1 + GEN-9 follow-up): Added random character preset generation, save-confirm flow, and mood summary/status behavior alignment.
- v1.5.19（INPUT-1 + GEN-9 追従）: ランダムキャラプリセット生成、保存確認フロー、気分サマリー/ステータス表示の仕様整合を追加しました。

## Compatibility / 互換性

- Existing settings and presets remain compatible.
- 既存の設定ファイルおよびプリセットはそのまま互換利用できます。
- Import does not overwrite conflicting presets unless overwrite is explicitly allowed.
- Import 時、上書き許可を明示しない限り競合プリセットは上書きされません。
