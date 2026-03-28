# Update Log (from v1.4.6)

## 目的
このドキュメントは、`v1.4.6` 以降の変更内容を次の開発者へ引き継ぐための要約です。

## バージョン運用ルール
- 細かい修正ごとに小数点以下を増分（例: `1.4.7 -> 1.4.71 -> 1.4.72`）
- `1.4.699x` 系は `1.4.7` として正式リリース済み

## 現在バージョン
- `1.5.13`


## 直近追記（v1.4.910）
- OUTPUT-8: 名前付きセッション保存を追加（`/sessions` 一覧・`/sessions/<n>` 保存/読込/削除）
- 同名保存時は `409 Conflict` を返し、`overwrite: true` で上書き保存
- `sessions/` ディレクトリを自動作成し、ファイル名サニタイズを実装
- UIに「保存済みセッション」一覧を追加し、Load/Deleteを実装
- 既存の `/session`（`anima_session_last.json`）自動保存・復元は維持
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
- Escaped the `set` sample in guide docs using a `raw` block.
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


## 直近追記（v1.4.71 ～ v1.4.718）

### 27) OUTPUT-4: メタデータ埋め込み基盤を実装
- `output_format`（`png`/`webp`）と `embed_metadata` を設定に追加。
- 起動時移行処理を追加し、既存 `pipeline_config.json` に不足キーがある場合は自動補完。
- 画像設定UIに `メタデータを埋め込む` トグルを追加（設定保存/復元、セッション復元対応）。

### 28) PNG / WebP のメタデータ書き込みを実装
- PNG:
  - `parameters` を `tEXt` へ保存。
  - 追加で `prompt` / `workflow` も保存（ComfyUI復元用途）。
- WebP:
  - Exif `UserComment` と XMP の両方へ保存。
  - WebP変換失敗時はPNGへフォールバックし、処理継続。

### 29) Civitai互換フォーマット調整（段階的）
- `Model hash` / `Lora hashes` を埋め込み。
- LoRAタグ `<lora:name:weight>` をメタデータ側プロンプトへ付与。
- `parameters` をA1111最小互換の3行構成へ整理:
  - Positive prompt
  - Negative prompt
  - `Steps, Sampler, CFG, Seed, Size, Model hash, Model, Lora hashes, Version`
- ハッシュはAutoV2互換（10桁・大文字）を優先して出力。

### 30) モデル/LoRAハッシュ解決の強化
- `comfyui_output_dir` / `workflow_json_path` からComfyUIルート候補を推定。
- `models/checkpoints` / `models/unet` / `models/diffusion_models` / `models/loras` を再帰探索。
- basename一致フォールバックと簡易キャッシュを追加。

### 31) 運用上の結論（実機検証結果）
- Civitai `Resources`:
  - PNG: 検出OK
  - WebP: 検出OK
- `embed_metadata = OFF`: 正常
- 複数LoRA: 正常
- ComfyUI再読込:
  - PNGはworkflow復元OK
  - WebPはworkflow復元なし（現状仕様/互換差として扱う）

### 32) 版上げ履歴（細修正）
- `1.4.71` → `1.4.711` → `1.4.712` → `1.4.713` → `1.4.714` → `1.4.715` → `1.4.716` → `1.4.717` → `1.4.718`


## 直近追記（v1.4.72 ～ v1.4.742）

### 33) OUTPUT-3: 生成履歴DB + 全履歴UI の初期実装
- `generation_history` をSQLiteで永続化（`history/history.db`）。
- 設定キーを追加:
  - `history_db_path`
  - `history_thumb_dir`
- APIを追加:
  - `GET /history_list`
  - `GET /history_detail`
  - `POST /history_update`
  - `POST /history_delete`
- 既存ギャラリーにタブを追加:
  - `セッション履歴`
  - `全履歴`

### 34) 既存DB向けマイグレーション修正
- 既存テーブルに不足カラムがある環境で `no such column` が出る問題を修正。
- 起動時/保存時に `PRAGMA table_info` を用いた不足カラム自動追加を実装。

### 35) ギャラリー画像/モーダル安定化（セッション + 全履歴）
- `/poll_status` で `file_paths` を優先し、`png -> webp` 置換を考慮。
- `/get_image` に書き込み中ファイル回避（サイズ安定確認）を追加。
- モーダル表示で画像候補フォールバック（元画像失敗時にサムネ等へ切替）。
- `get_image 404` 対策として `png` 不在時の `webp` 自動フォールバックを追加。

