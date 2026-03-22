# Feature Spec: INPUT-12 キャラ名・作品名の日英欄分離

## Meta

- Issue: #17
- Roadmap No.: INPUT-12
- Roadmap Priority: MUST（★★☆）
- Owner:
- Status: Approved
- Version: v1
- Last Updated: 2026-03-23
- Target Version: v1.4.9

---

## Goal / 目的

現在のキャラ名・作品名欄は水色（日本語OK）の1欄のみで、LLMなし生成時に日本語を入力すると `name_(series)` 形式への変換が壊れる。日本語欄（LLM用）と英語欄（Danbooru直接入力用）を分離し、LLMあり・なし両方で正しく動作するようにする。

---

## Scope

- **In Scope:**
  - キャラ名・作品名それぞれに日本語欄（水色）と英語欄（緑）を追加
  - 英語欄が空の場合は日本語欄をフォールバックで変換する現行挙動を維持
  - プリセットJSONに `name_en` / `series_en` キーを追加
  - 既存プリセット（`name_en` / `series_en` なし）のフォールバック読み込み対応
  - `collectCharaData()` / `collectSessionData()` への反映
  - LLMあり・なし両方の生成フローへの反映
- **Out of Scope:**
  - 英語欄へのDanbooruタグ予測補完（INPUT-12フェーズ2として別途実装）
  - キャラプリセット自動生成（`/generate_preset`）は今回変更なし（Out of Scope）

---

## User Story

> As a ユーザー, I want キャラ名・作品名を日本語と英語で別々に入力できる, so that LLMなし生成でも正しいDanbooruタグが出力される.

> As a LLMなしユーザー, I want 英語欄にDanbooruタグを直接入力できる, so that 日本語変換ミスなしに正確なプロンプトを送れる.

---

## Requirements / 要件

1. キャラ名・作品名それぞれに **日本語欄**（水色・既存）と **英語欄**（緑・新規）を追加する。
2. LLMあり生成時は**日本語欄**をLLMに渡す（現行と同じ）。
3. LLMなし生成時は**英語欄**を優先してDanbooruタグに使用する。英語欄が空の場合は日本語欄をフォールバックで `name_(series)` 形式に変換する（現行挙動を維持）。
4. プリセットJSONに `name_en` / `series_en` キーを追加する。既存プリセットにこれらのキーがない場合は空文字列として扱う（マイグレーション不要）。
5. `collectCharaData()` に `name_en` / `series_en` を追加し、セッション保存・復元にも反映する。

---

## UI/UX

### 表示場所 / Screen

各キャラブロックの上部、キャラ名・作品名入力エリア

### 変更点 / Changes

**変更前:**
```
キャラ名  [水色欄──────────────]
作品名    [水色欄──────────────]
```

**変更後:**
```
キャラ名  [水色欄（日本語）─────] [緑欄（English / Danbooru tag）─]
作品名    [水色欄（日本語）─────] [緑欄（English / Danbooru tag）─]
```

- 日本語欄は既存の水色欄をそのまま維持
- 英語欄はスマホでも折り返さず横並び、または2段に収まるレイアウト
- 英語欄のプレースホルダー: `e.g.: hakurei_reimu` / `e.g.: touhou`

### 文言 / Labels

| JA | EN |
|----|-----|
| キャラ名 JA | Name JA |
| キャラ名 EN | Name EN |
| 作品名 JA | Series JA |
| 作品名 EN | Series EN |

> 短縮表記（`JA` / `EN`）を採用。スマホでの表示崩れ防止とスペース節約のため。

---

## API / Data

### 既存エンドポイントへの変更

新規エンドポイントの追加はなし。既存の処理フローへの変更のみ。

**`collectCharaData(idx)` への追加:**
```javascript
ch.name_en   = (document.getElementById(`chara_name_en_${idx}`)  ||{value:''}).value.trim();
ch.series_en = (document.getElementById(`chara_series_en_${idx}`)||{value:''}).value.trim();
```

**LLMなし生成時のタグ変換ロジック変更:**
```javascript
// 変更前
const namePart   = ch.name.toLowerCase().replace(/\s+/g,'_')...
const seriesPart = (ch.series||'').toLowerCase()...

// 変更後
const nameSource   = ch.name_en   || ch.name;   // 英語欄優先、空ならJA欄フォールバック
const seriesSource = ch.series_en || ch.series;
const namePart   = nameSource.toLowerCase().replace(/\s+/g,'_')...
const seriesPart = seriesSource.toLowerCase()...
```

### プリセットJSONスキーマ変更

`chara/<n>.json` の `data` オブジェクトに追加:

```json
{
  "name":       "博麗霊夢",
  "name_en":    "hakurei_reimu",
  "series":     "東方Project",
  "series_en":  "touhou",
  ...
}
```

