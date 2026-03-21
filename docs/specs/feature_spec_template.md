# Feature Spec: <機能名 / Feature Name>

## Meta

- Issue: #<number>
- Roadmap No.: <例: GEN-1 / OUTPUT-3>
- Roadmap Priority: <MUST / HIGH / MID / LOW>
- Owner: <name>
- Status: Draft / Review / Approved / Implemented
- Version: v1
- Last Updated: YYYY-MM-DD
- Target Version: v1.4.x

---

## Goal / 目的

この機能で解決する課題を1〜2文で。
> 例: セッションを1ファイルで上書きしているため、複数プロジェクトを切り替えながら作業できない。

---

## Scope

- **In Scope:**
  -
- **Out of Scope:**
  -

---

## User Story

> As a <ユーザー像>, I want <操作・動作>, so that <得られる価値>.

例:
> As a ヘビーユーザー, I want セッションに名前をつけて複数保存できる, so that キャラごとにプロジェクトを切り替えられる.

---

## Requirements / 要件

1.
2.
3.

---

## UI/UX

### 表示場所 / Screen
- 追加・変更するUIセクション（例: `▶ 設定` パネル内、キャラブロック上部 など）

### 変更点 / Changes
- 追加するボタン・入力欄・セクションなど

### 文言 / Labels

| JA | EN |
|----|-----|
|  |  |

> 既存ラベルとの整合は `anima_pipeline.py` 内の i18n 辞書を確認すること。

---

## API / Data

### 新規エンドポイント（追加する場合）

```
METHOD /endpoint_name
```

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
|  |  |  |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `error` | string | エラー時のメッセージ |

### 既存エンドポイントへの変更（ある場合）
- 変更対象:
- 変更内容:

### 保存先 / Storage

| 種別 | パス / キー |
|------|------------|
| 設定ファイル | `settings/pipeline_config.json` → キー名: |
| プリセット | `chara/<name>.json` |
| セッション | `settings/anima_session_last.json` |
| その他 |  |

### 設定デフォルト値（追加する場合）
`settings/pipeline_config.default.json` に追加するキーと初期値:

```json
{
  "key_name": "default_value"
}
```

---

## i18n 対応

- [ ] UIラベルを i18n 辞書（`anima_pipeline.py` 内）に追加
- [ ] STATUS・進捗文言がある場合は動的生成パターンも追加
- [ ] JA / EN 往復切替（JA→EN→JA）で確認

---

## 既存機能との互換性

- **既存プリセット（`chara/*.json`）への影響:**
- **既存セッション（`anima_session_last.json`）への影響:**
- **既存ワークフローJSONへの影響:**
- **`pipeline_config.json` スキーマ変更の有無:**

> スキーマ変更が発生する場合は移行処理（デフォルト値補完など）を `anima_pipeline.py` 起動時に実装すること。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
|  |  |  | `[機能名]` プレフィックスで出力 |

> APIキー・トークン・認証情報はログにマスクされることを確認すること（既存のマスク対象: `token`, `api key`, `authorization`, `bearer`）。

---

## Acceptance Criteria / 完了基準

1.
2.
3.
- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）で表示・操作が正常
- [ ] 既存プリセット・セッションの読み込みが壊れない
- [ ] ログに秘匿情報が出力されない

---

## Test Plan / テスト計画

### Manual
-

### Edge Cases
- プリセットが0件のとき
- ワークフローJSONが存在しないとき
- ComfyUI未起動・LLM未設定のとき
- スマホ（同一Wi-Fi）からアクセスしたとき

### Regression
- 既存のプリセット保存・読込・削除が正常に動作するか
- セッション自動保存・復元が正常に動作するか
- 言語切替（JA↔EN）が往復で正常に動作するか

---

## Rollout / Migration

- **既存ユーザーへの影響:** （初回起動時に何か起きるか）
- **`pipeline_config.default.json` への追加:** あり / なし
- **移行処理:** あり / なし（ある場合は内容を記載）
- **`Update.md` への記載:** 実装後に `docs/updates/Update.md` へ追記する

---

## Open Questions / 未決事項

-

---

## 関連ファイル / Related Files

| ファイル | 役割 |
|---------|------|
| `anima_pipeline.py` | メインスクリプト（API・UI両方） |
| `settings/pipeline_config.json` | 設定保存先 |
| `settings/pipeline_config.default.json` | デフォルト値テンプレート |
| `settings/ui_options.json` | UIボタン選択肢の定義 |
| `docs/specs/feature_api_v1.md` | 既存APIリファレンス |
| `docs/updates/Update.md` | 実装後の変更ログ |
