# Feature Spec: OUTPUT-8 Session Named Save

## Meta

- Issue: #19
- Roadmap No.: OUTPUT-8
- Roadmap Priority: MUST (High)
- Owner:
- Status: Draft
- Version: v1
- Last Updated: 2026-03-23
- Target Version: v1.4.8

---

## Goal / 目的

現在のセッション保存は `anima_session_last.json` への1ファイル上書きのみで、複数のプロジェクトを切り替えながら作業できない。名前をつけたセッションを複数保存・呼び出しできるようにする。

---

## Scope

- **In Scope:**
  - セッションに名前をつけて `sessions/<n>.json` として保存（`<n>` はサニタイズ済みファイル名）
  - 保存済みセッション一覧の表示・読込・削除
  - 既存の `anima_session_last.json` 自動保存・復元はそのまま維持
  - `Session Save` ボタンの挙動を拡張（名前入力ダイアログ追加）

- **Out of Scope:**
  - セッションのサムネイル表示
  - セッションの検索・タグ付け
  - クラウド同期・エクスポート共有

---

## ファイル命名規則

- セッション名に含まれる特殊文字（`/ \ : * ? " < > |`）はアンダースコア `_` に置換してサニタイズする
- サニタイズ後の文字列を `<n>` としてファイル名に使用する
- 例: セッション名 `霊夢/2026` → ファイル名 `sessions/霊夢_2026.json`
- 名前が空またはサニタイズ後に空になる場合はタイムスタンプ（`Anima_Pipeline_YYYY-MM-DD_HH-MM`）をデフォルト名として使用する

---

## User Story

> As a ヘビーユーザー, I want セッションに名前をつけて複数保存できる, so that キャラごと・プロジェクトごとに設定を素早く切り替えられる.

---

## Requirements / 要件

1. `Session Save` ボタン押下時に名前入力ダイアログを表示し、`sessions/<n>.json` として保存する。
2. 名前が空またはサニタイズ後に空になる場合はタイムスタンプをデフォルト名として使用する。
3. UI上で同名セッションが存在する場合は上書き確認ダイアログを表示する。APIは `overwrite: true` フラグを受け取って上書きし、フラグなしの場合は `409 Conflict` を返す。
4. セッション一覧UIをSession Save/Open ボタン行の直下に追加する。一覧には保存名と保存日時を表示する。
5. 一覧のエントリをクリックで読込、削除ボタンで削除できる。
6. 既存の自動保存（`anima_session_last.json`）・ファイル読込（`Open`）はそのまま維持する。
7. `sessions/` ディレクトリが存在しない場合は初回保存時に自動作成する。

---

## UI/UX

### 表示場所 / Screen

既存の `Session Save` / `Open` ボタン行の直下

### 変更点 / Changes

```
[Session Save]  [Open]               <- 既存（動作拡張）

[▼ Saved Sessions]                  <- 新規追加（開閉式トグル）
  reimu_project   2026-03-21   [Load] [Delete]
  original_A      2026-03-20   [Load] [Delete]
  test            2026-03-19   [Load] [Delete]
```

- セッション一覧は初期状態で閉じている（開閉トグル）
- スマホでは縦並びで表示

### Labels (JA / EN)

| JA | EN |
|----|-----|
| セッション保存 | Save Session |
| セッション名を入力 | Enter session name |
| 保存済みセッション | Saved Sessions |
| セッションを読込 | Load Session |
| セッションを削除 | Delete Session |
| 同名のセッションが存在します。上書きしますか？ | A session with the same name already exists. Overwrite? |

> 既存の `セッション保存` / `開く` ラベルとの整合は i18n 辞書を確認すること。

---

## API / Data

### 新規エンドポイント

#### `GET /sessions`

保存済みセッション一覧を返す。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `sessions` | array | セッション情報の配列（`name`・`savedAt`・`filename`） |
| `status` | string | `"ok"` または `"error"` |

---

#### `POST /sessions/<n>`

指定名でセッションを保存する。`<n>` はURLエンコード済みのセッション名（サーバー側でサニタイズする）。

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `data` | object | セッションデータ（既存の `POST /session` と同形式） |
| `overwrite` | boolean | `true` の場合は同名ファイルを上書き。省略時は同名存在で `409` を返す |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `error` | string | エラー時のメッセージ |

**HTTP ステータス**

| コード | 状況 |
|--------|------|
| 200 | 保存成功 |
| 409 | 同名セッションが存在し `overwrite` 未指定 |
| 500 | サーバーエラー |

---

#### `GET /sessions/<n>`

指定セッションのデータを返す。

**Response（JSON）:** セッションデータオブジェクト（`status: "ok"` を含む）

---

#### `DELETE /sessions/<n>`

指定セッションを削除する。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `error` | string | エラー時のメッセージ |

