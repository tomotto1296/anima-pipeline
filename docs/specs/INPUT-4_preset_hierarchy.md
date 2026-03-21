# Feature Spec: INPUT-4 プリセット階層化（キャラ/シーン/カメラ/品質/LoRA構成を分離）

## Meta

- Issue: #14
- Roadmap No.: INPUT-4
- Roadmap Priority: HIGH（★★☆）
- Owner:
- Status: Draft
- Version: v1
- Last Updated: 2026-03-22
- Target Version: v1.4.8

---

## Goal / 目的

現在のプリセットはキャラ情報（`chara/*.json`）と style/extra タグのフラット配列しか存在せず、シーン・カメラ・品質・LoRA構成を組み合わせて使い回すことができない。各パラメータ群を独立したプリセット種別として分離・保存・切替できるようにし、「このキャラ×この構図×この品質セット」といった柔軟な組み合わせ運用を可能にする。

---

## Scope

- **In Scope:**
  - プリセット種別の定義（キャラ / シーン / カメラ / 品質 / LoRA構成）
  - 各種別ごとの保存・読込・削除エンドポイント
  - 各種別ごとの UI セレクタ（ドロップダウン or ボタン）
  - 完成プリセット（全種別をまとめてスナップショット保存）
  - 既存 `chara/*.json` との後方互換維持
- **Out of Scope:**
  - プリセット間の依存・継承（例: シーンAはカメラBを必須とする）
  - クラウド同期・エクスポート共有（SHARE-1 / SHARE-2 で対応）
  - LoRA の検索・お気に入り・推奨weight（INPUT-6 で対応）
  - ネガティブプリセットの種別分離（INPUT-5 で対応）
  - 完成プリセットへの LLM 自動タグ付け

---

## User Story

> As a ヘビーユーザー, I want シーン・カメラ・品質・LoRA構成をそれぞれ独立したプリセットとして保存・切替できる, so that 「このキャラ×この構図×この品質セット」という組み合わせをすばやく試せる.

> As a ユーザー, I want よく使うセット全体を「完成プリセット」として1クリックで復元できる, so that 設定をゼロから組み直す手間がなくなる.

---

## Requirements / 要件

1. プリセット種別として **chara / scene / camera / quality / lora** の5カテゴリを定義し、それぞれ独立した保存ディレクトリを持つ。
2. 各カテゴリのプリセットは個別に保存・読込・削除できる（既存キャラプリセットと同じUI操作感）。
3. 複数カテゴリの現在状態を1ファイルにまとめた「完成プリセット（composite）」を保存・読込できる。
4. 既存の `chara/*.json` はそのまま読み込め、マイグレーション不要。
5. `style_tags.json` / `extra_tags.json` は引き続き動作し、scene/quality プリセットとは別管理（今後の統合は別 Issue で検討）。

---

## UI/UX

### 表示場所 / Screen

- 既存の「▶ キャラプリセット」セクションを「▶ プリセット」セクションに拡張
- セクション内にタブ or アコーディオンで種別を切り替え：**キャラ / シーン / カメラ / 品質 / LoRA構成 / 完成**

### 変更点 / Changes

- 種別切替タブ（6項目）を追加
- 各タブに既存キャラプリセットと同様の **プリセット一覧ドロップダウン + 保存/読込/削除** ボタン
- 「完成プリセット」タブ: 保存時に各種別の現在値を全部取り込んでスナップショット保存、読込時に全種別へ一括展開
- モバイル: タブはスクロール可能な横並びボタン列

### 文言 / Labels

| JA | EN |
|----|-----|
| プリセット | Presets |
| キャラ | Character |
| シーン | Scene |
| カメラ | Camera |
| 品質 | Quality |
| LoRA構成 | LoRA Set |
| 完成 | Composite |
| プリセットを保存 | Save Preset |
| プリセットを読込 | Load Preset |
| プリセットを削除 | Delete Preset |
| 完成プリセットを保存 | Save Composite |
| 完成プリセットを読込 | Load Composite |

> 既存ラベルとの整合は `anima_pipeline.py` 内の i18n 辞書を確認すること。

---

## API / Data

### 新規エンドポイント

```
GET  /presets/<category>
```
指定カテゴリのプリセット一覧を返す。`category` は `chara | scene | camera | quality | lora | composite`。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `presets` | array of string | プリセットファイル名（拡張子なし）の一覧 |
| `status` | string | `"ok"` または `"error"` |

