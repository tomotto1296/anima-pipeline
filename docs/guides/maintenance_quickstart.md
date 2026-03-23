# Anima Pipeline メンテナンス引き継ぎガイド（Quickstart）

最終更新: 2026-03-24  
対象: `worktrees/main`

## 1. このアプリは何をするものか

Anima Pipeline は、ブラウザUIで入力した内容をもとに、必要に応じてLLMでプロンプトを生成し、ComfyUIへ送信して画像を生成するローカルWebアプリです。  
あわせて、プリセット管理・履歴DB・セッション保存・診断UIを提供します。

## 2. 全体構成（まずここだけ押さえる）

```text
anima_pipeline.py            # 起動エントリ
core/                        # API/ロジック本体
  handlers.py                # HTTP APIルーティング
  comfyui.py                 # ComfyUI送信・進捗監視・メタデータ
  llm.py                     # LLM呼び出し
  config.py                  # 設定・ログ・移行
  history.py                 # 履歴DB
  presets.py                 # プリセット/名前付きセッション
frontend/
  index.html                 # UI本体（大半のUIロジック）
  i18n.js                    # 文言辞書
settings/                    # 設定ファイル
presets/, chara/             # プリセット実体
history/                     # 履歴DBとサムネ
docs/                        # 仕様・運用ドキュメント
```

## 3. 重要な現在仕様（運用で効くポイント）

1. 設定は「共有デフォルト + ローカル個人設定」の二層です。
2. デフォルト設定: `settings/pipeline_config.default.json`
3. 個人設定: `settings/pipeline_config.local.json`（Git追跡対象外）
4. 主要UIは `frontend/index.html` に集約されています。
5. API仕様書と実装に若干の命名差が出ることがあるため、最終判断は `core/handlers.py` を優先してください。

## 4. 変更時の入口（機能別）

1. API追加・変更: `core/handlers.py`
2. ComfyUI連携/画像後処理: `core/comfyui.py`
3. LLM挙動: `core/llm.py`, `settings/llm_system_prompt.txt`
4. 設定キー追加: `core/config.py` + `settings/pipeline_config.default.json`
5. 履歴周り: `core/history.py`
6. プリセット/セッション: `core/presets.py`
7. 画面文言/挙動: `frontend/index.html`, `frontend/i18n.js`

## 5. 障害時の一次切り分け手順

1. `GET /diagnostics`（UIの Run Setup Diagnostics）を実行
2. ComfyUI URL / workflow / node id の妥当性を確認
3. `logs/` の当日ログを確認（token等はマスク済み）
4. 生成不能時は `/generate` の返却 `error` と ComfyUI側ログを突合
5. 画像は出るが履歴に出ない場合は `history/history.db` と `history/thumbs/` を確認

## 6. よく使うチェックコマンド

```bash
python scripts/check_frontend_syntax.py
python scripts/run_quick_checks.py --include-hooks-guard
python -m py_compile anima_pipeline.py core/handlers.py
```

## 7. 参照優先ドキュメント

1. 機能一覧: `docs/specs/features.md`
2. API仕様: `docs/specs/feature_api_v1.md`
3. 運用ガイド: `docs/guides/anima_pipeline_guide.md`
4. 変更履歴: `docs/updates/Update.md`
5. 今後予定: `docs/updates/roadmap.md`

## 8. メンテ担当向け注意点

1. `settings/pipeline_config.local.json` は個人値を含むためコミットしないでください。
2. 既存APIの後方互換（特にプリセット・セッション系）を優先してください。
3. フロント修正時は JA/EN 切替の往復確認（JA -> EN -> JA）を実施してください。
4. 進捗表示やWS連携は起動直後に揺らぐ場合があるため、再現確認は2回以上行ってください。
