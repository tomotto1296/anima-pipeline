const __LANG_STORAGE_KEY__ = 'anima_ui_lang_v2';
const __OS_DEFAULT_LANG__ = (typeof __OS_LANG__ === 'string' && __OS_LANG__.toLowerCase().startsWith('ja')) ? 'ja' : 'en';
let currentLang = localStorage.getItem(__LANG_STORAGE_KEY__) || __OS_DEFAULT_LANG__;
if(currentLang !== 'ja' && currentLang !== 'en') currentLang = __OS_DEFAULT_LANG__;

const BASE_I18N_MAP_EN = {
  'キャラクター生成（プロンプト+画像）': 'Character Generation (Prompt + Image)',
  '設定': 'Settings',
  '必須': 'Required',
  '必須設定': 'Required Settings',
  'LLMを使わないなら不要': 'Not required if LLM is disabled',
  'オプション': 'Optional',
  '画像設定': 'Image Settings',
  '生成パラメータ': 'Generation Params',
  'キャラクター': 'Character',
  'シーン・雰囲気': 'Scene / Mood',
  'プロンプト調整・追加（再生成に反映されます）': 'Prompt Tuning / Additions (used for re-generation)',
  'ネガティブ調整': 'Negative Prompt Tuning',
  '処理状況': 'Status',
  '先頭へ': 'Back to Top',
  '設定を保存': 'Save Settings',
  'セッション保存': 'Save Session',
  '開く': 'Open',
  '再読み込み': 'Reload',
  '接続テスト': 'Connection Test',
  '接続テスト中...': 'Connection Test in progress...',
  '接続確認': 'Connection Check',
  '接続中': 'Connecting',
  '接続OK': 'Connected',
  '接続失敗': 'Connection failed',
  '接続エラー': 'Connection error',
  'モデル': 'Model',
  '保存形式': 'Output Format',
  'メタデータを埋め込む': 'Embed Metadata',
  '生成開始': 'Generate',
  '生成中止': 'Cancel',
  '再画像生成': 'Re-generate Image',
  '生成結果': 'Generated Result',
  'プロンプト再利用': 'Reuse Prompt',
  'フォルダを開く': 'Open Folder',
  '閉じる': 'Close',
  '生成履歴（このセッション）': 'Generation History (Session)',
  'セッション履歴': 'Session History',
  '全履歴': 'All History',
  '全履歴はまだありません': 'No history yet',
  'クリア': 'Clear',
  'コピー': 'Copy',
  'コピー済': 'Copied',
  'ポジティブ': 'Positive',
  'ネガティブ': 'Negative',
  '状況': 'Status',
  '画像': 'Image',
  'パラメータ': 'Params',
  'キャラ': 'Chara',
  'シーン': 'Scene',
  'ポジ調整': 'Prompt',
  'ネガ調整': 'Negative',
  '読み込みエラー': 'Load error',
  '保存しました': 'Saved',
  '削除しますか？': 'Delete this item?',
  'をDelete this item?': ' to delete?',
  '削除': 'Delete',
  'プリセット一覧（サムネイル）': 'Preset List (Thumbnails)',
  '対象プリセット': 'Target Preset',
  'ギャラリー画像を拡大表示してから「プリセットのサムネイル作成」を押してください': 'Open a gallery image, then click "Create Preset Thumbnail".',
  'プリセットのサムネイル作成': 'Create Preset Thumbnail',
  'サムネイル未設定': 'No thumbnail',
  'サムネ作成対象のプリセットを選択してください': 'Select a preset to assign thumbnail.',
  'ギャラリー画像を先に開いてください': 'Open a gallery image first.',
  'サムネイルを更新しますか？': 'Update this thumbnail?',
  'サムネイル保存: ': 'Thumbnail saved: ',
  'サムネイル作成失敗: ': 'Thumbnail creation failed: ',
  '追加': 'Add',
  'エラー': 'Error',
  '不明なエラー': 'Unknown error',
  '中止されました': 'Cancelled',
  '中止': 'Cancel',
  'ネットワークエラー': 'Network error',
  'スキップ': 'Skipped',
  '完了': 'Done',
  '送信失敗': 'Send failed',
  'キューに追加': 'Queued',
  '生成中': 'Generating',
  '枚完了': 'done',
  '枚': 'images',
  'ランダムな値を生成': 'Generate random value',
  'キャラ名を入力してください': 'Please enter character name',
  'シリーズまたはいずれかのキャラ名を入力してください': 'Please enter a series or at least one character name',
  'プロンプトを再利用モードに設定しました。「↺ 再画像生成」ボタンで送信できます。': 'Prompt was set to reuse mode. Use the "Re-generate Image" button to submit.',
  'Danbooru Wiki+LLMでプリセット自動生成': 'Auto-generate preset with Danbooru Wiki + LLM',
  '（長押しで選択）': '(Long-press to select)',
  '読込': 'Load',
  '保存': 'Save',
  '詳細': 'Details',
  '女': 'Female',
  '男': 'Male',
  '不明': 'Unknown',
  '未設定': 'Unset',
  '大人': 'Adult',
  '子供': 'Child',
  '髪型': 'Hair Style',
  '髪色': 'Hair Color',
  '肌の色': 'Skin Tone',
  '目の状態': 'Eye State',
  '目の色': 'Eye Color',
  '口の形': 'Mouth',
  '表情': 'Expression',
  '向き': 'Direction',
  '状態': 'State',
  '前': 'Front',
  '後ろ': 'Back',
  '日本語入力': 'Input in English',
  'その他': 'Other',
  '作品名': 'Series',
  'キャラ名': 'Character Name',
  'キャラ名 JA *': 'Name JA *',
  'キャラ名 EN': 'Name EN',
  '作品名 JA': 'Series JA',
  '作品名 EN': 'Series EN',
  'オリジナル': 'Original',
  'プリセット選択': 'Preset',
  'ネガティブプリセット': 'Negative Preset',
  'ネガティブプリセットを選択': 'Select negative preset',
  '── ネガティブプリセット選択 ──': '── Select negative preset ──',
  'ネガティブプリセット名を入力してください': 'Please enter negative preset name',
  '現在のネガティブ設定を上書きしますか？': 'Overwrite current negative settings?',
  'ポジティブプリセット': 'Positive Preset',
  'ポジティブプリセットを選択': 'Select positive preset',
  '── ポジティブプリセット選択 ──': '── Select positive preset ──',
  'ポジティブプリセット名を入力してください': 'Please enter positive preset name',
  '現在のポジティブ設定を上書きしますか？': 'Overwrite current positive settings?',
  '共通作品（任意）': 'Shared Series (Optional)',
  'キャラ数': 'Chara Count',
  '全裸': 'Nude',
  '半裸': 'Half Nude',
  '上下': 'Top/Bottom',
  '背丈': 'Height',
  'バスト': 'Bust',
  '普通': 'Normal',
  '姿勢': 'Posture',
  '動作': 'Action',
  '動作・ポーズ': 'Action / Pose',
  '腕・手': 'Arms / Hands',
  '視線': 'Gaze',
  '時間帯': 'Time of Day',
  '天気': 'Weather',
  '画面TOP/BOTTOM': 'Frame Top / Bottom',
  '画面左右': 'Frame Left / Right',
  '場所': 'Location',
  '世界観': 'World',
  '体型': 'Body Build',
  '脚': 'Legs',
  '付属': 'Attachments',
  '尻尾': 'Tail',
  '翼': 'Wings',
  '瞳の色': 'Eye Color',
  '補足メモ（日本語）→ LLMに渡す（1回目のプロンプト生成のみ）': 'Additional Note (sent to LLM only on first generation)',
  '送信POSITIVEプロンプト（生成＋ADDタグ）': 'Sent POSITIVE Prompt (Generated + Added Tags)',
  '送信ポジティブプロンプト（生成＋追加タグ）': 'Sent Positive Prompt (Generated + Added Tags)',
  'Negativeプロンプト調整': 'Negative Prompt Tuning',
  '期間タグ（Positiveと共通）': 'Period Tags (shared with Positive)',
  '期間タグ': 'Period Tags',
  'ポジティブの期間タグ設定がネガティブにも反映されます': 'Positive period-tag settings are also applied to Negative.',
  '品質タグ（人間ベース: NORMAL/LOW/WORST）': 'Quality Tags (Human base: NORMAL/LOW/WORST)',
  '品質タグ（Pony）': 'Quality Tags (Pony)',
  '品質タグ（人間ベース）': 'Quality Tags (Human base)',
  'メタタグ': 'Meta Tags',
  '安全タグ（単一選択）': 'Safety Tags (single-select)',
  'スタイル（@アーティスト名・ネガティブ専用）': 'Style (@Artist Name, Negative only)',
  'スタイル（@アーティスト名）': 'Style (@Artist Name)',
  '新規Add': 'Add New',
  '追記文（英語）→ プロンプト末尾に直接Add': 'Extra Text (English) -> append directly to prompt end',
  'カスタムタグを入力': 'Enter custom tag',
  '例:': 'e.g.:',
  'ワークフローJSONパス（フォールバック）': 'Workflow JSON Path (fallback)',
  'ワークフローJSONが見つかりません:': 'Workflow JSON not found:',
  'ワークフローJSONが見つかりません': 'Workflow JSON not found',
  'WORKFLOWS/ フォルダから選択（優先）': 'Select from WORKFLOWS/ folder (preferred)',
  'LLMを使うならRequired': 'Required if using LLM',
  '任意': 'Optional',
  'LLMツール統合': 'LLM Tool Integrations',
  '⑧ LLMツール統合': '⑧ LLM Tool Integrations',
  'COMFYUI OUTPUT フォルダ（WEBP変換用・絶対パスで入力推奨）': 'COMFYUI OUTPUT Folder (for WEBP conversion, absolute path recommended)',
  '⑨ COMFYUI OUTPUT フォルダ（WEBP変換用・絶対パス推奨）': '⑨ COMFYUI OUTPUT FOLDER (for WEBP conversion, absolute path recommended)',
  '⑨ COMFYUI OUTPUT フォルダ（WEBP変換用、絶対パス推奨）': '⑨ COMFYUI OUTPUT FOLDER (for WEBP conversion, absolute path recommended)',
  'WEBP変換用': 'for WEBP conversion',
  '絶対パス推奨': 'absolute path recommended',
  'ログ保存フォルダ': 'LOG DIRECTORY',
  '⑩ ログ保存フォルダ': '⑩ LOG DIRECTORY',
  'ログ保持日数': 'LOG RETENTION DAYS',
  '⑪ ログ保持日数': '⑪ LOG RETENTION DAYS',
  'ログレベル': 'LOG LEVEL',
  '⑫ ログレベル': '⑫ LOG LEVEL',
  'ログフォルダを開く': 'OPEN LOGS',
  'ログZIPをエクスポート': 'EXPORT LOGS ZIP',
  'プリセットを選択': 'Select a preset',
  'CharaプリセットDelete': 'Delete Character Preset',
  '送信枚数': 'Image Count',
  'PNG生成': 'Generate PNG',
  'WebP変換': 'Convert to WebP',
  'ランダム': 'Random',
  '固定': 'Fixed',
  '連番': 'Increment',
  '補足メモ（日本語）': 'Additional Note (Japanese)',
  'ワークフロー内のLoraLoader ノードに順番に注入されます。空欄はSkipped。': 'Injected in order into LoraLoader nodes in the workflow. Empty fields are skipped.',
  'カードをクリックでスロットに割り当て（再クリックで解除）': 'Click a card to assign it to a slot (click again to unassign).',
  '未使用': 'Unused',
  '強度': 'Strength',
  'LLMを使用する': 'Use LLM',
  '送信POSITIVEプロンプト（生成＋ADDタグ）': 'Sent POSITIVE Prompt (Generated + ADD Tags)',
  '送信ポジティブプロンプト': 'Sent Positive Prompt',
  '送信POSITIVEプロンプト': 'Sent POSITIVE Prompt',
  '▸ 送信ポジティブプロンプト': '▸ Sent Positive Prompt',
  '▸ 送信POSITIVEプロンプト': '▸ Sent POSITIVE Prompt',
  'LLM生成POSITIVEプロンプト': 'LLM-generated POSITIVE Prompt',
  '送信NEGATIVEプロンプト': 'Sent NEGATIVE Prompt',
  'LLMを使うなら': 'If using LLM',
  'フォルダから選択': 'Select from folder',
  'フォルダ': 'Folder',
  '絶対パスで入力推奨': 'absolute path recommended',
  'IMAGEサイズ（ANIMA推奨）': 'Image Size (ANIMA recommended)',
  'シード値': 'Seed',
  'LoraLoader ノードに順番に注入されます。空欄はSkipped。': 'Injected into LoraLoader nodes in order. Empty fields are skipped.',
  'ワークフロー内の': 'In workflow,',
  'ノードに順番に注入されます。': 'injected into nodes in order.',
  '空欄はSkipped。': 'Empty fields are skipped.',
  'Period Tags (Positiveと共通)': 'Period Tags (shared with Positive)',
  'Extraタグ（Negative専用・右クリックでDelete）': 'Extra Tags (Negative only, right-click to delete)',
  '追記文（英語）→ Negativeプロンプト末尾に直接Add': 'Extra Text (English) -> append directly to Negative prompt end',
  '新規Add': 'Add New',
  'タグをAdd': 'Add tag',
  '日本語': 'Japanese',
  '入力推奨': 'recommended',
  '例：': 'e.g.:',
  '例:': 'e.g.:',
  '（フォールバック）': '(fallback)',
  '（優先）': '(preferred)',
  '（任意）': '(optional)',
  '日本語入力（例:': 'Input in English (e.g.:',
  '日本語入力（例：': 'Input in English (e.g.:',
  '英語タグのみ': 'English tags only',
  'Input in English可': 'Input in English',
  'Input in English可（例:': 'Input in English (e.g.:',
  'Input in English可（例：': 'Input in English (e.g.:',
  '日本語入力可': 'Input in English',
  '日本語入力可（例:': 'Input in English (e.g.:',
  '日本語入力可（例：': 'Input in English (e.g.:',
  '屋外': 'Outdoor',
  '屋内': 'Indoor',
  '特殊': 'Special',
  'ワークフローJSONパス（フォールバック）': 'Workflow JSON Path (fallback)',
  'WORKFLOWS/ フォルダから選択（優先）': 'Select from WORKFLOWS/ folder (preferred)',
  'anima_pipeline/workflows/ にJSONを置くと表示されます。選択時にNode IDを自動検出します（ControlNet等が挟まる場合は手動確認を）': 'Files appear when JSON is placed in `anima_pipeline/workflows/`. Node IDs are auto-detected on selection (verify manually if ControlNet or other nodes are inserted).',
  'にJSONを置くと表示されます。': 'appears when JSON is placed there.',
  '選択時にNode IDを自動検出します': 'Node IDs are auto-detected on selection',
  'ControlNet等が挟まる場合は手動確認を': 'verify manually if ControlNet or similar nodes are inserted',
  'workflows/ フォルダから選択（優先）': 'Select from workflows/ folder (preferred)',
  '　 workflows/ フォルダから選択（優先）': 'Select from workflows/ folder (preferred)',
  'WORKFLOWS/ フォルダから選択(PREFERRED)': 'Select from WORKFLOWS/ folder (PREFERRED)',
  'LLMを使うなら必須': 'Required if using LLM',
  '⑥ LLMプラットフォーム': '⑥ LLM Platform',
  '空欄 または トークン文字列': 'Blank or token string',
  'Seed（シード値）': 'Seed',
  'COMFYUI OUTPUT フォルダ（CONVERT TO WEBP用・絶対パスで入力推奨）': 'COMFYUI OUTPUT Folder (for CONVERT TO WEBP, absolute path recommended)',
  '例: 緊張感、幻想的な雰囲気': 'e.g.: tense, fantastical atmosphere',
  '例: お姉さんが弟分を甘やかしている雰囲気、ドキドキしている': 'e.g.: caring older-sister vibe, heart-pounding mood',
  'ワークフロー内の LoraLoader ノードに順番に注入されます。空欄はスキップ。': 'Injected in order into LoraLoader nodes in the workflow. Empty fields are skipped.',
  '空欄はスキップ。': 'Empty fields are skipped.',
  '▼ Negativeプロンプト調整': '▼ Negative Prompt Tuning',
  '新規Add (e.g.: bad_artist)': 'Add New (e.g.: bad_artist)',
  'タグをAdd (e.g.: bad anatomy)': 'Add tag (e.g.: bad anatomy)',
  '追記文（英語）→ Negativeプロンプト末尾に直接Add': 'Extra Text (English) -> append directly to Negative prompt end',
  '追記文（英語）→ プロンプト末尾に直接追加': 'Extra Text (English) -> append directly to prompt end',
  '追記文（英語）→ ネガティブプロンプト末尾に直接追加': 'Extra Text (English) -> append directly to Negative prompt end',
  'Negativeプロンプト調整': 'Negative Prompt Tuning',
  'ネガティブプロンプト調整': 'Negative Prompt Tuning',
  '▼ ネガティブプロンプト調整': '▼ Negative Prompt Tuning',
  'COMFYUI 送信POSITIVEプロンプト（生成＋ADDタグ）': 'COMFYUI Sent POSITIVE Prompt (Generated + ADD Tags)',
  'COMFYUI 送信NEGATIVEプロンプト': 'COMFYUI Sent NEGATIVE Prompt',
  'スタイル（@アーティスト名）': 'Style (@Artist Name)',
  'スタイル（@アーティスト名・ネガティブ専用）': 'Style (@Artist Name, Negative only)',
  '※英語表記': '*English only',
  '※英語表記で入力': '*Input in English',
  '新規追加（例: bad_artist）': 'Add New (e.g.: bad_artist)',
  'タグを追加（例: bad anatomy）': 'Add tag (e.g.: bad anatomy)',
  '⑥ Extraタグ（Chara・Sceneタグの後にAdd）': '⑥ Extra Tags (add after Chara/Scene tags)',
  '⑦ 追記文（英語）→ プロンプト末尾に直接Add': '⑦ Extra Text (English) -> append directly to prompt end',
  '⑦ 追記文（英語）→ Negativeプロンプト末尾に直接Add': '⑦ Extra Text (English) -> append directly to Negative prompt end',
  '⑦ 追記文（英語）→ ネガティブプロンプト末尾に直接追加': '⑦ Extra Text (English) -> append directly to Negative prompt end',
  'アクセサリー': 'Accessories',
  'エフェクト': 'Effects',
  '衣装': 'Outfit',
  'オッドアイ': 'Odd Eyes',
  '左目': 'Left Eye',
  '右目': 'Right Eye',
  '全体': 'All',
  '⑫ 脚': '⑫ Legs',
  'プリセット名を入力してください': 'Please enter preset name',
  '同名のプリセットが存在します。上書きしますか？': 'A preset with the same name already exists. Overwrite?',
  'プリセット管理（Scene/Camera/Quality/LoRA/Composite）': 'Preset Manager (Scene/Camera/Quality/LoRA/Composite)',
  '小': 'Small',
  '低': 'Short',
  '高': 'Tall',
  '大柄': 'Large',
  '痩': 'Thin',
  '太': 'Heavy',
  '開き': 'Open',
  '半目': 'Half-Closed',
  '閉じ': 'Closed',
  'LORA一覧取得': 'Fetch LORA List',
  '例: スペシャルウィーク': 'e.g.: Special Week',
  '例: ウマ娘、ブルアカ': 'e.g.: Umamusume, Blue Archive',
  '青肌': 'blue skin',
  '緑肌': 'green skin',
  '白 ドレス': 'white dress',
  'お団子': 'hair bun',
  'ドレッド': 'dreadlocks',
  'グラデーション': 'gradient',
  'メッシュ': 'mesh',
  '日本語入力可（例: 青肌、緑肌）': 'Input in English (e.g.: blue skin, green skin)',
  '日本語入力可（例: 白 ドレス、maid_apron）': 'Input in English (e.g.: white dress, maid_apron)',
  '日本語入力可（例: お団子、ドレッド）': 'Input in English (e.g.: hair bun, dreadlocks)',
  '日本語入力可（例: グラデーション、メッシュ）': 'Input in English (e.g.: gradient, mesh)',
  '持ち物': 'Held Item',
  '⑯ 持ち物': '⑯ Held Item',
  '俯瞰': "Bird's-Eye",
  '仰視': "Worm's-Eye",
  '品質タグ（PonyV7 aestheticベース）': 'Quality Tags (PonyV7 aesthetic base)',
  '▸ ComfyUI 送信ネガティブプロンプト': '▸ ComfyUI Sent NEGATIVE Prompt',
  '▸ 送信ネガティブプロンプト': '▸ Sent NEGATIVE Prompt',
  '▼ ⑥ Extraタグ（ネガティブ専用・右クリックで削除）': '▼ ⑥ Extra Tags (Negative only, right-click to delete)'
  ,
  '性別 *': 'Gender *',
  '年齢': 'Age',
  '口': 'Mouth',
  '⑤ 口': '⑤ Mouth',
  '耳': 'Ears',
  '廃墟': 'Ruins',
  'Period Tags (Positiveと共通)': 'Period Tags (shared with Positive)',
  '① Period Tags (Positiveと共通)': '① Period Tags (shared with Positive)',
  'Positiveと共通': 'shared with Positive',
  '（複数作品の場合はCharaごとに入力）': '(for multiple series, set per character)',
  '(複数作品の場合はCharaごとに入力)': '(for multiple series, set per character)',
  '(複数作品の場合はChara': '(for multiple series, Chara',
  '（複数作品の場合はChara': '(for multiple series, Chara',
  '複数作品の場合はCharaごとに入力': 'for multiple series, set per character',
  '（複数作品の場合はキャラごとに入力）': '(for multiple series, set per character)',
  '複数作品の場合はキャラごとに入力': 'for multiple series, set per character',
  '① Period Tags (Positiveと共通)': '① Period Tags (shared with Positive)',
  '▼ ① Period Tags (Positiveと共通)': '▼ ① Period Tags (shared with Positive)',
  '⑥ Extraタグ（Chara・Sceneタグの後にAdd）': '⑥ Extra Tags (add after Chara/Scene tags)',
  '▼ ⑥ Extraタグ（Chara・Sceneタグの後にAdd）': '▼ ⑥ Extra Tags (add after Chara/Scene tags)',
  '⑥ Extraタグ（Chara・Sceneタグの後にAdd)': '⑥ Extra Tags (add after Chara/Scene tags)',
  '▼ ⑥ Extraタグ（Chara・Sceneタグの後にAdd)': '▼ ⑥ Extra Tags (add after Chara/Scene tags)',
  '⑥ Extraタグ（キャラ・シーンタグの後に追加）': '⑥ Extra Tags (add after Chara/Scene tags)',
  '▼ ⑥ Extraタグ（キャラ・シーンタグの後に追加）': '▼ ⑥ Extra Tags (add after Chara/Scene tags)',
  'LLM生成POSITIVEプロンプト': 'LLM-generated POSITIVE Prompt',
  '▸ LLM生成POSITIVEプロンプト': '▸ LLM-generated POSITIVE Prompt',
  'COMFYUI 送信POSITIVEプロンプト（生成＋ADDタグ）': 'COMFYUI Sent POSITIVE Prompt (Generated + ADD Tags)',
  'ComfyUI 送信ポジティブプロンプト（生成＋追加タグ）': 'ComfyUI Sent Positive Prompt (Generated + Added Tags)',
  'COMFYUI 送信ポジティブプロンプト（生成＋追加タグ）': 'COMFYUI SENT POSITIVE PROMPT (GENERATED + ADDED TAGS)',
  '▸ ComfyUI 送信ポジティブプロンプト（生成＋追加タグ）': '▸ ComfyUI Sent Positive Prompt (Generated + Added Tags)',
  '▸ COMFYUI 送信ポジティブプロンプト（生成＋追加タグ）': '▸ COMFYUI SENT POSITIVE PROMPT (GENERATED + ADDED TAGS)',
  '送信Positiveプロンプト': 'Sent Positive Prompt',
  '▸ 送信Positiveプロンプト': '▸ Sent Positive Prompt',
  'LLM生成ポジティブプロンプト': 'LLM-generated Positive Prompt',
  '▸ LLM生成ポジティブプロンプト': '▸ LLM-generated Positive Prompt',
  'ポジティブ': 'Positive',
  '追加タグ': 'Added Tags',
  'COMFYUI 送信POSITIVEプロンプト（生成+ADDタグ）': 'COMFYUI Sent POSITIVE Prompt (Generated + ADD Tags)',
  '▸ COMFYUI 送信POSITIVEプロンプト（生成＋ADDタグ）': '▸ COMFYUI Sent POSITIVE Prompt (Generated + ADD Tags)',
  '▸ COMFYUI 送信POSITIVEプロンプト（生成+ADDタグ）': '▸ COMFYUI Sent POSITIVE Prompt (Generated + ADD Tags)',
  '⑰ 画面TOP/BOTTOM': '⑰ Frame Top / Bottom',
  '▼ ⑰ 画面TOP/BOTTOM': '▼ ⑰ Frame Top / Bottom',
  'なし': 'None',
  '🗑️ CharaプリセットDelete': '🗑️ Delete Character Preset',
  'IMAGEサイズ（ANIMA推奨）': 'Image Size (ANIMA Recommended)',
  'IMAGEサイズ': 'Image Size',
  'ANIMA推奨': 'ANIMA Recommended',
  'プリセットDelete': 'Preset Delete',
  'プリセット': 'Preset',
  'サイズ': 'Size',
  '推奨': 'Recommended',
  '黒': 'Black',
  '濃茶': 'Dark Brown',
  '茶': 'Brown',
  '薄茶': 'Light Brown',
  '赤': 'Red',
  '桃': 'Pink',
  '橙': 'Orange',
  '薄桃': 'Light Pink',
  '黄': 'Yellow',
  '緑': 'Green',
  '薄緑': 'Light Green',
  '水緑': 'Teal',
  '青': 'Blue',
  '水色': 'Light Blue',
  '紺': 'Navy',
  '灰': 'Gray',
  '銀': 'Silver',
  '紫': 'Purple',
  '薄紫': 'Light Purple',
  '白': 'White',
  '金': 'Gold',
  'マルチ': 'Multicolor',
  '🔄 LORA一覧取得': '🔄 Fetch LORA List',
  'ウマ娘': 'Umamusume',
  '場所を自由入力（例: 競馬場、魔法学校）': 'Enter any location (e.g.: racetrack, magic academy)',
  '画面上下': 'Frame Top / Bottom',
  '⑰ 画面上下': '⑰ Frame Top / Bottom',
  '貧乳': 'Flat',
  '中': 'Medium',
  '大': 'Large',
  '爆': 'Huge',
  '超爆': 'Gigantic',
  '短い': 'Short',
  '長い': 'Long',
  'ローアングル': 'Low Angle',
  'ハイアングル': 'High Angle',
  '魚眼': 'Fisheye',
  '獣尻尾': 'Animal',
  '猫尻尾': 'Cat',
  '犬尻尾': 'Dog',
  '狐尻尾': 'Fox',
  '龍尻尾': 'Dragon',
  '悪魔尻尾': 'Demon',
  '天使翼': 'Angel',
  '悪魔翼': 'Demon',
  '龍翼': 'Dragon',
  '羽翼': 'Feathered',
  '機械翼': 'Mechanical',
  'ショート': 'Short',
  'ミディアム': 'Medium',
  'ロング': 'Long',
  '超ロング': 'VLong',
  'ボブ': 'Bob',
  'ストレート': 'Straight',
  'ウェーブ': 'Wavy',
  'クセ毛': 'Curly',
  '縦ロール': 'Drill',
  'お団子': 'Bun',
  'ぱっつん': 'Blunt',
  '流し前髪': 'Swept',
  'サイド流し': 'Side Swept'
};

