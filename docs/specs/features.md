# AnimaPipeline 機能一覧

最終更新: 2026-03-28 / 対応バージョン: v1.5.21

> 実装予定・ロードマップは [roadmap.md](../updates/roadmap.md) を参照してください。

---

## 最新完了機能（v1.4.718〜v1.5.20）

| 機能 | バージョン |
|------|-----------|
| メタデータ埋め込み強化（LoRA・ワークフローJSONバージョン記録） | v1.4.718 |
| 生成履歴DB化＋再編集 | v1.4.730 |
| プリセット階層化（キャラ/シーン/カメラ/品質/LoRA構成分離） | v1.4.740 |
| アイコン配信 | v1.4.743 |
| モジュール分割（anima_pipeline.py -> core/・frontend/） | v1.4.892 |
| キャラ名・作品名の日英欄分離（name_en / series_en） | v1.4.900 |
| ポジティブ・ネガティブタグのプリセット保存対応 | v1.4.900 |
| セッション複数保存（名前付き保存） | v1.4.910 |
| 自己診断UI（エラー原因候補・ノード不足警告） | v1.4.911 |
| INPUT-6: LoRA管理強化（検索・お気に入り・推奨weight表示） | v1.5.13 |
| UI-5: ダークモード（端末連動 / Light / Dark 切替、可読性調整） | v1.5.15 |
| UI-5 follow-up: ダーク時コントラスト最終調整（active状態/disabled ADD/動的入力背景のテーマ連動） | v1.5.18 |
| GEN-9: 「今日の気分」ボタン（既存プリセット1件＋シーン/時間帯/天気をランダム適用、STATUSサマリー表示） | v1.5.16 |
| INPUT-1: ランダムキャラプリセット作成（ui_options由来の属性ランダム生成） | v1.5.19 |
| SHARE-1: プリセット共有zip Export/Import（`/presets_export`・`/presets_import`、overwrite確認） | v1.5.20 |
| OUTPUT-9: プロンプト差分ビューア（Positive/Negative差分表示、トグル対応。Negativeは差分時のみ表示） | v1.5.17 |
| INPUT-6 follow-up: モバイルLoRA UIレイアウト調整（カード/スロットの視認性改善） | v1.5.18 |
| 配布バージョン更新（v1.5.1） | v1.5.1 |

---
## 基本・接続

| 機能 | バージョン |
|------|-----------|
| Webブラウザ UI（localhost:7860）/ Pythonサーバー起動・BAT対応 | v1.1.0 |
| ComfyUI 接続設定・接続テスト / キュー数表示 | v1.2.0 |
| LLM API 接続テスト | v1.2.0 |
| BAT起動安定化（UTF-8対応 chcp65001 / PYTHONUTF8=1、py -3 固定） | v1.4.7 |
| Tailscale版 BAT（tailscale ip -4 自動検出・URL表示） | v1.4.7 |

### 画像生成

| 機能 | バージョン |
|------|-----------|
| ComfyUI へのプロンプト送信・画像生成 | v1.1.0 |
| ワークフロー選択ドロップダウン | v1.4.0 |
| 自前ワークフロー（API形式JSON）対応 / Node ID 自動検出 | v1.4.3 |
| LoRA 注入 | v1.4.0 |
| LoraLoaderノード自動バイパス（LoRA未選択・一部選択時の400エラー修正） | v1.4.2 |
| 生成進捗 % 表示（WebSocket） | v1.4.5 |
| 再画像生成ボタン | v1.3.0 |
| SaveImageExtended 対応（WebP出力・ファイル名カスタマイズ） | v1.4.6 |
| 画像サイズプリセット（ui_options.json でカスタマイズ可） | v1.1.0 |

### LLM プロンプト生成

| 機能 | バージョン |
|------|-----------|
| LLM によるプロンプト自動生成（Gemini / OpenAI / LM Studio 他 OpenAI互換API対応） | v1.1.0 |
| LLM システムプロンプトのカスタマイズ（settings/llm_system_prompt.txt） | v1.1.0 |
| LLM スキップ（直接タグ送信）モード | v1.1.0 |
| LLMシステムプロンプトに /no_think 追加（思考モデルの応答速度改善） | v1.4.6 |

### キャラクター設定

| 機能 | バージョン |
|------|-----------|
| キャラクター属性選択UI（性別・年齢・髪型・髪色・瞳色・表情・肌・衣装・バスト・体型・脚・付属・エフェクト・ポーズ・持ち物・画面位置など） | v1.1.0 |
| ExtraTag 入力欄（二重挿入修正済み） | v1.4.4 |
| 複数キャラ対応（キャラ1〜6） | v1.4.4 |
| キャラ数 0 許可（0体スタートから追加運用に対応） | v1.4.7 |

