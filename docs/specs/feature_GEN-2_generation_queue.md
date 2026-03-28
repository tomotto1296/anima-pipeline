# Feature Spec: GEN-2 生成キュー

## Meta

- Issue: #（未採番）
- Roadmap No.: GEN-2
- Roadmap Priority: HIGH
- Owner:
- Status: Draft
- Version: v1
- Last Updated: 2026-03-29
- Target Version: v1.5.2

---

## Goal / 目的

UIから生成ジョブをその場で積み上げて順次処理できるインタラクティブなキューを提供する。GEN-1（ファイル入力による一括生成）とは異なり、現在の画面設定を即座にキューへ追加・並替・キャンセル・再実行できるため、手動での試行錯誤を止めずに次の生成を先回りして予約できる。

---

## Scope

- **In Scope:**
  - 「キューに追加」ボタンで現在の画面設定をジョブとしてキューへ追加する
  - キューの一覧表示（待機中 / 実行中 / 完了 / 失敗 のステータス）
  - 待機中ジョブのドラッグ＆ドロップによる並替え（モバイルは上下ボタン）
  - 個別ジョブのキャンセル・削除
  - 失敗ジョブの再実行（Re-run）
  - キュー全体の一時停止・再開
  - 完了ジョブのクリア

- **Out of Scope:**
  - ファイル（CSV/txt）からのキュー自動生成（→ GEN-1 の役割）
  - キュー処理の並列実行（ComfyUI 側が1件ずつ処理するため、パイプライン側も逐次処理とする）
  - キュー状態のエクスポート（将来検討）

---

## User Story

> As a ユーザー, I want 今の設定のまま「キューに追加」を押して次の生成を予約しておきたい, so that 1枚目の生成を待たずに次のバリエーションを仕込んでおける。

---

## GEN-1 との役割分担

| 観点 | GEN-1（一括生成） | GEN-2（生成キュー） |
|------|-----------------|------------------|
| ジョブの追加方法 | CSV/TXTファイル or テキスト貼り付け | UIで現在の設定をその場で追加 |
| 操作スタイル | まとめて流す・放置向け | 手動で積みながら随時確認 |
| 並替え | 不可（ファイル順固定） | ドラッグ＆ドロップで自由に並替え |
| 再実行 | 中断→再開（レジューム） | 失敗ジョブ単体を個別 Re-run |
| 主なユースケース | キャラ量産・夜間バッチ | 試行錯誤しながらの予約生成 |

> GEN-1 と GEN-2 はバックエンドのキュー処理ロジックを共通化できる可能性があるが、v1.5.2 では独立実装を優先し、共通化は後フェーズで検討する（Open Questions 参照）。

---

## Requirements / 要件

1. メインUIに「▶ 生成キュー」セクションを追加し、現在のキュー状態を一覧表示する。
2. 「キューに追加」ボタンで現在の画面設定（キャラ・シーン・LoRA・パラメータ・ワークフロー）をスナップショットとしてキューに積む。
3. キューは先入れ先出し（FIFO）で順次処理する。処理中は既存の `/generate` ロジックを内部で呼び出す。
4. 各ジョブにはステータス（待機中 / 実行中 / 完了 / 失敗）を表示し、実行中のジョブには進捗（%）をリアルタイムで反映する。
5. 待機中ジョブはドラッグ＆ドロップで並替えできる。モバイルでは上下矢印ボタンで対応する。
6. 各ジョブに「削除」ボタンを配置する。実行中ジョブを削除した場合は `/cancel` を呼び出してから削除する。
7. 失敗したジョブには「再実行」ボタンを表示し、クリックで同じ設定をキューの末尾に再追加する。
8. キュー全体を「一時停止」できる。一時停止中は現在のジョブ完了後に次のジョブを開始しない。「再開」で処理を続行する。
9. 「完了をクリア」ボタンで完了・失敗ジョブをまとめて削除できる。
10. キュー状態は `settings/queue_state.json` に随時保存し、アプリ再起動後も復元する。
11. キューの `state` が `"running"` の間は単発の「生成開始」ボタンを `disabled` にする。キューを一時停止または完了すると再び有効化する。割り込み生成が必要な場合は「一時停止 → 単発生成」の運用で対応する。

---

## UI/UX

### 表示場所 / Screen

メインUIの「▶ 生成キュー」セクション（既存の生成セクションの下、一括生成セクションの上）。トグル開閉式。

### 変更点 / Changes

```
[▶ 生成開始 ※キュー実行中はdisabled]  [+ キューに追加]   <- 既存ボタン横に追加

▼ 生成キュー                              [⏸ 一時停止]  [🗑 完了をクリア]

  ┌─────────────────────────────────────────────────────────────────┐
  │ ⠿ #1  hatsune_miku   school / morning / clear    ⏳ 待機中  [✕] │
  │ ⠿ #2  saber          fantasy / evening / rain    ⏳ 待機中  [✕] │
  │    #3  rem            bedroom / —— / ——           ⚙ 実行中  71% │
  │    #4  zero_two       city / noon / clear         ✅ 完了   [↺] │
  │    #5  initial_d      school / —— / ——             ❌ 失敗   [↺] │
  └─────────────────────────────────────────────────────────────────┘
  5 件（待機: 2 / 実行中: 1 / 完了: 1 / 失敗: 1）
```

