# Guides Index

最終更新: 2026-03-28

このディレクトリは、Anima Pipeline の運用・利用・保守に関するガイド集です。  
用途別に次の順で読むと迷いにくくなります。

## 読み順（推奨）

1. 利用者向け（日本語）  
   [anima_pipeline_guide.md](./anima_pipeline_guide.md)
2. Users (English)  
   [anima_pipeline_guide_en.md](./anima_pipeline_guide_en.md)
3. メンテ担当の引き継ぎ  
   [maintenance_quickstart.md](./maintenance_quickstart.md)
4. クイックチェック／Git hooks  
   [quick_checks_and_hooks.md](./quick_checks_and_hooks.md)

## アーカイブ

- 既存版向け追補（v1.4.6 -> v1.4.699999）  
  [anima_pipeline_guide_addendum_v1.4.699999.md](./archive/anima_pipeline_guide_addendum_v1.4.699999.md)

## メンテナンス方針

- 設定ファイルの説明は `settings/pipeline_config.default.json` と `settings/pipeline_config.local.json` の二層構成を基準に統一する。
- APIや挙動に差分が出た場合、まず `core/handlers.py` の実装を正として更新する。
- 変更後は最低限 `quick_checks_and_hooks.md` にある代表コマンドで確認する。