---

```
POST /presets/<category>/<name>
```
指定カテゴリに新規プリセットを保存する。

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `data` | object | カテゴリ固有のフィールド群（下記スキーマ参照） |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `error` | string | エラー時のメッセージ |

---

```
GET  /presets/<category>/<name>
```
指定プリセットのデータを返す。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `name` | string | プリセット名 |
| `data` | object | カテゴリ固有のフィールド群 |
| `savedAt` | string | ISO 8601 保存日時 |
| `status` | string | `"ok"` または `"error"` |

---

```
DELETE /presets/<category>/<name>
```
指定プリセットを削除する。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `error` | string | エラー時のメッセージ |

---

### 既存エンドポイントへの変更

- `/chara_list`・`/chara_load`・`/chara_save`・`/chara_delete` は引き続き動作させ、内部で `GET/POST/DELETE /presets/chara/<name>` へリダイレクトまたは共通関数に統合する（後方互換）。

---

### 各カテゴリのデータスキーマ

#### scene プリセット
```json
{
  "scene_world": "",
  "scene_tod": "",
  "scene_weather": "",
  "scene_free": ""
}
```

#### camera プリセット
```json
{
  "pos_camera": "",
  "camera_free": ""
}
```

#### quality プリセット
```json
{
  "quality_preset_key": "quality_human",
  "quality_tags": ["best quality"],
  "quality_neg_tags": ["normal quality", "low quality", "worst quality"]
}
```

#### lora プリセット
```json
{
  "loras": [
    { "name": "lora_name", "weight": 0.8 }
  ]
}
```

#### composite プリセット
```json
{
  "chara": "<chara preset name or null>",
  "scene": "<scene preset name or null>",
  "camera": "<camera preset name or null>",
  "quality": "<quality preset name or null>",
  "lora": "<lora preset name or null>",
  "snapshot": {
    "chara": { ... },
    "scene": { ... },
    "camera": { ... },
    "quality": { ... },
    "lora": { ... }
  }
}
```
> composite はプリセット名参照 + スナップショット両方を保持する。名前参照が破損していてもスナップショットから復元できる。

---

### 保存先 / Storage

| 種別 | パス |
|------|------|
| キャラプリセット | `chara/<name>.json`（既存） |
| シーンプリセット | `presets/scene/<name>.json` |
| カメラプリセット | `presets/camera/<name>.json` |
| 品質プリセット | `presets/quality/<name>.json` |
| LoRA構成プリセット | `presets/lora/<name>.json` |
| 完成プリセット | `presets/composite/<name>.json` |

### 設定デフォルト値（追加する場合）

`settings/pipeline_config.default.json` に追加するキーと初期値:

```json
{
  "last_scene_preset": "",
  "last_camera_preset": "",
  "last_quality_preset": "",
  "last_lora_preset": "",
  "last_composite_preset": ""
}
```

---

## i18n 対応

- [ ] UIラベルを i18n 辞書（`anima_pipeline.py` 内）に追加（上記 Labels 表の全項目）
- [ ] プリセット種別名（シーン・カメラ等）のタブ文言を JA/EN 両方対応
- [ ] JA / EN 往復切替（JA→EN→JA）で表示が崩れないことを確認

---

## 既存機能との互換性

- **既存プリセット（`chara/*.json`）への影響:** なし。既存ファイルはそのまま読み込む。`chara/` ディレクトリは変更しない。
- **既存セッション（`anima_session_last.json`）への影響:** scene/camera/quality/lora プリセット名のフィールドが新規追加されるが、旧セッションには存在しないためデフォルト空文字列で補完する。
- **既存ワークフローJSONへの影響:** なし。
- **`pipeline_config.json` スキーマ変更の有無:** あり（`last_*_preset` キーを追加）。起動時に存在しないキーを `""` で補完する移行処理を実装すること。

