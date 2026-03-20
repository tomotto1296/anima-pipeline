# Update Log (from v1.4.6)

## 目的
このドキュメントは、`v1.4.6` 以降の変更内容を次の開発者へ引き継ぐための要約です。

## バージョン運用ルール
- 細かい修正ごとに小数点以下を増分（例: `1.4.7 -> 1.4.71 -> 1.4.72`）
- `1.4.699x` 系は `1.4.7` として正式リリース済み

## 現在バージョン
- `1.4.7`（正式リリース）

## 実装サマリー（v1.4.6以降）

### 1) 起動不良・文字化け修正
- `SyntaxError`（文字列終端不正）を修正
- UTF-8/BOM混在による読み込みエラーを修正
- BAT起動時の文字化けを抑制する方向で調整

### 2) プリセット読み込み安定化
- `000_default.json` が出ない不具合を修正
- `/chara_presets` で `utf-8-sig` 読み込み対応

### 3) UI言語切替（日本語/英語）
- 初期表示言語をOS言語ベースで自動決定
- UIボタンで日本語/英語を切替可能
- `localStorage` に言語設定を保存
- 表示テキストを動的に置換するi18nロジックを追加
- 正規化置換（全角/半角カッコ、`+`、空白差）に対応
- 英語->日本語へ戻した際に残る文言の取りこぼしを継続修正

### 4) UIラベル調整（短縮/統一）
- 画面幅に合わせて英語ラベルを短縮
- 例:
  - `Open Eyes -> Open`
  - `Half-Closed Eyes -> Half-Closed`
  - `Closed Eyes -> Closed`
  - `DELETE -> DEL`
- Bust/Height/Legs/Tail/Wings/View 等の表記をUI設計に合わせて調整

### 5) STATUS/進捗文言の多言語対応
- ステータス表示を言語切替に追従
- 例:
  - `LLM: Done`
  - `ComfyUI: 1 queued`
  - `ComfyUI: Generating... 7%`
- 動的生成文言（数値含む）の日本語化パターンを追加

### 6) コンソール表示言語
- コンソールの `[接続確認]` 以降はOS言語に追従する仕様へ変更
- UI言語とコンソール言語は用途上分離可能だが、現行はOS基準で統一寄り

### 7) ログ機能（配布先エラー回収向け）
- ログ出力を追加（配布先トラブルの回収用途）
- 既定ログ保存先: `anima-pipeline/logs/`
- マスク対象:
  - `token`
  - `api key`
  - `authorization`
  - `Bearer ...`
- 保持期間による自動削除を実装（初期値30日）
- ログレベルを追加（`normal` / `debug`）
- 例外フックで未処理例外をログ化
- API追加:
  - `GET /logs_info`
  - `GET /logs_zip`
- UI追加:
  - `LOG DIRECTORY`
  - `LOG RETENTION DAYS`
  - `LOG LEVEL`
  - `OPEN LOGS`
  - `EXPORT LOGS ZIP`

### 8) 設定デフォルトの更新
`settings/pipeline_config.default.json` に追加:
- `console_lang`
- `log_dir`
- `log_retention_days`（初期値30）
- `log_level`

### 9) ドキュメント整備（引き継ぎ/公開向け）
- `README.md` をUTF-8で再整理（現行機能・ログ機能・v1.4.7準備を反映）
- `README_EN.md` を再整備（日本語版と同等の構成に統一）
- `release_notes_v1.4.699999.md` を作成し、日本語/英語併記化
- `note_article_draft.md` を「変更価値中心 + 手順はガイド参照」方針で更新
- 関連ファイルとして `note_article_draft_v1.4.699999.md` / `anima_pipeline_guide_addendum_v1.4.699999.md` を作成
- デバッグ用空ファイル `_debug_page.html` を削除

## 主な変更ファイル
- `anima_pipeline.py`
- `start_anima_pipeline.bat`
- `start_anima_pipeline - Tailscale.bat`
- `settings/pipeline_config.default.json`
- `README.md`
- `README_EN.md`
- `release_notes_v1.4.699999.md`（追加）
- `note_article_draft.md`
- `note_article_draft_v1.4.699999.md`（追加）
- `anima_pipeline_guide_addendum_v1.4.699999.md`（追加）
- `LLM_candidates.md`（追加）
- `docs/updates/Update.md`

## 運用上の注意
- `releases` は配布用テスト環境のため、今後は編集しない
- UIは見た目だけでなく、言語切替の往復（JA->EN->JA / EN->JA->EN）で確認する

## 残タスク（次開発者向け）
- コンソールの全メッセージをUI言語と完全連動させるか、OS連動固定にするか仕様確定
- i18nキーの網羅テスト（特に動的生成ラベル）
- 配布ビルドでのログZIP取得導線の最終UX調整

## 直近追記（v1.4.6999991 ～ v1.4.6999996）

