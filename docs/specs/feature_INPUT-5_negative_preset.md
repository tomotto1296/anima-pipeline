# Feature Spec: INPUT-5 プリセット単位でネガティブタグを保存・自動切替

## Meta

- Issue: #18
- Roadmap No.: INPUT-5
- Roadmap Priority: MUST（★☆☆）
- Owner:
- Status: Draft
- Version: v1
- Last Updated: 2026-03-23
- Target Version: v1.4.8

---

## Goal / 目的

現在のネガティブタグ（`neg_extra_tags.json` / `neg_style_tags.json`）はアプリ全体で1つの設定しか持てない。キャラや用途によってよく出る失敗（手崩れ・融合・変な構図など）が異なるため、プリセット単位でネガティブタグを保存・切替できるようにする。

---

## Scope

- **In Scope:**
  - `quality`プリセット（INPUT-4で実装済み）に `neg_tags` フィールドを追加する形でネガティブタグを保存
  - quality プリセット読込時にネガティブ品質タグも一括復元
  - `presets/negative/<n>.json` として独立したネガティブプリセットを保存・読込・削除できるようにする
  - ネガティブプリセットのUIセレクタをネガティブプロンプト調整セクションに追加
- **Out of Scope:**
  - ネガティブタグのカテゴリ別分類（品質・スタイル・Extraの統合）
  - `neg_extra_tags.json` / `neg_style_tags.json` の廃止・移行（引き続き動作させる）
  - composite プリセットへのネガティブ統合（INPUT-4の composite に将来追加可能な設計にしておく）

---

## User Story

> As a ユーザー, I want よく使うネガティブタグの組み合わせをプリセットとして保存・切替できる, so that キャラや用途ごとに最適なネガティブを素早く適用できる.

---

## Requirements / 要件

1. `presets/negative/<n>.json` としてネガティブプリセットを保存・読込・削除できる。
2. ネガティブプリセットには以下のフィールドを含む:
   - `neg_extra_tags`: 追加するネガティブタグの配列
   - `neg_style_tags`: ネガティブスタイルタグ（@アーティスト名）の配列
   - `neg_extra_note`: 追記文（英語）
3. ネガティブプロンプト調整セクションの上部にプリセット選択ドロップダウン＋保存/読込/削除ボタンを追加する。
4. プリセット読込時は現在のネガティブ設定を上書きする（確認ダイアログあり）。
5. INPUT-4で実装済みの `/presets/<category>` エンドポイントの `negative` カテゴリとして実装する（新規エンドポイント不要）。
6. 既存の `neg_extra_tags.json` / `neg_style_tags.json` はそのまま動作し、移行処理不要。

---

## UI/UX

### 表示場所 / Screen

ネガティブプロンプト調整セクション（赤枠）の最上部

### 変更点 / Changes

```
▼ ネガティブプロンプト調整
  ┌─────────────────────────────────────┐
  │ ネガティブプリセット [ドロップダウン▼] [読込] [保存] [削除] │  ← 新規追加
  └─────────────────────────────────────┘
  ① Period Tags（Positiveと共通）
  ② 品質タグ ...
  ...
```

### 文言 / Labels

| JA | EN |
|----|-----|
| ネガティブプリセット | Negative Preset |
| ネガティブプリセットを保存 | Save Negative Preset |
| ネガティブプリセットを読込 | Load Negative Preset |
| ネガティブプリセットを削除 | Delete Negative Preset |
| 現在のネガティブ設定を上書きしますか？ | Overwrite current negative settings? |

> 既存ラベルとの整合は i18n 辞書を確認すること。

---

## API / Data

### 既存エンドポイントの活用

INPUT-4で実装済みの `/presets/<category>` エンドポイントをそのまま使用する。

```
GET    /presets/negative          ← ネガティブプリセット一覧
GET    /presets/negative/<n>      ← 指定プリセット取得
POST   /presets/negative/<n>      ← 保存
DELETE /presets/negative/<n>      ← 削除
```

新規エンドポイントの追加はなし。

### ネガティブプリセットのデータスキーマ

