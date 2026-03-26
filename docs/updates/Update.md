# Update Log (from v1.4.6)

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

## 逶ｮ逧・縺薙・繝峨く繝･繝｡繝ｳ繝医・縲～v1.4.6` 莉･髯阪・螟画峩蜀・ｮｹ繧呈ｬ｡縺ｮ髢狗匱閠・∈蠑輔″邯吶＄縺溘ａ縺ｮ隕∫ｴ・〒縺吶・
## 繝舌・繧ｸ繝ｧ繝ｳ驕狗畑繝ｫ繝ｼ繝ｫ
- 邏ｰ縺九＞菫ｮ豁｣縺斐→縺ｫ蟆乗焚轤ｹ莉･荳九ｒ蠅怜・・井ｾ・ `1.4.7 -> 1.4.71 -> 1.4.72`・・- `1.4.699x` 邉ｻ縺ｯ `1.4.7` 縺ｨ縺励※豁｣蠑上Μ繝ｪ繝ｼ繧ｹ貂医∩

## 迴ｾ蝨ｨ繝舌・繧ｸ繝ｧ繝ｳ
- `1.5.1`


## 逶ｴ霑題ｿｽ險假ｼ・1.4.910・・- OUTPUT-8: 蜷榊燕莉倥″繧ｻ繝・す繝ｧ繝ｳ菫晏ｭ倥ｒ霑ｽ蜉・・/sessions` 荳隕ｧ繝ｻ`/sessions/<n>` 菫晏ｭ・隱ｭ霎ｼ/蜑企勁・・- 蜷悟錐菫晏ｭ俶凾縺ｯ `409 Conflict` 繧定ｿ斐＠縲～overwrite: true` 縺ｧ荳頑嶌縺堺ｿ晏ｭ・- `sessions/` 繝・ぅ繝ｬ繧ｯ繝医Μ繧定・蜍穂ｽ懈・縺励√ヵ繧｡繧､繝ｫ蜷阪し繝九ち繧､繧ｺ繧貞ｮ溯｣・- UI縺ｫ縲御ｿ晏ｭ俶ｸ医∩繧ｻ繝・す繝ｧ繝ｳ縲堺ｸ隕ｧ繧定ｿｽ蜉縺励´oad/Delete繧貞ｮ溯｣・- 譌｢蟄倥・ `/session`・・anima_session_last.json`・芽・蜍穂ｿ晏ｭ倥・蠕ｩ蜈・・邯ｭ謖・## 螳溯｣・し繝槭Μ繝ｼ・・1.4.6莉･髯搾ｼ・
### 1) 襍ｷ蜍穂ｸ崎憶繝ｻ譁・ｭ怜喧縺台ｿｮ豁｣
- `SyntaxError`・域枚蟄怜・邨らｫｯ荳肴ｭ｣・峨ｒ菫ｮ豁｣
- UTF-8/BOM豺ｷ蝨ｨ縺ｫ繧医ｋ隱ｭ縺ｿ霎ｼ縺ｿ繧ｨ繝ｩ繝ｼ繧剃ｿｮ豁｣
- BAT襍ｷ蜍墓凾縺ｮ譁・ｭ怜喧縺代ｒ謚大宛縺吶ｋ譁ｹ蜷代〒隱ｿ謨ｴ

