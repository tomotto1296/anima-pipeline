---
title: "【2026年版】技術力なくても推しキャラを量産！ComfyUI × LLMで自動プロンプト生成ツール「anima-pipeline」作った（2026-03-28更新）"
emoji: "😀"
type: "idea"
topics:
  - "ai画像生成"
  - "llm"
  - "comfyui"
  - "anima"
published: true
published_at: "2026-03-19 10:47"
---

![hero](https://raw.githubusercontent.com/tomotto1296/anima-pipeline/refs/heads/main/images/hero-ui-and-result.jpg)

## はじめに

ComfyUIでアニメ・美少女画像生成をしていると、こんな壁にぶつかりませんか？

- キャラ名からDanbooruタグを毎回ググるのが面倒
- 髪型・色・衣装・ポーズを毎回手打ちで入力するのがダルい
- 複数キャラ同時生成したいのに設定がリセットされる
- LLMで自動生成させたいけどUIがなくて挫折

そんな痛みを全部解決したくて、ブラウザUIでポチポチ入力するだけで**LLMがDanbooruタグを自動生成 → ComfyUI Animaワークフローに一発送信**できるツールを作りました。

https://www.youtube.com/watch?v=VS5mYS21q0c

Claudeと一緒に開発したので、初心者でも扱いやすい設計にしています。
（LLMなしでも普通に使えます。Gemini無料枠で動くのもおすすめ）

ここで軽く整理しておきます👇

■ そもそもComfyUIとは  
画像生成AIを「ノードで組む」タイプのツール  
→ 自由度が高く、かなり細かい調整ができます  

ただし最初は操作に少し慣れが必要です  

■ Animaって？  
ComfyUIで使える画像生成モデル＋専用ワークフロー（※） 

→ NVIDIAが開発しているモデル（Cosmos）をベースにしており、クオリティが安定しています  
→ 高品質な画像が出やすく、初心者でも扱いやすいのが特徴です  

■ anima-pipelineとは  
ノード操作なしでAnimaを使えるツール  

→ UIで入力するだけで画像生成できる  
→ 面倒なノード設定を一切触らなくてOK  
→ ComfyUIで作ったAnimaワークフロー（※）がそのまま使えます  
→ ComfyUIをこれから触る人にも、もっと楽に使いたい人にも向いています  

※画像生成の流れ
## 公式サイト・リポジトリ

UIのビジュアル・生成フロー・ギャラリーが詳しく見れる公式サイトを公開しています。

@[card](https://tomotto1296.github.io/anima-pipeline/index.html)
@[card](https://tomotto1296.github.io/anima-pipeline/index_en.html)

ソースコード・ZIPダウンロードはこちら：

@[card](https://github.com/tomotto1296/anima-pipeline)



## どんなことができる？

キャラ名・作品名入れるだけでLLMがDanbooruタグ自動生成（例: 「博麗霊夢 東方」→ masterpiece, 1girl, hakurei reimu, ...）
キャラ名・作品名の日英分離入力（name_en / series_en）に対応
UIのボタン/スライダーで髪型・瞳色・表情・衣装・ポーズを選択 → プロンプトに即反映
複数キャラ同時設定（双子ちゃんとか可能）
LoRA最大4スロット + サムネイル表示
生成履歴DB化 → 全履歴をUIで確認・過去設定をそのまま再編集
名前付きセッション複数保存 → よく使う設定をスロット管理
プリセット階層化（chara / scene / camera / quality / lora / composite）
セットアップ自己診断UI（/diagnostics で接続・設定を一括確認）
UI日英切替対応（OS言語を自動判定 + ヘッダーボタンで切替）
ログ機能（APIキー等を自動マスク・エラー記録・ZIP出力）
スマホ/タブレットから操作可能（同一Wi-Fiで）

## 生成例

| キャラ          | シーン/スタイル       | 生成画像（クリックで拡大） |
|-----------------|------------------------|----------------------------|
| 博麗霊夢       | 神社縁側で休憩        | ![霊夢](https://raw.githubusercontent.com/tomotto1296/anima-pipeline/refs/heads/main/images/reimu-shrine-relax.png)   |
| ずんだもん     | カフェで休憩          | ![ずんだもん](https://raw.githubusercontent.com/tomotto1296/anima-pipeline/refs/heads/main/images/sample_zundamon.png)  |

## 必要なもの（最小構成）

| 項目              | 詳細                                                                 | 備考                          |
|-------------------|----------------------------------------------------------------------|-------------------------------|
| Python            | 3.10以上                                                             | `pip install requests` のみ（bat起動時に自動インストール） |
| ComfyUI           | 最新版（0.16.4以上推奨）                                             | Anima対応ワークフロー必須     |
| Animaモデル       | Hugging Faceから3ファイルダウンロード                                | リンクは後述                  |
| LLM（オプション） | Gemini無料API / LM Studio / カスタムOpenAI互換                       | Geminiが一番手軽              |

:::message
外部ライブラリは `requests`（画像変換時はオプションで `Pillow`）のみです。WebUIはPython標準の `http.server` で動くため、GradioやFlaskなどの追加インストールは不要です。`requests` は `start_anima_pipeline.bat` 起動時に自動インストールされます。
:::

Animaモデルダウンロード（必須）：
@[card](https://huggingface.co/circlestone-labs/Anima/tree/main/split_files)

ComfyUI導入～Anima生成の手順についてはこちらでも解説！
https://youtu.be/HvHYzbqCWco?si=gWTsvN3G-WcK8Big&t=11
２分程度の短い動画です！

## セットアップ手順（10分で完了）

1. GitHubからZIPダウンロード → 解凍

@[card](https://github.com/tomotto1296/anima-pipeline)

2. ComfyUIでAnimaテンプレートを読み込み → 「Save (API Format)」で `image_anima_preview.json` として保存
   → リポジトリ内の `workflows/` フォルダに配置する（`anima_pipeline.py` と同じ階層）

:::message
ワークフローJSONは**必ず「Save (API Format)」で保存**してください。通常保存のJSONは使えません。
:::

3. `start_anima_pipeline.bat` をダブルクリック（Windowsの場合）
   初回はrequests自動インストール → 黒窓で何かキーを押す

:::message
batファイルがVS Code等で開く場合は、右クリック →「プログラムから開く」→「コマンドプロンプト」を選択してください。
:::

4. ブラウザで `http://localhost:7860` 開く → UI表示！

5. 初回設定（▶ 設定 パネル）
   - ComfyUI URL: `http://127.0.0.1:8188`（通常そのまま）
   - ワークフロー: `image_anima_preview.json`
   - LLMプラットフォーム: Gemini（おすすめ） → APIキー入力（Google AI Studioで無料取得）
   - 💾 設定を保存

:::message
スマホから使う場合は ComfyUI 起動時に `--listen --enable-cors-header` を追加し、PCのIPv4アドレス（`ipconfig`で確認）で `http://192.168.x.x:7860` にアクセスしてください。
:::

導入方法はこちらで解説！
https://youtu.be/DuQpBQhlbYE?si=Gp07MTaZEbEXJA9y&t=85

## 基本の使い方

1. キャラ名入力（水色欄） → LLM使用チェックONで「生成プロンプト」ボタン押す
2. 性別・年齢・髪型・色・表情などポチポチ選択
3. LoRA選択（サムネイル出るよ）
4. 生成パラメータ（Seed/Steps/CFG/Sampler）調整
5. ▶ 生成開始（Ctrl+EnterでもOK）

LLMなし派は直接英語タグ入力で最速生成可能。

### 便利機能

- プリセット保存/読込（よく使うキャラをJSONで管理）
- 🔍 自動プリセット生成（キャラ名からWiki+LLMで髪色・衣装自動埋め）
- ギャラリー表示 → クリックでプロンプト再利用

## トラブルシューティング（よくあるやつ）

| 症状 | 対処 |
|------|------|
| ComfyUIに繋がらない | URL確認 or ComfyUI起動忘れ |
| LLMエラー | APIキー再確認 / レート制限（Gemini無料は1日250回） |
| LoRAサムネイル出ない | ComfyUI `output` フォルダを**絶対パス**で設定 |
| ワークフローNode ID合わない | ワークフローJSONを自分で確認 |
| batファイルが開かない | 右クリック →「プログラムから開く」→「コマンドプロンプト」 |

詳細なガイドはこちら：

@[card](https://github.com/tomotto1296/anima-pipeline/blob/main/docs/guides/anima_pipeline_guide.md)

## 今後の予定

LoRA管理強化・ランダムプリセット・プリセット共有（v1.5.1）
一括生成・生成キュー・比較生成（v1.5.2）
LLM評価・自動タグ生成・再現補助（v1.5.x〜）

## 更新履歴
### 2026/03/27: v1.5.11リリース
非開発環境での安定性強化を目的としたリリースです
詳細リリースノート：
@[card](https://github.com/tomotto1296/anima-pipeline/releases/latest)

### 2026/03/23: v1.5.01リリース
- 生成履歴DB化 + 履歴からの再編集フロー
- プリセット階層化（chara/scene/camera/quality/lora/composite）
- 名前付きセッション複数保存
- セットアップ自己診断UI
- キャラ名・作品名の日英分離対応
- 起動時の設定自動補完・安定化

### 2026/03/20: v1.4.7リリース

- UI日英対応（ヘッダートグル + OS自動判定 + 永続保存）
- ログシステム追加（秘匿マスク・自動削除・API/ZIPエクスポート）
- プリセットサムネギャラリー実装
- 多数のバグ修正 & 起動安定化


## おわりに

技術力なくても、**キャラ愛だけで画像量産**できるようにしたくて作りました。
気に入ったらGitHubで⭐お願いします！
質問・issue・PR大歓迎です。

Xでも進捗つぶやいてます → [@RHU_AIstudio](https://x.com/RHU_AIstudio)

関連記事：

@[card](https://note.com/rhustudio/n/nf0dc2414f852)
