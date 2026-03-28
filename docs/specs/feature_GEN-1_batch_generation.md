# Feature Spec: GEN-1 一括生成モード

## Meta

- Issue: #（未採番）
- Roadmap No.: GEN-1
- Roadmap Priority: HIGH
- Owner:
- Status: Draft
- Version: v1
- Last Updated: 2026-03-29
- Target Version: v1.5.2

---

## Goal / 目的

毎回手動でキャラ・シーンを設定して生成ボタンを押す作業を繰り返さなくても、複数のプリセット組み合わせをまとめて順次生成できるようにする。途中で中断しても再開（レジューム）できるため、大量生成を安心して実行できる。

---

## Scope

- **In Scope:**
  - CSVまたはtxtファイルを入力として複数の生成ジョブを順次実行する
  - 一括生成の進捗表示（何件目 / 全件）
  - 中断・一時停止・再開（レジューム）機能
  - 各ジョブの成功・失敗をステータス表示
  - 既存の `/generate` エンドポイントを内部で呼び出す形で実装（生成ロジックの二重化なし）

- **Out of Scope:**
  - リアルタイムキュー管理・並替・追加（→ GEN-2 の役割）
  - 比較生成・グリッド出力（→ GEN-3 の役割）
  - 入力ファイルのGUIエディタ（テキストエリアでの直接編集のみ対応）
  - LLMなしモード限定の制約はなし（`use_llm` は各行で指定するか設定に従う）

---

## User Story

> As a ヘビーユーザー, I want キャラ・シーンの組み合わせリストをまとめて渡して自動生成させたい, so that 1枚ずつ設定する手間なく大量のバリエーション画像を一気に作れる。

---

## 入力フォーマット仕様

### CSV形式（推奨）

1行1ジョブ。1行目はヘッダー行（必須）。

```
preset_name,scene_world,scene_tod,scene_weather,extra_tags,negative_tags,count,workflow_file
initial_d_takumi,school,morning,clear,,,,
saber,fantasy,evening,rain,armor shining,,2,
```

| カラム | 必須 | 説明 |
|--------|------|------|
| `preset_name` | 必須 | キャラプリセット名（`chara/` 配下に存在するもの） |
| `scene_world` | 任意 | シーン世界観（`ui_options.json` の値 or 空欄でプリセット値を維持） |
| `scene_tod` | 任意 | 時間帯（空欄で維持） |
| `scene_weather` | 任意 | 天気（空欄で維持） |
| `extra_tags` | 任意 | 追加タグ（スペース区切り） |
| `negative_tags` | 任意 | ネガティブ追加タグ（スペース区切り） |
| `count` | 任意 | 生成枚数（デフォルト: 設定値 or 1） |
| `workflow_file` | 任意 | ワークフローJSONファイル名（空欄で現在の設定を使用） |

### TXT形式（シンプル版）

1行1プリセット名のみ指定。シーン設定はすべてプリセット値を維持。

```
initial_d_takumi
saber
hatsune_miku
```

---

## Requirements / 要件

1. UIに「一括生成」セクションを追加し、CSVまたはtxtのファイルアップロードまたはテキストエリア入力を受け付ける。
2. 「一括生成を開始」ボタンで順次生成を開始する。既存の `/generate` エンドポイントを1ジョブずつ順番に呼び出す。
3. 生成中は進捗バー＋テキスト（例: `3 / 10 完了`）を表示し、現在処理中のジョブ内容（プリセット名など）も表示する。
4. 各ジョブの完了・失敗をリストで確認できる（ステータス列: 待機中 / 生成中 / 完了 / 失敗）。
5. 「中断」ボタンで現在のジョブ完了後に停止し、進捗をファイルに保存する。
6. 「再開」ボタンで保存された進捗から中断箇所の次のジョブから再スタートできる（レジューム）。
7. 全ジョブ完了後に完了通知をSTATUSに表示する。
8. 存在しないプリセット名が指定された場合は当該ジョブをスキップしてエラーをログに出力し、残りのジョブを続行する。

---

## UI/UX

### 表示場所 / Screen

メインUIの「▶ 一括生成」セクション（既存の生成セクションの下に追加）。トグル開閉式。

### 変更点 / Changes

```
▼ 一括生成
  ┌─────────────────────────────────────┐
  │ [ファイルを選択] または テキスト入力  │
  │ [テキストエリア: CSV/txt 貼り付け]   │
  └─────────────────────────────────────┘
  フォーマット: ● CSV  ○ TXT       [▶ 一括生成を開始]

  進捗: ████████░░  3 / 10 完了
  現在: initial_d_takumi（シーン: school / morning / clear）

  ┌──────────────────────────────────────────────┐
  │ #  プリセット名          ステータス           │
  │ 1  initial_d_takumi     ✅ 完了              │
  │ 2  saber                ✅ 完了              │
  │ 3  hatsune_miku         ⏳ 生成中...         │
  │ 4  rem                  ⏸ 待機中             │
  │ 5  zero_two             ⏸ 待機中             │
  └──────────────────────────────────────────────┘

  [⏹ 中断]  [▶ 再開]  [🗑 クリア]
```