> `⠿` はドラッグハンドル（待機中ジョブのみ表示）。`↺` は再実行ボタン。

### 文言 / Labels

| JA | EN |
|----|-----|
| 生成キュー | Generation Queue |
| キューに追加 | Add to Queue |
| 一時停止 | Pause Queue |
| 再開 | Resume Queue |
| 完了をクリア | Clear Completed |
| 待機中 | Queued |
| 実行中 | Generating |
| 完了 | Done |
| 失敗 | Failed |
| 再実行 | Re-run |
| キューが空です | Queue is empty |
| キューを一時停止しました | Queue paused |
| キューを再開しました | Queue resumed |
| ジョブをキューに追加しました | Job added to queue |
| 件（待機: {q} / 実行中: {r} / 完了: {d} / 失敗: {f}） | jobs (Queued: {q} / Running: {r} / Done: {d} / Failed: {f}) |

---

## API / Data

### 新規エンドポイント

#### `GET /queue`

現在のキュー状態を返す。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `state` | string | `"idle"` / `"running"` / `"paused"` |
| `jobs` | array | ジョブ一覧（後述のジョブオブジェクト） |
| `summary` | object | `{ queued, running, done, failed }` 件数 |

---

#### `POST /queue/add`

現在の設定をスナップショットとしてキューに追加する。

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `snapshot` | object | `POST /generate` と同等の入力パラメータ（`input`, `use_llm`, `width`, `height`, `lora_slots`, `workflow_file` 等） |
| `label` | string | 表示用ラベル（任意。省略時はプリセット名またはタイムスタンプ） |
| `client_id` | string | WebSocket クライアントID |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"added"` または `"error"` |
| `job_id` | string | 追加されたジョブのID |

---

#### `DELETE /queue/<job_id>`

ジョブを削除する。実行中の場合は `/cancel` 相当の処理を行ってから削除する。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |

---

#### `POST /queue/reorder`

待機中ジョブの順序を変更する。

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `order` | array[string] | 待機中ジョブの `job_id` を新しい順に並べたリスト |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |

---

#### `POST /queue/rerun/<job_id>`

失敗または完了ジョブを同じ設定でキューの末尾に再追加する。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"added"` または `"error"` |
| `job_id` | string | 再追加された新しいジョブのID |

---

#### `POST /queue/pause`

キューを一時停止する（現在のジョブ完了後に次を開始しない）。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"paused"` |

---

#### `POST /queue/resume`

一時停止中のキューを再開する。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"resumed"` |

---

#### `POST /queue/clear`

