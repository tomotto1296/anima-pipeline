# ごろ寝しながらAI画像生成——Anima PipelineとTailscaleでスマホから自宅PCを操作する

## はじめに

布団に寝転がりながら、スマホで「生成」を押す。自宅のPCが唸りながら画像を作り始める——そんな使い方がAnima Pipelineでできます。

Anima Pipelineには、Tailscale経由でスマホからアクセスするための起動スクリプトが同梱されています。Tailscaleのセットアップさえ済ませれば、**あとはbatファイルを叩くだけ**。外出先でも、別の部屋からでも、自宅PCのComfyUIを操作できます。

この記事では、同一LAN接続からTailscale経由のアクセスまでを順番に説明します。

:::message
Anima Pipeline自体の概要・セットアップ・基本的な使い方は以下の記事をご覧ください。
https://zenn.dev/rhu/articles/anima-pipeline-comfyui-llm
:::

---

## 同一LAN接続（まず試したい人向け）

外出先からのアクセスより先に、同じWi-Fi内でスマホからアクセスする方法です。5分で確認できます。

### 手順

1. PCのIPv4アドレスを確認する（Windowsなら `ipconfig` で `192.168.x.x` 形式のもの）
2. PCでAnima Pipelineを起動する
3. スマホのブラウザで `http://<PCのIPv4>:7860` を開く

### ComfyUIの起動オプション（重要）

スマホからアクセスする場合、ComfyUIを以下のオプション付きで起動してください。

```
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --lowvram --listen --enable-cors-header
```

**なぜこのオプションが必要か：**
- `--listen` — ComfyUIをローカルホスト以外からも受け付ける設定。これがないとスマホからの接続を弾きます
- `--enable-cors-header` — Anima PipelineはWebSocketで生成進捗（%表示）をリアルタイム受信しています。CORS設定がないとスマホ側でWebSocket接続が失敗します

### つながらない場合のチェックポイント

- PCのファイアウォールでポート `7860` の受信が許可されているか
- URLが `https://` ではなく `http://` になっているか

---

## Tailscaleのセットアップ（外出先・別部屋からアクセスするために）

Tailscaleは、VPNを自分で構築しなくても「自分のデバイス同士をつなぐプライベートネットワーク」を作れるサービスです。無料プランで今回の用途は十分まかなえます。

### セットアップ手順（初回のみ）

1. [Tailscale公式サイト](https://tailscale.com/) でアカウントを作成
2. **PC側**：Tailscaleをインストールしてログイン
3. **スマホ側**：Tailscaleアプリをインストールして同じアカウントでログイン

これだけです。ルーターの設定変更やポート開放は不要です。

:::message
TailscaleのインストールやアカウントのセットアップはTailscale公式ドキュメントが詳しいです。
https://tailscale.com/kb/1017/install
:::

---

## Tailscale.batで接続する

Anima PipelineのZipには `start_anima_pipeline - Tailscale.bat` が同梱されています。

### 起動する

`start_anima_pipeline - Tailscale.bat` をダブルクリックして実行します。

コンソールに以下のように表示されたら成功です。

```
==============================
 Anima Pipeline Launcher
==============================
[INFO] Starting server... Open http://100.x.x.x:7860
```

**このURLをスマホのブラウザで開く**——これだけで接続完了です。

### batが何をしているか

このbatは起動時に `tailscale ip -4` コマンドでTailscaleのIPアドレスを自動検出し、コンソールに接続先URLを表示します。IPアドレスを自分で調べる手間がありません。

### つながらない場合

```
[WARN] Tailscale IP not found. Is Tailscale connected?
```

このメッセージが出た場合は、スマホ・PCの両方でTailscaleアプリがオンになっているか確認してください。

### 常用するならTailscale版一択

Tailscale版のbatは**同一LAN内でも問題なく動作します**。セットアップが済んだら、通常版とTailscale版を使い分ける必要はありません。以降はTailscale版を常用するのがおすすめです。

---

## スマホでの操作感

Anima Pipelineはスマホでの操作を考慮したUIになっています。

- **フローティングナビが画面下部に固定される** — スクロールせずに各セクションへジャンプできます
- **生成進捗がリアルタイム表示される** — 生成中に何%まで進んでいるかスマホで確認できます
- **接続バナーが表示される** — 起動直後にComfyUIへのWebSocket接続状況を画面上に通知します

布団の上でスマホを持ちながらでも、キャラ設定を変えて生成ボタンを押す——そういう使い方が一通りできます。

---

## まとめ

- ComfyUIを `--listen --enable-cors-header` 付きで起動する
- Tailscaleをスマホ・PC両方に入れてログインする
- `start_anima_pipeline - Tailscale.bat` を叩く
- コンソールに表示されたURLをスマホで開く

これだけで、ごろ寝しながらでも自宅PCでAI画像生成ができます。

Anima Pipelineは以下のリポジトリで公開しています。

https://github.com/tomotto1296/anima-pipeline

Anima Pipeline自体の概要・使い方はこちら。

https://zenn.dev/rhu/articles/anima-pipeline-comfyui-llm
