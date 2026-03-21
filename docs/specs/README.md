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

## Operational Docs / Roadmap & Features

- Manage implemented features in `docs/specs/features.md`.
- Manage planned features in `docs/updates/roadmap.md`.
- Keep `features.md` for implemented items only.
- Keep `roadmap.md` for planned items only.
- Keep links in both files so users can move between them quickly.

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

新規仕様書はテンプレートファイルをコピーして作成してください。
Use the dedicated template file for new spec documents.

- Template: [feature_spec_template.md](feature_spec_template.md)
- Path: `docs/specs/feature_spec_template.md`

---

## Notes / 備考

- `README.md` と `README_EN.md` はルート直下で維持する / Keep `README.md` and `README_EN.md` at the repository root
- 仕様書は「実装する前」に更新する / Update specs **before** implementation
- 英語版 API 仕様書は `feature_api_v<n>_en.md` として同フォルダに保存する / English API references are saved as `feature_api_v<n>_en.md` in the same folder