完了・失敗ジョブを削除する。`target` で対象を絞れる。

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `target` | string | `"completed"` (完了のみ) / `"failed"` (失敗のみ) / `"all"` (実行中以外すべて) |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` |
| `removed` | int | 削除件数 |

---

### 既存エンドポイントへの変更

- **`POST /cancel`:** 変更なし。実行中ジョブ削除時に内部で呼び出す。

### 保存先 / Storage

| 種別 | パス / キー |
|------|------------|
| キュー状態ファイル | `settings/queue_state.json` |
| 設定ファイル | `settings/pipeline_config.json` → `queue_max_jobs` |

### ジョブオブジェクト スキーマ

```json
{
  "job_id": "q_20260329_143012_001",
  "label": "hatsune_miku",
  "status": "queued",
  "snapshot": { "...POST /generate と同等の入力パラメータ..." },
  "created_at": "2026-03-29T14:30:12",
  "started_at": null,
  "completed_at": null,
  "error": null,
  "progress": 0
}
```

### 設定デフォルト値（追加）

`core/config.py` の `DEFAULT_CONFIG` に追加するキーと初期値:

```python
'queue_max_jobs': 50,
```

> `_backfill_config` により既存ユーザーの設定ファイルへ自動補完される。`pipeline_config.default.json` への追記は不要。

---

## i18n 対応

- [ ] UIラベルを i18n 辞書（`frontend/i18n.js`）に追加（上記 Labels 表の全項目）
- [ ] サマリーテキスト（`{q} / {r} / {d} / {f}` 形式）の動的生成を JA / EN 両対応
- [ ] JA / EN 往復切替（JA→EN→JA）で表示が崩れないことを確認

---

## 既存機能との互換性

- **既存の単発生成フロー（`POST /generate`）への影響:** なし。「キューに追加」はあくまで予約であり、既存の「生成開始」ボタンは独立して動作し続ける。ただし単発生成とキュー実行が同時に走った場合の ComfyUI 側の競合挙動を確認すること（Open Questions 参照）。
- **既存プリセット・セッションへの影響:** なし。スナップショットは生成時点の設定をコピーして保持するため、元のプリセットが変更されても影響しない。
- **`pipeline_config.json` スキーマ変更の有無:** `queue_max_jobs` キーを追加。`_backfill_config` で自動補完。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
| キューが上限（`queue_max_jobs`）に達した | キューが上限（{n}件）に達しています | Queue is full ({n} jobs max) | `[GEN-2]` |
| 実行中ジョブのキャンセル失敗 | ジョブのキャンセルに失敗しました | Failed to cancel the job | `[GEN-2]` |
| 存在しない `job_id` への操作 | 指定されたジョブが見つかりません | Job not found | `[GEN-2]` |
| 待機中以外のジョブへの並替え要求 | 待機中のジョブのみ並替えできます | Only queued jobs can be reordered | `[GEN-2]` |
| ComfyUI 未起動でジョブが失敗 | ComfyUI に接続できません | Cannot connect to ComfyUI | `[GEN-2]` |
| キュー実行中に単発生成ボタンが押された（JS側で弾くが念のため） | キュー実行中は単発生成できません。一時停止してから実行してください | Cannot generate while queue is running. Pause the queue first. | `[GEN-2]` |
| キュー状態ファイルの読み込み失敗 | キュー状態の復元に失敗しました。空のキューで起動します | Failed to restore queue state. Starting with empty queue. | `[GEN-2]` |

---

## Acceptance Criteria / 完了基準

1. 「キューに追加」で現在の設定がキューに積まれ、一覧に表示される
2. キューが順次処理され、各ジョブのステータスがリアルタイムで更新される
3. 待機中ジョブをドラッグ＆ドロップで並替えられる
4. 個別ジョブを削除できる（実行中の場合はキャンセルしてから削除）
5. 失敗ジョブを「再実行」でキューの末尾に再追加できる
6. キューを一時停止・再開できる
7. アプリ再起動後にキュー状態が復元される

- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）でジョブ一覧が正常に表示・操作できる（上下ボタンでの並替え）
- [ ] 既存の単発生成フローが壊れない
- [ ] ログに秘匿情報が出力されない

---

## Test Plan / テスト計画

### Manual

- 「キューに追加」を3回押す → 3件がキューに積まれ、順次生成されること
- 生成中に「キューに追加」を押す → 待機中として末尾に追加されること
- 待機中ジョブをドラッグ → 順序が変わり、変更後の順で処理されること
- 実行中ジョブを削除 → キャンセルされ次のジョブが開始されること
- 失敗ジョブの「再実行」→ 末尾に再追加され、順番が来たら再生成されること
- 「一時停止」→ 現在のジョブ完了後に止まること
- 「再開」→ 続きから処理が始まること
- アプリ再起動 → キュー状態（待機中・失敗）が復元されること

### Edge Cases

- キューが空の状態で「一時停止」を押した場合
- 「キューに追加」と単発「生成開始」が同時に走った場合の競合
- `queue_max_jobs` 上限に達した状態で追加しようとした場合
- 全ジョブが完了済みの状態でアプリ再起動した場合（空のキューとして起動）
- モバイルで並替えボタンを連打した場合

### Regression

- 既存の単発生成ボタンが正常に動作するか
- セッション自動保存・復元が正常に動作するか
- 言語切替（JA↔EN）が往復で正常に動作するか
- ギャラリー・生成履歴が正常に表示されるか

---

## Rollout / Migration

- **既存ユーザーへの影響:** `queue_max_jobs` キーが未存在でも、次回起動時に `_backfill_config` によって自動補完される。その他の影響なし。
- **移行処理:** `core/config.py` の `DEFAULT_CONFIG` に `'queue_max_jobs': 50` を追加するだけでよい。カスタム移行コードの追記は不要。
- **`pipeline_config.default.json` への追加:** 不要（`DEFAULT_CONFIG` が正本）。
- **`Update.md` への記載:** 実装後に `docs/updates/Update.md` へ追記する

---

## Open Questions / 未決事項

- GEN-1（一括生成）とのバックエンド共通化: 両者のジョブ実行ループは構造が類似しているため、将来的に `core/queue.py` のような共通モジュールに統合できる。v1.5.2 では独立実装を優先し、共通化は v1.5.x 以降で検討する。
- `queue_state.json` の肥大化対策: 完了ジョブを無制限に保持すると肥大化するため、自動削除の上限件数（例: 完了ジョブは最新50件まで保持）を設けるかどうか。

---

## Related Files / 関連ファイル

| ファイル | 役割 |
|---------|------|
| `core/handlers.py` | キューAPIエンドポイントの実装先 |
| `core/comfyui.py` | 生成ロジック（内部呼び出し対象） |
| `frontend/index.html` | 生成キューセクションのUI |
| `frontend/i18n.js` | i18n ラベル辞書 |
| `settings/queue_state.json` | キュー状態の保存先（実行時に生成） |
| `settings/pipeline_config.json` | `queue_max_jobs` の設定 |
| `docs/specs/feature_GEN-1_batch_generation.md` | 一括生成との役割分担 |
| `docs/specs/feature_api_v2.md` | 既存APIリファレンス |
| `docs/updates/Update.md` | 実装後の変更ログ |