### 10) 起動BATの安定化（通常版 + Tailscale版）
- `start_anima_pipeline.bat` / `start_anima_pipeline - Tailscale.bat` を更新
- UTF-8コンソール対策を追加（`chcp 65001` / `PYTHONUTF8=1`）
- `setlocal/endlocal` を追加し環境変数の影響を局所化
- `py` 呼び出しを `py -3` に固定
- Tailscale版に `tailscale ip -4` 検出とURL表示を追加

### 11) README/README_EN 整備
- `README.md` を全面整理（文字化け除去、現行機能とv1.4.7準備を反映）
- `README_EN.md` を同等構成で再整備
- `README.md` の関連記事表記を統一（`zenn:` 形式）

### 12) UI文言短縮（英語表示）
- `Bird's-Eye View` / `Worm's-Eye View` → `Bird's-Eye` / `Worm's-Eye`
- `Large Frame` → `Large`
- `Very Long` / `Bob Cut` → `VLong` / `Bob`

### 13) 髪型ボタンの視認性改善
- 髪型グループ `全体` を2段レイアウト化
- 髪型グループ `後ろ` も2段レイアウト化
- 日本語UI/英語UIの両方で同様に適用

## 直近追記（v1.4.69999961 ～ v1.4.69999977）

### 14) Issue #2 着手（プリセット一覧＋サムネ基盤）
- `キャラ` セクション内に「プリセット一覧（サムネイル）」UIを仮実装
- ギャラリーモーダルに「プリセットのサムネイル作成」ボタンを追加
- API追加:
  - `POST /chara_preset_thumb`（ギャラリー画像 -> `chara/<preset>.webp` 生成）
  - `GET /chara_thumb?file=...`（プリセットサムネ配信）
- `/chara_presets` 応答に `_thumb_path` を追加
- プリセット削除時に同名 `.webp` も削除

### 15) サムネ生成・表示不具合の修正
- `source image not found` の原因を修正
  - `view URL` 解析前にパス変換していた不具合を解消
  - `view URL` / ローカルパス両対応
- ギャラリー非表示化不具合を修正（`view_urls` 優先に復帰）
- `/chara_presets?_ts=...` による404を修正（完全一致ルート対応）
- `/chara_thumb` 404の原因（GETルート未配置）を修正

### 16) プリセット一覧UIの最適化（スマホ負荷対策）
- プリセット一覧を開閉式に変更（初期は閉）
- サムネ画像は一覧を開いた時だけ取得
- スマホ起動時に `loadCharaPresets()` を遅延し初期描画を軽量化
- 目標: 白画面待ち時間の短縮

### 17) LoRAサムネ一覧に寄せたデザイン調整
- グリッド密度・カード比率・ラベル帯・枠線をLoRA側へ統一
- サムネ未作成カードの大量表示を廃止し、作成済みのみグリッド表示
- 「更新先」は別セレクトで全プリセットから選択可能にして運用性を維持

### 18) プリセット起点のキャラ追加機能
- 「更新先」横に `＋ キャラ追加` ボタンを追加
- 仕様:
  - 選択中プリセットを対象にキャラ数を+1（最大6）
  - 追加された `キャラ1〜6` 側のプリセット選択に自動セット
  - **読込（Load）は行わない**

### 19) キャラ数 `0` 許可への仕様変更
- `B. キャラ数` の `min` を `0` に変更
- 各ロジックの下限を `1` -> `0` に統一
  - `updateCharaBlocks`
  - `collectInput`
  - `collectSessionData`
  - セッション復元処理
- 0体スタートから必要に応じて追加できる運用に変更

### 20) スマホUI崩れ修正（更新先セレクト）
- `更新先` セレクトと `＋キャラ追加` の折り返し/全幅制御を追加
- スマホでセレクトが極細表示になる崩れを修正

## Recent Additions (v1.4.69999978 - v1.4.69999983)

### 21) Docs Reorganization
- Kept `README.md` / `README_EN.md` at repository root.
- Moved supporting documents under `docs/`:
  - `docs/guides/`
  - `docs/release_notes/`
  - `docs/articles/`
  - `docs/updates/`
  - `docs/llm/`

### 22) GitHub Pages Build Fix
- Fixed Liquid parsing error in `docs/guides/anima_pipeline_guide.md`.
- Escaped `{%- set ... %}` sample with `raw` block.
- `pages build and deployment` recovered to green.

### 23) Mobile UI Improvements (Issue #5)
- Added mobile wrapping and sizing adjustments for `Gender / Age` rows.
- Reduced button overflow on narrow screens.
- Improved STATUS long-line readability on mobile.

### 24) I18N Fixes (Issue #4)
- Fixed mixed-language connection test progress text:
  - `LLM Connection Test (mixed text)` -> `LLM Connection Test in progress...`
- Added English mapping for workflow-not-found error text.
- Added English mapping for workflow helper note text.

### 25) Preset Panel Order Unification (Mobile/PC)
- Unified order across devices:
  - `Chara Count -> Preset List -> Chara 1..6`
- Removed mobile-only fixed bottom-sheet behavior.
- Restored inline panel flow to match desktop behavior.

### 26) Specs Folder Initialization (Local)
- Added `docs/specs/README.md`.
- Included spec template, naming rule, and update workflow.

