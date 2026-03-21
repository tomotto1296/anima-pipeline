# Feature Spec: OUTPUT-4 メタデータ埋め込み強化（LoRA・ワークフローJSONバージョンも記録）

## Meta

- Issue: #8
- Roadmap No.: OUTPUT-4
- Roadmap Priority: HIGH
- Owner:
- Status: Implemented
- Version: v1
- Last Updated: 2026-03-22
- Target Version: v1.4.718

---

## Goal / 目的

画像生成時にプロンプト・モデル名・LoRA一覧・ワークフローJSONバージョンを画像メタデータとして埋め込む。WebP形式への変換オプションも提供し、Civitai等への投稿時に手動入力の手間を省く。

---

## Scope

- **In Scope:**
  - PNG / WebP 画像へのメタデータ埋め込み（プロンプト、ネガティブプロンプト、モデル名、LoRA一覧、ワークフローJSONバージョン）
  - 保存形式としてWebP変換を選択できるUIオプション
  - Civitai互換のメタデータフォーマット（`parameters` フィールド）
- **Out of Scope:**
  - クラウド分散処理（ローカル限定）
  - JPEG / AVIF など WebP・PNG 以外の形式
  - メタデータの後付け編集（生成時のみ対象）

---

## User Story

> As a 画像生成ユーザー, I want 生成画像にプロンプトやLoRA情報をメタデータとして自動埋め込みしたい, so that Civitaiなどへ画像をアップロードする際に手動入力の手間がなくなる.

---

## Requirements / 要件

1. 生成完了時、出力画像（PNG）にメタデータを埋め込む：
   - 正プロンプト（positive prompt）
   - ネガティブプロンプト（negative prompt）
   - モデル名（チェックポイント名）
   - 使用LoRA一覧（名前・重み）
   - ワークフローJSONバージョン（ファイル名またはバージョン識別子）
   - 生成パラメータ（steps, cfg, sampler, scheduler, seed）
2. `pipeline_config.json` に保存形式設定 `output_format`（`"png"` / `"webp"`）を追加する。
3. `output_format = "webp"` の場合、PNGをWebPに変換してメタデータを `Exif` または `XMP` で埋め込む。
4. Civitai互換フォーマット（`parameters` テキストブロック形式）でもメタデータを出力する。
5. LoRAが0件の場合も正常に動作する（空リストとして記録）。

---

## UI/UX

### 表示場所 / Screen
- `▶ 出力設定` パネル内（既存の保存先設定の近傍）

### 変更点 / Changes
- 保存形式セレクタを追加: `PNG` / `WebP`
- メタデータ埋め込みトグル（デフォルト: ON）を追加

### 文言 / Labels

| JA | EN |
|----|----|
| 保存形式 | Output Format |
| メタデータを埋め込む | Embed Metadata |
| PNG (標準) | PNG (default) |
| WebP (軽量・Civitai推奨) | WebP (smaller, Civitai-ready) |

> 既存ラベルとの整合は `anima_pipeline.py` 内の i18n 辞書を確認すること。

---

## API / Data

### 既存エンドポイントへの変更（ある場合）
- 変更対象: 画像保存処理（`/generate` または相当する生成フロー内）
- 変更内容: 保存前に `embed_metadata()` を呼び出し、設定に応じて PNG または WebP で書き出す

### 保存先 / Storage

| 種別 | パス / キー |
|------|------------|
| 設定ファイル | `settings/pipeline_config.json` → `output_format`, `embed_metadata` |
| その他 | 出力画像は既存の出力ディレクトリ（`output/` 等）に保存 |

### 設定デフォルト値（追加する場合）
`settings/pipeline_config.default.json` に追加するキーと初期値:

```json
{
  "output_format": "png",
  "embed_metadata": true
}
```

### メタデータ構造

```
Positive prompt: <prompt>
Negative prompt: <negative_prompt>
Steps: <steps>, Sampler: <sampler>, CFG scale: <cfg>, Seed: <seed>,
Model: <checkpoint_name>,
Lora hashes: "<lora_name>: <weight>, ...",
Workflow version: <workflow_json_version>
```

> PNG の場合は `tEXt` チャンク（`parameters` キー）へ格納。WebP の場合は Exif UserComment または XMP へ格納。

---

## i18n 対応

