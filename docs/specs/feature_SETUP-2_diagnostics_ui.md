# Feature Spec: SETUP-2 失敗時の自己診断UI（エラー原因候補・ノード不足警告）

## Meta

- Issue: #20
- Roadmap No.: SETUP-2
- Roadmap Priority: MUST（★★☆）
- Owner:
- Status: Draft
- Version: v1
- Last Updated: 2026-03-23
- Target Version: v1.4.8

---

## Goal / 目的

初回セットアップや設定変更後に生成が失敗したとき、ユーザーが原因を特定するのに時間がかかる。接続テスト・設定検証・ワークフローノード確認を一か所でまとめて実行し、問題の原因候補と対処法をUIに表示する。

---

## Scope

- **In Scope:**
  - ComfyUI 接続・LLM 接続・ワークフローJSON・Node ID・LoRAノード数の検証
  - 各チェック項目の結果（OK / WARNING / ERROR）とその対処法をUI表示
  - 「診断を実行」ボタンで全チェックを一括実行
  - 既存の `🔌 ComfyUI 接続テスト` / `🤖 LLM 接続テスト` との統合（重複排除）
- **Out of Scope:**
  - ComfyUI のノード自動インストール
  - Python 依存パッケージの自動修復
  - ログ収集・送信機能（既存のログ機能で対応済み）

---

## User Story

> As a 初回ユーザー, I want セットアップ後に「診断を実行」ボタンを押すだけで問題箇所と対処法がわかる, so that ComfyUIのノード不足や設定ミスで詰まる時間を減らせる.

> As a ユーザー, I want 生成失敗後に原因候補が表示される, so that ログを読まなくても何が問題かすぐわかる.

---

## Requirements / 要件

1. 「診断を実行」ボタンを `▶ 設定` パネル内の接続テストボタン付近に追加する。
2. 以下の項目を順番にチェックし、結果を一覧表示する:

| チェック項目 | 判定基準 |
|-------------|---------|
| ComfyUI 接続 | `/test_connection?target=comfyui` が OK か |
| LLM 接続 | `/test_connection?target=llm` が OK か（LLM未設定の場合はSKIP） |
| ワークフローJSON | 指定パスにファイルが存在し、JSONとして読み込めるか |
| Positive Node ID | ワークフロー内に設定済みのNode IDが存在するか |
| Negative Node ID | 同上 |
| KSampler Node ID | 同上 |
| LoRAノード数 | ワークフロー内の LoraLoader ノード数と設定スロット数の整合 |
| output_dir | ComfyUI outputフォルダが設定されているか（WebP変換時のみ必須） |

3. 各チェック結果は `✅ OK` / `⚠ WARNING` / `❌ ERROR` で表示し、ERROR・WARNINGには対処法の文言を添える。
4. 全チェック完了後に「問題なし」または「X件の問題が見つかりました」のサマリーを表示する。
5. 既存の `🔌 ComfyUI 接続テスト` / `🤖 LLM 接続テスト` ボタンは残す（診断の内訳として流用）。

---

## UI/UX

### 表示場所 / Screen

`▶ 設定` パネル内、既存の接続テストボタンの下

### 変更点 / Changes

```
[🔌 ComfyUI 接続テスト]  [🤖 LLM 接続テスト]   ← 既存（維持）

[🔍 セットアップ診断を実行]                       ← 新規追加

診断結果:
  ✅ ComfyUI 接続: OK (Python 3.11.x)
  ✅ LLM 接続: OK (Gemini)
  ✅ ワークフローJSON: 読み込みOK
  ✅ Positive Node ID (11): 検出OK
  ✅ Negative Node ID (12): 検出OK
  ✅ KSampler Node ID (19): 検出OK
  ⚠ LoRAノード: ワークフロー内に LoraLoader が見つかりません
     → LoRA×4対応ワークフロー（image_anima_preview_Lora4.json）を使用してください
  ⚠ output_dir: 未設定
     → WebP変換を使う場合は ComfyUI output フォルダを設定してください

⚠ 2件の警告があります
```

### 文言 / Labels

| JA | EN |
|----|-----|
| セットアップ診断を実行 | Run Setup Diagnostics |
| 診断結果 | Diagnostics Result |
| 診断中... | Running diagnostics... |
| 問題なし | No issues found |
| 件の問題が見つかりました | issue(s) found |
| 件の警告があります | warning(s) found |
| ComfyUI 接続 | ComfyUI Connection |
| LLM 接続 | LLM Connection |
| ワークフローJSON | Workflow JSON |
| Node ID検出 | Node ID Detection |
| LoRAノード | LoRA Nodes |
| output_dir | Output Directory |

---

## API / Data

### 新規エンドポイント

```
GET /diagnostics
```

全チェック項目を実行して結果を返す。