### 2) 繝励Μ繧ｻ繝・ヨ隱ｭ縺ｿ霎ｼ縺ｿ螳牙ｮ壼喧
- `000_default.json` 縺悟・縺ｪ縺・ｸ榊・蜷医ｒ菫ｮ豁｣
- `/chara_presets` 縺ｧ `utf-8-sig` 隱ｭ縺ｿ霎ｼ縺ｿ蟇ｾ蠢・
### 3) UI險隱槫・譖ｿ・域律譛ｬ隱・闍ｱ隱橸ｼ・- 蛻晄悄陦ｨ遉ｺ險隱槭ｒOS險隱槭・繝ｼ繧ｹ縺ｧ閾ｪ蜍墓ｱｺ螳・- UI繝懊ち繝ｳ縺ｧ譌･譛ｬ隱・闍ｱ隱槭ｒ蛻・崛蜿ｯ閭ｽ
- `localStorage` 縺ｫ險隱櫁ｨｭ螳壹ｒ菫晏ｭ・- 陦ｨ遉ｺ繝・く繧ｹ繝医ｒ蜍慕噪縺ｫ鄂ｮ謠帙☆繧喫18n繝ｭ繧ｸ繝・け繧定ｿｽ蜉
- 豁｣隕丞喧鄂ｮ謠幢ｼ亥・隗・蜊願ｧ偵き繝・さ縲～+`縲∫ｩｺ逋ｽ蟾ｮ・峨↓蟇ｾ蠢・- 闍ｱ隱・>譌･譛ｬ隱槭∈謌ｻ縺励◆髫帙↓谿九ｋ譁・ｨ縺ｮ蜿悶ｊ縺薙⊂縺励ｒ邯咏ｶ壻ｿｮ豁｣

### 4) UI繝ｩ繝吶Ν隱ｿ謨ｴ・育洒邵ｮ/邨ｱ荳・・- 逕ｻ髱｢蟷・↓蜷医ｏ縺帙※闍ｱ隱槭Λ繝吶Ν繧堤洒邵ｮ
- 萓・
  - `Open Eyes -> Open`
  - `Half-Closed Eyes -> Half-Closed`
  - `Closed Eyes -> Closed`
  - `DELETE -> DEL`
- Bust/Height/Legs/Tail/Wings/View 遲峨・陦ｨ險倥ｒUI險ｭ險医↓蜷医ｏ縺帙※隱ｿ謨ｴ

### 5) STATUS/騾ｲ謐玲枚險縺ｮ螟夊ｨ隱槫ｯｾ蠢・- 繧ｹ繝・・繧ｿ繧ｹ陦ｨ遉ｺ繧定ｨ隱槫・譖ｿ縺ｫ霑ｽ蠕・- 萓・
  - `LLM: Done`
  - `ComfyUI: 1 queued`
  - `ComfyUI: Generating... 7%`
- 蜍慕噪逕滓・譁・ｨ・域焚蛟､蜷ｫ繧・峨・譌･譛ｬ隱槫喧繝代ち繝ｼ繝ｳ繧定ｿｽ蜉

### 6) 繧ｳ繝ｳ繧ｽ繝ｼ繝ｫ陦ｨ遉ｺ險隱・- 繧ｳ繝ｳ繧ｽ繝ｼ繝ｫ縺ｮ `[謗･邯夂｢ｺ隱江` 莉･髯阪・OS險隱槭↓霑ｽ蠕薙☆繧倶ｻ墓ｧ倥∈螟画峩
- UI險隱槭→繧ｳ繝ｳ繧ｽ繝ｼ繝ｫ險隱槭・逕ｨ騾比ｸ雁・髮｢蜿ｯ閭ｽ縺縺後∫樟陦後・OS蝓ｺ貅悶〒邨ｱ荳蟇・ｊ

### 7) 繝ｭ繧ｰ讖溯・・磯・蟶・・繧ｨ繝ｩ繝ｼ蝗槫庶蜷代￠・・- 繝ｭ繧ｰ蜃ｺ蜉帙ｒ霑ｽ蜉・磯・蟶・・繝医Λ繝悶Ν縺ｮ蝗槫庶逕ｨ騾費ｼ・- 譌｢螳壹Ο繧ｰ菫晏ｭ伜・: `anima-pipeline/logs/`
- 繝槭せ繧ｯ蟇ｾ雎｡:
  - `token`
  - `api key`
  - `authorization`
  - `Bearer ...`
- 菫晄戟譛滄俣縺ｫ繧医ｋ閾ｪ蜍募炎髯､繧貞ｮ溯｣・ｼ亥・譛溷､30譌･・・- 繝ｭ繧ｰ繝ｬ繝吶Ν繧定ｿｽ蜉・・normal` / `debug`・・- 萓句､悶ヵ繝・け縺ｧ譛ｪ蜃ｦ逅・ｾ句､悶ｒ繝ｭ繧ｰ蛹・- API霑ｽ蜉:
  - `GET /logs_info`
  - `GET /logs_zip`
- UI霑ｽ蜉:
  - `LOG DIRECTORY`
  - `LOG RETENTION DAYS`
  - `LOG LEVEL`
  - `OPEN LOGS`
  - `EXPORT LOGS ZIP`

### 8) 險ｭ螳壹ョ繝輔か繝ｫ繝医・譖ｴ譁ｰ
`settings/pipeline_config.default.json` 縺ｫ霑ｽ蜉:
- `console_lang`
- `log_dir`
- `log_retention_days`・亥・譛溷､30・・- `log_level`

### 9) 繝峨く繝･繝｡繝ｳ繝域紛蛯呻ｼ亥ｼ輔″邯吶℃/蜈ｬ髢句髄縺托ｼ・- `README.md` 繧旦TF-8縺ｧ蜀肴紛逅・ｼ育樟陦梧ｩ溯・繝ｻ繝ｭ繧ｰ讖溯・繝ｻv1.4.7貅門ｙ繧貞渚譏・・- `README_EN.md` 繧貞・謨ｴ蛯呻ｼ域律譛ｬ隱樒沿縺ｨ蜷檎ｭ峨・讒区・縺ｫ邨ｱ荳・・- `release_notes_v1.4.699999.md` 繧剃ｽ懈・縺励∵律譛ｬ隱・闍ｱ隱樔ｽｵ險伜喧
- `note_article_draft.md` 繧偵悟､画峩萓｡蛟､荳ｭ蠢・+ 謇矩・・繧ｬ繧､繝牙盾辣ｧ縲肴婿驥昴〒譖ｴ譁ｰ
- 髢｢騾｣繝輔ぃ繧､繝ｫ縺ｨ縺励※ `note_article_draft_v1.4.699999.md` / `anima_pipeline_guide_addendum_v1.4.699999.md` 繧剃ｽ懈・
- 繝・ヰ繝・げ逕ｨ遨ｺ繝輔ぃ繧､繝ｫ `_debug_page.html` 繧貞炎髯､

## 荳ｻ縺ｪ螟画峩繝輔ぃ繧､繝ｫ
- `anima_pipeline.py`
- `start_anima_pipeline.bat`
- `start_anima_pipeline - Tailscale.bat`
- `settings/pipeline_config.default.json`
- `README.md`
- `README_EN.md`
- `release_notes_v1.4.699999.md`・郁ｿｽ蜉・・- `note_article_draft.md`
- `note_article_draft_v1.4.699999.md`・郁ｿｽ蜉・・- `anima_pipeline_guide_addendum_v1.4.699999.md`・郁ｿｽ蜉・・- `LLM_candidates.md`・郁ｿｽ蜉・・- `docs/updates/Update.md`

## 驕狗畑荳翫・豕ｨ諢・- `releases` 縺ｯ驟榊ｸ・畑繝・せ繝育腸蠅・・縺溘ａ縲∽ｻ雁ｾ後・邱ｨ髮・＠縺ｪ縺・- UI縺ｯ隕九◆逶ｮ縺縺代〒縺ｪ縺上∬ｨ隱槫・譖ｿ縺ｮ蠕蠕ｩ・・A->EN->JA / EN->JA->EN・峨〒遒ｺ隱阪☆繧・
## 谿九ち繧ｹ繧ｯ・域ｬ｡髢狗匱閠・髄縺托ｼ・- 繧ｳ繝ｳ繧ｽ繝ｼ繝ｫ縺ｮ蜈ｨ繝｡繝・そ繝ｼ繧ｸ繧旦I險隱槭→螳悟・騾｣蜍輔＆縺帙ｋ縺九＾S騾｣蜍募崋螳壹↓縺吶ｋ縺倶ｻ墓ｧ倡｢ｺ螳・- i18n繧ｭ繝ｼ縺ｮ邯ｲ鄒・ユ繧ｹ繝茨ｼ育音縺ｫ蜍慕噪逕滓・繝ｩ繝吶Ν・・- 驟榊ｸ・ン繝ｫ繝峨〒縺ｮ繝ｭ繧ｰZIP蜿門ｾ怜ｰ守ｷ壹・譛邨６X隱ｿ謨ｴ

## 逶ｴ霑題ｿｽ險假ｼ・1.4.6999991 ・・v1.4.6999996・・
### 10) 襍ｷ蜍稗AT縺ｮ螳牙ｮ壼喧・磯壼ｸｸ迚・+ Tailscale迚茨ｼ・- `start_anima_pipeline.bat` / `start_anima_pipeline - Tailscale.bat` 繧呈峩譁ｰ
- UTF-8繧ｳ繝ｳ繧ｽ繝ｼ繝ｫ蟇ｾ遲悶ｒ霑ｽ蜉・・chcp 65001` / `PYTHONUTF8=1`・・- `setlocal/endlocal` 繧定ｿｽ蜉縺礼腸蠅・､画焚縺ｮ蠖ｱ髻ｿ繧貞ｱ謇蛹・- `py` 蜻ｼ縺ｳ蜃ｺ縺励ｒ `py -3` 縺ｫ蝗ｺ螳・- Tailscale迚医↓ `tailscale ip -4` 讀懷・縺ｨURL陦ｨ遉ｺ繧定ｿｽ蜉

### 11) README/README_EN 謨ｴ蛯・- `README.md` 繧貞・髱｢謨ｴ逅・ｼ域枚蟄怜喧縺鷹勁蜴ｻ縲∫樟陦梧ｩ溯・縺ｨv1.4.7貅門ｙ繧貞渚譏・・- `README_EN.md` 繧貞酔遲画ｧ区・縺ｧ蜀肴紛蛯・- `README.md` 縺ｮ髢｢騾｣險倅ｺ玖｡ｨ險倥ｒ邨ｱ荳・・zenn:` 蠖｢蠑擾ｼ・
### 12) UI譁・ｨ遏ｭ邵ｮ・郁恭隱櫁｡ｨ遉ｺ・・- `Bird's-Eye View` / `Worm's-Eye View` 竊・`Bird's-Eye` / `Worm's-Eye`
- `Large Frame` 竊・`Large`
- `Very Long` / `Bob Cut` 竊・`VLong` / `Bob`

### 13) 鬮ｪ蝙九・繧ｿ繝ｳ縺ｮ隕冶ｪ肴ｧ謾ｹ蝟・- 鬮ｪ蝙九げ繝ｫ繝ｼ繝・`蜈ｨ菴伝 繧・谿ｵ繝ｬ繧､繧｢繧ｦ繝亥喧
- 鬮ｪ蝙九げ繝ｫ繝ｼ繝・`蠕後ｍ` 繧・谿ｵ繝ｬ繧､繧｢繧ｦ繝亥喧
- 譌･譛ｬ隱朸I/闍ｱ隱朸I縺ｮ荳｡譁ｹ縺ｧ蜷梧ｧ倥↓驕ｩ逕ｨ

## 逶ｴ霑題ｿｽ險假ｼ・1.4.69999961 ・・v1.4.69999977・・
### 14) Issue #2 逹謇具ｼ医・繝ｪ繧ｻ繝・ヨ荳隕ｧ・九し繝繝榊渕逶､・・- `繧ｭ繝｣繝ｩ` 繧ｻ繧ｯ繧ｷ繝ｧ繝ｳ蜀・↓縲後・繝ｪ繧ｻ繝・ヨ荳隕ｧ・医し繝繝阪う繝ｫ・峨攻I繧剃ｻｮ螳溯｣・- 繧ｮ繝｣繝ｩ繝ｪ繝ｼ繝｢繝ｼ繝繝ｫ縺ｫ縲後・繝ｪ繧ｻ繝・ヨ縺ｮ繧ｵ繝繝阪う繝ｫ菴懈・縲阪・繧ｿ繝ｳ繧定ｿｽ蜉
- API霑ｽ蜉:
  - `POST /chara_preset_thumb`・医ぐ繝｣繝ｩ繝ｪ繝ｼ逕ｻ蜒・-> `chara/<preset>.webp` 逕滓・・・  - `GET /chara_thumb?file=...`・医・繝ｪ繧ｻ繝・ヨ繧ｵ繝繝埼・菫｡・・- `/chara_presets` 蠢懃ｭ斐↓ `_thumb_path` 繧定ｿｽ蜉
- 繝励Μ繧ｻ繝・ヨ蜑企勁譎ゅ↓蜷悟錐 `.webp` 繧ょ炎髯､

### 15) 繧ｵ繝繝咲函謌舌・陦ｨ遉ｺ荳榊・蜷医・菫ｮ豁｣
- `source image not found` 縺ｮ蜴溷屏繧剃ｿｮ豁｣
  - `view URL` 隗｣譫仙燕縺ｫ繝代せ螟画鋤縺励※縺・◆荳榊・蜷医ｒ隗｣豸・  - `view URL` / 繝ｭ繝ｼ繧ｫ繝ｫ繝代せ荳｡蟇ｾ蠢・- 繧ｮ繝｣繝ｩ繝ｪ繝ｼ髱櫁｡ｨ遉ｺ蛹紋ｸ榊・蜷医ｒ菫ｮ豁｣・・view_urls` 蜆ｪ蜈医↓蠕ｩ蟶ｰ・・- `/chara_presets?_ts=...` 縺ｫ繧医ｋ404繧剃ｿｮ豁｣・亥ｮ悟・荳閾ｴ繝ｫ繝ｼ繝亥ｯｾ蠢懶ｼ・- `/chara_thumb` 404縺ｮ蜴溷屏・・ET繝ｫ繝ｼ繝域悴驟咲ｽｮ・峨ｒ菫ｮ豁｣

### 16) 繝励Μ繧ｻ繝・ヨ荳隕ｧUI縺ｮ譛驕ｩ蛹厄ｼ医せ繝槭・雋闕ｷ蟇ｾ遲厄ｼ・- 繝励Μ繧ｻ繝・ヨ荳隕ｧ繧帝幕髢牙ｼ上↓螟画峩・亥・譛溘・髢会ｼ・- 繧ｵ繝繝咲判蜒上・荳隕ｧ繧帝幕縺・◆譎ゅ□縺大叙蠕・- 繧ｹ繝槭・襍ｷ蜍墓凾縺ｫ `loadCharaPresets()` 繧帝≦蟒ｶ縺怜・譛滓緒逕ｻ繧定ｻｽ驥丞喧
- 逶ｮ讓・ 逋ｽ逕ｻ髱｢蠕・■譎る俣縺ｮ遏ｭ邵ｮ

### 17) LoRA繧ｵ繝繝堺ｸ隕ｧ縺ｫ蟇・○縺溘ョ繧ｶ繧､繝ｳ隱ｿ謨ｴ
- 繧ｰ繝ｪ繝・ラ蟇・ｺｦ繝ｻ繧ｫ繝ｼ繝画ｯ皮紫繝ｻ繝ｩ繝吶Ν蟶ｯ繝ｻ譫邱壹ｒLoRA蛛ｴ縺ｸ邨ｱ荳
- 繧ｵ繝繝肴悴菴懈・繧ｫ繝ｼ繝峨・螟ｧ驥剰｡ｨ遉ｺ繧貞ｻ・ｭ｢縺励∽ｽ懈・貂医∩縺ｮ縺ｿ繧ｰ繝ｪ繝・ラ陦ｨ遉ｺ
- 縲梧峩譁ｰ蜈医阪・蛻･繧ｻ繝ｬ繧ｯ繝医〒蜈ｨ繝励Μ繧ｻ繝・ヨ縺九ｉ驕ｸ謚槫庄閭ｽ縺ｫ縺励※驕狗畑諤ｧ繧堤ｶｭ謖・
### 18) 繝励Μ繧ｻ繝・ヨ襍ｷ轤ｹ縺ｮ繧ｭ繝｣繝ｩ霑ｽ蜉讖溯・
- 縲梧峩譁ｰ蜈医肴ｨｪ縺ｫ `・・繧ｭ繝｣繝ｩ霑ｽ蜉` 繝懊ち繝ｳ繧定ｿｽ蜉
- 莉墓ｧ・
  - 驕ｸ謚樔ｸｭ繝励Μ繧ｻ繝・ヨ繧貞ｯｾ雎｡縺ｫ繧ｭ繝｣繝ｩ謨ｰ繧・1・域怙螟ｧ6・・  - 霑ｽ蜉縺輔ｌ縺・`繧ｭ繝｣繝ｩ1縲・` 蛛ｴ縺ｮ繝励Μ繧ｻ繝・ヨ驕ｸ謚槭↓閾ｪ蜍輔そ繝・ヨ
  - **隱ｭ霎ｼ・・oad・峨・陦後ｏ縺ｪ縺・*

### 19) 繧ｭ繝｣繝ｩ謨ｰ `0` 險ｱ蜿ｯ縺ｸ縺ｮ莉墓ｧ伜､画峩
- `B. 繧ｭ繝｣繝ｩ謨ｰ` 縺ｮ `min` 繧・`0` 縺ｫ螟画峩
- 蜷・Ο繧ｸ繝・け縺ｮ荳矩剞繧・`1` -> `0` 縺ｫ邨ｱ荳
  - `updateCharaBlocks`
  - `collectInput`
  - `collectSessionData`
  - 繧ｻ繝・す繝ｧ繝ｳ蠕ｩ蜈・・逅・- 0菴薙せ繧ｿ繝ｼ繝医°繧牙ｿ・ｦ√↓蠢懊§縺ｦ霑ｽ蜉縺ｧ縺阪ｋ驕狗畑縺ｫ螟画峩

### 20) 繧ｹ繝槭・UI蟠ｩ繧御ｿｮ豁｣・域峩譁ｰ蜈医そ繝ｬ繧ｯ繝茨ｼ・- `譖ｴ譁ｰ蜈・ 繧ｻ繝ｬ繧ｯ繝医→ `・九く繝｣繝ｩ霑ｽ蜉` 縺ｮ謚倥ｊ霑斐＠/蜈ｨ蟷・宛蠕｡繧定ｿｽ蜉
- 繧ｹ繝槭・縺ｧ繧ｻ繝ｬ繧ｯ繝医′讌ｵ邏ｰ陦ｨ遉ｺ縺ｫ縺ｪ繧句ｴｩ繧後ｒ菫ｮ豁｣

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


## 逶ｴ霑題ｿｽ險假ｼ・1.4.71 ・・v1.4.718・・
### 27) OUTPUT-4: 繝｡繧ｿ繝・・繧ｿ蝓九ａ霎ｼ縺ｿ蝓ｺ逶､繧貞ｮ溯｣・- `output_format`・・png`/`webp`・峨→ `embed_metadata` 繧定ｨｭ螳壹↓霑ｽ蜉縲・- 襍ｷ蜍墓凾遘ｻ陦悟・逅・ｒ霑ｽ蜉縺励∵里蟄・`pipeline_config.json` 縺ｫ荳崎ｶｳ繧ｭ繝ｼ縺後≠繧句ｴ蜷医・閾ｪ蜍戊｣懷ｮ後・- 逕ｻ蜒剰ｨｭ螳啅I縺ｫ `繝｡繧ｿ繝・・繧ｿ繧貞沂繧∬ｾｼ繧` 繝医げ繝ｫ繧定ｿｽ蜉・郁ｨｭ螳壻ｿ晏ｭ・蠕ｩ蜈・√そ繝・す繝ｧ繝ｳ蠕ｩ蜈・ｯｾ蠢懶ｼ峨・
### 28) PNG / WebP 縺ｮ繝｡繧ｿ繝・・繧ｿ譖ｸ縺崎ｾｼ縺ｿ繧貞ｮ溯｣・- PNG:
  - `parameters` 繧・`tEXt` 縺ｸ菫晏ｭ倥・  - 霑ｽ蜉縺ｧ `prompt` / `workflow` 繧ゆｿ晏ｭ假ｼ・omfyUI蠕ｩ蜈・畑騾費ｼ峨・- WebP:
  - Exif `UserComment` 縺ｨ XMP 縺ｮ荳｡譁ｹ縺ｸ菫晏ｭ倥・  - WebP螟画鋤螟ｱ謨玲凾縺ｯPNG縺ｸ繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ縺励∝・逅・ｶ咏ｶ壹・
### 29) Civitai莠呈鋤繝輔か繝ｼ繝槭ャ繝郁ｪｿ謨ｴ・域ｮｵ髫守噪・・- `Model hash` / `Lora hashes` 繧貞沂繧∬ｾｼ縺ｿ縲・- LoRA繧ｿ繧ｰ `<lora:name:weight>` 繧偵Γ繧ｿ繝・・繧ｿ蛛ｴ繝励Ο繝ｳ繝励ヨ縺ｸ莉倅ｸ弱・- `parameters` 繧但1111譛蟆丈ｺ呈鋤縺ｮ3陦梧ｧ区・縺ｸ謨ｴ逅・
  - Positive prompt
  - Negative prompt
  - `Steps, Sampler, CFG, Seed, Size, Model hash, Model, Lora hashes, Version`
- 繝上ャ繧ｷ繝･縺ｯAutoV2莠呈鋤・・0譯√・螟ｧ譁・ｭ暦ｼ峨ｒ蜆ｪ蜈医＠縺ｦ蜃ｺ蜉帙・
### 30) 繝｢繝・Ν/LoRA繝上ャ繧ｷ繝･隗｣豎ｺ縺ｮ蠑ｷ蛹・- `comfyui_output_dir` / `workflow_json_path` 縺九ｉComfyUI繝ｫ繝ｼ繝亥呵｣懊ｒ謗ｨ螳壹・- `models/checkpoints` / `models/unet` / `models/diffusion_models` / `models/loras` 繧貞・蟶ｰ謗｢邏｢縲・- basename荳閾ｴ繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ縺ｨ邁｡譏薙く繝｣繝・す繝･繧定ｿｽ蜉縲・
### 31) 驕狗畑荳翫・邨占ｫ厄ｼ亥ｮ滓ｩ滓､懆ｨｼ邨先棡・・- Civitai `Resources`:
  - PNG: 讀懷・OK
  - WebP: 讀懷・OK
- `embed_metadata = OFF`: 豁｣蟶ｸ
- 隍・焚LoRA: 豁｣蟶ｸ
- ComfyUI蜀崎ｪｭ霎ｼ:
  - PNG縺ｯworkflow蠕ｩ蜈グK
  - WebP縺ｯworkflow蠕ｩ蜈・↑縺暦ｼ育樟迥ｶ莉墓ｧ・莠呈鋤蟾ｮ縺ｨ縺励※謇ｱ縺・ｼ・
### 32) 迚井ｸ翫￡螻･豁ｴ・育ｴｰ菫ｮ豁｣・・- `1.4.71` 竊・`1.4.711` 竊・`1.4.712` 竊・`1.4.713` 竊・`1.4.714` 竊・`1.4.715` 竊・`1.4.716` 竊・`1.4.717` 竊・`1.4.718`


## 逶ｴ霑題ｿｽ險假ｼ・1.4.72 ・・v1.4.742・・
### 33) OUTPUT-3: 逕滓・螻･豁ｴDB + 蜈ｨ螻･豁ｴUI 縺ｮ蛻晄悄螳溯｣・- `generation_history` 繧担QLite縺ｧ豌ｸ邯壼喧・・history/history.db`・峨・- 險ｭ螳壹く繝ｼ繧定ｿｽ蜉:
  - `history_db_path`
  - `history_thumb_dir`
- API繧定ｿｽ蜉:
  - `GET /history_list`
  - `GET /history_detail`
  - `POST /history_update`
  - `POST /history_delete`
- 譌｢蟄倥ぐ繝｣繝ｩ繝ｪ繝ｼ縺ｫ繧ｿ繝悶ｒ霑ｽ蜉:
  - `繧ｻ繝・す繝ｧ繝ｳ螻･豁ｴ`
  - `蜈ｨ螻･豁ｴ`

### 34) 譌｢蟄魯B蜷代￠繝槭う繧ｰ繝ｬ繝ｼ繧ｷ繝ｧ繝ｳ菫ｮ豁｣
- 譌｢蟄倥ユ繝ｼ繝悶Ν縺ｫ荳崎ｶｳ繧ｫ繝ｩ繝縺後≠繧狗腸蠅・〒 `no such column` 縺悟・繧句撫鬘後ｒ菫ｮ豁｣縲・- 襍ｷ蜍墓凾/菫晏ｭ俶凾縺ｫ `PRAGMA table_info` 繧堤畑縺・◆荳崎ｶｳ繧ｫ繝ｩ繝閾ｪ蜍戊ｿｽ蜉繧貞ｮ溯｣・・
### 35) 繧ｮ繝｣繝ｩ繝ｪ繝ｼ逕ｻ蜒・繝｢繝ｼ繝繝ｫ螳牙ｮ壼喧・医そ繝・す繝ｧ繝ｳ + 蜈ｨ螻･豁ｴ・・- `/poll_status` 縺ｧ `file_paths` 繧貞━蜈医＠縲～png -> webp` 鄂ｮ謠帙ｒ閠・・縲・- `/get_image` 縺ｫ譖ｸ縺崎ｾｼ縺ｿ荳ｭ繝輔ぃ繧､繝ｫ蝗樣∩・医し繧､繧ｺ螳牙ｮ夂｢ｺ隱搾ｼ峨ｒ霑ｽ蜉縲・- 繝｢繝ｼ繝繝ｫ陦ｨ遉ｺ縺ｧ逕ｻ蜒丞呵｣懊ヵ繧ｩ繝ｼ繝ｫ繝舌ャ繧ｯ・亥・逕ｻ蜒丞､ｱ謨玲凾縺ｫ繧ｵ繝繝咲ｭ峨∈蛻・崛・峨・- `get_image 404` 蟇ｾ遲悶→縺励※ `png` 荳榊惠譎ゅ・ `webp` 閾ｪ蜍輔ヵ繧ｩ繝ｼ繝ｫ繝舌ャ繧ｯ繧定ｿｽ蜉縲・
### 36) 騾ｲ謐・陦ｨ遉ｺ縺ｮ蠕ｩ譌ｧ縺ｨ繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ
- WebSocket騾ｲ謐怜女菫｡縺ｮ閠先ｧ繧貞ｼｷ蛹厄ｼ域枚蟄怜・/Blob荳｡蟇ｾ蠢懶ｼ峨・- WS譛ｪ謗･邯壹・騾ｲ謐玲悴蜿嶺ｿ｡譎ゅ〒繧ゅ√・繝ｼ繝ｪ繝ｳ繧ｰ繝吶・繧ｹ縺ｮ逍台ｼｼ%陦ｨ遉ｺ繧定ｿｽ蜉縲・- 逕滓・荳ｭ `%` 陦ｨ遉ｺ縺悟・縺ｪ縺・こ繝ｼ繧ｹ繧貞屓驕ｿ縲・
### 37) 迚井ｸ翫￡螻･豁ｴ・育ｴｰ菫ｮ豁｣・・- `1.4.72` 竊・`1.4.721` 竊・`1.4.722` 竊・`1.4.723` 竊・`1.4.724` 竊・`1.4.725` 竊・`1.4.726` 竊・`1.4.727` 竊・`1.4.728` 竊・`1.4.729` 竊・`1.4.730` 竊・`1.4.731` 竊・`1.4.732` 竊・`1.4.733` 竊・`1.4.734` 竊・`1.4.735` 竊・`1.4.736` 竊・`1.4.737` 竊・`1.4.738` 竊・`1.4.739` 竊・`1.4.740` 竊・`1.4.741` 竊・`1.4.742`
### 38) INPUT-4・亥ｾ御ｻ倥￠險倬鹸・・ 繝励Μ繧ｻ繝・ヨ髫主ｱ､蛹・- 譛ｬ鬆・岼縺ｯ `v1.4.740` 譎らせ縺ｧ螳溯｣・ｸ医∩讖溯・繧貞ｾ御ｻ倥￠縺ｧ險倬鹸縺励◆繧ゅ・縲・- API:
  - `GET /presets/<category>`
  - `GET /presets/<category>/<name>`
  - `POST /presets/<category>/<name>`
  - `DELETE /presets/<category>/<name>`
- 蟇ｾ蠢懊き繝・ざ繝ｪ:
  - `chara / scene / camera / quality / lora / composite`
- 譌｢蟄倅ｺ呈鋤繝ｩ繝・ヱ繝ｼ:
  - `GET /chara_list`
  - `GET /chara_load?name=...`
  - `POST /chara_save`
  - `POST /chara_delete`
- 譌｢螳壹・繝ｪ繧ｻ繝・ヨ:
  - `Scene_default.json`
  - `Camera_default.json`
  - `Quality_default.json`
  - `Lora_default.json`
  - `Composite_default.json`
- Composite隱ｭ霎ｼ蜆ｪ蜈磯・ｽ・
  - 繧ｹ繝翫ャ繝励す繝ｧ繝・ヨ蜆ｪ蜈茨ｼ亥錐蜑榊盾辣ｧ縺ｯ陬懷勧諠・ｱ縺ｨ縺励※菫晄戟・・
### 39) INPUT-4 螳溯｣・ｿｮ豁｣・・1.4.740 譎らせ・・- Scene繧ｫ繝・ざ繝ｪ・亥ｱ句､・螻句・/迚ｹ谿奇ｼ峨→ sub・亥ｱ句､・螻倶ｸ・螻句・・峨・菫晄戟繝ｻ蠕ｩ蜈・ｒ菫ｮ豁｣縲・- `collectCheckedNeg is not defined` 縺ｫ繧医ｋQuality菫晏ｭ倥お繝ｩ繝ｼ繧剃ｿｮ豁｣縲・- 隱ｭ霎ｼ陦ｨ遉ｺ譁・ｨ繧・`隱ｭ霎ｼ謌仙粥: <name>` 縺ｫ邨ｱ荳縲・- 螳溯｣・せ繧ｭ繝ｼ繝槫ｷｮ蛻・
  - Scene: `scene_place` / `scene_outdoor` / `scene_place_category` 繧剃ｿ晄戟縲・  - Camera: `posv` / `posh` / `pos_camera` / `camera_free` 縺ｨ `all[*].posc` 繧剃ｿ晄戟縲・
### INPUT-4 蜍穂ｽ懃｢ｺ隱搾ｼ亥ｮ御ｺ・ｼ・- Scene / Camera / Quality / Lora / Composite 縺ｮ菫晏ｭ倥・隱ｭ霎ｼ繝ｻ蜑企勁
- Composite 縺ｮ菫晄戟・・cene/camera/quality/lora/chara snapshot・・- 譌｢蟄倥く繝｣繝ｩ繝励Μ繧ｻ繝・ヨ縺ｮ莠呈鋤蜍穂ｽ懶ｼ郁ｪｭ霎ｼ/菫晏ｭ・蜑企勁・・- 蜀崎ｵｷ蜍募ｾ後・繝励Μ繧ｻ繝・ヨ荳隕ｧ菫晄戟
- 逕滓・繝輔Ο繝ｼ縺ｮ蝗槫ｸｰ縺ｪ縺暦ｼ育函謌・螻･豁ｴ/蜀咲函謌撰ｼ・

## 逶ｴ霑題ｿｽ險假ｼ・1.4.743・・
### 40) 繧｢繧､繧ｳ繝ｳ驟堺ｿ｡蟆守ｷ壹・謨ｴ逅・ｼ医い繝励Μ / GitHub Pages 荳｡蟇ｾ蠢懶ｼ・- 繝ｫ繝ｼ繝磯・菫｡逕ｨ繧｢繧ｻ繝・ヨ繧定ｿｽ蜉: `assets/icons/*`縲・- GitHub Pages驟堺ｿ｡逕ｨ繧｢繧ｻ繝・ヨ繧定ｿｽ蜉: `docs/assets/*` + `docs/manifest.json`縲・- `docs/index.html` / `docs/index_en.html` 縺ｮ `<head>` 縺ｫ莉･荳九ｒ險ｭ螳・
  - `favicon-light.ico`
  - `favicon-dark.ico`・・prefers-color-scheme: dark`・・  - `apple-touch-icon.png`
  - `manifest.json`

### 41) favicon 縺ｮ繝ｩ繧､繝・繝繝ｼ繧ｯ蛻・屬
- 逕滓・繝輔ぃ繧､繝ｫ繧・`favicon-light.ico` / `favicon-dark.ico` 縺ｫ蛻・屬縲・- SVG驕狗畑繧貞ｻ・ｭ｢縺励￣NG/ICO驕狗畑縺ｸ邨ｱ荳縲・
### 42) 繧｢繝励Μ蜀・TTP驟堺ｿ｡縺ｫ髱咏噪繧｢繧､繧ｳ繝ｳ繝ｫ繝ｼ繝医ｒ霑ｽ蜉
- `anima_pipeline.py` 蛛ｴ縺ｧ莉･荳九ｒ驟堺ｿ｡:
  - `GET /assets/...`
  - `GET /manifest.json`
  - `GET /favicon.ico` / `GET /favicon-light.ico` / `GET /favicon-dark.ico`
- 繧｢繝励ΜUI (`/`) 縺ｮ `<head>` 縺ｫ favicon / manifest 蜿ら・繧定ｿｽ蜉縲・
### 43) Version Guard 縺ｮ菫ｮ豁｣
- `scripts/check_version_bump.py` 縺ｮ蟾ｮ蛻・愛螳壹ｒ菫ｮ豁｣・・git diff` 蠑墓焚鬆・ｼ峨・- 譁・ｭ励さ繝ｼ繝牙叙繧頑桶縺・ｒ螳牙ｮ壼喧・・utf-8` + `errors=replace`・峨・- `scripts/check_version_bump.py` 閾ｪ霄ｫ縺ｮ螟画峩縺ｯ迚井ｸ翫￡蠢・亥愛螳壹°繧蛾勁螟悶・
### 44) 迚井ｸ翫￡螻･豁ｴ
- `1.4.742` -> `1.4.743`

### 45) GitHub Pages逋ｽ逕ｻ髱｢縺ｮ蠕ｩ譌ｧ
- 莠玖ｱ｡:
  - `docs/index.html` / `docs/index_en.html` 縺ｫ譁・ｭ怜喧縺醍罰譚･縺ｮHTML遐ｴ謳搾ｼ磯哩縺倥ち繧ｰ蟠ｩ繧鯉ｼ峨′豺ｷ蜈･縺励；itHub Pages縺ｧ逋ｽ逕ｻ髱｢蛹悶・- 蜴溷屏:
  - 騾比ｸｭ邱ｨ髮・凾縺ｮ譁・ｭ励さ繝ｼ繝・鄂ｮ謠帛・逅・〒譌･譛ｬ隱曰TML譛ｬ譁・′遐ｴ謳阪・- 蟇ｾ蠢・
  - 逶ｴ霑第ｭ｣蟶ｸ繧ｳ繝溘ャ繝医・ `index` 2繝輔ぃ繧､繝ｫ縺ｸ蠕ｩ蜈・＠縺滉ｸ翫〒縲’avicon/manifest繝ｪ繝ｳ繧ｯ縺ｮ縺ｿ螳牙・縺ｫ蜀埼←逕ｨ縲・  - 菫ｮ豁｣繧ｳ繝溘ャ繝・ `162dda2`
- 陬懆ｶｳ:
  - 繧｢繧､繧ｳ繝ｳ霑ｽ蜉閾ｪ菴難ｼ・favicon-light/dark`, `manifest`・峨・逋ｽ逕ｻ髱｢縺ｮ逶ｴ謗･蜴溷屏縺ｧ縺ｯ縺ｪ縺・％縺ｨ繧堤｢ｺ隱阪・
---

## 逶ｴ霑題ｿｽ險假ｼ・1.4.875 ・・v1.4.883・・
### v1.4.875
- `core/handlers.py` 蠕ｩ譌ｧ縲・- `GET /chara_presets` 縺ｨ `POST /chara_presets` 縺ｮ豺ｷ邱壹ｒ菫ｮ豁｣縲・- 螢翫ｌ縺ｦ縺・◆ `POST` 繝倥Ν繝代・蜻ｨ霎ｺ縺ｮ荳崎ｦ∵妙迚・ｒ髯､蜴ｻ縲・
### v1.4.876
- `do_POST` 縺九ｉ `/config` 縺ｨ `/session` 繧偵・繝ｫ繝代・蛹悶・  - `_handle_post_config`
  - `_handle_post_session`

### v1.4.877
- `do_POST` 蜈磯ｭ縺ｮ繝励Μ繧ｻ繝・ヨ邉ｻ蛻・ｲ舌ｒ繝倥Ν繝代・蛹悶・  - `_handle_post_preset_routes`
  - 蟇ｾ雎｡: `/presets/*`, `/chara_save`, `/chara_delete`

### v1.4.878
- `do_POST` 譛ｫ蟆ｾ繝ｫ繝ｼ繝医ｒ繝倥Ν繝代・蛹悶・  - `_handle_post_terminal_routes`
  - 蟇ｾ雎｡: `/get_image`, `/chara_thumb`, `/cancel`, `/generate`

### v1.4.879
- `do_POST` 縺ｮ `/regen` 螟ｧ繝悶Ο繝・け繧帝未謨ｰ謚ｽ蜃ｺ縲・  - `_handle_post_regen`

### v1.4.880
- `do_POST` 荳ｭ谿ｵ繝ｫ繝ｼ繝医ｒ繝倥Ν繝代・蛹悶・  - `_handle_post_common_routes`
  - 蟇ｾ雎｡: `/config`, `/session`, `/history_update`, `/history_delete`, `/chara_presets`, `/chara_preset_thumb`, `*_tags`
- `do_POST` 縺ｮ蛻・ｲ先紛逅・ｼ医・繝ｪ繧ｻ繝・ヨ / 蜈ｱ騾・/ regen / 譛ｫ蟆ｾ繝ｫ繝ｼ繝茨ｼ峨・
### v1.4.881
- `do_POST` 縺ｮ蛻ｶ蠕｡繝輔Ο繝ｼ繧堤峩蛻・`if/return` 縺ｫ邨ｱ荳縲・- 譛ｪ蟇ｾ蠢・POST 繝代せ縺ｮ `404` 繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ繧定ｿｽ蜉縲・- 蛻・ｲ宣・ｒ譏守｢ｺ蛹厄ｼ・reset -> common -> regen -> terminal -> 404・峨・
### v1.4.882
- `do_DELETE` 繧偵・繝ｫ繝代・蛻・牡縲・  - `_handle_delete_preset_routes`
- DELETE 縺ｮ蛻ｶ蠕｡繝輔Ο繝ｼ繧・`if/return` 蠖｢蠑上〒謨ｴ逅・・- 譌｢蟄俶嫌蜍包ｼ・/presets/*` 縺ｮ蜑企勁API縺ｨ404繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ・峨・邯ｭ謖√・
### v1.4.883
- URL隗｣譫舌ｒ蜈ｱ騾壼喧縺吶ｋ `_parse_request_path_qs` 繧定ｿｽ蜉縲・- `do_GET` / `do_POST` / `do_DELETE` 縺ｮ蜀帝ｭ隗｣譫舌ｒ蜈ｱ騾壹・繝ｫ繝代・蛻ｩ逕ｨ縺ｸ邨ｱ荳縲・- 隗｣譫舌Ο繧ｸ繝・け縺ｮ驥崎､・炎貂幢ｼ域嫌蜍募､画峩縺ｪ縺暦ｼ峨・
## Checks
- `python -m py_compile core/handlers.py anima_pipeline.py` pass
- `python scripts/run_quick_checks.py --include-hooks-guard` pass


### v1.4.884
- `do_GET` 縺九ｉ `/session` 縺ｨ `/chara_presets` 繧偵・繝ｫ繝代・縺ｸ蛻・屬縲・  - `_handle_get_session_route`
  - `_handle_get_chara_presets_route`
- `do_GET` 蛻・ｲ舌・遏ｭ邵ｮ・域嫌蜍募､画峩縺ｪ縺暦ｼ峨・
### v1.4.885
- `GET /generate_preset` 蛻・ｲ舌ｒ繝倥Ν繝代・縺ｸ謚ｽ蜃ｺ縲・  - `_handle_get_generate_preset_route`
- `do_GET` 縺ｮ蛻・ｲ占ｦ矩壹＠繧呈隼蝟・ｼ域嫌蜍募､画峩縺ｪ縺暦ｼ峨・
### v1.4.886
- `do_GET` 縺ｮ `/session` 縺ｨ `/chara_presets` 繧呈里蟄倥・繝ｫ繝代・蜻ｼ縺ｳ蜃ｺ縺励∈邨ｱ荳縲・- GET蛻・ｲ舌・驥崎､・さ繝ｼ繝峨ｒ蜑頑ｸ幢ｼ域嫌蜍募､画峩縺ｪ縺暦ｼ峨・
### v1.4.887
- `do_GET` 繧呈ｮｵ髫弱ョ繧｣繧ｹ繝代ャ繝√↓蜀肴ｧ区・縲・  - `early -> info -> poll -> session -> history -> generate_preset -> chara_presets -> misc -> image -> 404`
- 霑ｽ蜉繝倥Ν繝代・:
  - `_handle_get_misc_routes`
  - `_handle_get_terminal_image_routes`
- GET縺ｮ雋ｬ蜍吝・髮｢繧貞ｼｷ蛹厄ｼ域嫌蜍募､画峩縺ｪ縺暦ｼ峨・
### v1.4.888
- `GET /poll_status` 繧偵Ν繝ｼ繝医・繝ｫ繝代・蛹悶・  - `_handle_get_poll_route`
- `do_GET` 縺ｮ蛻・ｲ舌ヱ繧ｿ繝ｼ繝ｳ繧堤ｵｱ荳・医☆縺ｹ縺ｦ繝倥Ν繝代・蛻､螳壹・繝ｼ繧ｹ・峨・
## 譛邨・UI遒ｺ隱搾ｼ・1.4.888・・1. 襍ｷ蜍輔＠縺ｦ繝医ャ繝苓｡ｨ遉ｺ・育區逕ｻ髱｢/譁・ｭ怜喧縺代↑縺暦ｼ峨・2. 險隱槫・譖ｿ: 譌･譛ｬ隱樞℡闍ｱ隱槭ｒ蠕蠕ｩ縺励※繝ｩ繝吶Ν蟠ｩ繧後↑縺励・3. 逕滓・繝輔Ο繝ｼ: Generate -> Cancel -> Re-Generate 縺ｧ迥ｶ諷玖｡ｨ遉ｺ縺悟崋逹縺励↑縺・・4. 螻･豁ｴ陦ｨ遉ｺ: 繧ｻ繝・す繝ｧ繝ｳ螻･豁ｴ/蜈ｨ螻･豁ｴ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縲√し繝繝崎｡ｨ遉ｺ縲√・繝ｼ繧ｸ繝ｳ繧ｰ縲・5. 繝励Μ繧ｻ繝・ヨ: 菫晏ｭ・隱ｭ霎ｼ/蜑企勁縲√し繝繝堺ｽ懈・縲√ワ繝ｼ繝峨Μ繝ｭ繝ｼ繝牙ｾ後・蜀崎｡ｨ遉ｺ縲・6. LoRA: 荳隕ｧ蜿門ｾ励√き繝ｼ繝牙牡蠖薙√し繝繝崎｡ｨ遉ｺ・亥叙蠕励〒縺阪ｋ迺ｰ蠅・〒・峨・7. 險ｭ螳・ `/config` 菫晏ｭ伜ｾ後↓蜀崎ｵｷ蜍輔＠縺ｦ蛟､縺御ｿ晄戟縺輔ｌ繧九・8. 404邉ｻ: 蟄伜惠縺励↑縺・ヱ繧ｹ縺ｸ繧｢繧ｯ繧ｻ繧ｹ縺励※UI縺悟｣翫ｌ縺ｪ縺・・
蝠城｡後′蜃ｺ縺溘ｉ縲∝・迴ｾ謇矩・ｼ域桃菴憺・ｼ峨→ Console/Network 縺ｮ襍､繧ｨ繝ｩ繝ｼ繧偵◎縺ｮ縺ｾ縺ｾ蜈ｱ譛峨・
### v1.4.889
- `GET` 繝ｫ繝ｼ繝医・谺關ｽ繧貞ｾｩ譌ｧ縲・  - `/version`
  - `/extra_tags`
  - `/style_tags`
  - `/neg_extra_tags`
- 險隱槫・譖ｿ譎ゅ・螻･豁ｴ陦ｨ遉ｺ蟠ｩ繧後・Console 404 縺ｮ蝗槫ｸｰ繧剃ｿｮ豁｣縲・
### v1.4.890
- 螻･豁ｴ繧ｻ繧ｯ繧ｷ繝ｧ繝ｳ縺ｮ險隱槫・譖ｿ繝ｩ繝吶Ν蟠ｩ繧鯉ｼ・???`・峨ｒ菫ｮ豁｣縲・- `frontend/index.html` 縺ｮ豺ｷ蝨ｨ繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ譁・ｭ怜・繧呈ｭ｣蟶ｸ縺ｪJA/EN譁・ｨ縺ｫ鄂ｮ謠帙・- 蠖ｱ髻ｿ: `Generation History (Session)`, `Session History`, `All History`, `Clear`, 繝励Μ繧ｻ繝・ヨ邂｡逅・Λ繝吶Ν縲・
### v1.4.891
- 蛻晏屓襍ｷ蜍墓凾縺ｫ LoRA 繧ｵ繝繝阪′ 404 縺ｫ縺ｪ繧句屓蟶ｰ繧剃ｿｮ豁｣縲・- `GET /lora_thumbnail` 繧・`core/handlers.py` 縺ｮ GET misc 繝ｫ繝ｼ繝医↓蠕ｩ譌ｧ縲・- 繧ｵ繝繝肴悴逋ｺ隕区凾縺ｯ `204` 繧定ｿ斐☆譌｢蟄倅ｺ呈鋤謖吝虚繧堤ｶｭ謖√・
### v1.4.892
- 逕滓・荳ｭ縺ｮ豕ｨ諢乗枚縲娯ｻ 襍ｷ蜍慕峩蠕後・騾ｲ謐・縺瑚｡ｨ遉ｺ縺輔ｌ縺ｪ縺・ｴ蜷医′縺ゅｊ縺ｾ縺呻ｼ亥・蝗杆S謗･邯壹・繧ｿ繧､繝溘Φ繧ｰ縺ｫ繧医ｋ・峨阪・闍ｱ險ｳ繧定ｿｽ蜉縲・- 闍ｱ隱朸I譎ゅ↓隧ｲ蠖捺ｳｨ險倥′譌･譛ｬ隱槭・縺ｾ縺ｾ谿九ｋ蝠城｡後ｒ菫ｮ豁｣縲・
## 霑ｽ險假ｼ・026-03-23 / REFACTOR-1 邯咏ｶ夲ｼ・
### 11) 繝｢繧ｸ繝･繝ｼ繝ｫ蛻・牡縺ｮ譛ｬ菴馴←逕ｨ
- `anima_pipeline.py` 繧偵お繝ｳ繝医Μ繝昴う繝ｳ繝井ｸｭ蠢・∈謨ｴ逅・- `core/` 縺ｸ讖溯・蛻・屬・・onfig / handlers / presets / history / frontend / runtime / llm / comfyui・・- `frontend/index.html` 縺ｨ `frontend/i18n.js` 繧貞､門・縺鈴°逕ｨ縺ｸ邨ｱ荳

### 12) 蝗槫ｸｰ荳榊・蜷医・菫ｮ豁｣・井ｻ雁屓・・- 險隱槫・譖ｿ蠕後↓螻･豁ｴ隕句・縺励′ `???` 縺ｫ縺ｪ繧句撫鬘後ｒ菫ｮ豁｣
- 404蝗槫ｸｰ・・/version`, `/extra_tags`, `/neg_extra_tags`, `/style_tags`・峨ｒ菫ｮ豁｣
- LoRA 繧ｵ繝繝阪う繝ｫ縺ｮ蛻晏屓繝ｭ繝ｼ繝牙､ｱ謨暦ｼ・/lora_thumbnail`・峨ｒ蜀肴磁邯壼庄閭ｽ縺ｫ菫ｮ豁｣
- 襍ｷ蜍慕峩蠕梧ｳｨ諢乗枚縺ｮ闍ｱ險ｳ譛ｪ驕ｩ逕ｨ繧剃ｿｮ豁｣

### 13) 襍ｷ蜍輔・讀懆ｨｼ繝輔Ο繝ｼ縺ｮ謨ｴ蛯・- `start_anima_pipeline - Tailscale.bat` 繧貞・菴懈・
- Hook/Quick Check 蟆守ｷ壹ｒ邯ｭ謖・ｼ・re-commit / pre-push・・- 螳溯｡檎｢ｺ隱・
  - `python scripts/check_frontend_syntax.py` 笨・  - `python scripts/run_quick_checks.py --include-hooks-guard` 笨・
### 14) 迴ｾ蝨ｨ縺ｮ陬懆ｶｳ
- 譌｢遏･隱ｲ鬘後→縺励※縲瑚ｵｷ蜍慕峩蠕後・騾ｲ謐・霑ｽ蠕馴≦繧後阪・邯咏ｶ夊ｦｳ蟇滂ｼ郁・蜻ｽ縺ｧ縺ｯ縺ｪ縺・◆繧∝ｾ檎ｶ壼ｯｾ蠢懶ｼ・- 譛ｬ霑ｽ險俶凾轤ｹ縺ｮ譛ｬ菴薙ヰ繝ｼ繧ｸ繝ｧ繝ｳ: `1.4.900`

### v1.4.900
- INPUT-12: 繧ｭ繝｣繝ｩ蜷・菴懷刀蜷阪↓ JA/EN 谺・ｒ霑ｽ蜉・・name_en` / `series_en`・峨・- INPUT-12: LLM縺ｪ縺礼函謌舌〒 EN 谺・━蜈医∫ｩｺ谺・凾縺ｯ JA 谺・ヵ繧ｩ繝ｼ繝ｫ繝舌ャ繧ｯ縺ｧ `name_(series)` 逕滓・縲・- INPUT-12: 繧ｻ繝・す繝ｧ繝ｳ菫晏ｭ・蠕ｩ蜈・・繧ｭ繝｣繝ｩ繝励Μ繧ｻ繝・ヨ菫晏ｭ・隱ｭ霎ｼ縺ｫ `name_en` / `series_en` 繧貞渚譏縲・- INPUT-5: 繝励Μ繧ｻ繝・ヨ繧ｫ繝・ざ繝ｪ縺ｫ `negative` 繧定ｿｽ蜉縺励～/presets/negative/*` 縺ｧ菫晏ｭ・隱ｭ霎ｼ/蜑企勁蟇ｾ蠢懊・- INPUT-5: 繝阪ぎ繝・ぅ繝冶ｪｿ謨ｴ繧ｻ繧ｯ繧ｷ繝ｧ繝ｳ荳企Κ縺ｫ Negative Preset UI・磯∈謚・菫晏ｭ・隱ｭ霎ｼ/蜑企勁・峨ｒ霑ｽ蜉縲・- INPUT-5: 繝阪ぎ繝・ぅ繝悶・繝ｪ繧ｻ繝・ヨ縺ｧ `quality_neg_tags` / `neg_extra_tags` / `neg_style_tags` / `neg_extra_note` / `selected_neg_safety` 繧剃ｿ晏ｭ・蠕ｩ蜈・・- Config: `last_negative_preset` 繧・`pipeline_config` 縺ｮ菫晏ｭ伜ｯｾ雎｡縺ｫ霑ｽ蜉縲・- 讀懆ｨｼ: `python scripts/check_frontend_syntax.py` / `python scripts/run_quick_checks.py --include-hooks-guard` 謌仙粥縲・
### v1.4.901
- `/generate_preset` 縺ｮ蜻ｽ蜷阪ｒ JA/EN 騾｣蜍輔↓諡｡蠑ｵ縲Ａname_en` 縺悟・蜉帙＆繧後※縺・ｋ蝣ｴ蜷医∽ｿ晏ｭ伜錐縺ｮ譌｢螳壼､繧・`JA・・N・荏 蠖｢蠑上↓邨ｱ荳縲・- 閾ｪ蜍慕函謌舌・繝ｪ繧ｻ繝・ヨ菫晏ｭ俶凾縺ｫ `name_en` / `series_en` 繧ゆｿ晄戟縲・- 繝輔Ο繝ｳ繝医・縲後・繝ｪ繧ｻ繝・ヨ閾ｪ蜍慕函謌舌阪後く繝｣繝ｩ繝励Μ繧ｻ繝・ヨ菫晏ｭ倥阪・繝・ヵ繧ｩ繝ｫ繝亥錐繧貞酔縺倩ｦ丞援・・A・・N・牙━蜈茨ｼ峨↓邨ｱ荳縲・
### v1.4.902
- `settings/preset_gen_prompt.txt` 縺ｫ蜃ｺ蜉帙ヵ繧ｩ繝ｼ繝槭ャ繝亥宛邏・ｒ霑ｽ險假ｼ医さ繝ｼ繝峨ヵ繧ｧ繝ｳ繧ｹ遖∵ｭ｢繝ｻ蜊倅ｸJSON蠢・茨ｼ峨・- `/generate_preset` 縺ｧ LLM遨ｺ蠢懃ｭ・蜀・ｮｹ荳崎ｶｳ譎ゅ↓1蝗槭□縺題・蜍輔Μ繝医Λ繧､縺吶ｋ蜃ｦ逅・ｒ霑ｽ蜉縲・
### v1.4.903
- `/generate_preset` 縺ｧ `name_en` / `series_en` 縺ｮ閾ｪ蜍戊｣懷ｮ後ｒ霑ｽ蜉・・anbooru繧ｿ繧ｰ讀懃ｴ｢ -> 陬懷勧LLM謗ｨ螳・-> 繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ縺ｮ鬆・ｼ峨・- 譌･譛ｬ隱槫錐縺ｮ縺ｿ蜈･蜉帶凾縺ｧ繧ゅ∬ｿ泌唆繝励Μ繧ｻ繝・ヨ縺ｫ闍ｱ隱槭ち繧ｰ蛟呵｣懊ｒ蜷ｫ繧√ｋ繧医≧謾ｹ蝟・・- 閾ｪ蜍慕函謌舌・繝ｪ繧ｻ繝・ヨ蜷阪・譌｢螳壼､蛻､螳壹ｒ陬懷ｮ悟ｾ後・ `name_en` 繝吶・繧ｹ縺ｫ邨ｱ荳・・JA・・N・荏・峨・
### v1.4.904
- 闍ｱ隱槫錐陬懷勧謗ｨ螳壹〒蛻ｶ蠕｡隱橸ｼ井ｾ・ `no_think`・峨ｒ蛟呵｣懊°繧蛾勁螟悶☆繧九ぎ繝ｼ繝峨ｒ霑ｽ蜉縲・- 陬懷勧謗ｨ螳壹・繝ｭ繝ｳ繝励ヨ繧定ｪｿ謨ｴ縺励∽ｸ崎ｦ√↑蛻ｶ蠕｡隱槭・豺ｷ蜈･繧呈椛蛻ｶ縲・
### v1.4.905
- `/generate_preset` 縺ｮ闍ｱ隱槫錐陬懷勧謗ｨ螳壹↓螯･蠖捺ｧ繝舌Μ繝・・繧ｷ繝ｧ繝ｳ繧定ｿｽ蜉縲・- 謖・､ｺ譁・ｷｷ蜈･邉ｻ縺ｮ荳肴ｭ｣蛟呵｣懶ｼ井ｾ・ `the_user_wants_to_convert...`・峨ｒ髯､螟悶・
### v1.4.906
- `Series EN` 縺檎ｩｺ縺ｫ縺ｪ繧九こ繝ｼ繧ｹ蜷代￠縺ｫ縲～name_(series)` 蠖｢蠑上・繧ｭ繝｣繝ｩ繧ｿ繧ｰ縺九ｉ series 繧呈歓蜃ｺ縺吶ｋ繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ繧定ｿｽ蜉縲・- 縺薙ｌ縺ｫ繧医ｊ JA菴懷刀蜷阪・縺ｿ蜈･蜉帶凾縺ｧ繧ゅ√く繝｣繝ｩ繧ｿ繧ｰ縺ｫ series 縺悟性縺ｾ繧後ｋ蝣ｴ蜷医・ `Series EN` 繧定｣懷ｮ悟庄閭ｽ縲・
### v1.4.907
- EN陬懷ｮ悟､縺ｮ豁｣隕丞喧繧定ｿｽ蜉: `name_(series)` 縺ｯ `Name EN=name` / `Series EN=series` 縺ｫ蛻・屬縲・- `Series EN` 縺ｮ `fate_(series)` 蠖｢蠑上ｒ `fate` 縺ｸ豁｣隕丞喧縲・- `Name EN` 縺ｫ縺ｯASCII繧ｿ繧ｰ螯･蠖捺ｧ繝√ぉ繝・け繧帝←逕ｨ縺励∵律譛ｬ隱槭ｄ謖・､ｺ譁・ｷｷ蜈･繧帝勁螟悶・
### v1.4.908
- Positive preset 繧定ｿｽ蜉・・ositive 繧ｫ繝・ざ繝ｪ菫晏ｭ・隱ｭ霎ｼ/蜑企勁・峨・- 繝昴ず繝・ぅ繝冶ｪｿ謨ｴ繧ｻ繧ｯ繧ｷ繝ｧ繝ｳ荳企Κ縺ｫ Positive Preset UI・磯∈謚・菫晏ｭ・隱ｭ霎ｼ/蜑企勁・峨ｒ霑ｽ蜉縲・- Positive preset 縺ｧ selected_period / year / quality_tags / meta_tags / selected_safety / style_tags / extra_tags / extra_note 繧剃ｿ晏ｭ・蠕ｩ蜈・・- Config/Session 縺ｫ last_positive_preset / lastPositivePreset 繧定ｿｽ蜉縺励∵怙邨る∈謚槭ｒ蠕ｩ蜈・・
### v1.4.909
- Positive Preset UI 譁・ｨ縺ｮ譁・ｭ怜喧縺代ｒ菫ｮ豁｣・磯∈謚櫁い繝ｻ遒ｺ隱阪ム繧､繧｢繝ｭ繧ｰ繝ｻ繧ｨ繝ｩ繝ｼ繝｡繝・そ繝ｼ繧ｸ・峨・- Positive preset 縺ｮ隱ｭ霎ｼ/菫晏ｭ・蜑企勁蟆守ｷ壹〒陦ｨ遉ｺ繝｡繝・そ繝ｼ繧ｸ繧呈ｭ｣蟶ｸ蛹悶・
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

### 15) guides蜀肴紛蛯呻ｼ・026-03-23・・- `docs/guides/anima_pipeline_guide.md` 繧偵Μ繝輔ぃ繧ｯ繧ｿ蠕梧ｧ区・縺ｫ蜷医ｏ縺帙※蜈ｨ髱｢譖ｴ譁ｰ・域枚蟄怜喧縺題ｧ｣豸茨ｼ・- `docs/guides/anima_pipeline_guide_en.md` 繧貞酔蜀・ｮｹ縺ｧ蜀肴紛蛯呻ｼ域ｧ区・繝ｻ襍ｷ蜍輔・譛蟆城・蟶・そ繝・ヨ繧堤樟陦悟喧・・- 繧ｯ繧､繝・け繝√ぉ繝・け蟆守ｷ壹ｒ `quick_checks_and_hooks.md` 蜿ら・縺ｸ邨ｱ荳

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
- 驟榊ｸ・ヰ繝ｼ繧ｸ繝ｧ繝ｳ繧・1.4.914 -> 1.5.0 縺ｫ譖ｴ譁ｰ縲・- README.md / README_EN.md / docs/specs/features.md / docs/updates/roadmap.md 縺ｮ迴ｾ蝨ｨ繝舌・繧ｸ繝ｧ繝ｳ陦ｨ險倥ｒ `v1.5.0` 縺ｫ蜷梧悄縲・

### v1.5.01
- Added startup config backfill for missing keys from `DEFAULT_CONFIG` in `load_config()`.
- Added backfill log line: `[config] 荳崎ｶｳ繧ｭ繝ｼ繧定｣懷ｮ後＠縺ｾ縺励◆`.
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