### 36) 進捗%表示の復旧とフォールバック
- WebSocket進捗受信の耐性を強化（文字列/Blob両対応）。
- WS未接続・進捗未受信時でも、ポーリングベースの疑似%表示を追加。
- 生成中 `%` 表示が出ないケースを回避。

### 37) 版上げ履歴（細修正）
- `1.4.72` → `1.4.721` → `1.4.722` → `1.4.723` → `1.4.724` → `1.4.725` → `1.4.726` → `1.4.727` → `1.4.728` → `1.4.729` → `1.4.730` → `1.4.731` → `1.4.732` → `1.4.733` → `1.4.734` → `1.4.735` → `1.4.736` → `1.4.737` → `1.4.738` → `1.4.739` → `1.4.740` → `1.4.741` → `1.4.742`
### 38) INPUT-4（後付け記録）: プリセット階層化
- 本項目は `v1.4.740` 時点で実装済み機能を後付けで記録したもの。
- API:
  - `GET /presets/<category>`
  - `GET /presets/<category>/<name>`
  - `POST /presets/<category>/<name>`
  - `DELETE /presets/<category>/<name>`
- 対応カテゴリ:
  - `chara / scene / camera / quality / lora / composite`
- 既存互換ラッパー:
  - `GET /chara_list`
  - `GET /chara_load?name=...`
  - `POST /chara_save`
  - `POST /chara_delete`
- 既定プリセット:
  - `Scene_default.json`
  - `Camera_default.json`
  - `Quality_default.json`
  - `Lora_default.json`
  - `Composite_default.json`
- Composite読込優先順位:
  - スナップショット優先（名前参照は補助情報として保持）

### 39) INPUT-4 実装修正（v1.4.740 時点）
- Sceneカテゴリ（屋外/屋内/特殊）と sub（屋外/屋上/屋内）の保持・復元を修正。
- `collectCheckedNeg is not defined` によるQuality保存エラーを修正。
- 読込表示文言を `読込成功: <name>` に統一。
- 実装スキーマ差分:
  - Scene: `scene_place` / `scene_outdoor` / `scene_place_category` を保持。
  - Camera: `posv` / `posh` / `pos_camera` / `camera_free` と `all[*].posc` を保持。

### INPUT-4 動作確認（完了）
- Scene / Camera / Quality / Lora / Composite の保存・読込・削除
- Composite の保持（scene/camera/quality/lora/chara snapshot）
- 既存キャラプリセットの互換動作（読込/保存/削除）
- 再起動後のプリセット一覧保持
- 生成フローの回帰なし（生成/履歴/再生成）


## 直近追記（v1.4.743）

### 40) アイコン配信導線の整理（アプリ / GitHub Pages 両対応）
- ルート配信用アセットを追加: `assets/icons/*`。
- GitHub Pages配信用アセットを追加: `docs/assets/*` + `docs/manifest.json`。
- `docs/index.html` / `docs/index_en.html` の `<head>` に以下を設定:
  - `favicon-light.ico`
  - `favicon-dark.ico`（`prefers-color-scheme: dark`）
  - `apple-touch-icon.png`
  - `manifest.json`

### 41) favicon のライト/ダーク分離
- 生成ファイルを `favicon-light.ico` / `favicon-dark.ico` に分離。
- SVG運用を廃止し、PNG/ICO運用へ統一。

### 42) アプリ内HTTP配信に静的アイコンルートを追加
- `anima_pipeline.py` 側で以下を配信:
  - `GET /assets/...`
  - `GET /manifest.json`
  - `GET /favicon.ico` / `GET /favicon-light.ico` / `GET /favicon-dark.ico`
- アプリUI (`/`) の `<head>` に favicon / manifest 参照を追加。

### 43) Version Guard の修正
- `scripts/check_version_bump.py` の差分判定を修正（`git diff` 引数順）。
- 文字コード取り扱いを安定化（`utf-8` + `errors=replace`）。
- `scripts/check_version_bump.py` 自身の変更は版上げ必須判定から除外。

### 44) 版上げ履歴
- `1.4.742` -> `1.4.743`

### 45) GitHub Pages白画面の復旧
- 事象:
  - `docs/index.html` / `docs/index_en.html` に文字化け由来のHTML破損（閉じタグ崩れ）が混入し、GitHub Pagesで白画面化。
- 原因:
  - 途中編集時の文字コード/置換処理で日本語HTML本文が破損。
