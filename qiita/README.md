# Qiita publishing workspace

このディレクトリは Qiita CLI 連携専用です。

## 初回セットアップ

1. GitHub のリポジトリ Secrets に `QIITA_TOKEN` を設定する
2. `main` または `master` へ push する
3. GitHub Actions の `Publish Qiita Articles` が実行される

## ローカル作業

- 記事作成:
  - `npx @qiita/qiita-cli new your_article_name`
- プレビュー:
  - `npx @qiita/qiita-cli preview`
- ログイン（ローカル preview 用）:
  - `npx @qiita/qiita-cli login`

## 注意

- 実際に投稿するかは各記事の `ignorePublish` で制御します
- 既定は `qiita/public/*.md` が投稿対象です
