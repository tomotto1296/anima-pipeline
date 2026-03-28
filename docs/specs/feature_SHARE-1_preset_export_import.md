# Feature Spec: SHARE-1 プリセット共有 zip Export/Import

## Meta

- Issue: #（未採番）
- Roadmap No.: SHARE-1
- Roadmap Priority: HIGH
- Owner:
- Status: Draft
- Version: v1
- Last Updated: 2026-03-28
- Target Version: v1.5.1

---

## Goal / 目的

作り込んだキャラプリセットを他のユーザーや別の環境に配布・移行できない。プリセットJSON＋サムネイルをzipにまとめてエクスポート・インポートできるようにする。

---

## Scope

- **In Scope:**
  - `chara/` プリセットの単体または複数選択でzip Export
  - zipにはJSON（`chara/<n>.json`）とサムネイル（`chara/<n>.webp`）を含める
  - zipのImport（zipを選択してプリセットを一括展開）
  - 同名プリセットが存在する場合の上書き確認
  - `presets/` カテゴリ（scene/camera/quality/lora/composite）のExport/Import

- **Out of Scope:**
  - URLコード共有（SHARE-2）
  - LoRA本体ファイルのExport
  - クラウドへのアップロード

---

## User Story

> As a ユーザー, I want 作ったキャラプリセットをzipで配布・受け取りできる, so that 別環境への移行やコミュニティ共有が楽になる.

---

## Requirements / 要件

1. 設定パネルまたはプリセット一覧UIに `Export Presets` ボタンを追加する。
2. Exportは `chara/` の全プリセット（JSON＋webp）をzipにまとめてダウンロードする。個別選択はフェーズ2とする。
3. `Import Presets` ボタンでzipファイルを選択し、中のJSONとwebpを `chara/` に展開する。
4. Import時に同名ファイルが存在する場合は上書き確認ダイアログを表示する。
5. `presets/` カテゴリ（scene/camera/quality/lora/composite）も同様にExport/Import対応する。
6. Export zipのファイル名は `anima-presets_YYYY-MM-DD.zip` とする。

---

## UI/UX

### 表示場所 / Screen

`▶ 設定` パネル内、キャラプリセット削除セクションの近く

### 変更点 / Changes

```
[Export Presets]  [Import Presets]   <- 新規追加
```

### Labels (JA / EN)

| JA | EN |
|----|-----|
| プリセットをエクスポート | Export Presets |
| プリセットをインポート | Import Presets |
| エクスポート成功 | Export successful |
| インポート成功 | Import successful |
| 同名のプリセットが存在します。上書きしますか？ | A preset with the same name already exists. Overwrite? |

---

## API / Data

### 新規エンドポイント

#### `GET /presets_export`

`chara/` と `presets/` の全ファイルをzip化してダウンロードさせる。

**Response:** ZIPファイル（`Content-Type: application/zip`、`Content-Disposition: attachment`）

---

#### `POST /presets_import`

zipファイルを受け取り、`chara/` と `presets/` に展開する。

**Request:** `multipart/form-data`（`file` フィールドにzipを添付）

**Query Parameters**

| パラメータ | 型 | 説明 |
|----------|---|------|
| `overwrite` | boolean | `true` の場合は同名ファイルを上書き。省略時は `409` を返す |

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `imported` | number | インポートしたファイル数 |
| `skipped` | number | スキップしたファイル数 |
| `error` | string | エラー時のメッセージ |

**HTTP ステータス**

| コード | 状況 |
|--------|------|
| 200 | インポート成功 |
| 409 | 同名ファイルが存在し `overwrite` 未指定 |
| 400 | zipの形式不正 |
| 500 | サーバーエラー |

---

### 保存先 / Storage

| 種別 | パス |
|------|------|
| キャラプリセット | `chara/<n>.json` / `chara/<n>.webp` |
| カテゴリプリセット | `presets/<category>/<n>.json` |

---

## i18n 対応

- [ ] UIラベルを i18n 辞書に追加（上記 Labels 表の全項目）
- [ ] JA / EN 往復切替（JA→EN→JA）で表示が崩れないことを確認

---

## 既存機能との互換性

- **既存プリセット（`chara/*.json`）:** Import時に既存ファイルを上書きしない限り影響なし。
- **`pipeline_config.json` スキーマ変更の有無:** なし。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
| Export失敗 | エクスポートに失敗しました | Export failed | `[SHARE-1]` |
| Import失敗 | インポートに失敗しました | Import failed | `[SHARE-1]` |
| zip形式不正 | zipファイルが正しくありません | Invalid zip file | `[SHARE-1]` |
| 同名ファイル存在（overwrite未指定） | 同名のプリセットが存在します。上書きしますか？ | Preset already exists. Overwrite? | — |

---

## Acceptance Criteria / 完了基準

1. Export ボタンでプリセットzip（JSON＋webp）がダウンロードされる
2. Import ボタンでzipを選択してプリセットが展開される
3. 同名プリセット存在時に上書き確認ダイアログが表示される
4. 既存プリセットの動作が壊れない

---

## Checklist / チェックリスト

- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）で正常に表示・操作できる
- [ ] 既存プリセット・セッションの読み込みが壊れない

---

## Test Plan / テスト計画

### Manual

- Export ボタン → zipがダウンロードされ、中にJSON＋webpが含まれること
- ダウンロードしたzipを別環境でImport → プリセットが展開されること
- 同名プリセットがある状態でImport → 上書き確認ダイアログが表示されること

### Edge Cases

- プリセットが0件の状態でExport（空のzipが生成されるか）
- webpがないプリセットのExport（JSONのみでも動作するか）
- 壊れたzipをImportしようとした場合

### Regression

- 既存プリセットの保存・読込・削除が正常に動作するか
- 言語切替（JA↔EN）が往復で正常に動作するか

---

## Rollout / Migration

- **既存ユーザーへの影響:** なし。Import時のみ既存ファイルへの影響が発生する（確認ダイアログあり）。
- **移行処理:** なし
- **`pipeline_config.default.json` への追加:** なし
- **`Update.md` への記載:** 実装と同じコミットで追記する

---

## Open Questions / 未決事項

- プリセットの個別選択Export（チェックボックスで選択）はフェーズ2とする
- `presets/sessions/` もExport対象に含めるか

---

## Related Files / 関連ファイル

| ファイル | 役割 |
|---------|------|
| `frontend/index.html` | Export/ImportボタンUI |
| `core/handlers.py` | `/presets_export` / `/presets_import` エンドポイント追加 |
| `chara/` | キャラプリセット保存先 |
| `presets/` | カテゴリプリセット保存先 |
| `docs/updates/Update.md` | 実装後の変更ログ |
