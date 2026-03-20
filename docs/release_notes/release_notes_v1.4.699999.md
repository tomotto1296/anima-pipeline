# v1.4.699999 Release Notes / リリースノート

## Overview / 概要
- This release focuses on stabilization and internationalization quality.
- 今回のリリースは、安定化と国際化対応の品質改善が中心です。

## Added / 追加

### UI language switch (JA/EN) / UI言語切替（日本語/英語）
- Added OS-language-based initial UI language detection.
- OS言語を基準に初期表示言語を自動決定。
- Added language toggle buttons in UI.
- UI上で日本語/英語を切替可能に。
- Added persistent language preference storage.
- 言語設定の保存に対応。

### Logging system / ログ機能
- Added runtime logs under `logs/`.
- `logs/` への実行ログ出力を追加。
- Added sensitive-data masking (`token`, `api key`, `authorization`, `bearer`).
- 秘匿情報マスク（`token` / `api key` / `authorization` / `bearer`）に対応。
- Added retention cleanup (default: 30 days).
- 保持期間による自動削除を追加（初期値30日）。
- Added log API endpoints: `GET /logs_info`, `GET /logs_zip`.
- ログAPI追加: `GET /logs_info`, `GET /logs_zip`.
- Added UI controls: `LOG DIRECTORY`, `LOG RETENTION DAYS`, `LOG LEVEL`, `OPEN LOGS`, `EXPORT LOGS ZIP`.
- UI項目追加: `LOG DIRECTORY`, `LOG RETENTION DAYS`, `LOG LEVEL`, `OPEN LOGS`, `EXPORT LOGS ZIP`.

### Preset thumbnail gallery / プリセットサムネイル一覧
- Added character preset thumbnail gallery UI.
- キャラプリセットのサムネイル一覧UIを追加。
- Added preset thumbnail creation flow from expanded gallery image and save to `chara/` as `.webp`.
- ギャラリー拡大画像からサムネイルを作成し、`chara/` に `.webp` 保存する導線を追加。
- Added lazy-load behavior for mobile performance (load thumbnails when the list is opened).
- モバイル性能向上のため、一覧展開時にサムネイルを読み込む遅延取得に対応。
- Added "add character from selected preset" flow (without immediate preset load).
- 選択プリセットを即時読込せず、キャラ枠へ追加する導線を追加。
- Updated character count behavior to allow `0`.
- キャラ数 `0` を選択可能に更新。

## Changed / 変更
- Improved UTF-8/BOM read compatibility.
- UTF-8/BOM混在ファイルの読み込み耐性を改善。
- Improved dynamic translation consistency and round-trip switching.
- 動的文言の翻訳整合性と言語往復切替を改善。
- Refined console language behavior to follow OS policy in startup block.
- 起動時コンソール表示のOS言語追従挙動を整理。

## Fixed / 修正
- Fixed startup `SyntaxError` caused by broken string literal.
- 起動時の文字列終端不正による `SyntaxError` を修正。
- Fixed missing preset display issue (`000_default.json`).
- `000_default.json` が表示されない問題を修正。
- Fixed white-screen/partial-i18n timing issues.
- 白画面や翻訳未反映のタイミング問題を修正。

## Config defaults / デフォルト設定
Updated `settings/pipeline_config.default.json` / `settings/pipeline_config.default.json` 更新:
- `console_lang`
- `log_dir`
- `log_retention_days` (30)
- `log_level`

## Major files / 主な更新ファイル
- `anima_pipeline.py`
- `settings/pipeline_config.default.json`
- `Updfate.md`

## Notes / 補足
- `releases/` is excluded from this development track.
- `releases/` は本開発トラックの編集対象外です。
- Version remains in `1.4.699x` during translation stabilization.
- 翻訳安定化中のためバージョンは `1.4.699x` を継続。