> 既存プリセットに `name_en` / `series_en` が存在しない場合は `""` として扱う。読み込み時に補完処理不要（JSのオプショナルチェーン・デフォルト値で対応）。

### 保存先 / Storage

| 種別 | 変更内容 |
|------|---------|
| `chara/<n>.json` | `name_en` / `series_en` キーを追加 |
| `settings/anima_session_last.json` | `name_en` / `series_en` がセッションに含まれるようになる |

設定ファイル（`pipeline_config.json`）への変更はなし。

---

## i18n 対応

- [ ] 英語欄のプレースホルダー文言を i18n 辞書に追加
- [ ] ラベル文言（`キャラ名（English）` 等）を i18n 辞書に追加
- [ ] JA / EN 往復切替（JA→EN→JA）で表示が崩れないことを確認

---

## 既存機能との互換性

- **既存プリセット（`chara/*.json`）への影響:** `name_en` / `series_en` がないプリセットは空文字列として扱う。読み込み時にエラーにならない。
- **既存セッション（`anima_session_last.json`）への影響:** 旧セッションに `name_en` / `series_en` がない場合は空文字列として復元される。
- **LLMあり生成への影響:** 日本語欄をLLMに渡す挙動は変わらない。
- **LLMなし生成への影響:** 英語欄が入力されていれば精度向上。空なら現行と同じ挙動。
- **`/generate_preset`（自動プリセット生成）への影響:** 今回変更なし。Danbooru Wiki検索キーは `ch.name`（日本語欄）を引き続き使用。生成されたプリセットへの `name_en` / `series_en` 自動入力は別 Issue で検討。

---

## Error Handling / エラー処理

新規エラーケースはなし。英語欄が空の場合は既存の日本語欄フォールバックで処理される。

---

## Acceptance Criteria / 完了基準

1. 英語欄に入力した値がLLMなし生成時のDanbooruタグに反映される
2. 英語欄が空の場合、日本語欄フォールバックで従来通り動作する
3. プリセット保存時に `name_en` / `series_en` が保存される
4. 既存プリセット（`name_en` なし）を読み込んでもエラーにならない
5. セッション保存・復元で `name_en` / `series_en` が維持される
- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）で日英欄が正常に表示・入力できる
- [ ] 既存プリセット・セッションの読み込みが壊れない

---

## Test Plan / テスト計画

### Manual

- 日本語欄のみ入力してLLMなし生成 → 日本語欄がフォールバックで変換されること
- 英語欄に `hakurei_reimu` と入力してLLMなし生成 → 英語欄の値がそのまま使われること
- 英語欄あり・なし両方でプリセット保存 → JSONに `name_en` / `series_en` が入っていること
- 旧プリセット（`name_en` なし）を読み込み → エラーなく読み込まれること
- LLMあり生成 → 日本語欄の値がLLMに渡されること（英語欄は影響しない）

### Edge Cases

- 日本語欄・英語欄ともに空のとき（バリデーションは現行と同じ）
- 英語欄にスペース・特殊文字を含む場合
- 既存セッション復元時に `name_en` が存在しない場合

### Regression

- 既存プリセットの保存・読込・削除が正常に動作するか
- セッション自動保存・復元が正常に動作するか
- LLMあり・なし両方の生成が正常に完了するか
- 言語切替（JA↔EN）が往復で正常に動作するか

---

## Rollout / Migration

- **既存ユーザーへの影響:** 英語欄が新規追加されるが空欄のまま使える。既存の挙動は変わらない。
- **既存プリセットの移行:** 不要。`name_en` / `series_en` がないプリセットは空文字列として扱う。
- **`pipeline_config.default.json` への追加:** なし
- **`Update.md` への記載:** 実装と同じコミットで `docs/updates/Update.md` へ追記する

---

## フェーズ2（将来実装）

英語欄にDanbooruタグ予測補完を追加する。

- 英語欄入力中にDanbooru Wiki検索で候補を表示
- 候補クリックで英語欄に転記
- INPUT-2（衣装・髪型・ポーズ等の汎用補完）とは別軸の、キャラ名・作品名専用の補完として実装

---

## Open Questions / 未決事項

- ~~`/generate_preset` への `name_en` / `series_en` 自動入力~~ → 今回は変更なし。将来別 Issue で検討。

---

## 関連ファイル / Related Files

| ファイル | 役割 |
|---------|------|
| `anima_pipeline.py` | メインスクリプト（UI・API両方） |
| `chara/*.json` | キャラプリセット（`name_en` / `series_en` キー追加） |
| `settings/anima_session_last.json` | セッション保存先 |
| `docs/specs/feature_INPUT-4_preset_hierarchy.md` | 関連仕様（プリセット階層化） |
| `docs/updates/Update.md` | 実装後の変更ログ |