- 対応:
  - 直近正常コミットの `index` 2ファイルへ復元した上で、favicon/manifestリンクのみ安全に再適用。
  - 修正コミット: `162dda2`
- 補足:
  - アイコン追加自体（`favicon-light/dark`, `manifest`）は白画面の直接原因ではないことを確認。

---

## 直近追記（v1.4.875 ～ v1.4.883）

### v1.4.875
- `core/handlers.py` 復旧。
- `GET /chara_presets` と `POST /chara_presets` の混線を修正。
- 壊れていた `POST` ヘルパー周辺の不要断片を除去。

### v1.4.876
- `do_POST` から `/config` と `/session` をヘルパー化。
  - `_handle_post_config`
  - `_handle_post_session`

### v1.4.877
- `do_POST` 先頭のプリセット系分岐をヘルパー化。
  - `_handle_post_preset_routes`
  - 対象: `/presets/*`, `/chara_save`, `/chara_delete`

### v1.4.878
- `do_POST` 末尾ルートをヘルパー化。
  - `_handle_post_terminal_routes`
  - 対象: `/get_image`, `/chara_thumb`, `/cancel`, `/generate`

### v1.4.879
- `do_POST` の `/regen` 大ブロックを関数抽出。
  - `_handle_post_regen`

### v1.4.880
- `do_POST` 中段ルートをヘルパー化。
  - `_handle_post_common_routes`
  - 対象: `/config`, `/session`, `/history_update`, `/history_delete`, `/chara_presets`, `/chara_preset_thumb`, `*_tags`
- `do_POST` の分岐整理（プリセット / 共通 / regen / 末尾ルート）。

### v1.4.881
- `do_POST` の制御フローを直列 `if/return` に統一。
- 未対応 POST パスの `404` フォールバックを追加。
- 分岐順を明確化（preset -> common -> regen -> terminal -> 404）。

### v1.4.882
- `do_DELETE` をヘルパー分割。
  - `_handle_delete_preset_routes`
- DELETE の制御フローを `if/return` 形式で整理。
- 既存挙動（`/presets/*` の削除APIと404フォールバック）は維持。

### v1.4.883
- URL解析を共通化する `_parse_request_path_qs` を追加。
- `do_GET` / `do_POST` / `do_DELETE` の冒頭解析を共通ヘルパー利用へ統一。
- 解析ロジックの重複削減（挙動変更なし）。

## Checks
- `python -m py_compile core/handlers.py anima_pipeline.py` pass
- `python scripts/run_quick_checks.py --include-hooks-guard` pass


### v1.4.884
- `do_GET` から `/session` と `/chara_presets` をヘルパーへ分離。
  - `_handle_get_session_route`
  - `_handle_get_chara_presets_route`
- `do_GET` 分岐の短縮（挙動変更なし）。

### v1.4.885
- `GET /generate_preset` 分岐をヘルパーへ抽出。
  - `_handle_get_generate_preset_route`
- `do_GET` の分岐見通しを改善（挙動変更なし）。

### v1.4.886
- `do_GET` の `/session` と `/chara_presets` を既存ヘルパー呼び出しへ統一。
- GET分岐の重複コードを削減（挙動変更なし）。

### v1.4.887
- `do_GET` を段階ディスパッチに再構成。
  - `early -> info -> poll -> session -> history -> generate_preset -> chara_presets -> misc -> image -> 404`
- 追加ヘルパー:
  - `_handle_get_misc_routes`
  - `_handle_get_terminal_image_routes`
- GETの責務分離を強化（挙動変更なし）。

### v1.4.888
- `GET /poll_status` をルートヘルパー化。
  - `_handle_get_poll_route`
- `do_GET` の分岐パターンを統一（すべてヘルパー判定ベース）。

## 最終GUI確認（v1.4.888）
1. 起動してトップ表示（白画面/文字化けなし）。
2. 言語切替: 日本語⇄英語を往復してラベル崩れなし。
3. 生成フロー: Generate -> Cancel -> Re-Generate で状態表示が固着しない。
4. 履歴表示: セッション履歴/全履歴の読み込み、サムネ表示、ページング。
5. プリセット: 保存/読込/削除、サムネ作成、ハードリロード後の再表示。
6. LoRA: 一覧取得、カード割当、サムネ表示（取得できる環境で）。
7. 設定: `/config` 保存後に再起動して値が保持される。
8. 404系: 存在しないパスへアクセスしてUIが壊れない。

問題が出たら、再現手順（操作順）と Console/Network の赤エラーをそのまま共有。

