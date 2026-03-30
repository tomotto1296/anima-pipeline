---
name: start-feature
description: 新機能実装の開始。スペック確認 → ブランチ作成 → 実装計画の提示
argument-hint: [feature-id] (例: GEN-2, INPUT-6, fix/comfyui-timeout)
allowed-tools: Read, Glob, Bash
---

以下の手順で新機能の実装準備をしてください。

## Step 1: 現在のブランチ確認
`git branch` で現在のブランチを確認する。

## Step 2: スペック確認
引数 `$ARGUMENTS` を受け取り、対応する仕様書を探す。

- `docs/specs/` 以下で `$ARGUMENTS` を含むファイルを Glob で検索する
- 見つかった仕様書を読み、以下を日本語で要約する:
  - **目的**: 何を実現するか
  - **スコープ（In Scope）**: 実装する内容
  - **スコープ（Out of Scope）**: 実装しない内容
  - **変更対象ファイル**: 触るべきファイル一覧
  - **完了条件**: 実装完了の判断基準

スペックが見つからない場合は「仕様書が見つかりません。`docs/specs/` を確認してください」と報告して終了する。

## Step 3: ブランチ作成の提案
以下の形式でブランチ名を提案し、作成してよいか確認を求める:
- 機能追加: `feature/$ARGUMENTS-[概要]`
- バグ修正: `fix/$ARGUMENTS-[概要]`

承認されたら `git checkout -b [ブランチ名]` を実行する。

## Step 4: 実装計画の提示
スペックに基づいて、実装ステップを箇条書きで提示する。
実装には着手せず、「実装を開始してください」と言われるまで待機する。
