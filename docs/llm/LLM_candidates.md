# LLM候補まとめ（anima_pipeline向け）

作成日: 2026-03-20

## 前提
このアプリは、以下の流れを前提に動作します。
1. UIで入力
2. LLMへ入力内容を渡す
3. LLMが画像生成用プロンプトを返す

## 要件（優先度）
1. THINKINGなど余計な出力を混ぜない（最優先）
2. なるべく無料
3. NSFW対応可能
4. LM Studioで使えると望ましい

---

## 推奨構成（結論）

### A. 第一候補（本命）
**LM Studioローカル + Instruct系モデル**

- 理由:
  - 余計な推論文（THINKING）を抑えやすい
  - 実質無料で継続運用しやすい
  - NSFWの運用自由度が高い
  - LM Studio要件を満たす

- 推奨モデル名（具体）:
  - `qwen2.5-14b`（バランス）
  - `hermes-3-8b`（軽量）
  - `mistral-small`（品質寄り）

### B. 第二候補（クラウド無料枠の保険）
**Gemini Flash-Lite**

- 推奨モデル名（具体）:
  - `gemini-2.5-flash-lite`（本命）
  - `gemini-2.5-flash`（上位・予備）

- 注意:
  - NSFWはクラウド側ポリシー制限が入る
  - THINKING抑制は可能だが、ローカルより制御余地は小さい

---

## 最終おすすめ（2本立て）
1. メイン運用: **LM Studio + `qwen2.5-14b`**
2. 代替運用: **Gemini API + `gemini-2.5-flash-lite`**

---

## THINKING混入を減らす実装メモ

- Thinking系ではなく **Instruct系** を使う
- 出力形式を固定する
  - 例: `Return only comma-separated prompt tags. No explanations.`
- `temperature` を低め（0.1〜0.3）
- 必要ならJSONスキーマで出力拘束

---

## 参考リンク

### Gemini
- Models: https://ai.google.dev/gemini-api/docs/models/gemini
- Pricing: https://ai.google.dev/pricing

### LM Studio
- OpenAI互換API: https://lmstudio.ai/docs/app/api/endpoints/openai/
- Local server: https://lmstudio.ai/docs/developer/core/server
- Model page: https://lmstudio.ai/models

### モデル個別（参考）
- Qwen2.5 14B: https://lmstudio.ai/model/qwen2.5-14b-instruct
- Hermes 3 8B: https://lmstudio.ai/model/hermes-3-llama-3.1-8b
- Mistral Small: https://lmstudio.ai/models/mistral-small