### v1.4.889
- `GET` ルートの欠落を復旧。
  - `/version`
  - `/extra_tags`
  - `/style_tags`
  - `/neg_extra_tags`
- 言語切替時の履歴表示崩れ・Console 404 の回帰を修正。

### v1.4.890
- 履歴セクションの言語切替ラベル崩れ（`???`）を修正。
- `frontend/index.html` の混在フォールバック文字列を正常なJA/EN文言に置換。
- 影響: `Generation History (Session)`, `Session History`, `All History`, `Clear`, プリセット管理ラベル。

### v1.4.891
- 初回起動時に LoRA サムネが 404 になる回帰を修正。
- `GET /lora_thumbnail` を `core/handlers.py` の GET misc ルートに復旧。
- サムネ未発見時は `204` を返す既存互換挙動を維持。

### v1.4.892
- 生成中の注意文「※ 起動直後は進捗%が表示されない場合があります（初回WS接続のタイミングによる）」の英訳を追加。
- 英語UI時に該当注記が日本語のまま残る問題を修正。

## 追記（2026-03-23 / REFACTOR-1 継続）

### 11) モジュール分割の本体適用
- `anima_pipeline.py` をエントリポイント中心へ整理
- `core/` へ機能分離（config / handlers / presets / history / frontend / runtime / llm / comfyui）
- `frontend/index.html` と `frontend/i18n.js` を外出し運用へ統一

### 12) 回帰不具合の修正（今回）
- 言語切替後に履歴見出しが `???` になる問題を修正
- 404回帰（`/version`, `/extra_tags`, `/neg_extra_tags`, `/style_tags`）を修正
- LoRA サムネイルの初回ロード失敗（`/lora_thumbnail`）を再接続可能に修正
- 起動直後注意文の英訳未適用を修正

### 13) 起動・検証フローの整備
- `start_anima_pipeline - Tailscale.bat` を再作成
- Hook/Quick Check 導線を維持（pre-commit / pre-push）
- 実行確認:
  - `python scripts/check_frontend_syntax.py` ✅
  - `python scripts/run_quick_checks.py --include-hooks-guard` ✅

### 14) 現在の補足
- 既知課題として「起動直後の進捗%追従遅れ」は継続観察（致命ではないため後続対応）
- 本追記時点の本体バージョン: `1.4.900`

### v1.4.900
- INPUT-12: キャラ名/作品名に JA/EN 欄を追加（`name_en` / `series_en`）。
- INPUT-12: LLMなし生成で EN 欄優先、空欄時は JA 欄フォールバックで `name_(series)` 生成。
- INPUT-12: セッション保存/復元・キャラプリセット保存/読込に `name_en` / `series_en` を反映。
- INPUT-5: プリセットカテゴリに `negative` を追加し、`/presets/negative/*` で保存/読込/削除対応。
- INPUT-5: ネガティブ調整セクション上部に Negative Preset UI（選択/保存/読込/削除）を追加。
- INPUT-5: ネガティブプリセットで `quality_neg_tags` / `neg_extra_tags` / `neg_style_tags` / `neg_extra_note` / `selected_neg_safety` を保存/復元。
- Config: `last_negative_preset` を `pipeline_config` の保存対象に追加。
- 検証: `python scripts/check_frontend_syntax.py` / `python scripts/run_quick_checks.py --include-hooks-guard` 成功。

### v1.4.901
- `/generate_preset` の命名を JA/EN 連動に拡張。`name_en` が入力されている場合、保存名の既定値を `JA（EN）` 形式に統一。
- 自動生成プリセット保存時に `name_en` / `series_en` も保持。
- フロントの「プリセット自動生成」「キャラプリセット保存」のデフォルト名を同じ規則（JA（EN）優先）に統一。

### v1.4.902
- `settings/preset_gen_prompt.txt` に出力フォーマット制約を追記（コードフェンス禁止・単一JSON必須）。
- `/generate_preset` で LLM空応答/内容不足時に1回だけ自動リトライする処理を追加。

### v1.4.903
- `/generate_preset` で `name_en` / `series_en` の自動補完を追加（Danbooruタグ検索 -> 補助LLM推定 -> フォールバックの順）。
- 日本語名のみ入力時でも、返却プリセットに英語タグ候補を含めるよう改善。
- 自動生成プリセット名の既定値判定を補完後の `name_en` ベースに統一（`JA（EN）`）。

### v1.4.904
- 英語名補助推定で制御語（例: `no_think`）を候補から除外するガードを追加。
- 補助推定プロンプトを調整し、不要な制御語の混入を抑制。

