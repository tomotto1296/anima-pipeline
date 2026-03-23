# v1.5.0 Release Notes / リリースノート
**Release Date / リリース日:** 2026-03-23

---

## Overview / 概要
> v1.5.0 is the foundation milestone release that consolidates the 1.4.8xx to 1.4.91x development track into an official distribution version.

> v1.5.0 は、1.4.8xx〜1.4.91x の開発トラックを正式配布版として統合した、基盤フェーズ完了リリースです。

---

## Highlights / 主要ポイント

| EN | JA |
|----|----|
| Module split (`anima_pipeline.py` -> `core/` + `frontend/`) for maintainability | 保守性向上のため `anima_pipeline.py` を `core/` + `frontend/` に分割 |
| Generation History DB and history re-edit workflow | 生成履歴DB化と履歴再編集フローを実装 |
| Preset hierarchy (`chara/scene/camera/quality/lora/composite`) | プリセット階層化（`chara/scene/camera/quality/lora/composite`）を実装 |
| Positive/Negative preset save-load support | ポジティブ/ネガティブプリセットの保存・読込に対応 |
| Named session multi-save (`sessions/`) | 名前付きセッション複数保存（`sessions/`）に対応 |
| Character/work name JA/EN split (`name_en`, `series_en`) | キャラ名・作品名の日英分離（`name_en`, `series_en`）に対応 |
| Setup diagnostics UI + `GET /diagnostics` endpoint | セットアップ自己診断UIと `GET /diagnostics` を追加 |

---

## Included From Prior Development Track / 取り込み範囲

| EN | JA |
|----|----|
| Includes stable features landed between v1.4.718 and v1.4.911 | v1.4.718〜v1.4.911 で実装済みの安定機能を取り込み |
| Version labels across major docs are synchronized to `v1.5.0` | 主要ドキュメントの現在バージョン表記を `v1.5.0` に同期 |
| Foundation phase in roadmap is marked completed (`v1.4.8-v1.5.0`) | roadmap 上の基盤フェーズ（`v1.4.8-v1.5.0`）を完了扱いに更新 |

---

## Documentation Sync / 関連ドキュメント同期

- `README.md`
- `README_EN.md`
- `docs/specs/features.md`
- `docs/updates/roadmap.md`
- `docs/updates/Update.md`

---

## Notes / 補足

| EN | JA |
|----|----|
| `releases/` remains out of scope for this development track and should not be edited | `releases/` は本開発トラックの編集対象外のため変更しない |
| Next planned phase starts from `v1.5.1` (daily workflow improvements) | 次フェーズは `v1.5.1`（日常利用強化）から開始 |
