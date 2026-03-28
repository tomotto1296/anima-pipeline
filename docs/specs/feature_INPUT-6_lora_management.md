# Feature Spec: INPUT-6 LoRA管理強化

## Meta

- Issue: #（未採番）
- Roadmap No.: INPUT-6
- Roadmap Priority: MUST (High)
- Owner:
- Status: Draft
- Version: v1
- Last Updated: 2026-03-28
- Target Version: v1.5.1

---

## Goal / 目的

現在のLoRAセクションはドロップダウン選択と強度入力のみで、LoRA数が増えると目的のLoRAを探すのに時間がかかる。検索・お気に入り・推奨weightの表示を追加し、日常的なLoRA選択を高速化する。

---

## Scope

- **In Scope:**
  - LoRAドロップダウンにインクリメンタル検索（テキスト入力でフィルタ）
  - お気に入り登録・解除（LoRAカードにスター表示）
  - お気に入りを一覧の先頭に表示
  - 推奨weight表示（LoRAファイル名またはメタデータから推定）
  - お気に入りの永続保存（`settings/lora_favorites.json`）

- **Out of Scope:**
  - CivitaiからのLoRA自動DL（OUTPUT-10・SKIP）
  - LoRA使用頻度統計（OUTPUT-7・LOW）
  - LoRAのタグ付け・カテゴリ分類
  - 推奨weightのCivitai APIからの自動取得

---

## User Story

> As a ヘビーユーザー, I want よく使うLoRAをすぐ見つけて選べる, so that LoRAが増えても選択にストレスがかからない.

---

## Requirements / 要件

1. LoRAスロットのドロップダウンの上に検索ボックスを追加し、入力した文字列でLoRA一覧をリアルタイムフィルタする。
2. LoRAカードにスターボタンを追加し、クリックでお気に入り登録・解除できる。
3. LoRA一覧表示時、お気に入りを先頭にグループ表示し、それ以外はアルファベット順に続く。
4. お気に入りは `settings/lora_favorites.json`（LoRAファイル名の配列）に永続保存する。
5. 推奨weight表示: LoRAファイル名に `_w0.8` などのパターンがある場合はそれを表示。なければデフォルト1.0をグレーで表示。
6. `settings/lora_favorites.json` が存在しない場合は空配列として扱う（自動作成は不要）。

---

## UI/UX

### 表示場所 / Screen

`▶ LoRA` セクション内、各スロット行

### 変更点 / Changes

```
[🔄 LoRA一覧取得]

[検索: ___________]           <- 新規追加（全スロット共通）

Slot 1: [★ | DropDown v] 強度 [1.00] 推奨: 0.8   <- ★ボタン追加・推奨weight表示
Slot 2: [★ | DropDown v] 強度 [1.00]
...

★ = お気に入り登録済み（黄）/ ☆ = 未登録（グレー）
```

### Labels (JA / EN)

| JA | EN |
|----|-----|
| LoRA検索 | Search LoRA |
| お気に入り | Favorites |
| 推奨 | Recommended |
| お気に入りに追加 | Add to favorites |
| お気に入りから削除 | Remove from favorites |

---

## API / Data

### 新規エンドポイント

#### `GET /lora_favorites`

お気に入りLoRA一覧を返す。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `favorites` | array | LoRAファイル名の配列 |
| `status` | string | `"ok"` または `"error"` |

---

#### `POST /lora_favorites`

お気に入りLoRA一覧を保存する。

**Request（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `favorites` | array | LoRAファイル名の配列 |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |

---

### 保存先 / Storage

| 種別 | パス |
|------|------|
| お気に入り | `settings/lora_favorites.json` |

### 設定デフォルト値

`pipeline_config.default.json` への追加なし。

---

## i18n 対応

- [ ] UIラベルを i18n 辞書に追加（上記 Labels 表の全項目）
- [ ] JA / EN 往復切替（JA→EN→JA）で表示が崩れないことを確認

---

## 既存機能との互換性

- **既存LoRAスロット（`lora_name_0`〜）:** 変更なし。セッション保存・復元も引き続き動作する。
- **既存の `GET /lora_list`:** 変更なし。返却データにお気に入りフラグを付加する場合はオプション対応。
- **`pipeline_config.json` スキーマ変更の有無:** なし。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
| お気に入り保存失敗 | お気に入りの保存に失敗しました | Failed to save favorites | `[INPUT-6]` |
| お気に入り読込失敗 | お気に入りの読み込みに失敗しました | Failed to load favorites | `[INPUT-6]` |

---

## Acceptance Criteria / 完了基準

1. 検索ボックスに入力するとLoRAドロップダウンがリアルタイムでフィルタされる
2. スターボタンでお気に入り登録・解除ができ、`settings/lora_favorites.json` に保存される
3. LoRA一覧表示時にお気に入りが先頭にグループ表示される
4. 推奨weightがファイル名から読み取れる場合に表示される
5. 既存のLoRAスロット・セッション保存・復元が壊れない

---

## Checklist / チェックリスト

- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）で正常に表示・操作できる
- [ ] 既存のLoRAスロット・セッション保存が壊れない
- [ ] ログに秘匿情報が出力されない

---

## Test Plan / テスト計画

### Manual

- 検索ボックスに文字入力 → ドロップダウンがフィルタされること
- スターボタンクリック → お気に入り登録され先頭に表示されること
- 再起動後にお気に入りが保持されること
- ファイル名に `_w0.8` パターンがあるLoRAで推奨weight `0.8` が表示されること

### Edge Cases

- LoRAが0件のとき（検索ボックスが空でも表示が崩れないか）
- `lora_favorites.json` が存在しない状態での起動
- 検索結果が0件のとき

### Regression

- 既存のLoRAスロットへの選択・強度設定が正常に動作するか
- セッション保存・復元でLoRAスロットが正しく復元されるか
- 言語切替（JA↔EN）が往復で正常に動作するか

---

## Rollout / Migration

- **既存ユーザーへの影響:** `lora_favorites.json` がない場合は空配列として動作。既存設定への影響なし。
- **移行処理:** なし
- **`pipeline_config.default.json` への追加:** なし
- **`Update.md` への記載:** 実装と同じコミットで追記する

---

## Open Questions / 未決事項

- 推奨weightのパターンを `_w0.8` 以外にも対応するか（例: `(0.8)` など）
- お気に入りをLoRAプリセット（INPUT-4の `lora` カテゴリ）と統合するか（今回はスコープ外）

---

## Related Files / 関連ファイル

| ファイル | 役割 |
|---------|------|
| `frontend/index.html` | LoRAセクションUI |
| `core/handlers.py` | `/lora_favorites` エンドポイント追加 |
| `settings/lora_favorites.json` | お気に入り保存先（新規） |
| `docs/updates/Update.md` | 実装後の変更ログ |