**Response（JSON）**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `status` | string | `"ok"` または `"error"` |
| `results` | array | チェック結果の配列（下記参照） |
| `summary` | object | `{ "errors": N, "warnings": N }` |

**チェック結果オブジェクト**

| フィールド | 型 | 説明 |
|-----------|---|------|
| `key` | string | チェック項目キー（`comfyui` / `llm` / `workflow` / `pos_node` / `neg_node` / `ksampler` / `lora_nodes` / `output_dir`） |
| `label` | string | 表示名（JA） |
| `level` | string | `"ok"` / `"warning"` / `"error"` / `"skip"` |
| `message` | string | 結果メッセージ |
| `hint` | string | 対処法（WARNING / ERROR 時のみ） |

### 既存エンドポイントへの変更

- `GET /test_connection`: 変更なし。`/diagnostics` の内部で呼び出して結果を流用する。

### 保存先 / Storage

なし（診断結果は都度取得・表示のみ。永続化しない）。

---

## i18n 対応

- [ ] UIラベルを i18n 辞書に追加（上記 Labels 表の全項目）
- [ ] チェック結果の `message` / `hint` 文言を JA/EN 両対応
- [ ] JA / EN 往復切替（JA→EN→JA）で表示が崩れないことを確認

---

## 既存機能との互換性

- **既存の接続テストボタン:** 残す。`/diagnostics` はこれらを内部で活用する。
- **既存の設定パネル:** 接続テストボタンの下に診断ボタンを追加するだけ。既存レイアウト変更なし。
- **`pipeline_config.json` スキーマ変更の有無:** なし。

---

## Error Handling / エラー処理

| 想定エラー | 表示文言（JA） | 表示文言（EN） | ログ出力 |
|-----------|-------------|-------------|---------|
| 診断中に予期せぬエラー | 診断中にエラーが発生しました | An error occurred during diagnostics | `[SETUP-2]` |
| ComfyUI未起動 | ComfyUIに接続できません。起動しているか確認してください | Cannot connect to ComfyUI. Please check if it is running. | — |
| ワークフローJSONが見つからない | ワークフローJSONが見つかりません。パスを確認してください | Workflow JSON not found. Please check the path. | — |
| Node IDが見つからない | Node ID (XX) がワークフロー内に見つかりません | Node ID (XX) not found in workflow | — |

---

## Acceptance Criteria / 完了基準

1. 「診断を実行」ボタンを押すと全チェック項目が実行され、結果が一覧表示される
2. ERROR・WARNING にはそれぞれ対処法の文言が表示される
3. 全チェックOKの場合は「問題なし」が表示される
4. ComfyUI未起動・ワークフロー未設定・Node ID不一致などの典型的な失敗ケースで適切な診断結果が出る
5. 既存の接続テストボタンが引き続き動作する
- [ ] JA / EN 言語切替で表示が崩れない
- [ ] スマホ（モバイルUI）で正常に表示できる
- [ ] ログに秘匿情報が出力されない

---

## Test Plan / テスト計画

### Manual

- ComfyUI起動中に診断実行 → ComfyUI接続がOKになること
- ComfyUI未起動で診断実行 → ComfyUI接続がERRORになり対処法が表示されること
- 存在しないワークフローJSONパスで診断実行 → ERRORと対処法が表示されること
- LoRAなしワークフローでLoRAスロットを設定した状態で診断 → WARNINGが表示されること
- LLM未設定で診断実行 → LLM接続がSKIPになること
- 全設定が正常な状態で診断 → 全項目OKになること

### Edge Cases

- ワークフローJSONが破損している場合
- Node IDが空文字列の場合
- output_dir が設定されているが存在しないパスの場合

### Regression

- 既存の `🔌 ComfyUI 接続テスト` / `🤖 LLM 接続テスト` ボタンが動作するか
- 設定パネルの既存レイアウトが崩れていないか
- 言語切替（JA↔EN）が往復で正常に動作するか

---

## Rollout / Migration

- **既存ユーザーへの影響:** 設定パネルに診断ボタンが追加されるのみ。既存機能への影響なし。
- **移行処理:** なし
- **`pipeline_config.default.json` への追加:** なし
- **`Update.md` への記載:** 実装と同じコミットで `docs/updates/Update.md` へ追記する

---

## Open Questions / 未決事項

- output_dir が未設定の場合を ERROR にするか WARNING にするか（WebP変換を使わないユーザーには不要なため WARNING が適切か）
- 将来的に診断結果をログに自動保存するか（現状は表示のみ）

---

## 関連ファイル / Related Files

| ファイル | 役割 |
|---------|------|
| `anima_pipeline.py` | メインスクリプト（API・UI両方） |
| `settings/pipeline_config.json` | 接続先・Node ID等の設定参照 |
| `docs/specs/feature_api_v1.md` | 既存APIリファレンス（`/test_connection` 参照） |
| `docs/updates/Update.md` | 実装後の変更ログ |
