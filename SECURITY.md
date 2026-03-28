# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.5.x   | :white_check_mark: |
| < 1.5   | :x:                |

## Reporting a Vulnerability

セキュリティ上の問題を発見した場合は、Issueではなく以下の方法でご連絡ください。

- GitHub の [Private vulnerability reporting](https://github.com/tomotto1296/anima-pipeline/security/advisories/new) を使用してください
- 対応状況は1週間以内にお知らせします

### 注意事項

- `pipeline_config.json` に記載したAPIトークンやパスワードは **絶対にGitにコミットしないでください**
- `.gitignore` に `pipeline_config.json` を追加することを推奨します
