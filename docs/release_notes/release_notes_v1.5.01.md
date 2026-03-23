# v1.5.01 Release Notes / リリースノート
**Release Date / リリース日:** 2026-03-23

---

## Overview / 概要
> v1.5.01 is a follow-up stabilization release on top of v1.5.0, and this release note includes the cumulative update scope from v1.4.7 through v1.5.0.

> v1.5.01 は v1.5.0 のフォローアップ安定化リリースです。本ノートには v1.4.7〜v1.5.0 の累積更新範囲もあわせて記載します。

---

## New In v1.5.01 / v1.5.01の追加・修正

| EN | JA |
|----|----|
| Startup config backfill for missing keys in `pipeline_config.json` based on `DEFAULT_CONFIG` | `pipeline_config.json` の不足キーを `DEFAULT_CONFIG` から起動時に自動補完 |
| Backfill log line added: `[config] 不足キーを補完しました` | 補完実行時のログ出力を追加: `[config] 不足キーを補完しました` |
| Header version badge fallback via injected `__APP_VERSION__` (still updated by `/version` when available) | ヘッダー版表示のフォールバックとして `__APP_VERSION__` を注入（`/version` 応答時は従来どおり更新） |
| Documentation sync for `v1.5.01` update history | `v1.5.01` の更新履歴ドキュメントを同期 |

---

## Cumulative Scope Included (v1.4.7 - v1.5.0) / 累積反映範囲（v1.4.7〜v1.5.0）

### v1.4.7 Highlights
- JA/EN UI language switch with OS language detection
- Logging system (`logs/`, masking, retention, export ZIP)
- Preset thumbnail gallery + related API improvements
- Character count minimum update (`0` allowed)
- UTF-8/BOM mixed file read improvements

### v1.5.0 Highlights
- Module split (`anima_pipeline.py` -> `core/` + `frontend/`)
- Generation History DB + history re-edit flow
- Preset hierarchy (`chara/scene/camera/quality/lora/composite`)
- Positive/Negative preset save-load support
- Named sessions multi-save
- Character/work name JA/EN split (`name_en`, `series_en`)
- Setup diagnostics UI + `GET /diagnostics`

---

## Related Docs / 関連ドキュメント

- `docs/release_notes/release_notes_v1.4.7.md`
- `docs/release_notes/release_notes_v1.5.0.md`
- `docs/updates/Update.md`
- `docs/specs/features.md`

---

## Notes / 補足

| EN | JA |
|----|----|
| This release is intended to stabilize distribution behavior and keep existing user settings forward-compatible. | 本リリースは配布挙動の安定化と、既存ユーザー設定の前方互換維持を目的としています。 |
| Next feature phase remains aligned with roadmap (`v1.5.1` and later). | 次の機能フェーズは roadmap（`v1.5.1` 以降）に準拠します。 |