function humanizeValue(v){
  const s = String(v||'').trim();
  if(!s) return '';
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function hasAsciiWord(v){
  return /^[a-z0-9_ -]+$/i.test(String(v||''));
}

function buildAutoLabelMapFromOptions(root){
  const map = {};
  const conflicts = new Set();
  const walk = (node)=>{
    if(Array.isArray(node)){
      node.forEach(walk);
      return;
    }
    if(node && typeof node === 'object'){
      if(typeof node.label === 'string' && typeof node.v === 'string'){
        const label = node.label.trim();
        const v = node.v.trim();
        if(label && v && hasAsciiWord(v)){
          const hv = humanizeValue(v);
          if(map[label] && map[label] !== hv){
            conflicts.add(label);
          }else if(!map[label]){
            map[label] = hv;
          }
        }
      }
      Object.values(node).forEach(walk);
    }
  };
  walk(root);
  conflicts.forEach((k)=>{ delete map[k]; });
  return map;
}

const AUTO_I18N_MAP_EN = buildAutoLabelMapFromOptions(typeof __OPT__ === 'object' ? __OPT__ : {});
const I18N_MAP_EN = Object.assign({}, AUTO_I18N_MAP_EN, BASE_I18N_MAP_EN);

const I18N_MAP_JA = Object.fromEntries(
  Object.entries(I18N_MAP_EN).map(([ja, en]) => [en, ja])
);

function normalizeI18nKey(s){
  return String(s ?? '')
    .replace(/[（]/g, '(')
    .replace(/[）]/g, ')')
    .replace(/[＋]/g, '+')
    .replace(/\s+/g, ' ')
    .trim();
}

function buildNormalizedExactMap(dict){
  const out = {};
  for(const [k,v] of Object.entries(dict)){
    const nk = normalizeI18nKey(k);
    if(nk && !out[nk]) out[nk] = v;
  }
  return out;
}

function buildReplacers(dict){
  return Object.entries(dict)
    .filter(([from, to]) => from && to && from !== to)
    .sort((a, b) => b[0].length - a[0].length);
}
const I18N_REPLACERS_EN = buildReplacers(I18N_MAP_EN);
const I18N_REPLACERS_JA = buildReplacers(I18N_MAP_JA);
const I18N_EXACT_NORM_EN = buildNormalizedExactMap(I18N_MAP_EN);
const I18N_EXACT_NORM_JA = buildNormalizedExactMap(I18N_MAP_JA);

let __i18nObserver = null;
const __hasJaLike = /[ぁ-んァ-ン一-龠々〆ヵヶ]/;

function i18nReplace(text){
  let out = String(text ?? '');
  if(!out) return out;
  if(currentLang === 'ja'){
    const s = out.trim();
    let m = s.match(/^LLM:\s*Done$/i);
    if(m) return 'LLM: 完了';
    m = s.match(/^LLM:\s*Skipped$/i);
    if(m) return 'LLM: スキップ';
    m = s.match(/^LLM:\s*Generating prompt\.\.\.$/i);
    if(m) return 'LLM: プロンプト生成中...';
    m = s.match(/^ComfyUI:\s*(\d+)\s*queued$/i);
    if(m) return `ComfyUI: ${m[1]} 件キュー投入`;
    m = s.match(/^ComfyUI:\s*Queued\s*\((\d+)\)$/i);
    if(m) return `ComfyUI: キュー投入 (${m[1]})`;
    m = s.match(/^ComfyUI:\s*Generating\.\.\.\s*(\d+)%$/i);
    if(m) return `ComfyUI: 生成中... ${m[1]}%`;
    m = s.match(/^ComfyUI:\s*Generating\.\.\.$/i);
    if(m) return 'ComfyUI: 生成中...';
  }
  const dict = (currentLang === 'en') ? I18N_MAP_EN : I18N_MAP_JA;
  if(dict[out]) return dict[out];
  const normExact = (currentLang === 'en') ? I18N_EXACT_NORM_EN : I18N_EXACT_NORM_JA;
  const nk = normalizeI18nKey(out);
  if(normExact[nk]) return normExact[nk];
  if(currentLang === 'en' && !__hasJaLike.test(out) && !out.includes('（長押しで選択）')) return out;
  if(currentLang === 'ja' && __hasJaLike.test(out)) return out;
  const replacers = ((currentLang === 'en') ? I18N_REPLACERS_EN : I18N_REPLACERS_JA)
    .filter(([from]) => from.length >= 2);
  for(const [from, to] of replacers){
    out = out.split(from).join(to);
  }

  // Fallback for mixed JA/EN fragments when exact dictionary keys miss.
  if(currentLang === 'en'){
    out = out
      .split('Preset??').join('Preset Manager')
      .split('???????').join('Preset Manager')
      .split('??????????????').join('Preset List (Thumbnails)')
      .split('??Add').join('Add New')
      .split('????').join('Add New');
  }

  return out;
}

const _nativeAlert = window.alert.bind(window);
const _nativeConfirm = window.confirm.bind(window);
const _nativePrompt = window.prompt.bind(window);
window.alert = (msg)=>_nativeAlert(i18nReplace(msg));
window.confirm = (msg)=>_nativeConfirm(i18nReplace(msg));
window.prompt = (msg, def='')=>_nativePrompt(i18nReplace(msg), i18nReplace(def));

function applyI18nToElement(el){
  if(!el) return;
  if(el.nodeType === Node.TEXT_NODE){
    if(el.parentElement && !['SCRIPT','STYLE'].includes(el.parentElement.tagName)){
      const nextText = i18nReplace(el.nodeValue);
      if(nextText !== el.nodeValue) el.nodeValue = nextText;
    }
    return;
  }
  if(el.nodeType !== Node.ELEMENT_NODE) return;
  if(el.title){
    const nextTitle = i18nReplace(el.title);
    if(nextTitle !== el.title) el.title = nextTitle;
  }
  if(el.placeholder){
    const nextPh = i18nReplace(el.placeholder);
    if(nextPh !== el.placeholder) el.placeholder = nextPh;
  }
  if(el.tagName === 'INPUT' && (el.type === 'button' || el.type === 'submit') && el.value){
    const nextValue = i18nReplace(el.value);
    if(nextValue !== el.value) el.value = nextValue;
  }
  for(const c of el.childNodes) applyI18nToElement(c);
}

function refreshLangButtons(){
  const jaBtn = document.getElementById('langBtnJa');
  const enBtn = document.getElementById('langBtnEn');
  if(!jaBtn || !enBtn) return;
  jaBtn.classList.toggle('active', currentLang === 'ja');
  enBtn.classList.toggle('active', currentLang === 'en');
}

function setLang(lang){
  const nextLang = (lang === 'ja') ? 'ja' : 'en';
  if(nextLang === currentLang) return;
  currentLang = nextLang;
  localStorage.setItem(__LANG_STORAGE_KEY__, currentLang);
  document.documentElement.lang = currentLang === 'ja' ? 'ja' : 'en';
  refreshLangButtons();
  applyI18nToElement(document.body);
  setupI18nObserver();
}
window.setLang = setLang;

function teardownI18nObserver(){
  if(__i18nObserver){
    try{ __i18nObserver.disconnect(); }catch(_){}
    __i18nObserver = null;
  }
}

function setupI18nObserver(){
  teardownI18nObserver();
  __i18nObserver = new MutationObserver((muts)=>{
    for(const m of muts){
      if(m.type === 'characterData'){
        applyI18nToElement(m.target);
      }else if(m.type === 'childList'){
        m.addedNodes.forEach(n => applyI18nToElement(n));
      }
    }
  });
  __i18nObserver.observe(document.body, {
    subtree: true,
    childList: true,
    characterData: true
  });
}

function scheduleI18nIfNeeded(){
  const run = ()=>{
    applyI18nToElement(document.body);
    setupI18nObserver();
  };
  if('requestIdleCallback' in window){
    window.requestIdleCallback(run, {timeout: 1200});
  }else{
    setTimeout(run, 0);
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  document.documentElement.lang = currentLang === 'ja' ? 'ja' : 'en';
  refreshLangButtons();
  // Startup fast-path: Japanese mode skips full-DOM i18n walk.
  scheduleI18nIfNeeded();
});