---

### 既存エンドポイントへの変更

- `POST /session`（自動保存）: 変更なし。引き続き `settings/anima_session_last.json` に書き込む。
- `GET /session`（自動復元）: 変更なし。

### 保存先 / Storage

| 種別 | パス |
|------|------|
| 自動保存（既存・変更なし） | `settings/anima_session_last.json` |
| 名前付きセッション（新規） | `sessions/<n>.json` |

### 設定デフォルト値

`pipeline_config.default.json` への追加なし。

---

## i18n 対応

- [ ] UIラベルを i18n 辞書に追加（上記 Labels 表の全項目）
- [ ] JA / EN 往復切替（JA→EN→JA）で表示が崩れないことを確認

---

## 既存機能との互換性

- **既存自動保存（`anima_session_last.json`）:** 変更なし。起動時の自動復元もそのまま。
- **既存の `Open`（ファイル選択）:** 変更なし。ローカルJSONを直接開く機能は維持。
- **既存セッションの移行:** 不要。`anima_session_last.json` は引き続き自動保存に使う。
- **`pipeline_config.json` スキーマ変更の有無:** なし。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
| セッション保存失敗 | セッションの保存に失敗しました | Failed to save session | `[OUTPUT-8]` |
| 同名セッション存在（overwrite未指定） | 同名のセッションが存在します。上書きしますか？ | Session already exists. Overwrite? | — |
| セッション読込失敗 | セッションの読み込みに失敗しました | Failed to load session | `[OUTPUT-8]` |
| セッション削除失敗 | セッションの削除に失敗しました | Failed to delete session | `[OUTPUT-8]` |
| sessions/ 作成失敗 | セッション保存先の作成に失敗しました | Failed to create sessions directory | `[OUTPUT-8]` |
| JSONパースエラー | セッションファイルが破損しています | Session file is corrupted | `[OUTPUT-8]` |

---

## Acceptance Criteria / 完了基準

1. 名前をつけてセッションを保存でき、`sessions/<n>.json` が生成される
2. 保存済みセッション一覧が表示され、クリックで読込できる
3. セッションを削除でき、一覧から消えファイルも削除される
4. 既存の自動保存（`anima_session_last.json`）・ファイル読込（`Open`）が壊れない
5. 同名保存時にUI上で確認ダイアログが表示され、APIは `overwrite` フラグなしで `409` を返す
6. セッション名の特殊文字がサニタイズされてファイル名に反映される

---

## Checklist / チェックリスト

- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）で正常に表示・操作できる
- [ ] 既存のプリセット・セッションの読み込みが壊れない
- [ ] ログに秘匈情報が出力されない

---

## Test Plan / テスト計画

### Manual

- セッション保存ボタン押下 → 名前入力ダイアログが出ること
- 名前を入力して保存 → `sessions/<n>.json` が生成されること
- 一覧に保存したセッションが表示されること
- 一覧のエントリをクリック → セッションが復元されること
- 削除ボタン → 一覧から消え、ファイルも削除されること
- 名前を空で保存 → タイムスタンプ名で保存されること
- 同名で再保存 → 上書き確認ダイアログが表示され、確認後に上書きされること
- 特殊文字を含む名前で保存 → サニタイズされたファイル名で保存されること

### Edge Cases

- `sessions/` ディレクトリが存在しない状態で保存（自動作成されるか）
- セッションが0件のとき（一覧が空でも表示が崩れないか）
- セッション名が空白のみの場合（タイムスタンプ名にフォールバックされるか）
- 破損したセッションJSONを読み込もうとした場合

### Regression

- 自動保存（`anima_session_last.json`）が引き続き動作するか
- `Open` でローカルJSONを読み込めるか
- セッション保存・復元後に生成が正常に動作するか
- 言語切替（JA⇔EN）が往復で正常に動作するか

---

## Rollout / Migration

- **既存ユーザーへの影響:** 初回保存時に `sessions/` が自動作成される。既存の `anima_session_last.json` には影響なし。
- **移行処理:** なし
- **`pipeline_config.default.json` への追加:** なし
- **`Update.md` への記載:** 実装と同じコミットで `docs/updates/Update.md` へ追記する

---

## Open Questions / 未決事項

- セッション一覧の件数上限を設けるか（無制限 or 直近20件）
- 将来的にサムネイル（最後に生成した画像）をセッションカードに表示するか（OUTPUT-3の履歴DBと連携可能）

---

## Related Files

| ファイル | 役割 |
|---------|------|
| `anima_pipeline.py` | メインスクリプト（API・UI両方） |
| `sessions/` | 名前付きセッション保存先（新規） |
| `settings/anima_session_last.json` | 自動保存（変更なし） |
| `docs/updates/Update.md` | 実装後の変更ログ |
