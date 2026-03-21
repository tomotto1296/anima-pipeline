# Feature Spec: OUTPUT-3 生成履歴DB化＋再編集（サムネ・prompt・seed・LoRA・お気に入り管理）

## Meta

- Issue: #12
- Roadmap No.: OUTPUT-3
- Roadmap Priority: MUST
- Owner:
- Status: Draft
- Version: v1
- Last Updated: 2026-03-22
- Target Version: v1.4.8

---

## Goal / 目的

現在、生成履歴はセッション内メモリのみに存在するため、アプリ再起動で消える。生成単位の履歴をSQLiteに永続化し、サムネ・プロンプト・パラメータ・LoRA情報をいつでも参照・再利用できるようにする。

> **依存関係:** この機能は OUTPUT-5（LLM評価・振り分け）・OUTPUT-7（LoRA統計）・GEN-3（比較生成）の結果保存先を兼ねるため、後続機能より先に実装する必要がある。

---

## Scope

- **In Scope:**
  - 生成完了ごとにSQLiteへ履歴レコードを書き込む
  - サムネイル（WebP縮小版）の生成・保存
  - 履歴一覧UI（グリッド表示・ページネーション）
  - 履歴レコードからのセッション再読み込み（「この条件で再編集」）
  - お気に入りフラグのON/OFF切替
  - タグ付け（自由テキスト、カンマ区切り）
  - 履歴の削除（単件・一括）
  - 履歴検索・絞り込み（ワークフロー名・LoRA・お気に入り・日時範囲）
- **Out of Scope:**
  - クラウド同期・外部DB
  - LLM自動評価・品質スコアリング（OUTPUT-5）
  - LoRA統計・推奨weight算出（OUTPUT-7）
  - 比較生成UI（GEN-3）
  - 画像→プロンプト再現（OUTPUT-6）
  - 履歴のExport/Import（SHARE系機能として別途検討）

---

## User Story

> As a ヘビーユーザー, I want 生成した画像の条件（プロンプト・seed・LoRA等）をアプリ再起動後も参照・再利用できる, so that 過去の良い結果を即座に再現・応用できる.

> As a ユーザー, I want 気に入った生成結果にお気に入りフラグとタグを付けられる, so that 大量の履歴から目的の画像をすぐ見つけられる.

---

## Requirements / 要件