- [ ] UIラベルを i18n 辞書（`anima_pipeline.py` 内）に追加
- [ ] `保存形式` / `Output Format` の選択肢ラベル追加
- [ ] JA / EN 往復切替（JA→EN→JA）で確認

---

## 既存機能との互換性

- **既存プリセット（`chara/*.json`）への影響:** なし
- **既存セッション（`anima_session_last.json`）への影響:** なし
- **既存ワークフローJSONへの影響:** なし（読み取りのみ、バージョン情報を参照）
- **`pipeline_config.json` スキーマ変更の有無:** あり（`output_format`, `embed_metadata` を追加）

> スキーマ変更が発生するため、起動時に `output_format` / `embed_metadata` が存在しない場合はデフォルト値を補完する移行処理を `anima_pipeline.py` に実装すること。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
| WebP変換失敗（ライブラリ不足等） | WebP変換に失敗しました。PNGで保存します。 | WebP conversion failed. Saved as PNG. | `[OUTPUT-4] WebP conversion error: <detail>` |
| メタデータ書き込み失敗 | メタデータの埋め込みに失敗しました。画像は保存されます。 | Failed to embed metadata. Image saved without metadata. | `[OUTPUT-4] Metadata embed error: <detail>` |
| ワークフローJSONバージョン取得失敗 | ワークフローバージョンを取得できませんでした。 | Could not retrieve workflow version. | `[OUTPUT-4] Workflow version read error: <detail>` |

> APIキー・トークン・認証情報はログにマスクされることを確認すること（既存のマスク対象: `token`, `api key`, `authorization`, `bearer`）。

---

## Acceptance Criteria / 完了基準

1. [x] PNG保存時、`parameters` テキストチャンクにプロンプト・モデル・LoRA一覧・ワークフローバージョンが含まれている
2. [x] WebP変換オプションONの場合、出力がWebP形式であり、メタデータが埋め込まれている
3. [x] Civitaiへアップロードした際、プロンプト等が自動認識される（PNG・WebP両形式確認済み）
4. [x] 複数LoRAのメタデータがCivitaiに正しく表示される
5. [x] メタデータ埋め込みトグルOFFでメタデータなし保存が動作する
6. WebP変換失敗時はPNGにフォールバックし、エラーをユーザーに通知する
- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）で表示・操作が正常
- [ ] 既存プリセット・セッションの読み込みが壊れない
- [ ] ログに秘匿情報が出力されない

---

## Test Plan / テスト計画

### Manual
- [x] PNG形式で生成 → Civitaiにメタデータ・LoRAが表示されることを確認（複数LoRA含む）
- [x] WebP形式で生成 → Civitaiにメタデータ・LoRAが表示されることを確認（複数LoRA含む）
- [x] メタデータ埋め込みトグルOFF → メタデータなしで保存されることを確認

### Edge Cases
- LoRAが0件のとき
- ワークフローJSONが存在しないとき
- WebP変換ライブラリ（Pillow等）が利用不可のとき
- プロンプトに特殊文字・絵文字が含まれるとき
- ComfyUI未起動・LLM未設定のとき
- スマホ（同一Wi-Fi）からアクセスしたとき

### Regression
- 既存のプリセット保存・読込・削除が正常に動作するか
- セッション自動保存・復元が正常に動作するか
- 言語切替（JA↔EN）が往復で正常に動作するか
- PNG形式（デフォルト）での保存が従来通り動作するか

---

## Rollout / Migration

- **既存ユーザーへの影響:** 初回起動時に `output_format: "png"` / `embed_metadata: true` がデフォルト補完される（既存動作に影響なし）
- **`pipeline_config.default.json` への追加:** あり（`output_format`, `embed_metadata`）
- **移行処理:** あり（`pipeline_config.json` に該当キーが存在しない場合、デフォルト値を補完して保存）
- **`Update.md` への記載:** 実装後に `docs/updates/Update.md` へ追記する

---

## Open Questions / 未決事項

- ~~WebP のメタデータ埋め込み方式: Exif UserComment と XMP どちらを優先するか~~ → **決定・実機確認済み: PNG・WebP 両形式で Civitai にメタデータ・LoRA（複数含む）が正常表示された。** v1.4.718 で動作確認済み。
- ワークフローJSONバージョンの識別子形式: ファイル名・タイムスタンプ・手動バージョン文字列のどれを使うか
- `embed_metadata` トグルをUIに常時表示するか、詳細設定として折りたたむか

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