```json
{
  "neg_extra_tags": ["bad anatomy", "worst quality"],
  "neg_style_tags": ["@bad_artist"],
  "neg_extra_note": ""
}
```

### 保存先 / Storage

| 種別 | パス |
|------|------|
| ネガティブプリセット | `presets/negative/<n>.json`（新規） |
| 既存ネガティブExtraタグ | `settings/neg_extra_tags.json`（変更なし） |
| 既存ネガティブスタイルタグ | `settings/neg_style_tags.json`（変更なし） |

設定ファイル（`pipeline_config.json`）への変更はなし。

---

## i18n 対応

- [ ] UIラベルを i18n 辞書に追加（上記 Labels 表の全項目）
- [ ] JA / EN 往復切替（JA→EN→JA）で表示が崩れないことを確認

---

## 既存機能との互換性

- **`neg_extra_tags.json` / `neg_style_tags.json` への影響:** なし。引き続き動作する。
- **既存セッション（`anima_session_last.json`）への影響:** ネガティブプリセット名のフィールドは追加しない（セッション復元時にプリセットを自動適用する機能は今回スコープ外）。
- **INPUT-4 composite プリセットへの影響:** なし。将来 composite に `negative` を追加する際の拡張ポイントとして設計しておく。
- **`pipeline_config.json` スキーマ変更の有無:** なし。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
| プリセットファイルが存在しない | プリセットが見つかりません | Preset not found | `[INPUT-5]` |
| JSON パースエラー | プリセットファイルが破損しています | Preset file is corrupted | `[INPUT-5]` |
| 同名プリセットへの上書き | 同名のプリセットが存在します。上書きしますか？ | Overwrite existing preset? | — |

---

## Acceptance Criteria / 完了基準

1. ネガティブプリセットの保存・読込・削除が正常に動作する
2. プリセット読込時にネガティブExtraタグ・スタイルタグ・追記文が復元される
3. 既存の `neg_extra_tags.json` / `neg_style_tags.json` の動作が壊れない
4. `presets/negative/` ディレクトリが存在しない場合に自動作成される
- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）で正常に表示・操作できる
- [ ] 既存プリセット・セッションの読み込みが壊れない

---

## Test Plan / テスト計画

### Manual

- ネガティブタグを設定した状態でプリセット保存 → `presets/negative/` にJSONが生成されること
- プリセットを読込 → ネガティブ設定が復元されること
- プリセットを削除 → 一覧から消えること
- 既存の `neg_extra_tags.json` / `neg_style_tags.json` が引き続き動作すること

### Edge Cases

- プリセットが0件のとき（ドロップダウンが空でも操作可能か）
- `presets/negative/` が存在しない状態で起動したとき（自動作成されるか）
- 全フィールドが空のプリセットを保存・読込したとき

### Regression

- 既存キャラプリセット・シーンプリセット等（INPUT-4）の動作が壊れていないか
- セッション自動保存・復元が正常に動作するか
- 言語切替（JA↔EN）が往復で正常に動作するか

---

## Rollout / Migration

- **既存ユーザーへの影響:** 初回起動時に `presets/negative/` が自動作成される（INPUT-4の `presets/` 以下に追加されるだけ）。既存設定への影響なし。
- **移行処理:** なし
- **`pipeline_config.default.json` への追加:** なし
- **`Update.md` への記載:** 実装と同じコミットで `docs/updates/Update.md` へ追記する

---

## Open Questions / 未決事項

- composite プリセットに `negative` を将来追加する場合のスキーマ拡張方法（INPUT-4の composite スキーマに `negative` キーを追加するだけで対応可能な設計にしておく）

---

## 関連ファイル / Related Files

| ファイル | 役割 |
|---------|------|
| `anima_pipeline.py` | メインスクリプト（API・UI両方） |
| `presets/negative/` | ネガティブプリセット保存先（新規） |
| `settings/neg_extra_tags.json` | 既存ネガティブExtraタグ（変更なし） |
| `settings/neg_style_tags.json` | 既存ネガティブスタイルタグ（変更なし） |
| `docs/specs/feature_INPUT-4_preset_hierarchy.md` | 依存仕様（プリセット階層化） |
| `docs/updates/Update.md` | 実装後の変更ログ |