### v1.4.905
- `/generate_preset` の英語名補助推定に妥当性バリデーションを追加。
- 指示文混入系の不正候補（例: `the_user_wants_to_convert...`）を除外。

### v1.4.906
- `Series EN` が空になるケース向けに、`name_(series)` 形式のキャラタグから series を抽出するフォールバックを追加。
- これにより JA作品名のみ入力時でも、キャラタグに series が含まれる場合は `Series EN` を補完可能。

### v1.4.907
- EN補完値の正規化を追加: `name_(series)` は `Name EN=name` / `Series EN=series` に分離。
- `Series EN` の `fate_(series)` 形式を `fate` へ正規化。
- `Name EN` にはASCIIタグ妥当性チェックを適用し、日本語や指示文混入を除外。

### v1.4.908
- Positive preset を追加（positive カテゴリ保存/読込/削除）。
- ポジティブ調整セクション上部に Positive Preset UI（選択/保存/読込/削除）を追加。
- Positive preset で selected_period / year / quality_tags / meta_tags / selected_safety / style_tags / extra_tags / extra_note を保存/復元。
- Config/Session に last_positive_preset / lastPositivePreset を追加し、最終選択を復元。

### v1.4.909
- Positive Preset UI 文言の文字化けを修正（選択肢・確認ダイアログ・エラーメッセージ）。
- Positive preset の読込/保存/削除導線で表示メッセージを正常化。

## Recent Addendum (v1.4.910)
- OUTPUT-8 follow-up fix: prevented mixed JA/EN labels in the Named Sessions panel during language toggle.
- Added a dedicated no-auto-i18n boundary for the sessions panel (`data-no-i18n="1"`).
- Language switch now explicitly refreshes the sessions panel title/list after global i18n pass.
- Sessions panel UI updated to collapsible style with internal scroll (`max-height` + `overflow-y`) to avoid page overgrowth.
- Confirm dialogs for overwrite/delete now use deterministic panel-local text selection.


## Addendum (2026-03-23 / SETUP-2)

### v1.4.911
- SETUP-2: Added `GET /diagnostics`.
  - Checks: `comfyui`, `llm`, `workflow`, `pos_node`, `neg_node`, `ksampler`, `lora_nodes`, `output_dir`
  - Response: `status`, `results[]`, `summary { errors, warnings }`
- Added `Run Setup Diagnostics` button and diagnostics panel in Settings UI.
- Improved workflow path resolution.
  - `workflow_file` is preferred when set.
  - Relative `workflow_json_path` values like `image_anima_preview.json` are also resolved under `workflows/`.
- Fixed diagnostics display mixing/garbling.
  - Diagnostics panel is excluded from auto i18n (`data-no-i18n`) to prevent text corruption.
  - Diagnostics strings are currently fixed to English to avoid `????` corruption.
- Version bump: `1.4.910` -> `1.4.911`

## Checks
- `python -m py_compile anima_pipeline.py core/handlers.py` pass
- `python scripts/check_frontend_syntax.py` pass

### 15) guides再整備（2026-03-23）
- `docs/guides/anima_pipeline_guide.md` をリファクタ後構成に合わせて全面更新（文字化け解消）
- `docs/guides/anima_pipeline_guide_en.md` を同内容で再整備（構成・起動・最小配布セットを現行化）
- クイックチェック導線を `quick_checks_and_hooks.md` 参照へ統一

## Addendum (2026-03-23 / Preset Defaults + Guides)

### v1.4.912
- Updated `settings/pipeline_config.default.json` for INPUT-4 default preset pointers.
  - Added `workflow_file` key.
  - Set default last preset values to `Scene_default` / `Camera_default` / `Quality_default` / `Lora_default` / `Composite_default`.
- Version bump: `1.4.911` -> `1.4.912`

### v1.4.913
- Updated guides to document INPUT-4 preset hierarchy behavior.
  - `docs/guides/anima_pipeline_guide.md`
  - `docs/guides/anima_pipeline_guide_en.md`
- Added notes for:
  - independent preset categories,
  - composite snapshot-first restore,
  - camera per-character `all[]` + fallback behavior.
- Version bump: `1.4.912` -> `1.4.913`

### v1.4.914
- Updated `docs/updates/Update.md` to include v1.4.912/v1.4.913 history entries.
- Version bump: `1.4.913` -> `1.4.914`


