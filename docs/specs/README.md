# Specs Directory Guide / 仕様書ディレクトリガイド

このフォルダは、新機能の仕様書を管理するための場所です。
This folder is for managing feature specification documents.

---

## Purpose / 目的

- 実装前に仕様を明文化して、認識ズレを防ぐ
  Clarify specifications before implementation to prevent misunderstandings.
- Issue と実装内容を追跡しやすくする
  Make it easier to trace Issues to implementation.
- 後から見返して判断理由を確認できるようにする
  Allow reviewing decisions and reasoning after the fact.

---

## Location Policy / 保存場所のルール

- 仕様書は `docs/specs/` に保存する / Save specs under `docs/specs/`
- 旧版は `docs/specs/archive/` へ移動する / Move old versions to `docs/specs/archive/`
- 実装後の更新履歴は `docs/updates/Update.md` に記載する / Record post-implementation changes in `docs/updates/Update.md`

---

## File Naming / ファイル命名規則

形式 / Format: `feature_<short_name>_v<major>.md`

例 / Examples:
- `feature_preset_thumbnail_v1.md`
- `feature_mobile_layout_v1.md`
- `feature_console_i18n_v1.md`

API仕様書 / API reference: `feature_api_v<major>.md` — `feature_api_v<major>_en.md` for English

---

## Recommended Workflow / 推奨ワークフロー

1. Issue を作成する / Create an Issue
2. `docs/specs/` に仕様書を作成する / Create a spec document in `docs/specs/`
3. 仕様レビュー後に実装する / Implement after spec review
4. 実装差分を `docs/updates/Update.md` に反映する / Record changes in `docs/updates/Update.md`
5. 仕様変更が発生したら仕様書のバージョンを更新する / Update the spec version if requirements change

---

## Spec Template / 仕様書テンプレート

以下をコピーして新規仕様書を作成してください。
Copy the template below to start a new spec document.

```md
# Feature Spec: <Feature Name>

## Meta
- Issue: #<number>
- Owner: <name>
- Status: Draft / Review / Approved / Implemented
- Version: v1
- Last Updated: YYYY-MM-DD

## Goal / 目的
- この機能で解決する課題 / Problem this feature solves

## Scope
- In Scope:
  -
- Out of Scope:
  -

## User Story
- As a <user>, I want <behavior>, so that <benefit>.

## Requirements / 要件
1.
2.
3.

## UI/UX
- 画面 / Screen:
- 変更点 / Changes:
- 文言（JA/EN） / Labels (JA/EN):

## API / Data
- Endpoint:
- Request:
- Response:
- 保存先/設定キー / Storage / Config key:

## Error Handling / エラー処理
- 想定エラー / Expected errors:
- 表示文言 / Error messages:
- ログ出力方針 / Logging policy:

## Acceptance Criteria / 完了基準
1.
2.
3.

## Test Plan / テスト計画
- Manual:
- Edge Cases:
- Regression:

## Rollout / Migration / リリース・移行
- 既存ユーザーへの影響 / Impact on existing users:
- 互換性 / Compatibility:

## Open Questions / 未決事項
-
```

---

## Notes / 備考

- `README.md` と `README_EN.md` はルート直下で維持する / Keep `README.md` and `README_EN.md` at the repository root
- 仕様書は「実装する前」に更新する / Update specs **before** implementation
- 英語版 API 仕様書は `feature_api_v<n>_en.md` として同フォルダに保存する / English API references are saved as `feature_api_v<n>_en.md` in the same folder