### キャラプリセット

| 機能 | バージョン |
|------|-----------|
| キャラプリセット 保存・読み込み・削除 | v1.2.0 |
| プリセット自動生成（Danbooru Wiki + LLM でキャラ名から髪色・衣装を自動埋め） | v1.2.1 |
| サムネイル一覧UI（開閉式・遅延読み込み・グリッド表示） | v1.4.7 |
| ギャラリー画像からサムネイル作成（chara/<name>.webp として保存） | v1.4.7 |
| プリセット起点のキャラ追加（＋キャラ追加ボタン） | v1.4.7 |
| 今日の気分ボタン（生成ボタン横、キャラプリセット1件＋シーン/時間帯/天気をランダム適用、STATUS表示） | v1.5.16 |
| ランダムキャラプリセット作成（INPUT-1: 属性ランダム生成＋保存確認） | v1.5.19 |
| プリセット共有zip Export/Import（`chara/` + `presets/` 一括、上書き確認） | v1.5.20 |
| BOM混在 JSON 読み込み対応（utf-8-sig） | v1.4.7 |

### LoRA

| 機能 | バージョン |
|------|-----------|
| LoRA 一覧・選択 | v1.4.0 |
| LoRA サムネイル表示 | v1.4.1 |
| LoRA お気に入り（`settings/lora_favorites.json` 永続化） | v1.5.13 |
| LoRA 検索フィルタ（カード + スロットドロップダウン連動） | v1.5.13 |
| LoRA 推奨weight表示（`_w0.8` 形式のファイル名解析） | v1.5.13 |

### シーン・スタイル

| 機能 | バージョン |
|------|-----------|
| シーン設定（場所・時間帯・天気等）/ シーンブロック独立化 | v1.3.0 |
| スタイルタグ プリセット管理（settings/style_tags.json） | v1.1.0 |
| プロンプト調整・追加欄（ポジ・ネガ） | v1.1.0 |
| 色選択ドロップダウン化 | v1.2.1 |

### ギャラリー・セッション

| 機能 | バージョン |
|------|-----------|
| ギャラリー（生成履歴）表示 / 拡大・プロンプト再利用・フォルダを開く | v1.3.0 |
| セッション保存・読み込み / 自動保存（anima_session_last.json） | v1.3.0 |

### UI / UX

| 機能 | バージョン |
|------|-----------|
| 生成パラメータセクション（Seed / Steps / CFG / Sampler） | v1.3.0 |
| フローティングナビゲーション | v1.3.0 |
| 各セクション トグル開閉 | v1.4.1 |
| スマホ対応（モバイルUI大幅改善・WSバナー） | v1.4.1 |
| バージョン表示 | v1.4.1 |
| UI 言語切替（JA / EN）/ OS言語自動判定・ブラウザ保存・往復切替対応 | v1.4.7 |
| 表示テーマ切替（Device / Light / Dark）+ ダーク配色可読性調整 | v1.5.15 |
| ダークテーマ追補: 選択ボタン(active)と無効ボタン(disabled)の視認性、動的入力背景の色同期を改善 | v1.5.18 |
| STATUS / 進捗文言の多言語対応 | v1.4.7 |
| UIボタン カスタマイズ（settings/ui_options.json） | v1.1.0 |
| モバイル Gender/Age 行レイアウト改善 | v1.4.7 |

### ログ

| 機能 | バージョン |
|------|-----------|
| 実行ログ保存（logs/ フォルダ）/ 保持期間自動削除 / ログレベル normal/debug | v1.4.7 |
| 秘匿情報自動マスク（token / api key / authorization / bearer） | v1.4.7 |
| 未処理例外フック | v1.4.7 |
| ログ設定UI（LOG DIRECTORY / RETENTION DAYS / LOG LEVEL / OPEN LOGS / EXPORT ZIP） | v1.4.7 |

### API エンドポイント

| エンドポイント | 追加バージョン |
|--------------|--------------|
| GET /lora_list, GET /lora_thumb | v1.4.0 |
| GET /lora_favorites, POST /lora_favorites | v1.5.13 |
| GET /workflow_list, GET /workflow_node_ids | v1.4.3 |
| GET /chara_presets, POST /save_chara_preset, POST /delete_chara_preset | v1.2.0 |
| POST /chara_preset_thumb, GET /chara_thumb | v1.4.7 |
| POST /save_session, GET /last_session | v1.3.0 |
| GET /connection_test, GET /llm_connection_test | v1.2.0 |
| GET /logs_info, GET /logs_zip | v1.4.7 |