> スキーマ変更が発生するため、移行処理（デフォルト値補完）を `anima_pipeline.py` 起動時に実装すること。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
| プリセットファイルが存在しない | プリセットが見つかりません | Preset not found | `[INPUT-4]` プレフィックスで出力 |
| `presets/<category>/` ディレクトリ作成失敗 | プリセット保存先の作成に失敗しました | Failed to create preset directory | `[INPUT-4]` |
| JSON パースエラー（読込時） | プリセットファイルが破損しています | Preset file is corrupted | `[INPUT-4]` |
| 同名プリセットが既に存在（上書き確認） | 同名のプリセットが存在します。上書きしますか？ | A preset with the same name already exists. Overwrite? | — |
| カテゴリ名が不正 | 不明なプリセット種別です | Unknown preset category | `[INPUT-4]` |

> APIキー・トークン・認証情報はログにマスクされることを確認すること。

---

## Acceptance Criteria / 完了基準

1. scene / camera / quality / lora の各カテゴリで、プリセットの保存・読込・削除が正常に動作する
2. 完成プリセットを保存すると全カテゴリの現在状態がスナップショットとして保存され、読込で全カテゴリへ一括展開される
3. 既存の `chara/*.json` が引き続き正常に保存・読込・削除できる
4. 旧セッションファイル（`last_*_preset` キーなし）を読み込んでも起動エラーにならない
- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）でタブ切替・プリセット操作が正常
- [ ] 既存プリセット・セッションの読み込みが壊れない
- [ ] ログに秘匿情報が出力されない

---

## Test Plan / テスト計画

### Manual

- 各カテゴリ（scene / camera / quality / lora）でプリセットを新規保存 → 一覧に表示される
- 各カテゴリでプリセットを読込 → 対応する UI フィールドに値が反映される
- 各カテゴリでプリセットを削除 → 一覧から消える
- 完成プリセットを保存 → `presets/composite/` に JSON が生成される
- 完成プリセットを読込 → 全カテゴリの UI フィールドが一括更新される
- キャラプリセット（既存）の保存・読込・削除が正常に動作する

### Edge Cases

- プリセットが0件のとき（ドロップダウンが空でも操作可能か）
- `presets/` ディレクトリが存在しない状態で起動したとき（自動作成されるか）
- composite プリセットが参照しているプリセット名が削除済みのとき（スナップショットから復元できるか）
- 同名プリセットへの上書き保存
- プリセット名に特殊文字（スペース・日本語・記号）を含む場合

### Regression

- 既存のキャラプリセット保存・読込・削除が正常に動作するか
- セッション自動保存・復元が正常に動作するか
- 言語切替（JA↔EN）が往復で正常に動作するか
- `style_tags.json` / `extra_tags.json` の読込・保存が壊れていないか

---

## Rollout / Migration

- **既存ユーザーへの影響:** 初回起動時に `presets/` ディレクトリが自動作成される。既存 `chara/` には変更なし。`pipeline_config.json` に `last_*_preset` キーが自動補完される。
- **`pipeline_config.default.json` への追加:** あり（`last_scene_preset` 等 5 キー）
- **移行処理:** あり — 起動時に `pipeline_config.json` へ不足キーをデフォルト値で補完する処理を `anima_pipeline.py` に追加
- **`Update.md` への記載:** 実装後に `docs/updates/Update.md` へ追記する

---

## Open Questions / 未決事項

- 完成プリセットの読込時、スナップショット展開とプリセット名参照のどちらを優先するか（→ 現状はスナップショット優先を推奨）
- `style_tags.json` / `extra_tags.json` を将来的に scene/quality プリセットへ統合するか（→ 別 Issue で検討）
- LoRA構成プリセットと ComfyUI ワークフロー内の LoRA ノードとのマッピング方法（ワークフロー依存のため要調査）
- quality プリセットの `quality_preset_key`（`quality_human` / `quality_pony` 等）は `ui_options.json` に依存するが、動的に選択肢を生成するか静的にハードコードするか

---

## 関連ファイル / Related Files

| ファイル | 役割 |
|---------|------|
| `anima_pipeline.py` | メインスクリプト（API・UI両方） |
| `chara/*.json` | 既存キャラプリセット（変更なし） |
| `presets/` | 新規プリセットディレクトリ（scene/camera/quality/lora/composite） |
| `settings/pipeline_config.json` | `last_*_preset` キー追加 |
| `settings/pipeline_config.default.json` | デフォルト値テンプレート |
| `settings/ui_options.json` | scene_world / scene_tod / pos_camera / quality_human 等の選択肢定義 |
| `docs/specs/feature_api_v1.md` | 既存APIリファレンス |
| `docs/updates/Update.md` | 実装後の変更ログ |