### v1.5.0
- 配布バージョンを 1.4.914 -> 1.5.0 に更新。
- README.md / README_EN.md / docs/specs/features.md / docs/updates/roadmap.md の現在バージョン表記を `v1.5.0` に同期。


### v1.5.01
- Added startup config backfill for missing keys from `DEFAULT_CONFIG` in `load_config()`.
- Added backfill log line: `[config] 不足キーを補完しました`.
- Added version badge fallback display on initial page load (`__APP_VERSION__` injection + client-side fallback before `/version` response).
- Added release notes index/file:
  - `docs/release_notes/README.md`
  - `docs/release_notes/release_notes_v1.5.0.md`
- Version bump: `1.5.0` -> `1.5.01`.

### 32) v1.5.02: Personal Config Split and Secret-Safe Tracking
- Split runtime config management into shared defaults + local personal config.
- New priority for config load:
  - `settings/pipeline_config.local.json` (personal, preferred)
  - `settings/pipeline_config.json` (legacy fallback)
  - `settings/pipeline_config.default.json` (shared defaults)
- Save target was changed to `settings/pipeline_config.local.json`.
- Added ignore rules to prevent local secrets from being tracked:
  - `settings/pipeline_config.local.json`
  - `.env`
  - `.env.local`
- `settings/pipeline_config.json` was removed from Git tracking to avoid leaking personal values.

### 33) v1.5.03: Docs/API Governance and Repository Hygiene
- Updated API documentation strategy:
  - Added `docs/specs/feature_api_v2.md`
  - Added `docs/specs/feature_api_v2_en.md`
  - Clarified API spec versioning policy in `docs/specs/README.md`
- Aligned public docs to released version `v1.5.01` (README/features).
- Unified ignore management to `.gitignore` only (removed duplicate `gitignore`).
- Added `.gitattributes` and normalized line endings for tracked text files.
- Version bump: `1.5.02` -> `1.5.03`.

### 34) v1.5.1: Release Preparation and Version Sync
- Bumped application version: `anima_pipeline.py` `__version__` -> `1.5.1`.
- Added release notes:
  - `docs/release_notes/release_notes_v1.5.1.md`
  - Updated `docs/release_notes/README.md` latest index.
- Synchronized version labels in key docs:
  - `README.md` / `README_EN.md`
  - `docs/specs/features.md`
  - `docs/updates/roadmap.md`
  - API v2 metadata (`feature_api_v2*.md`) target release
- Version bump: `1.5.03` -> `1.5.1`.

## 2026-03-26 - v1.5.11

- Release version updated to `v1.5.11`.
- Launcher updated for portable-first behavior:
  - Prefer bundled `python_embeded/python.exe`.
  - Fallback to system `python` / `py` only when bundled Python is unavailable.
- Workflow bundle policy updated to include four templates:
  - `image_anima_preview.json`
  - `image_anima_preview_Lora4.json`
  - `image_anima2_preview.json`
  - `image_anima2_preview_Lora4.json`
- Documentation updated:
  - README requirements clarified (bundled Python behavior).
  - User guides' requirements updated for portable usage and bundled workflows.
- Release notes added: `docs/release_notes/release_notes_v1.5.11.md`.
- Release notes updated with Japanese details for reflected changes and compatibility.
- Prepared minimal package zip for v1.5.11 release asset:
  - `dist/anima-pipeline_v1.5.11_minimal.zip`

## 2026-03-28 - v1.5.12

- Release version updated to `v1.5.12`.
- Updated visible version labels:
  - `anima_pipeline.py` `__version__`
  - `README.md` / `README_EN.md`
  - `docs/index.html` / `docs/index_en.html`
  - `docs/updates/Update.md` current version
- Updated frontend syntax check temp-file behavior:
  - `scripts/check_frontend_syntax.py` now deletes `frontend/.check_inline_main.js` when checks pass.
  - On check failure, the temp file is kept for debugging.

## 2026-03-28 - v1.5.13

- INPUT-6 (LoRA管理強化) の初期実装を追加:
  - LoRA検索（カードグリッドの絞り込み）
  - LoRAお気に入り（★）の登録/解除
  - 推奨weight（LoRAごとに保存し、再選択時に自動適用）
  - 自動候補（お気に入り優先表示）
- Added LoRA preferences API:
  - `GET /lora_favorites`
  - `POST /lora_favorites`
  - 保存先: `settings/lora_favorites.json`
- Updated version labels:
  - `anima_pipeline.py` `__version__`: `1.5.13`
  - `README.md` / `README_EN.md`
  - `docs/updates/Update.md` current version