1. 生成完了時に以下のフィールドをSQLiteの `generation_history` テーブルへ保存する:
   - `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
   - `created_at` (TEXT, ISO8601)
   - `thumbnail_path` (TEXT) — WebP縮小版の相対パス
   - `image_path` (TEXT) — 出力画像の相対パス
   - `prompt` (TEXT)
   - `negative_prompt` (TEXT)
   - `seed` (INTEGER)
   - `steps` (INTEGER)
   - `cfg` (REAL)
   - `sampler` (TEXT)
   - `scheduler` (TEXT)
   - `workflow_name` (TEXT)
   - `loras` (TEXT) — JSON配列 `[{"name":"...", "weight":0.8}, ...]`
   - `session_snapshot` (TEXT) — 再編集用のセッションJSON全体（gzip圧縮Base64）
   - `favorite` (INTEGER, 0/1, デフォルト 0)
   - `tags` (TEXT) — カンマ区切り文字列
2. 履歴UIは既存のギャラリーセクション（`▶ ギャラリー`）を拡張し、タブまたはトグルで「現在のセッション履歴」と「全履歴DB」を切り替えられる。
3. 履歴エントリをクリックすると拡大プレビューとメタデータを表示し、「この条件で再編集」ボタンで `session_snapshot` をセッションに復元する。
4. お気に入りボタン（★）はその場でトグルし、DBを即時更新する。
5. タグ入力欄は拡大プレビュー内に配置し、フォーカスアウトで自動保存する。
6. サムネイルは縦横最大 256px のWebP（品質 80）として `history/thumbs/` へ保存する。
7. `pipeline_config.json` に `history_db_path`（デフォルト: `"history/history.db"`）と `history_thumb_dir`（デフォルト: `"history/thumbs/"`）を追加する。
8. DBが存在しない場合は初回起動時に自動作成する。

---

## UI/UX

### 表示場所 / Screen

- 既存の `▶ ギャラリー` セクション内を拡張
- セクション上部にタブ切替: `セッション履歴` / `全履歴`
- 全履歴タブに絞り込みバー（お気に入りのみ・ワークフロー名・タグ）を追加

### 変更点 / Changes

- 履歴グリッド: サムネイル + 生成日時 + ★ボタン を1カードとして表示
- カードクリック → モーダルで拡大プレビュー
  - 表示項目: サムネ・prompt・negative・seed・steps・cfg・sampler・workflow・LoRA一覧・生成日時
  - ボタン: 「この条件で再編集」「お気に入り★」「削除」「閉じる」
  - タグ入力欄（プレースホルダー: `タグをカンマ区切りで入力 / Enter tags (comma-separated)`）
- 絞り込みバー
  - お気に入りフィルタトグル（★のみ表示）
  - ワークフロー名ドロップダウン（履歴に存在するもの）
  - タグ入力フィルタ
- ページネーション: 1ページ 20件、前後ページボタン

### 文言 / Labels

| JA | EN |
|----|----|
| 全履歴 | All History |
| セッション履歴 | Session History |
| この条件で再編集 | Reload Settings |
| お気に入り | Favorite |
| お気に入りのみ | Favorites Only |
| タグ | Tags |
| タグをカンマ区切りで入力 | Enter tags (comma-separated) |
| 履歴を削除 | Delete Entry |
| 一括削除 | Delete All |
| 履歴件数 | History Count |
| 絞り込み | Filter |
| ワークフロー | Workflow |

> 既存ラベルとの整合は `anima_pipeline.py` 内の i18n 辞書を確認すること。

---

## API / Data

### 新規エンドポイント

```
GET /history_list
```

**Query Parameters**

| パラメータ | 型 | 説明 |
|-----------|---|------|
| `page` | integer | ページ番号（1始まり、デフォルト 1） |
| `per_page` | integer | 1ページの件数（デフォルト 20） |
| `favorite` | integer | 1 = お気に入りのみ |
| `workflow` | string | ワークフロー名でフィルタ（部分一致） |
| `tag` | string | タグでフィルタ（部分一致） |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `total` | integer | 総件数 |
| `page` | integer | 現在ページ |
| `items` | array | 履歴レコード配列（`session_snapshot` は除く） |
| `error` | string | エラー時のメッセージ |

---

```
GET /history_detail
```

**Query Parameters**

| パラメータ | 型 | 説明 |
|-----------|---|------|
| `id` | integer | 履歴ID |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `item` | object | 全フィールド含む履歴レコード（`session_snapshot` 含む） |
| `error` | string | エラー時のメッセージ |

---

```
POST /history_update
```

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `id` | integer | 履歴ID |
| `favorite` | integer | 0 または 1（省略可） |
| `tags` | string | カンマ区切りタグ（省略可） |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `error` | string | エラー時のメッセージ |

---

```
POST /history_delete
```

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `id` | integer | 削除する履歴ID（`all: true` と排他） |
| `all` | boolean | `true` の場合全件削除（お気に入り除外オプションあり） |
| `keep_favorites` | boolean | `all: true` 時にお気に入りを保持するか（デフォルト `true`） |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `deleted` | integer | 削除件数 |
| `error` | string | エラー時のメッセージ |

---

### 既存エンドポイントへの変更

- 変更対象: 生成完了後の画像保存処理（`/generate` 相当）
- 変更内容: 保存完了後に `save_history_record()` を呼び出し、サムネイル生成とDB書き込みを行う

### 保存先 / Storage

| 種別 | パス / キー |
|------|------------|
| 設定ファイル | `settings/pipeline_config.json` → `history_db_path`, `history_thumb_dir` |
| 履歴DB | `history/history.db`（デフォルト） |
| サムネイル | `history/thumbs/<id>.webp`（デフォルト） |

### DBスキーマ

```sql
CREATE TABLE IF NOT EXISTS generation_history (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at       TEXT    NOT NULL,
    thumbnail_path   TEXT,
    image_path       TEXT,
    prompt           TEXT,
    negative_prompt  TEXT,
    seed             INTEGER,
    steps            INTEGER,
    cfg              REAL,
    sampler          TEXT,
    scheduler        TEXT,
    workflow_name    TEXT,
    loras            TEXT,
    session_snapshot TEXT,
    favorite         INTEGER NOT NULL DEFAULT 0,
    tags             TEXT    NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_history_created_at ON generation_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_favorite   ON generation_history(favorite);
CREATE INDEX IF NOT EXISTS idx_history_workflow   ON generation_history(workflow_name);
```

### 設定デフォルト値（追加する場合）

`settings/pipeline_config.default.json` に追加するキーと初期値:

```json
{
  "history_db_path": "history/history.db",
  "history_thumb_dir": "history/thumbs/"
}
```

---

## i18n 対応

- [ ] UIラベルを i18n 辞書（`anima_pipeline.py` 内）に追加
- [ ] 「この条件で再編集」「全履歴」「セッション履歴」等の文言を追加
- [ ] STATUS文言（「履歴を保存しました」等）がある場合は動的生成パターンも追加
- [ ] JA / EN 往復切替（JA→EN→JA）で確認

---

## 既存機能との互換性

- **既存プリセット（`chara/*.json`）への影響:** なし（独立したDB）
- **既存セッション（`anima_session_last.json`）への影響:** なし（履歴保存は追加書き込みのみ）
- **既存ワークフローJSONへの影響:** なし（ワークフロー名を文字列として記録するだけ）
- **`pipeline_config.json` スキーマ変更の有無:** あり（`history_db_path`, `history_thumb_dir` を追加）
- **既存ギャラリーUI（セッション内履歴表示）への影響:** タブ切替で共存。既存のセッション履歴表示はそのまま維持する。

> スキーマ変更が発生するため、起動時に該当キーが存在しない場合はデフォルト値を補完する移行処理を `anima_pipeline.py` に実装すること。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
| DB初期化失敗 | 履歴DBの初期化に失敗しました。履歴機能は無効です。 | Failed to initialize history DB. History feature is disabled. | `[OUTPUT-3] DB init error: <detail>` |
| レコード書き込み失敗 | 履歴の保存に失敗しました（生成画像は保存されます）。 | Failed to save history record. (Generated image is saved.) | `[OUTPUT-3] DB write error: <detail>` |
| サムネイル生成失敗 | サムネイルの生成に失敗しました。 | Failed to generate thumbnail. | `[OUTPUT-3] Thumbnail error: <detail>` |
| セッション復元失敗 | セッションの復元に失敗しました。 | Failed to restore session. | `[OUTPUT-3] Session restore error: <detail>` |
| DBファイルが見つからない | 履歴DBファイルが見つかりません。再起動してください。 | History DB not found. Please restart. | `[OUTPUT-3] DB not found: <path>` |

> APIキー・トークン・認証情報はログにマスクされることを確認すること（既存のマスク対象: `token`, `api key`, `authorization`, `bearer`）。

---

## Acceptance Criteria / 完了基準

1. 生成完了後、`history/history.db` にレコードが書き込まれ、`history/thumbs/` にサムネイルが保存される
2. アプリ再起動後も全履歴タブに過去の生成結果が表示される
3. 「この条件で再編集」ボタンを押すと、当時のプロンプト・seed・LoRA・ワークフローがセッションに反映される
4. お気に入りトグルが即時反映され、再起動後も保持される
5. タグ入力・保存が動作し、タグによる絞り込みが機能する
6. 履歴削除（単件・一括）が正常に動作し、サムネイルファイルも削除される
7. DB初期化失敗時に生成処理がブロックされない（履歴機能だけが無効化される）
- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）で表示・操作が正常
- [ ] 既存プリセット・セッションの読み込みが壊れない
- [ ] ログに秘匿情報が出力されない

---

## Test Plan / テスト計画

### Manual

- 画像を1枚生成し、`history.db` にレコードが存在すること・サムネが作成されることを確認
- アプリを再起動し、全履歴タブに生成結果が残っていることを確認
- 履歴カードをクリックし、モーダルにプロンプト・seed・LoRA等が正しく表示されることを確認
- 「この条件で再編集」を押し、画面上のパラメータが当時の値に復元されることを確認
- ★ボタンをON→OFF→再起動して、状態が保持されることを確認
- タグを入力し、再起動後も残っていること・タグ絞り込みで表示できることを確認
- 履歴を単件削除し、DBとサムネが削除されることを確認
- 一括削除（お気に入り保持）を実行し、★付き以外が消えることを確認

### Edge Cases

- サムネイル元画像が存在しない（手動削除済み）とき
- `session_snapshot` のdeserializeに失敗するとき（旧バージョンのスナップショット）
- 履歴が0件のとき（空状態の全履歴タブ表示）
- DBファイルが破損しているとき
- LoRAが0件の履歴レコードのとき
- プロンプトに特殊文字・絵文字が含まれるとき
- `history/` ディレクトリへの書き込み権限がないとき
- ComfyUI未起動・LLM未設定のとき
- スマホ（同一Wi-Fi）からアクセスしたとき

### Regression

- 既存のプリセット保存・読込・削除が正常に動作するか
- セッション自動保存・復元が正常に動作するか
- 言語切替（JA↔EN）が往復で正常に動作するか
- 既存ギャラリー（セッション履歴）の表示・プロンプト再利用が従来通り動作するか

---

## Rollout / Migration

- **既存ユーザーへの影響:** 初回起動時に `history/history.db` と `history/thumbs/` が自動作成される。既存の生成画像は移行しない（新規生成分から記録開始）。
- **`pipeline_config.default.json` への追加:** あり（`history_db_path`, `history_thumb_dir`）
- **移行処理:** あり（`pipeline_config.json` に該当キーがない場合デフォルト値を補完。`history/` ディレクトリが存在しない場合は起動時に自動作成）
- **`Update.md` への記載:** 実装後に `docs/updates/Update.md` へ追記する

---

## Open Questions / 未決事項

- `session_snapshot` の保存単位: セッション全体（キャラ全員）か、生成時のパラメータのみか → 「この条件で再編集」の復元範囲に影響する
- 履歴の保持上限: 件数上限（例: 直近1000件）または日時上限（例: 90日）を設けるか、無制限か
- 既存ギャラリーのセッション内履歴との統合方針: タブ切替か、全履歴に一本化するか
- 削除時に元画像ファイルも削除するか（サムネのみ削除か）
- OUTPUT-5（LLM評価）との連携スキーマ: `score` / `label` カラムを先行追加しておくか

---

## 関連ファイル / Related Files

| ファイル | 役割 |
|---------|------|
| `anima_pipeline.py` | メインスクリプト（API・UI両方） |
| `settings/pipeline_config.json` | 設定保存先 |
| `settings/pipeline_config.default.json` | デフォルト値テンプレート |
| `settings/ui_options.json` | UIボタン選択肢の定義 |
| `history/history.db` | 生成履歴SQLiteDB（新規作成） |
| `history/thumbs/` | サムネイル保存ディレクトリ（新規作成） |
| `docs/specs/feature_api_v1.md` | 既存APIリファレンス |
| `docs/specs/OUTPUT-4_metadata_embedding.md` | 依存機能（メタデータ埋め込み） |
| `docs/updates/Update.md` | 実装後の変更ログ |
