# v1.4.7 Release Notes / リリースノート

**Release Date / リリース日:** 2026-03-20

---

## Overview / 概要

> v1.4.7 is the official release of the v1.4.699x development series, focusing on stabilization, JA/EN UI internationalization, and new utility features.

> v1.4.7 は v1.4.699x 開発シリーズの正式リリースです。安定化・日英UI国際化・実用機能の追加が中心です。

---

## Added / 追加

### UI Language Switch (JA/EN) / UI言語切替（日本語/英語）

| EN | JA |
|----|----|
| OS-language-based initial UI language detection | OS言語を基準に初期表示言語を自動決定 |
| Language toggle buttons (JA / EN) in the UI header | UIヘッダーに言語切替ボタン（JA / EN）を追加 |
| Persistent language preference storage (browser) | 言語設定のブラウザ保存に対応 |
| Improved dynamic label translation consistency and round-trip switching | 動的ラベルの翻訳整合性と往復切替（JA→EN→JA）を改善 |

### Logging System / ログ機能

| EN | JA |
|----|----|
| Runtime log output to `logs/` directory | `logs/` フォルダへの実行ログ出力を追加 |
| Sensitive-data masking: `token`, `api key`, `authorization`, `bearer` | 秘匿情報の自動マスク対応（`token` / `api key` / `authorization` / `bearer`） |
| Retention-based auto cleanup (default: 30 days) | 保持期間による自動削除（初期値: 30日） |
| Uncaught-exception hook for unexpected error capture | 未処理例外をログに記録する例外フックを追加 |
| New API: `GET /logs_info`, `GET /logs_zip` | APIエンドポイント追加: `GET /logs_info`, `GET /logs_zip` |
| New settings UI: `LOG DIRECTORY`, `LOG RETENTION DAYS`, `LOG LEVEL`, `OPEN LOGS`, `EXPORT LOGS ZIP` | 設定UI追加: `LOG DIRECTORY`, `LOG RETENTION DAYS`, `LOG LEVEL`, `OPEN LOGS`, `EXPORT LOGS ZIP` |

### Preset Thumbnail Gallery / プリセットサムネイル一覧

| EN | JA |
|----|----|
| Character preset thumbnail gallery UI (collapsible, lazy-loaded) | キャラプリセットのサムネイル一覧UI（開閉式・遅延読み込み）を追加 |
| Thumbnail creation from expanded gallery image; saved as `chara/<name>.webp` | ギャラリー拡大画像からサムネイルを作成し `chara/<name>.webp` として保存する導線を追加 |
| Preset deletion also removes the associated `.webp` thumbnail | プリセット削除時に同名 `.webp` サムネイルも削除するよう変更 |
| "Add Character" button (＋) — sets preset on a new character slot without auto-loading | 「＋ キャラ追加」ボタンを追加（プリセットをセットするのみ、即時読込なし） |
| New API: `POST /chara_preset_thumb`, `GET /chara_thumb` | APIエンドポイント追加: `POST /chara_preset_thumb`, `GET /chara_thumb` |
| Character count minimum changed to `0` | キャラ数の最小値を `0` に変更 |

### Launch Script Improvements / 起動スクリプト改善

| EN | JA |
|----|----|
| Added `chcp 65001` / `PYTHONUTF8=1` for UTF-8 console output on Windows | Windows コンソールのUTF-8出力対策を追加 |
| Fixed `py` call to `py -3` to prevent Python 2 fallback | `py` 呼び出しを `py -3` に固定し Python 2 フォールバックを防止 |
| Tailscale version: added `tailscale ip -4` auto-detection and URL display | Tailscale版: IPアドレス自動検出とURL表示を追加 |

---

## Changed / 変更

| EN | JA |
|----|----|
| Console language now follows OS language policy from the startup block onward | 起動ブロック以降のコンソール表示をOS言語に追従する仕様に整理 |
| Shortened English UI labels for narrow screens (e.g., `Bird's-Eye View` → `Bird's-Eye`) | 狭い画面向けに英語UIラベルを短縮（例: `Bird's-Eye View` → `Bird's-Eye`） |
| Hair style buttons (`Overall` / `Back` groups) changed to 2-row layout | 髪型ボタン（全体 / 後ろグループ）を2段レイアウトに変更 |
| Unified preset panel order across mobile and desktop: Chara Count → Preset List → Chara 1…6 | モバイル・PCのプリセットパネル順を統一: キャラ数 → プリセット一覧 → キャラ1〜6 |

---

## Fixed / 修正

| EN | JA |
|----|----|
| Startup `SyntaxError` caused by broken string literal | 起動時の文字列終端不正による `SyntaxError` を修正 |
| `000_default.json` not appearing in the preset list | `000_default.json` がプリセット一覧に表示されない問題を修正 |
| White-screen and partial-i18n timing issues on page load | ページ読み込み時の白画面・翻訳未反映タイミング問題を修正 |
| UTF-8/BOM mixed-encoding read errors in config files | 設定ファイルでのBOM混在による読み込みエラーを修正 |
| Mixed-language text in LLM connection test progress display | LLM接続テストの進捗表示で日英混在していた文言を修正 |
| Mobile layout issues in Gender/Age rows and STATUS long-line display | モバイルの性別・年齢行レイアウト崩れ、STATUS長文の視認性を修正 |
| `source image not found` error in thumbnail creation | サムネイル作成時の `source image not found` エラーを修正 |
| `/chara_presets?_ts=...` returning 404 | `/chara_presets?_ts=...` が404を返す問題を修正 |

---

## Config Defaults Updated / デフォルト設定の変更

`settings/pipeline_config.default.json` updated / 更新:

| Key | Default | Description / 説明 |
|-----|---------|-------------------|
| `console_lang` | `""` | Follows OS / OS言語追従 |
| `log_dir` | `logs/` | Log folder / ログ保存先 |
| `log_retention_days` | `30` | Days to retain / 保持日数 |
| `log_level` | `normal` | `normal` or `debug` |

---

## Major Files Changed / 主な更新ファイル

- `anima_pipeline.py`
- `start_anima_pipeline.bat`
- `start_anima_pipeline - Tailscale.bat`
- `settings/pipeline_config.default.json`
- `docs/guides/anima_pipeline_guide.md`
- `docs/guides/anima_pipeline_guide_en.md` *(new / 新規)*
- `docs/specs/feature_api_v1.md`
- `docs/specs/feature_api_v1_en.md` *(new / 新規)*
- `docs/specs/README.md`
- `docs/updates/Update.md`
- `docs/release_notes/release_notes_v1.4.7.md` *(this file / このファイル)*

---

## Notes / 補足

| EN | JA |
|----|----|
| `releases/` is excluded from this development track and should not be edited. | `releases/` は本開発トラックの編集対象外です。 |
| The `1.4.699x` development series is now formally closed as v1.4.7. | `1.4.699x` 開発シリーズは v1.4.7 として正式にクローズされました。 |