### 文言 / Labels

| JA | EN |
|----|-----|
| 一括生成 | Batch Generation |
| ファイルを選択 | Choose File |
| テキストエリアに貼り付け | Paste CSV / TXT here |
| 一括生成を開始 | Start Batch |
| 中断 | Pause |
| 再開 | Resume |
| クリア | Clear |
| 待機中 | Queued |
| 生成中... | Generating... |
| 完了 | Done |
| 失敗 | Failed |
| スキップ | Skipped |
| 全ジョブ完了 | All jobs complete |
| 一括生成を中断しました | Batch paused |
| 一括生成を再開しました | Batch resumed |

---

## API / Data

### 新規エンドポイント

#### `POST /batch/start`

一括生成を開始する。

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `format` | string | `"csv"` または `"txt"` |
| `content` | string | CSV/TXT の生テキスト |
| `client_id` | string | WebSocket クライアントID |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"started"` または `"error"` |
| `total` | int | ジョブ総数 |
| `error` | string | エラー時のメッセージ |

---

#### `POST /batch/pause`

現在のジョブ完了後に一括生成を一時停止し、進捗をファイルへ保存する。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"pausing"` |
| `completed` | int | 完了済みジョブ数 |

---

#### `POST /batch/resume`

保存された進捗から一括生成を再開する。

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `client_id` | string | WebSocket クライアントID |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"resumed"` または `"error"` |
| `remaining` | int | 残りジョブ数 |
| `error` | string | エラー時のメッセージ |

---

#### `GET /batch/status`

現在の一括生成状態を返す。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `state` | string | `"idle"` / `"running"` / `"paused"` / `"done"` |
| `total` | int | ジョブ総数 |
| `completed` | int | 完了済み数 |
| `failed` | int | 失敗数 |
| `skipped` | int | スキップ数 |
| `current_job` | object\|null | 実行中ジョブの内容（`preset_name` 等） |
| `jobs` | array | 全ジョブの一覧と各ステータス |

---

#### `POST /batch/clear`

保存された進捗・キューをリセットする。`state` が `"running"` の場合はエラー。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |

---

### 既存エンドポイントへの変更

- **`POST /generate`:** 変更なし。バックエンドのバッチ処理が内部でこのエンドポイントのロジックを直接呼び出す（HTTP経由でなく関数呼び出しでもよい）。

### 保存先 / Storage

| 種別 | パス / キー |
|------|------------|
| バッチ進捗ファイル | `settings/batch_progress.json` |
| 設定ファイル（デフォルト枚数など） | `settings/pipeline_config.json` → `batch_default_count` |

### `batch_progress.json` スキーマ

```json
{
  "format": "csv",
  "total": 10,
  "completed": 3,
  "jobs": [
    {
      "index": 0,
      "preset_name": "initial_d_takumi",
      "scene_world": "school",
      "scene_tod": "morning",
      "scene_weather": "clear",
      "extra_tags": "",
      "negative_tags": "",
      "count": 1,
      "workflow_file": "",
      "status": "done"
    }
  ]
}
```

### 設定デフォルト値（追加）

`core/config.py` の `DEFAULT_CONFIG` に追加するキーと初期値:

```python
'batch_default_count': 1,
```

> `_backfill_config` により既存ユーザーの設定ファイルへ自動補完される。`pipeline_config.default.json` への追記は不要。

---

## i18n 対応

- [ ] UIラベルを i18n 辞書（`frontend/i18n.js`）に追加（上記 Labels 表の全項目）
- [ ] 進捗テキスト（`3 / 10 完了` 形式）の動的生成を JA / EN 両対応
- [ ] JA / EN 往復切替（JA→EN→JA）で表示が崩れないことを確認

---

## 既存機能との互換性

- **既存の生成フロー（`POST /generate`）への影響:** なし。バッチは独立したルートとして動作する。
- **既存プリセット（`chara/*.json`）への影響:** 読み込みのみ。変更なし。
- **既存セッション（`anima_session_last.json`）への影響:** バッチ生成中はセッション自動保存を抑制するか、最後のジョブ完了時のみ保存する方針で検討（Open Questions参照）。
- **`pipeline_config.json` スキーマ変更の有無:** `batch_default_count` キーを追加。起動時に未存在の場合はデフォルト値 `1` を補完する。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
| 存在しないプリセット名 | プリセット「{name}」が見つかりません。スキップします。 | Preset "{name}" not found. Skipping. | `[GEN-1]` |
| CSV パース失敗 | CSVの形式が正しくありません（{行数}行目） | Invalid CSV format (line {n}) | `[GEN-1]` |
| ComfyUI 未起動中のジョブ失敗 | ComfyUI に接続できません。一括生成を中断します。 | Cannot connect to ComfyUI. Batch paused. | `[GEN-1]` |
| 生成ジョブ単体の失敗 | ジョブ {n} が失敗しました。次のジョブを続行します。 | Job {n} failed. Continuing next job. | `[GEN-1]` |
| 空のCSV/TXT | ジョブが1件もありません | No jobs found in the input | `[GEN-1]` |
| バッチ実行中に再起動 | 前回の一括生成が中断されています。「再開」で続きから実行できます。 | Previous batch was paused. Click Resume to continue. | `[GEN-1]` |

---

## Acceptance Criteria / 完了基準

1. CSV/TXTファイルのアップロードまたはテキスト貼り付けで一括生成を開始できる
2. 各ジョブが順次実行され、進捗（件数・現在のジョブ）がリアルタイムで更新される
3. 中断ボタンで現在のジョブ完了後に停止し、再開ボタンで続きから再スタートできる
4. 存在しないプリセット名はスキップされ、残りのジョブが続行される
5. CSVのフォーマットが不正な行は警告を出してスキップし、処理を継続する
6. 全ジョブ完了後にSTATUSに完了通知が表示される

- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）で進捗リストが正常に表示・スクロールできる
- [ ] 既存の単発生成フローが壊れない
- [ ] ログに秘匿情報が出力されない

---

## Test Plan / テスト計画

### Manual

- 5件のCSVを用意し、一括生成を開始 → 順次生成が行われること
- 生成中に「中断」ボタン → 現在のジョブ完了後に停止すること
- 停止後に「再開」ボタン → 中断した次のジョブから再開すること
- 存在しないプリセット名を含むCSVを入力 → スキップされ残りのジョブが続行すること
- TXT形式で複数プリセット名を入力 → 各プリセットが順次生成されること
- 全ジョブ完了後 → 完了通知が表示され、「再開」ボタンが非活性になること

### Edge Cases

- CSVが空（ヘッダー行のみ）の場合
- プリセットが0件の状態で一括生成を開始した場合
- ComfyUI が途中でダウンした場合（バッチが一時停止されること）
- 1ジョブだけのCSVを入力した場合
- count 列に 0 や負の値が入っていた場合（デフォルト値 1 に補正）
- アプリ再起動後に `batch_progress.json` が残っていた場合（復元バナーが表示されること）

### Regression

- 既存の単発生成ボタンが正常に動作するか
- セッション自動保存・復元が正常に動作するか
- 言語切替（JA↔EN）が往復で正常に動作するか
- ギャラリー・生成履歴が正常に表示されるか

---

## Rollout / Migration

- **既存ユーザーへの影響:** `batch_default_count` キーが未存在でも、次回起動時に `_backfill_config` によって自動補完される。その他の影響なし。
- **移行処理:** `core/config.py` の `DEFAULT_CONFIG` に `'batch_default_count': 1` を追加するだけでよい。`load_config()` 内の `_backfill_config` が既存ユーザーの設定ファイルに自動でキーを補完するため、カスタム移行コードの追記は不要。
- **`pipeline_config.default.json` への追加:** 不要（`DEFAULT_CONFIG` が正本。`pipeline_config.default.json` はカスタムデフォルト上書き用途のため今回は対象外）。
- **`Update.md` への記載:** 実装後に `docs/updates/Update.md` へ追記する

---

## Open Questions / 未決事項

- バッチ生成中のセッション自動保存の扱い: 各ジョブ完了ごとに保存するか、最後の1件のみ保存するか、バッチ中は無効化するか。
- エラーが連続n件続いた場合に自動停止するかどうか（例: ComfyUIが落ちたと判断して中断する閾値の設定）。
- GEN-2（生成キュー）との統合可能性: GEN-1を「ファイル入力によるキュー作成の自動化」、GEN-2を「UIからのインタラクティブなキュー管理」として分割する方針で現状は進める。

---

## Related Files / 関連ファイル

| ファイル | 役割 |
|---------|------|
| `core/handlers.py` | バッチAPIエンドポイントの実装先 |
| `core/comfyui.py` | 生成ロジック（内部呼び出し対象） |
| `frontend/index.html` | 一括生成セクションのUI |
| `frontend/i18n.js` | i18n ラベル辞書 |
| `settings/batch_progress.json` | バッチ進捗の保存先（実行時に生成） |
| `settings/pipeline_config.json` | `batch_default_count` の設定 |
| `docs/specs/feature_api_v2.md` | 既存APIリファレンス |
| `docs/updates/Update.md` | 実装後の変更ログ |
