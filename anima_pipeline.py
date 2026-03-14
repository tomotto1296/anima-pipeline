#!/usr/bin/env python3
"""
Anima Pipeline
ブラウザUI → LLM → ComfyUI 自動連携スクリプト
"""

import requests
import json
import uuid
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

UI_PORT = 7860
_base_dir     = os.path.dirname(os.path.abspath(__file__))
_settings_dir = os.path.join(_base_dir, 'settings')
os.makedirs(_settings_dir, exist_ok=True)

def _sf(name): return os.path.join(_settings_dir, name)

CONFIG_FILE        = _sf('pipeline_config.json')
EXTRA_TAGS_FILE    = _sf('extra_tags.json')
STYLE_TAGS_FILE    = _sf('style_tags.json')
NEG_EXTRA_TAGS_FILE  = _sf('extra_tags_negative.json')
NEG_STYLE_TAGS_FILE  = _sf('style_tags_negative.json')
UI_OPTIONS_FILE      = _sf('ui_options.json')
CHARA_PRESETS_DIR    = os.path.join(_base_dir, 'chara')

def load_neg_extra_tags():
    if os.path.exists(NEG_EXTRA_TAGS_FILE):
        try:
            with open(NEG_EXTRA_TAGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return ["bad anatomy","extra fingers","missing fingers","multiple limbs",
            "poorly drawn hands","low quality","blurry","watermark","signature",
            "duplicate","cloned face","jpeg artifacts","sepia"]

def save_neg_extra_tags(tags: list):
    with open(NEG_EXTRA_TAGS_FILE, "w", encoding="utf-8") as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)

def load_neg_style_tags():
    if os.path.exists(NEG_STYLE_TAGS_FILE):
        try:
            with open(NEG_STYLE_TAGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return []

def save_neg_style_tags(tags: list):
    with open(NEG_STYLE_TAGS_FILE, "w", encoding="utf-8") as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)

def load_ui_options() -> dict:
    if os.path.exists(UI_OPTIONS_FILE):
        try:
            with open(UI_OPTIONS_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'[ui_options] 読み込みエラー: {e}')
    return {}

def load_style_tags():
    if os.path.exists(STYLE_TAGS_FILE):
        with open(STYLE_TAGS_FILE, encoding='utf-8') as f:
            return json.load(f).get('tags', [])
    return []

def save_style_tags(tags):
    with open(STYLE_TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'tags': tags}, f, ensure_ascii=False, indent=2)

def load_extra_tags():
    if os.path.exists(EXTRA_TAGS_FILE):
        try:
            with open(EXTRA_TAGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("tags", [])
        except: pass
    return []

def save_extra_tags(tags: list):
    with open(EXTRA_TAGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"tags": tags}, f, ensure_ascii=False, indent=2)

DEFAULT_CONFIG = {
    "llm_platform": "",
    "llm_url": "http://localhost:1234",
    "llm_token": "",
    "tool_danbooru_rag": True,
    "tool_danbooru_api": True,
    "tool_duckduckgo": True,
    "llm_model": "qwen/qwen3.5-9b-uncensored-hauhaucs-aggressive",
    "comfyui_url": "http://127.0.0.1:8188",
    "workflow_json_path": "image_anima_preview.json",
    "positive_node_id": "11",
    "negative_node_id": "12",
    "comfyui_output_dir": "",  # WebP変換用・絶対パスで入力推奨（空の場合は自動推定するが失敗することがある）
    "clip_node_id": "45",
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            cfg = DEFAULT_CONFIG.copy()
            saved = json.load(open(CONFIG_FILE, "r", encoding="utf-8"))
            # 旧キー（lm_studio_*）からの移行フォールバック
            for old_key, new_key in [("lm_studio_url","llm_url"),("lm_studio_token","llm_token"),("lm_studio_model","llm_model")]:
                if old_key in saved and new_key not in saved:
                    saved[new_key] = saved.pop(old_key)
            cfg.update(saved)
            return cfg
        except Exception as e:
            print(f"[設定] 読み込みエラー: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    try:
        json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[設定] 保存: {CONFIG_FILE}")
    except Exception as e:
        print(f"[設定] 保存エラー: {e}")


SYSTEM_PROMPT_FILE = _sf('llm_system_prompt.txt')
PRESET_GEN_PROMPT_FILE = _sf('preset_gen_prompt.txt')

# 旧パスからsettingsフォルダへ自動移行
for _fn in ['pipeline_config.json','extra_tags.json','extra_tags_negative.json','style_tags.json','style_tags_negative.json',
            'ui_options.json','anima_session_last.json',
            'lmstudio_system_prompt.txt','llm_system_prompt.txt']:
    _old = os.path.join(_base_dir, _fn)
    _new = _sf('llm_system_prompt.txt' if 'system_prompt' in _fn else _fn)
    if os.path.exists(_old) and not os.path.exists(_new):
        os.rename(_old, _new)
        print(f'[settings] 移行: {_fn} → settings/')
def load_preset_gen_prompt():
    try:
        with open(PRESET_GEN_PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return (
            'Generate a character preset JSON for anime image generation.\n'
            'Character: {chara_name}\nSeries: {chara_series}\nDanbooru Wiki: {wiki_text}\n\n'
            'Output ONLY a valid JSON object: {"gender":"female or male or other","age":"adult or child or unset",'
            '"hairstyle":"hair style tags e.g. long_hair,ponytail","haircolor":"single hair color tag e.g. purple_hair",'
            '"eyes":"single eye color tag e.g. red_eyes","skin":"skin tag or empty","bust":"bust tag or empty",'
            '"outfit":"default outfit tags comma separated"}\n'
            'IMPORTANT: Be accurate about hair/eye colors.\nRules: lowercase underscore Danbooru tags only. Output ONLY the JSON.'
        )

def load_system_prompt():
    try:
        with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f'[WARNING] {SYSTEM_PROMPT_FILE} not found. Using empty system prompt.')
        return ''
SYSTEM_PROMPT = load_system_prompt()


def call_llm(user_input: str, cfg: dict) -> str:
    # OpenAI互換エンドポイント
    _raw = cfg['llm_url'].rstrip('/')
    platform = cfg.get('llm_platform', '')
    if platform == 'gemini':
        # GeminiはURLをそのまま使う（/v1beta/openai/chat/completions）
        url = f"{_raw}/chat/completions"
    else:
        _base = _raw.removesuffix('/v1')
        url = f"{_base}/v1/chat/completions"
    print(f"[LLM] 送信先URL: {url}")
    # システムプロンプトを毎回再読み込み（txt編集が即反映される）
    system_prompt = load_system_prompt()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_input})

    payload = {
        "model": cfg["llm_model"],
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1024,
        "stream": False,
    }

    # MCPツール統合（LM Studio専用）
    if platform == "lmstudio" or platform == "":
        integrations = [i for i in [
            {"type": "plugin", "id": "mcp/danbooru-rag"} if cfg.get("tool_danbooru_rag", True) else None,
            {"type": "plugin", "id": "mcp/danbooru-api"} if cfg.get("tool_danbooru_api", True) else None,
            {"type": "plugin", "id": "danielsig/duckduckgo"} if cfg.get("tool_duckduckgo", True) else None,
        ] if i]
        if integrations:
            payload["integrations"] = integrations

    headers = {"Content-Type": "application/json"}
    token = cfg.get("llm_token", "").strip()
    print(f"[LLM] プラットフォーム: {platform or 'なし'}")
    print(f"[LLM] URL: {cfg.get('llm_url','')}")
    print(f"[LLM] token={'設定済み('+str(len(token))+'文字)' if token else '未設定・空'}")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    session = requests.Session()
    Handler.lm_session = session
    try:
        resp = session.post(url, json=payload, headers=headers, timeout=300)
    finally:
        Handler.lm_session = None
    print(f"[LLM] status={resp.status_code}")
    resp.raise_for_status()
    data = resp.json()
    # OpenAI互換レスポンス
    if "choices" in data and data["choices"]:
        msg = data["choices"][0].get("message", {})
        content = msg.get("content")
        if content:
            return content
        # contentがない場合（安全フィルターによるブロック等）
        finish_reason = data["choices"][0].get("finish_reason", "")
        print(f"[LLM] contentなし finish_reason={finish_reason!r} → フィルターブロックの可能性")
        raise ValueError(f"LLMがコンテンツを返しませんでした (finish_reason={finish_reason!r}). システムプロンプトを確認してください。")
    # 旧形式フォールバック
    if "output" in data:
        blocks = [i.get("content","") for i in data["output"] if i.get("type")=="message" and i.get("content","").strip()]
        return blocks[-1].strip() if blocks else ""
    return ""


def convert_png_to_webp(png_path: str, quality: int = 90):
    """PNGファイルをWebPに変換してPNGを削除"""
    try:
        from PIL import Image
        webp_path = png_path.replace(".png", ".webp")
        img = Image.open(png_path)
        img.save(webp_path, "WEBP", quality=quality)
        os.remove(png_path)
        print(f"[WebP] 変換完了: {webp_path}")
    except Exception as e:
        print(f"[WebP] 変換エラー: {e}")


def watch_and_convert(comfyui_url: str, output_dir: str, date_folder: str, prompt_id: str, client_id: str = None, quality: int = 90):
    """ComfyUI WebSocketでジョブ完了を検知し、生成されたPNGをWebPに変換"""
    import threading, json as _json, urllib.request, urllib.parse
    target_dir = os.path.join(output_dir, date_folder)
    print(f"[WebP] 監視開始: prompt_id={prompt_id}")

    # client_idを_watch呼び出し前に確定させてクロージャ問題を回避
    import uuid as _uuid_outer
    _client_id = client_id if client_id is not None else str(_uuid_outer.uuid4())

    def _watch():
        import time, socket, struct, hashlib, base64, ssl as _ssl
        ws_url = comfyui_url.replace("http://", "ws://").replace("https://", "wss://") + f"/ws?clientId={_client_id}"
        parsed = urllib.parse.urlparse(ws_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        path = (parsed.path or "/ws") + ("?" + parsed.query if parsed.query else "")

        try:
            sock = socket.create_connection((host, port), timeout=300)
            if parsed.scheme == "wss":
                sock = _ssl.wrap_socket(sock, server_hostname=host)

            # WebSocketハンドシェイク
            key = base64.b64encode(os.urandom(16)).decode()
            CRLF = "\r\n"
            handshake = (
                f"GET {path} HTTP/1.1{CRLF}"
                f"Host: {host}:{port}{CRLF}"
                f"Upgrade: websocket{CRLF}"
                f"Connection: Upgrade{CRLF}"
                f"Sec-WebSocket-Key: {key}{CRLF}"
                f"Sec-WebSocket-Version: 13{CRLF}{CRLF}"
            )
            sock.sendall(handshake.encode())
            # ハンドシェイク応答を読む
            resp = b""
            while b"\r\n\r\n" not in resp:
                resp += sock.recv(1024)
            print(f"[WebP] WebSocket接続OK")

            deadline = time.time() + 300
            buf = b""
            while time.time() < deadline:
                try:
                    sock.settimeout(5)
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    # WebSocketフレームのパース（テキストフレームのみ）
                    while len(buf) >= 2:
                        fin_op = buf[0]
                        opcode = fin_op & 0x0f
                        masked = (buf[1] & 0x80) != 0
                        plen = buf[1] & 0x7f
                        offset = 2
                        if plen == 126:
                            if len(buf) < 4: break
                            plen = struct.unpack(">H", buf[2:4])[0]; offset = 4
                        elif plen == 127:
                            if len(buf) < 10: break
                            plen = struct.unpack(">Q", buf[2:10])[0]; offset = 10
                        if masked: offset += 4
                        if len(buf) < offset + plen: break
                        payload = buf[offset:offset+plen]
                        buf = buf[offset+plen:]
                        if opcode == 1:  # テキストフレーム
                            try:
                                data = _json.loads(payload.decode("utf-8"))
                                print(f"[WebP] WS受信: type={data.get('type')} node={data.get('data',{}).get('node','?')} pid={data.get('data',{}).get('prompt_id','?')[:8] if data.get('data',{}).get('prompt_id') else '?'}")
                                if (data.get("type") == "executing" and
                                    data.get("data", {}).get("prompt_id") == prompt_id and
                                    data.get("data", {}).get("node") is None):
                                    print(f"[WebP] 生成完了検知: {prompt_id}")
                                    sock.close()
                                    time.sleep(1)
                                    hist_url = comfyui_url.rstrip("/") + f"/history/{prompt_id}"
                                    with urllib.request.urlopen(hist_url) as r:
                                        hist = _json.loads(r.read())
                                    outputs = hist.get(prompt_id, {}).get("outputs", {})
                                    for node_out in outputs.values():
                                        for img in node_out.get("images", []):
                                            fname = img.get("filename","")
                                            subfolder = img.get("subfolder","")
                                            if fname.endswith(".png"):
                                                fpath = os.path.join(output_dir, subfolder, fname) if subfolder else os.path.join(target_dir, fname)
                                                if os.path.exists(fpath):
                                                    print(f"[WebP] 変換対象: {fpath}")
                                                    convert_png_to_webp(fpath, quality)
                                                else:
                                                    print(f"[WebP] ファイル未検出: {fpath}")
                                    return
                            except Exception:
                                pass
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[WebP] 受信エラー: {e}")
                    break
            print("[WebP] タイムアウト")
            sock.close()
        except Exception as e:
            print(f"[WebP] 接続エラー: {e}")

    t = threading.Thread(target=_watch, daemon=True)
    t.start()


def extract_positive_prompt(text: str) -> str:
    for line in text.splitlines():
        if line.strip().startswith("Positive Prompt:"):
            return line.strip()[len("Positive Prompt:"):].strip()
    return text.strip()


# KSamplerなどでseedの次に"randomize"/"fixed"などのコントロール値が
# widgets_valuesに含まれる場合があるが、API送信には不要なためスキップする
SEED_CONTROL_VALUES = {"randomize", "fixed", "increment", "decrement"}

def workflow_to_api(workflow_data: dict) -> dict:
    """ComfyUI保存形式 → API送信形式に変換"""
    links_map = {link[0]: link for link in workflow_data.get("links", [])}
    api_prompt = {}
    for n in workflow_data.get("nodes", []):
        node_id = str(n["id"])
        inputs = {}
        widgets_values = list(n.get("widgets_values", []))
        # seed直後のコントロール値("randomize"等)を除去
        cleaned_values = []
        i = 0
        while i < len(widgets_values):
            val = widgets_values[i]
            cleaned_values.append(val)
            # 次の値がseedコントロール値なら除去
            if i + 1 < len(widgets_values) and widgets_values[i + 1] in SEED_CONTROL_VALUES:
                i += 2  # コントロール値をスキップ
            else:
                i += 1
        widget_idx = 0
        for inp in n.get("inputs", []):
            link_id = inp.get("link")
            if link_id is not None:
                link = links_map.get(link_id)
                if link:
                    inputs[inp["name"]] = [str(link[1]), link[2]]
            elif "widget" in inp:
                if widget_idx < len(cleaned_values):
                    inputs[inp["name"]] = cleaned_values[widget_idx]
                    widget_idx += 1
        # 出力のないノード（MarkdownNoteなど表示専用）は除外
        outputs = n.get("outputs", [])
        has_output = any(o.get("links") for o in outputs)
        has_input_links = any(i.get("link") is not None for i in n.get("inputs", []))
        is_display_only = not outputs and not has_input_links
        if is_display_only:
            continue
        api_prompt[node_id] = {"class_type": n.get("type", ""), "inputs": inputs}
    return api_prompt


def send_to_comfyui(positive_prompt: str, cfg: dict, width: int = 1024, height: int = 1024, fmt: str = 'png', client_id: str = None, negative_prompt: str = '') -> str:
    workflow_path = cfg.get("workflow_json_path", "").strip()
    if workflow_path and not os.path.isabs(workflow_path):
        workflow_path = os.path.join(_base_dir, workflow_path)
    if not workflow_path or not os.path.exists(workflow_path):
        raise FileNotFoundError(f"ワークフローJSONが見つかりません: {workflow_path}")

    workflow_data = json.load(open(workflow_path, "r", encoding="utf-8"))
    api_prompt = workflow_to_api(workflow_data)

    # Positive PromptノードのテキストをLM Studio出力で書き換え
    pos_id = cfg.get("positive_node_id", "11")
    if pos_id not in api_prompt:
        raise ValueError(f"Positiveノード {pos_id} がワークフローに存在しません")
    api_prompt[pos_id]["inputs"]["text"] = positive_prompt

    # Negative Promptノードの書き換え
    neg_id = cfg.get("negative_node_id", "").strip()
    if neg_id and neg_id in api_prompt and negative_prompt:
        api_prompt[neg_id]["inputs"]["text"] = negative_prompt
        print(f"[ComfyUI] ネガティブプロンプト設定 (node {neg_id})")

    # EmptyLatentImageノードのwidth/heightを書き換え
    for nid, node in api_prompt.items():
        if node.get("class_type") == "EmptyLatentImage":
            node["inputs"]["width"] = width
            node["inputs"]["height"] = height
            print(f"[ComfyUI] 画像サイズ設定: {width}x{height} (node {nid})")
            break

    # SaveImageノードのfilename_prefixに日付フォルダを設定
    import datetime, random
    date_folder = datetime.date.today().strftime("%Y-%m-%d")
    for nid, node in api_prompt.items():
        if node.get("class_type") == "SaveImage":
            ts = datetime.datetime.now().strftime("%H%M%S%f")[:10]
            node["inputs"]["filename_prefix"] = f"{date_folder}/{ts}_"
            print(f"[ComfyUI] 保存先: output/{date_folder}/{ts}_ (node {nid})")

    # KSamplerのseedをランダムに設定（複数枚生成時に同一画像にならないよう）
    for nid, node in api_prompt.items():
        if node.get("class_type") == "KSampler":
            node["inputs"]["seed"] = random.randint(0, 2**32 - 1)
            print(f"[ComfyUI] seed設定: {node['inputs']['seed']} (node {nid})")

    if client_id is None:
        client_id = str(uuid.uuid4())
    payload = {"prompt": api_prompt, "client_id": client_id}
    resp = requests.post(f"{cfg['comfyui_url']}/prompt", json=payload, timeout=30)
    print(f"[ComfyUI] status={resp.status_code} body={resp.text[:200]}")
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ComfyUI error: {data['error']}")
    return data.get("prompt_id", "unknown")


HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>キャラクター生成（プロンプト+画像）</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@300;400;700&family=DM+Mono:ital@0;1&display=swap');
  :root {
    --ink:#2d2640;
    --paper:#faf8ff;
    --accent:#b388d8;
    --accent2:#f0a8c8;
    --muted:#9b90b8;
    --border:#ddd6f0;
    --success:#6db88a;
    --single:#3a8c5c;
    --multi:#7c4dbf;
    --card:#ffffff;
    --highlight:#f3eeff;
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{
    background:var(--paper);color:var(--ink);
    font-family:'Zen Kaku Gothic New',sans-serif;
    min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem;
    background-image:
      radial-gradient(ellipse at 15% 20%, rgba(179,136,216,0.12) 0%, transparent 50%),
      radial-gradient(ellipse at 85% 75%, rgba(240,168,200,0.10) 0%, transparent 50%),
      repeating-linear-gradient(0deg,transparent,transparent 31px,rgba(221,214,240,0.5) 31px,rgba(221,214,240,0.5) 32px);
  }
  .container{width:100%;max-width:680px;background:rgba(255,255,255,0.85);
    border:1px solid var(--border);
    box-shadow:0 4px 24px rgba(124,77,191,0.08), 0 1px 3px rgba(124,77,191,0.12);
    border-radius:12px;padding:2.5rem;backdrop-filter:blur(8px);}
  h1{font-size:0.85rem;font-weight:300;letter-spacing:0.35em;text-transform:uppercase;color:var(--muted);margin-bottom:0.3rem;}
  h2{font-size:1.7rem;font-weight:700;margin-bottom:1.8rem;
    background:linear-gradient(120deg, var(--ink) 0%, #7c4dbf 100%);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
    border-bottom:1.5px solid var(--border);padding-bottom:0.8rem;}
  label{display:block;font-size:0.72rem;letter-spacing:0.18em;text-transform:uppercase;color:var(--muted);margin-bottom:0.4rem;}
  input[type=text],input[type=password],textarea{width:100%;background:var(--card);border:1px solid var(--border);
    border-radius:6px;padding:0.7rem 1rem;font-family:'Zen Kaku Gothic New',sans-serif;
    font-size:0.93rem;color:var(--ink);outline:none;transition:border-color 0.2s,box-shadow 0.2s;}
  input[type=text]:focus,input[type=password]:focus,textarea:focus{
    border-color:var(--accent);box-shadow:0 0 0 3px rgba(179,136,216,0.18);}
  textarea{min-height:90px;resize:vertical;font-size:0.95rem;}
  /* 日本語OK入力欄 */
  .inp-ja{background:#f0f7ff !important;border-color:#7ab3e0 !important;}
  .inp-ja:focus{border-color:#3a82c4 !important;box-shadow:0 0 0 3px rgba(58,130,196,0.15) !important;}
  .inp-ja::placeholder{color:#8ab4d8;}
  /* 英語専用入力欄 */
  .inp-en{background:#f5fff5 !important;border-color:#7ec47e !important;}
  .inp-en:focus{border-color:#3a9a3a !important;box-shadow:0 0 0 3px rgba(58,154,58,0.13) !important;}
  .inp-en::placeholder{color:#8aba8a;}
  .stoggle{margin-bottom:1.6rem;font-family:'DM Mono',monospace;font-size:0.75rem;letter-spacing:0.18em;
    text-transform:uppercase;color:var(--muted);cursor:pointer;user-select:none;
    background:linear-gradient(90deg,rgba(179,136,216,0.13),rgba(240,168,200,0.08));
    padding:0.4rem 0.8rem;border-left:3px solid var(--accent);border-radius:0 6px 6px 0;
    display:flex;align-items:center;gap:0.5rem;}
  .stoggle:hover{background:linear-gradient(90deg,rgba(179,136,216,0.22),rgba(240,168,200,0.14));color:var(--ink);}
  .sbody{display:none;margin-bottom:1.6rem;border:1px solid var(--border);border-radius:8px;padding:1.2rem;background:rgba(255,255,255,0.9);}
  .sbody.open{display:block;}
  .field{display:flex;flex-direction:column;gap:0.4rem;margin-bottom:0.9rem;}
  .field:last-of-type{margin-bottom:0;}
  .field input{font-family:'DM Mono',monospace;font-size:0.83rem;}
  .field-row{display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;}
  .save-btn{margin-top:1rem;width:100%;padding:0.6rem;background:white;color:var(--muted);border:1px solid var(--border);
    border-radius:6px;font-family:'DM Mono',monospace;font-size:0.78rem;letter-spacing:0.15em;
    text-transform:uppercase;cursor:pointer;transition:all 0.2s;}
  .save-btn:hover{background:var(--highlight);color:var(--multi);border-color:var(--accent);}
  .save-notice{font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--success);margin-top:0.5rem;display:none;text-align:center;}
  button{margin-top:1.2rem;width:100%;padding:0.9rem;
    background:linear-gradient(135deg,#5a3fa0 0%,#8b5dbf 60%,#c47ab0 100%);
    color:white;border:none;border-radius:8px;
    font-family:'Zen Kaku Gothic New',sans-serif;font-size:0.87rem;letter-spacing:0.2em;
    text-transform:uppercase;cursor:pointer;transition:all 0.2s;
    box-shadow:0 3px 12px rgba(124,77,191,0.3);}
  button:hover{background:linear-gradient(135deg,#4a2f90 0%,#7a4daf 60%,#b46aa0 100%);
    box-shadow:0 5px 18px rgba(124,77,191,0.4);transform:translateY(-1px);}
  button:active{transform:translateY(1px);box-shadow:0 2px 8px rgba(124,77,191,0.25);}
  button:disabled{background:linear-gradient(135deg,#bbb,#ccc);box-shadow:none;cursor:not-allowed;transform:none;}
  .status-box{margin-top:1.5rem;border:1px solid var(--border);background:rgba(255,255,255,0.9);padding:1rem;display:none;border-radius:8px;box-shadow:0 2px 12px rgba(124,77,191,0.07);}
  .status-box.show{display:block;}
  .status-label{font-size:0.7rem;letter-spacing:0.2em;text-transform:uppercase;color:var(--muted);margin-bottom:0.5rem;}
  .step{display:flex;align-items:center;gap:0.6rem;margin:0.3rem 0;font-size:0.82rem;font-family:'DM Mono',monospace;color:var(--muted);}
  .step.active{color:var(--ink);}
  .step.done{color:var(--success);}
  .step.error{color:var(--accent);}
  .dot{width:6px;height:6px;border-radius:50%;background:currentColor;flex-shrink:0;}
  .spinner{width:12px;height:12px;border:1.5px solid currentColor;border-top-color:transparent;border-radius:50%;animation:spin 0.7s linear infinite;flex-shrink:0;}
  @keyframes spin{to{transform:rotate(360deg);}}
  .prompt-output{margin-top:0.5rem;background:#f5f3ff;border-left:3px solid var(--accent);border-radius:0 6px 6px 0;padding:0.8rem 1rem;white-space:pre-wrap;
  font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);display:none;}
  .prompt-section-label{font-family:'DM Mono',monospace;font-size:0.68rem;letter-spacing:0.12em;
    text-transform:uppercase;color:var(--muted);margin-top:1rem;margin-bottom:0.25rem;
    display:flex;align-items:center;justify-content:space-between;}
  .lm-check-wrap{display:flex;align-items:center;gap:0.25rem;margin-left:0.4rem;flex-shrink:0;}
  .lm-check-wrap input[type=checkbox]{width:11px;height:11px;accent-color:var(--multi);cursor:pointer;margin:0;}
  .lm-check-wrap label{font-family:'DM Mono',monospace;font-size:0.6rem;color:var(--muted);cursor:pointer;white-space:nowrap;user-select:none;}
  .opt-label-wrap{display:flex;align-items:center;justify-content:flex-end;gap:0;}
  .odd-eye-btn .odd-short{display:none;}
  .odd-eye-btn .odd-long{display:inline;}
  .odd-eye-btn{overflow:hidden;white-space:nowrap;min-width:0;}
  @container odd-eye-btn-ctx (max-width:1px){} /* fallback */
  /* ボタン行が折り返しそうなとき＝ボタン自身が狭くなったときにshortへ */
  .odd-eye-btn.compact .odd-long{display:none;}
  .odd-eye-btn.compact .odd-short{display:inline;}
  .copy-btn{font-family:'DM Mono',monospace;font-size:0.68rem;border:1px solid var(--border);
    background:white;color:var(--muted);padding:0.15rem 0.5rem;border-radius:4px;cursor:pointer;
    letter-spacing:0;text-transform:none;transition:all 0.15s;flex-shrink:0;}
  .copy-btn:hover{background:var(--highlight);color:var(--multi);border-color:var(--accent);}
  .copy-btn.copied{background:var(--highlight);color:var(--single);border-color:var(--single);}
  .prompt-section-label:first-child{margin-top:0.5rem;}
  .prompt-final{margin-top:0.5rem;background:#fef5ff;border-left:3px solid var(--accent2);border-radius:0 6px 6px 0;padding:0.8rem 1rem;
    white-space:pre-wrap;
    font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);line-height:1.6;display:none;}
  .prompt-output.show{display:block;}
  select{width:100%;background:white;border:1px solid var(--border);padding:0.7rem 1rem;
    font-family:'DM Mono',monospace;font-size:0.83rem;color:var(--ink);outline:none;
    appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%238a7e6e'/%3E%3C/svg%3E");
    background-repeat:no-repeat;background-position:right 1rem center;cursor:pointer;}
  select:focus{border-color:var(--ink);}
  .size-row{display:grid;grid-template-columns:1fr 80px auto 80px;gap:0.5rem;align-items:center;margin-top:0.2rem;}
  .size-row select{min-width:0;}
  .size-row input[type=number]{width:80px;background:white;border:1px solid var(--border);
    padding:0.7rem 0.4rem;font-family:'DM Mono',monospace;font-size:0.83rem;color:var(--ink);
    outline:none;text-align:center;transition:border-color 0.2s;}
  .size-row input[type=number]:focus{border-color:var(--ink);}
  .size-sep{font-family:'DM Mono',monospace;font-size:0.85rem;color:var(--muted);text-align:center;}
  .fmt-row{display:flex;gap:0.5rem;margin-top:0.2rem;}
  .fmt-btn{flex:1;border:1px solid var(--border);background:white;padding:0.5rem;cursor:pointer;
    border-radius:5px;text-align:center;font-family:'DM Mono',monospace;font-size:0.8rem;color:var(--ink);transition:all 0.15s;}
  .fmt-btn:hover{border-color:#3a8c5c;}
  .fmt-btn.active{background:#3a8c5c;color:white;border-color:#3a8c5c;}
  .struct-fields{display:flex;flex-direction:column;gap:0.5rem;margin-bottom:1rem;}
  .struct-row{display:grid;grid-template-columns:9rem 1fr;gap:0.5rem;align-items:center;}
  .struct-label{font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);text-align:right;
    padding-right:0.5rem;white-space:nowrap;}
  .struct-row input{background:white;border:1px solid var(--border);padding:0.55rem 0.8rem;
    font-family:'DM Mono',monospace;font-size:0.82rem;color:var(--ink);outline:none;width:100%;
    box-sizing:border-box;transition:border-color 0.2s;}
  .struct-row input:focus{border-color:var(--ink);}
  .struct-row.required input{background:#f8f4ff;border-color:var(--accent);}
  .struct-row.required input:focus{border-color:var(--multi);}
  .struct-row.required .struct-label::after{content:" *";color:var(--accent);font-size:0.7rem;}
  .btn-cancel{width:100%;padding:0.9rem;border:1.5px solid #e0789a;background:#fff5f8;
    color:#c0507a;font-family:'Zen Kaku Gothic New',sans-serif;font-size:0.87rem;letter-spacing:0.08em;
    cursor:pointer;transition:all 0.2s;display:none;margin-top:0.5rem;border-radius:8px;}
  .btn-cancel:hover{background:#c0507a;color:white;}
  .btn-regen{width:100%;padding:0.9rem;border:1.5px solid var(--accent);
    background:var(--highlight);color:var(--multi);
    font-family:'Zen Kaku Gothic New',sans-serif;font-size:0.87rem;letter-spacing:0.12em;
    cursor:pointer;transition:all 0.2s;display:none;margin-top:0.5rem;border-radius:8px;
    box-shadow:0 2px 8px rgba(124,77,191,0.12);}
  .btn-regen:hover{background:var(--multi);color:white;box-shadow:0 4px 14px rgba(124,77,191,0.3);}
  .btn-regen.show{display:block;}
  .btn-cancel.show{display:block;}
  /* キャラブロック */
  .chara-block{border:1px solid var(--border);border-left:3px solid var(--accent);padding:0.8rem;margin-bottom:0.8rem;background:rgba(255,255,255,0.92);border-radius:8px;box-shadow:0 2px 8px rgba(124,77,191,0.06);}
  .chara-header{display:flex;flex-direction:column;gap:0.4rem;
    background:linear-gradient(90deg,rgba(179,136,216,0.08),transparent);padding:0.5rem 0.6rem;border-radius:5px;}
  .chara-header-row1{display:grid;grid-template-columns:auto 1fr 1fr auto;gap:0.5rem;align-items:end;}
  .chara-header-row2{display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;align-items:start;}
  .chara-attr-group{display:flex;flex-direction:column;gap:0.15rem;}
  .chara-attr-label{font-family:'DM Mono',monospace;font-size:0.65rem;color:var(--muted);letter-spacing:0.05em;}
  .chara-attr-btns{display:flex;gap:0.25rem;}
  .chara-attr-btns .gender-btn,
  .chara-attr-btns .age-btn{flex:1;text-align:center;}
  .chara-num{font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--muted);white-space:nowrap;padding-top:0.2rem;}
  .gender-row{display:flex;gap:0.3rem;margin-top:0.2rem;}
  .gender-btn{flex:1;border:1px solid var(--border);background:white;padding:0.4rem 0.3rem;
    border-radius:5px;font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--ink);cursor:pointer;
    text-align:center;transition:all 0.15s;user-select:none;}
  .gender-btn:hover{border-color:#2d7a4f;}
  .gender-btn.active{background:#2d7a4f;color:white;border-color:#2d7a4f;}
  .chara-expand{background:none;border:1px solid var(--border);padding:0.3rem 0.6rem;
    font-family:'DM Mono',monospace;font-size:0.7rem;color:var(--muted);cursor:pointer;white-space:nowrap;}
  .chara-expand:hover{border-color:var(--ink);color:var(--ink);}
  .chara-optional{margin-top:0.5rem;border-top:1px solid var(--border);padding-top:0.5rem;}
  .opt-row{display:grid;grid-template-columns:7rem 1fr;gap:0.4rem;align-items:center;margin-bottom:0.3rem;}
  .opt-label{font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);text-align:right;padding-right:0.4rem;white-space:nowrap;}
  .opt-row input{background:white;border:1px solid var(--border);padding:0.45rem 0.6rem;
    font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;
    width:100%;box-sizing:border-box;}
  .opt-row input:focus{border-color:var(--ink);}
  /* シーン */
  .scene-block{margin-top:0.8rem;}
  .scene-toggle{font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--muted);
    cursor:pointer;display:flex;align-items:center;gap:0.3rem;user-select:none;
    background:linear-gradient(90deg,rgba(179,136,216,0.13),rgba(240,168,200,0.08));
    padding:0.4rem 0.8rem;border-left:3px solid var(--accent);border-radius:0 6px 6px 0;}
  .scene-toggle:hover{background:linear-gradient(90deg,rgba(179,136,216,0.22),rgba(240,168,200,0.14));color:var(--ink);}
  /* Extraタグ */
  .extra-block{margin-top:0.8rem;border:1px solid var(--border);border-radius:8px;padding:1rem;background:rgba(255,255,255,0.9);}
  .extra-presets{display:flex;flex-wrap:wrap;gap:0.3rem;margin-top:0.4rem;}
  .extra-preset-btn,.preset-btn{border:1px solid var(--border);background:white;padding:0.35rem 0.7rem;
    font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--ink);cursor:pointer;
    transition:all 0.15s;user-select:none;}
  .extra-preset-btn:hover,.preset-btn:hover{border-color:#3a8c5c;}
  .extra-preset-btn.active,.preset-btn.active{background:#3a8c5c;color:white;border-color:#3a8c5c;}
  .extra-custom{display:flex;gap:0.4rem;margin-top:0.5rem;}
  .extra-custom input{flex:1;min-width:0;background:white;border:1px solid var(--border);
    padding:0.45rem 0.6rem;font-family:'DM Mono',monospace;font-size:0.78rem;
    color:var(--ink);outline:none;}
  .extra-custom input:focus{border-color:var(--ink);}
  .extra-custom button{flex-shrink:0;width:4rem;border:1px solid var(--border);background:white;
    padding:0.45rem 0;font-family:'DM Mono',monospace;font-size:0.72rem;
    color:var(--ink);cursor:pointer;white-space:nowrap;text-align:center;}
  .extra-custom button:hover{background:var(--ink);color:var(--paper);}
  .extra-badges{display:flex;flex-wrap:wrap;gap:0.3rem;margin-top:0.5rem;min-height:1.2rem;}
  .extra-badge{background:linear-gradient(135deg,var(--multi),#b06bc8);color:white;padding:0.25rem 0.6rem;border-radius:20px;
    font-family:'DM Mono',monospace;font-size:0.72rem;cursor:pointer;display:flex;align-items:center;gap:0.3rem;}
  .extra-badge:hover{opacity:0.7;}
  .age-row{display:flex;gap:0.3rem;margin-top:0.2rem;}
  .style-row{display:flex;gap:0.4rem;margin-bottom:0.4rem;}
  .style-badge{background:#2c5f8a;color:white;padding:0.25rem 0.6rem;
    font-family:'DM Mono',monospace;font-size:0.72rem;cursor:pointer;display:inline-flex;align-items:center;gap:0.3rem;}
  .style-badge:hover{opacity:0.7;}
  .period-row{display:flex;gap:0.3rem;flex-wrap:wrap;margin-top:0.3rem;}
  .period-btn{border:1px solid var(--border);background:white;padding:0.35rem 0.6rem;
    border-radius:5px;font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--ink);cursor:pointer;user-select:none;}
  .period-btn:hover{border-color:#2d7a4f;}
  .period-btn.active{background:#2d7a4f;color:white;border-color:#2d7a4f;}
  .tag-check-group{display:flex;flex-wrap:wrap;gap:0.3rem;margin-top:0.3rem;}
  .tag-check{display:flex;align-items:center;gap:0.25rem;border:1px solid var(--border);
    padding:0.3rem 0.55rem;cursor:pointer;user-select:none;background:white;font-family:'DM Mono',monospace;font-size:0.72rem;transition:all 0.15s;}
  .tag-check:has(input:checked){background:var(--highlight);border-color:var(--multi);color:var(--multi);}
  .tag-check input{cursor:pointer;margin:0;width:12px;height:12px;}
  .safety-btn{border:1px solid var(--border);background:white;padding:0.35rem 0.6rem;
    border-radius:5px;font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--ink);cursor:pointer;user-select:none;}
  .safety-btn:hover{border-color:#2d7a4f;}
  .safety-btn.active{background:#2d7a4f;color:white;border-color:#2d7a4f;}
  .save-load-row{display:flex;gap:0.4rem;margin-bottom:0.5rem;}
  .sl-btn{flex:1;border:1px solid var(--border);background:var(--card);padding:0.55rem 0;
    border-radius:6px;font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--muted);cursor:pointer;text-align:center;transition:all 0.2s;}
  .sl-btn:hover{background:var(--highlight);color:var(--multi);border-color:var(--accent);}
  .multi-btn{display:inline-flex;align-items:center;justify-content:center;
    padding:0.3rem 0.55rem;border-radius:5px;font-size:0.75rem;cursor:pointer;
    border:1.5px solid var(--border);background:white;color:var(--ink);
    transition:background 0.15s,color 0.15s,border-color 0.15s;user-select:none;}
  .multi-btn.active{background:var(--multi);color:white;border-color:var(--multi);}
  .multi-btn:hover:not(.active){background:var(--highlight);}
  .age-btn{flex:1;border:1px solid var(--border);background:white;padding:0.4rem 0.3rem;
    border-radius:5px;font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--ink);cursor:pointer;
    text-align:center;transition:all 0.15s;user-select:none;}
  .age-btn:hover{border-color:#2d7a4f;}
  .age-btn.active{background:#2d7a4f;color:white;border-color:#2d7a4f;}
  .age-btn[style*="background-color"].active{outline:3px solid #222;outline-offset:1px;filter:brightness(1.15);}
  .age-btn[style*="background-color"]:hover{filter:brightness(1.1);}
</style>
</head>
<body>
<div class="container">
  <h1>Anima Pipeline</h1>
  <h2>キャラクター生成（プロンプト+画像）</h2>

  <div class="stoggle" onclick="toggleSettings()">
    <span id="sarrow">▶</span> 設定
  </div>
  <div class="sbody" id="sbody">
    <!-- 必須 -->
    <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#c0392b;font-weight:bold;margin-bottom:0.4rem;letter-spacing:0.05em;">■ 必須</div>
    <div style="border:1.5px solid #e74c3c;border-radius:7px;padding:0.8rem;margin-bottom:0.8rem;background:#fff9f9;">
      <div class="field">
        <label>① ワークフローJSONパス</label>
        <input type="text" id="workflowInput" placeholder="C:\ComfyUI\...\image_anima_preview.json">
      </div>
      <div class="field-row">
        <div class="field">
          <label>② Positive Node ID</label>
          <input type="text" id="posNodeInput" placeholder="11">
        </div>
        <div class="field">
          <label>③ Negative Node ID</label>
          <input type="text" id="negNodeInput" placeholder="12">
        </div>
      </div>
      <div class="field">
        <label>④ ComfyUI URL</label>
        <input type="text" id="comfyUrlInput" placeholder="http://127.0.0.1:8188">
      </div>
    </div>
    <!-- LLM使うなら必須 -->
    <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#e67e22;font-weight:bold;margin-bottom:0.4rem;letter-spacing:0.05em;">■ LLMを使うなら必須</div>
    <div style="border:1.5px solid #e67e22;border-radius:7px;padding:0.8rem;margin-bottom:0.8rem;background:#fffaf5;">
      <div class="field">
        <label>⑤ LLMプラットフォーム</label>
        <div style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-top:0.3rem;" id="llmPlatformBtns">
          <div class="period-btn active" data-plat="" onclick="selLLMPlatform(this)">なし</div>
          <div class="period-btn" data-plat="lmstudio" onclick="selLLMPlatform(this)">LM Studio</div>
          <div class="period-btn" data-plat="gemini" onclick="selLLMPlatform(this)">Gemini</div>
          <div class="period-btn" data-plat="custom" onclick="selLLMPlatform(this)">カスタム</div>
        </div>
      </div>
      <div id="llmDetailFields" style="display:none;">
        <div class="field" style="margin-top:0.6rem;">
          <label>⑤-1 LLM URL</label>
          <input type="text" id="lmsUrlInput" placeholder="http://localhost:1234">
        </div>
        <div class="field">
          <label>⑤-2 LLM API Token</label>
          <input type="password" id="tokenInput" placeholder="空欄 または トークン文字列">
        </div>
        <div class="field">
          <label>⑤-3 LLMモデル名</label>
          <input type="text" id="modelInput" placeholder="qwen/qwen3.5-9b-uncensored-hauhaucs-aggressive">
        </div>
      </div>
    </div>
    <!-- 任意 -->
    <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#27ae60;font-weight:bold;margin-bottom:0.4rem;letter-spacing:0.05em;">■ 任意</div>
    <div style="border:1.5px solid #27ae60;border-radius:7px;padding:0.8rem;margin-bottom:0.8rem;background:#f9fff9;">
      <div class="field">
        <label>⑧ LLMツール統合</label>
        <div style="display:flex;gap:0.8rem;flex-wrap:wrap;margin-top:0.3rem;">
          <label style="display:flex;align-items:center;gap:0.3rem;font-size:0.78rem;cursor:pointer;">
            <input type="checkbox" id="tool_danbooru_rag" checked style="accent-color:var(--multi);">
            Danbooru RAG
          </label>
          <label style="display:flex;align-items:center;gap:0.3rem;font-size:0.78rem;cursor:pointer;">
            <input type="checkbox" id="tool_danbooru_api" checked style="accent-color:var(--multi);">
            Danbooru API
          </label>
          <label style="display:flex;align-items:center;gap:0.3rem;font-size:0.78rem;cursor:pointer;">
            <input type="checkbox" id="tool_duckduckgo" checked style="accent-color:var(--multi);">
            DuckDuckGo
          </label>
        </div>
      </div>
      <div class="field">
        <label>⑨ ComfyUI output フォルダ（WebP変換用・<strong style="color:#e74c3c">絶対パスで入力推奨</strong>）</label>
        <input type="text" id="outputDirInput" placeholder="例: D:\ComfyUI_Portable\ComfyUI_windows_portable\ComfyUI\output">
      </div>
    </div>
    <button class="save-btn" onclick="saveSettings()">💾 設定を保存</button>
    <div class="save-notice" id="saveNotice">✓ pipeline_config.json に保存しました</div>
    <div style="display:flex;gap:0.5rem;margin-top:0.5rem;">
      <button class="sl-btn" style="flex:1" onclick="testConnection('comfyui')">🔌 ComfyUI 接続テスト</button>
      <button class="sl-btn" style="flex:1" onclick="testConnection('llm')">🤖 LLM 接続テスト</button>
    </div>
    <div id="testResult" style="display:none;font-family:'DM Mono',monospace;font-size:0.75rem;margin-top:0.4rem;padding:0.4rem 0.6rem;border-radius:5px;"></div>
    <!-- キャラプリセット削除 -->
    <div style="margin-top:0.8rem;padding:0.6rem 0.7rem;background:#fff5f5;border:1px solid #e0779a;border-radius:7px;">
      <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:#c0392b;font-weight:bold;margin-bottom:0.4rem;">📋 キャラプリセット削除</div>
      <div style="display:flex;gap:0.4rem;align-items:center;">
        <select id="presetDeleteSel" style="flex:1;min-width:0;font-family:'DM Mono',monospace;font-size:0.72rem;border:1px solid #e0779a;border-radius:5px;padding:0.3rem 0.5rem;background:white;color:var(--ink);cursor:pointer;">
          <option value="">── プリセットを選択 ──</option>
        </select>
        <button onclick="deleteCharaPresetFromSettings()" style="font-family:'DM Mono',monospace;font-size:0.72rem;padding:0.3rem 0;width:2.8rem;text-align:center;border:1px solid #e0779a;border-radius:5px;background:white;color:#c0392b;cursor:pointer;">削除</button>
      </div>
    </div>
  </div>

  <div class="save-load-row" style="margin-bottom:1rem;">
    <button class="sl-btn" onclick="saveSession()">💾 セッション保存</button>
    <button class="sl-btn" onclick="document.getElementById('loadFileInput').click()">📂 開く</button>
    <input type="file" id="loadFileInput" accept=".json" style="display:none" onchange="loadSession(this)">
  </div>
  <div id="loadedFileName" style="display:none;font-family:'DM Mono',monospace;font-size:0.72rem;
    color:var(--muted);margin-top:-0.6rem;margin-bottom:0.8rem;padding:0.3rem 0.5rem;
    background:#f5f5f0;border-left:2px solid var(--border);">📄 <span id="loadedFileNameText"></span></div>

  <!-- ブロックA: 画像設定 -->
  <div class="scene-toggle" onclick="toggleBlock('blockA','arrowA')" style="margin-bottom:0.5rem;">
    <span id="arrowA">▶</span> 画像設定
  </div>
  <div id="blockA" style="display:none;border:1px solid var(--border);border-radius:8px;padding:1rem;background:rgba(255,255,255,0.9);margin-bottom:1rem;">
    <div style="margin-bottom:0.8rem;">
      <label>画像サイズ（Anima推奨）</label>
      <div class="size-row">
        <select id="sizePreset" onchange="applyPreset(this.value)" style="min-width:0;"></select>
        <input type="number" id="widthInput" value="1024" min="1" max="8192" step="1" oninput="selectedW=parseInt(this.value)||1024">
        <span class="size-sep">×</span>
        <input type="number" id="heightInput" value="1024" min="1" max="8192" step="1" oninput="selectedH=parseInt(this.value)||1024">
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;align-items:start;">
      <div>
        <label>保存形式</label>
        <div class="fmt-row" style="margin-top:0.2rem;">
          <div class="fmt-btn active" data-fmt="png" onclick="selectFmt(this)">PNG生成</div>
          <div class="fmt-btn" data-fmt="webp" onclick="selectFmt(this)">WebP変換</div>
        </div>
      </div>
      <div>
        <label>送信枚数</label>
        <input type="number" id="countInput" value="1" min="1" step="1"
          style="margin-top:0.2rem;width:100%;background:white;border:1px solid var(--border);border-radius:6px;
          padding:0.7rem 0.8rem;font-family:'DM Mono',monospace;font-size:0.83rem;color:var(--ink);
          outline:none;box-sizing:border-box;"
          oninput="selectedCount=Math.max(1,parseInt(this.value)||1)">
      </div>
    </div>
  </div>

  <!-- ブロックB: キャラクター・シーン -->
  <div class="scene-toggle" onclick="toggleBlock('blockB','arrowB')" style="margin-bottom:0.5rem;">
    <span id="arrowB">▼</span> キャラクター・シーン
  </div>
  <div id="blockB">
    <div style="border:1px solid var(--border);border-radius:8px;padding:1rem;background:rgba(255,255,255,0.9);margin-bottom:1rem;">
      <!-- 共通作品 -->
      <div class="struct-fields" style="margin-bottom:0.8rem;">
        <div class="struct-row required">
          <label class="struct-label">A. 共通作品（任意）</label>
          <input type="text" id="f_series" class="inp-ja" placeholder="例: ウマ娘、ブルアカ（複数作品の場合はキャラごとに入力）">
        </div>
      </div>
      <!-- キャラ数 -->
      <div style="margin-bottom:0.5rem;display:grid;grid-template-columns:9rem 1fr;gap:0.5rem;align-items:center;">
        <label class="struct-label" style="text-align:right;padding-right:0.5rem;font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--muted);">B. キャラ数 *</label>
        <input type="number" id="f_charcount" value="1" min="1" max="6" step="1"
          style="width:80px;background:#f8f4ff;border:1px solid var(--accent);border-radius:6px;padding:0.55rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.82rem;color:var(--ink);outline:none;"
          oninput="updateCharaBlocks()">
      </div>
      <!-- キャラブロック -->
      <div id="charaContainer"></div>
      <!-- シーン -->
      <div class="scene-block">
        <div class="scene-toggle" onclick="toggleScene()" style="cursor:pointer;">
          <span id="sceneArrow">▶</span> C. シーン・雰囲気（任意）
        </div>
        <div class="scene-optional" id="sceneOptional" style="display:none;padding-top:0.4rem;">
          <div class="opt-row">
            <label class="opt-label">C-1. 世界観</label>
            <div style="display:flex;gap:0.25rem;flex-wrap:wrap;">
              <div id="world_btns" style="display:flex;gap:0.25rem;flex-wrap:wrap;"></div>
            </div>
          </div>
          <div class="opt-row" style="margin-top:0.4rem;align-items:start;">
            <label class="opt-label" style="padding-top:0.3rem;">C-2. 場所</label>
            <div style="display:flex;flex-direction:column;gap:0.3rem;width:100%;">
              <!-- カテゴリタブ（屋外/屋内/特殊） -->
              <div id="place_cat_row" style="display:flex;gap:0.2rem;flex-wrap:wrap;">
                <div class="period-btn" data-placecat="屋外" onclick="showPlaceCat('屋外',this)">屋外</div>
                <div class="period-btn" data-placecat="屋内" onclick="showPlaceCat('屋内',this)">屋内</div>
                <div class="period-btn" data-placecat="特殊" onclick="showPlaceCat('特殊',this)">特殊</div>
              </div>
              <!-- 屋外/屋上/室内 サブ選択（カテゴリ連動） -->
              <div id="place_sub_row" style="display:none;gap:0.2rem;flex-wrap:wrap;"></div>
              <!-- 場所選択肢エリア -->
              <div id="place_item_row" style="display:none;gap:0.2rem;flex-wrap:wrap;"></div>
              <!-- 自由入力 -->
              <input type="text" id="f_place" class="inp-ja" placeholder="場所を自由入力（例: 競馬場、魔法学校）">
              <input type="hidden" id="f_outdoor" value="">
            </div>
          </div>
          <div class="opt-row" style="margin-top:0.4rem;">
            <label class="opt-label">C-4. 時間帯</label>
            <div style="display:flex;gap:0.25rem;flex-wrap:wrap;">
              <div id="tod_btns" style="display:flex;gap:0.25rem;flex-wrap:wrap;"></div>
            </div>
          </div>
          <div class="opt-row" style="margin-top:0.4rem;">
            <label class="opt-label">C-5. 天気</label>
            <div style="display:flex;gap:0.25rem;flex-wrap:wrap;">
              <div id="weather_btns" style="display:flex;gap:0.25rem;flex-wrap:wrap;"></div>
            </div>
          </div>
          <div class="opt-row" style="margin-top:0.4rem;">
            <label class="opt-label">C-6. その他</label>
            <input type="text" id="f_misc" class="inp-ja" placeholder="例: 緊張感、幻想的な雰囲気">
          </div>
          <input type="hidden" id="f_world" value="">
          <input type="hidden" id="f_outdoor" value="">
          <input type="hidden" id="f_tod" value="">
          <input type="hidden" id="f_weather" value="">
        </div>
      </div>
      <!-- 補足メモ -->
      <div style="margin-top:0.6rem;">
        <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.2rem;">D. 補足メモ（日本語）→ LLMに渡す（1回目のプロンプト生成のみ）</div>
        <textarea id="extraNoteJa" class="inp-ja" rows="2" placeholder="例: お姉さんが弟分を甘やかしている雰囲気、ドキドキしている"
          style="width:100%;background:white;border:1px solid var(--border);border-radius:6px;padding:0.5rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;
          resize:vertical;box-sizing:border-box;"></textarea>
      </div>
    </div>
  </div>

  <div style="display:flex;align-items:center;justify-content:center;gap:0.5rem;margin-bottom:0.5rem;">
    <input type="checkbox" id="useLLM" checked style="width:14px;height:14px;accent-color:var(--multi);cursor:pointer;">
    <label for="useLLM" style="font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--muted);cursor:pointer;user-select:none;">LLMを使用する</label>
  </div>
  <button id="btn" onclick="generate()">▶ 生成開始　(Ctrl+Enter)</button>
  <button class="btn-cancel" id="cancelBtn" onclick="cancelGenerate()">■ 生成中止</button>

  <!-- Extra（生成完了後に表示） -->
  <div class="extra-block" id="extraBlock" style="margin-top:0.8rem;border:1px solid var(--border);padding:0.8rem;background:#fafaf8;">
    <div class="scene-toggle" onclick="toggleExtraContent()" style="cursor:pointer;margin-bottom:0.5rem;">
      <span id="extraContentArrow">▶</span> プロンプト調整・追加（再生成に反映されます）
    </div>
    <div id="extraContent" style="display:none;">

    <!-- 期間タグ（Anima推奨: 先頭） -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">① 期間タグ</div>
      <div class="period-row">
        <div class="period-btn" data-p="" onclick="selPeriod(this)">－</div>
        <div class="period-btn" data-p="newest" onclick="selPeriod(this)">newest</div>
        <div class="period-btn" data-p="recent" onclick="selPeriod(this)">recent</div>
        <div class="period-btn" data-p="mid" onclick="selPeriod(this)">mid</div>
        <div class="period-btn" data-p="early" onclick="selPeriod(this)">early</div>
        <div class="period-btn" data-p="old" onclick="selPeriod(this)">old</div>
      </div>
      <div style="display:flex;gap:0.4rem;margin-top:0.4rem;align-items:center;">
        <span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);">year:</span>
        <input type="number" id="yearInput" placeholder="例: 2025、1995" min="1900" max="2099" step="1"
          style="width:90px;background:white;border:1px solid var(--border);padding:0.45rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;">
      </div>
    </div>

    <!-- 品質タグ -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">② 品質タグ（人間ベース）</div>
      <div class="tag-check-group" id="qualityHuman"></div>
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin:0.4rem 0 0.3rem;">② 品質タグ（PonyV7 aestheticベース）</div>
      <div class="tag-check-group" id="qualityPony"></div>
    </div>

    <!-- メタタグ -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">③ メタタグ</div>
      <div class="tag-check-group" id="metaTags"></div>
    </div>

    <!-- 安全タグ -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">④ 安全タグ（単一選択）</div>
      <div style="display:flex;gap:0.3rem;">
        <div id="safety_btns" style="display:flex;gap:0.25rem;flex-wrap:wrap;"></div>
      </div>
    </div>

    <!-- スタイル（@artist） -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">⑤ スタイル（@アーティスト名）<span style="color:#c0392b;"> ※英語表記で入力（例: takeuchi naoko）</span></div>
      <div class="extra-presets" id="stylePresets"></div>
      <div class="style-row" style="margin-top:0.4rem;">
        <input type="text" id="styleInput" class="inp-en" placeholder="新規追加（例: takeuchi naoko）"
          style="flex:1;min-width:0;background:white;border:1px solid var(--border);padding:0.45rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;">
        <button onclick="addStyle()"
          style="flex-shrink:0;width:4rem;border:1px solid var(--border);background:white;
          padding:0.45rem 0;font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--ink);
          cursor:pointer;text-align:center;">追加</button>
      </div>
      <div id="styleBadges" style="display:flex;flex-wrap:wrap;gap:0.3rem;margin-top:0.4rem;min-height:1rem;"></div>
    </div>

    <!-- ⑥ Extraタグ（キャラ・シーンの後） -->
    <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">⑥ Extraタグ（キャラ・シーンタグの後に追加）</div>
    <div class="extra-presets" id="extraPresets"></div>
    <div class="extra-custom" style="margin-top:0.5rem;">
      <input type="text" id="extraCustomInput" class="inp-en" placeholder="カスタムタグを入力（例: breast_grab）">
      <button onclick="addCustomTag()">追加</button>
    </div>
    <div class="extra-badges" id="extraBadges"></div>
    <!-- ⑦ 追記文（英語） -->
    <div style="margin-top:0.6rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.2rem;">⑦ 追記文（英語）→ プロンプト末尾に直接追加</div>
      <textarea id="extraNoteEn" class="inp-en" rows="2" placeholder="e.g. she gently strokes his hair with a warm smile"
        style="width:100%;background:white;border:1px solid var(--border);border-radius:6px;padding:0.5rem 0.6rem;
        font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;
        resize:vertical;box-sizing:border-box;"></textarea>
    </div>
    </div><!-- /extraContent -->
  </div>

  <!-- ネガティブプロンプト調整 -->
  <div style="margin-top:0.6rem;border:1px solid #e8c4c4;border-radius:8px;padding:0.8rem;background:#fff9f9;">
    <div class="scene-toggle" onclick="toggleNegContent()" style="cursor:pointer;margin-bottom:0.5rem;color:#c0392b;">
      <span id="negContentArrow">▶</span> ネガティブプロンプト調整
    </div>
    <div id="negContent" style="display:none;">

    <!-- ① 期間タグ（ポジティブと共有） -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">① 期間タグ（ポジティブと共通）</div>
      <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:#aaa;">ポジティブの期間タグ設定がネガティブにも反映されます</div>
    </div>

    <!-- ② 品質タグ -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">② 品質タグ（人間ベース: NORMAL/LOW/WORST）</div>
      <div class="tag-check-group" id="qualityHumanNeg"></div>
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin:0.4rem 0 0.3rem;">② 品質タグ（Pony）</div>
      <div class="tag-check-group" id="qualityPonyNeg"></div>
    </div>

    <!-- ③ メタタグ -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">③ メタタグ</div>
      <div class="tag-check-group" id="metaTagsNeg"></div>
    </div>

    <!-- ④ 安全タグ（ネガティブ独立） -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">④ 安全タグ（単一選択）</div>
      <div id="neg_safety_btns" style="display:flex;gap:0.25rem;flex-wrap:wrap;"></div>
    </div>

    <!-- ⑤ スタイル（ネガティブ独立） -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">⑤ スタイル（@アーティスト名・ネガティブ専用）<span style="color:#c0392b;"> ※英語表記</span></div>
      <div class="extra-presets" id="negStylePresets"></div>
      <div class="style-row" style="margin-top:0.4rem;">
        <input type="text" id="negStyleInput" class="inp-en" placeholder="新規追加（例: bad_artist）"
          style="flex:1;min-width:0;background:white;border:1px solid #e8c4c4;padding:0.45rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;">
        <button onclick="addNegStyle()"
          style="flex-shrink:0;width:4rem;border:1px solid #e8c4c4;background:white;
          padding:0.45rem 0;font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--ink);
          cursor:pointer;text-align:center;">追加</button>
      </div>
      <div id="negStyleBadges" style="display:flex;flex-wrap:wrap;gap:0.3rem;margin-top:0.4rem;min-height:1rem;"></div>
    </div>

    <!-- ⑥ Extraタグ（ネガティブ専用） -->
    <div style="margin-bottom:0.7rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">⑥ Extraタグ（ネガティブ専用・右クリックで削除）</div>
      <div class="extra-presets" id="negExtraPresets"></div>
      <div class="extra-custom" style="margin-top:0.5rem;">
        <input type="text" id="negExtraCustomInput" class="inp-en" placeholder="タグを追加（例: bad anatomy）">
        <button onclick="addNegCustomTag()">追加</button>
      </div>
      <div class="extra-badges" id="negExtraBadges"></div>
    </div>

    <!-- ⑦ 追記文（英語） -->
    <div style="margin-top:0.6rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.2rem;">⑦ 追記文（英語）→ ネガティブプロンプト末尾に直接追加</div>
      <textarea id="negExtraNoteEn" class="inp-en" rows="2" placeholder="e.g. cropped, out of frame"
        style="width:100%;background:white;border:1px solid #e8c4c4;border-radius:6px;padding:0.5rem 0.6rem;
        font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;
        resize:vertical;box-sizing:border-box;"></textarea>
    </div>

    </div><!-- /negContent -->
  </div>

  <button class="btn-regen" id="regenBtn" onclick="regenPrompt()">↺ 再画像生成</button>

  <div class="status-box" id="statusBox">
    <div class="status-label">処理状況</div>
    <div id="steps"></div>
    <div class="prompt-section-label" id="lmLabel" style="display:none;">
      <span>▸ LLM生成ポジティブプロンプト</span>
      <button class="copy-btn" onclick="copyPrompt('promptOutput',this)">コピー</button>
    </div>
    <div class="prompt-output" id="promptOutput"></div>
    <div class="prompt-section-label" id="finalLabel" style="display:none;">
      <span>▸ ComfyUI 送信ポジティブプロンプト（生成＋追加タグ）</span>
      <button class="copy-btn" onclick="copyPrompt('promptFinal',this)">コピー</button>
    </div>
    <div class="prompt-final" id="promptFinal" style="display:none;font-family:'DM Mono',monospace;font-size:0.8rem;color:var(--ink);"></div>
    <div class="prompt-section-label" id="negFinalLabel" style="display:none;">
      <span>▸ ComfyUI 送信ネガティブプロンプト</span>
      <button class="copy-btn" onclick="copyPrompt('promptNegFinal',this)">コピー</button>
    </div>
    <div class="prompt-final" id="promptNegFinal" style="display:none;font-family:'DM Mono',monospace;font-size:0.8rem;color:#c0392b;"></div>
  </div>
</div>

<script>
let running=false, settingsOpen=false, lastPositivePrompt=null;
let charaPresets = [];  // キャラプリセット一覧

// ===== キャラプリセット管理 =====
async function loadCharaPresets(){
  try{
    const res = await fetch('/chara_presets');
    charaPresets = await res.json();
    updateAllPresetSelects();
  }catch(e){ charaPresets=[]; }
}

async function saveCharaPresetToServer(preset, filename=null){
  const body = {action:'save', preset, filename};
  const res = await fetch('/chara_presets',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  return await res.json();
}

async function deleteCharaPresetFromServer(filename){
  const body = {action:'delete', filename};
  await fetch('/chara_presets',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
}

function collectCharaData(idx){
  const ch = {
    series:   (document.getElementById('chara_series_'+idx)||{value:''}).value,
    original: document.getElementById('chara_orig_'+idx)?.classList.contains('active')||false,
    name:     (document.getElementById('chara_name_'+idx)||{value:''}).value,
    gender:   document.querySelector(`#chara_${idx} .gender-btn.active`)?.dataset.g||'female',
    age:      document.querySelector(`#chara_${idx} .age-btn.active`)?.dataset.a||'unset',
  };
  ['outfit','action','hair','hairstyle','hairstyle_lm','haircolor','eyes','skin','body','misc'].forEach(f=>{
    ch[f] = (document.getElementById(`chara_${f}_${idx}`)||{value:''}).value;
  });
  ['bust','face','eyestate','mouth','effect','ears','tail','wings','acc','item','posv','posh'].forEach(f=>{
    ch[f] = (document.getElementById(`chara_${f}_${idx}`)||{value:''}).value;
  });
  ch.outfit_cat   = document.querySelector(`#chara_${idx} [data-cat].active`)?.dataset.cat||'';
  ch.outfit_color = document.querySelector(`#chara_${idx} [data-ocolor]`)?.dataset.ocolor||'';
  ch.outfit_item  = document.querySelector(`#chara_${idx} [data-oitem].active`)?.dataset.oitem||'';
  ch.outfit_free     = document.querySelector(`#chara_${idx} #chara_outfit_${idx}`)?.value||'';
  ch.skinOther       = (document.getElementById(`chara_skin_other_${idx}`)||{value:''}).value;
  ch.hairstyle_free  = (document.getElementById(`chara_hairstyle_free_${idx}`)||{value:''}).value;
  ch.hairother       = (document.getElementById(`chara_hairother_${idx}`)||{value:''}).value;
  ch.action_free     = (document.getElementById(`chara_action_free_${idx}`)||{value:''}).value;
  ch.item_free       = (document.getElementById(`chara_item_free_${idx}`)||{value:''}).value;
  return ch;
}

async function generateCharaPreset(idx){
  const nameEl = document.getElementById('chara_name_'+idx);
  const seriesEl = document.getElementById('chara_series_'+idx);
  const name = nameEl?.value.trim()||'';
  const series = seriesEl?.value.trim()||'';
  if(!name){ alert('キャラ名を入力してください'); return; }
  const btn = document.querySelector('#chara_'+idx+' button[title*="自動生成"]');
  if(btn){ btn.textContent='⏳'; btn.disabled=true; }
  try{
    const url = '/generate_preset?name='+encodeURIComponent(name)+'&series='+encodeURIComponent(series);
    const res = await fetch(url);
    const data = await res.json();
    if(data.ok){
      const preset = data.preset;
      charaPresets.push(preset);
      updateAllPresetSelects();
      // 自動的に読込
      const sel = document.getElementById('chara_preset_sel_'+idx);
      if(sel){ sel.value = charaPresets.length-1; }
      loadCharaPreset(idx);
      alert('「'+preset.name+'」のプリセットを生成・読込しました');
    } else {
      alert('生成失敗: '+(data.error||'不明なエラー'));
    }
  }catch(e){
    alert('エラー: '+e.message);
  } finally {
    if(btn){ btn.textContent='🔍'; btn.disabled=false; }
  }
}

async function saveCharaPreset(idx){
  const ch = collectCharaData(idx);
  const label = ch.name || 'キャラ'+(idx+1);
  const name = prompt('プリセット名を入力してください', label);
  if(name===null) return;
  const preset = { name: name.trim()||label, data: ch, savedAt: new Date().toISOString() };
  const res = await saveCharaPresetToServer(preset);
  if(res.ok){
    preset._filename = res.filename;
    charaPresets.push(preset);
    updateAllPresetSelects();
    alert(`「${preset.name}」を保存しました`);
  }
}

async function deleteCharaPreset(idx){
  const sel = document.getElementById('chara_preset_sel_'+idx);
  if(!sel || sel.value==='') return;
  const i = parseInt(sel.value);
  if(isNaN(i)) return;
  const preset = charaPresets[i];
  if(!preset) return;
  if(!confirm(`「${preset.name}」を削除しますか？`)) return;
  await deleteCharaPresetFromServer(preset._filename);
  charaPresets.splice(i, 1);
  updateAllPresetSelects();
}

function updatePresetSelect(selEl){
  if(!selEl) return;
  const cur = selEl.value;
  selEl.innerHTML = '<option value="">── プリセットを選択 ──</option>';
  charaPresets.forEach((p,i)=>{
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = p.name;
    selEl.appendChild(opt);
  });
  if(cur!=='' && charaPresets[parseInt(cur)]) selEl.value = cur;
}

function updateAllPresetSelects(){
  document.querySelectorAll('[id^="chara_preset_sel_"]').forEach(sel=>updatePresetSelect(sel));
  updatePresetSelect(document.getElementById('presetDeleteSel'));
}

async function deleteCharaPresetFromSettings(){
  const sel = document.getElementById('presetDeleteSel');
  if(!sel || sel.value==='') return;
  const i = parseInt(sel.value);
  if(isNaN(i)) return;
  const preset = charaPresets[i];
  if(!preset) return;
  if(!confirm(`「${preset.name}」を削除しますか？`)) return;
  await deleteCharaPresetFromServer(preset._filename);
  charaPresets.splice(i, 1);
  updateAllPresetSelects();
}

function loadCharaPreset(idx){
  const sel = document.getElementById('chara_preset_sel_'+idx);
  if(!sel || sel.value==='') return;
  const preset = charaPresets[parseInt(sel.value)];
  if(!preset) return;
  // applySessionのキャラ部分を流用
  const ch = preset.data;
  setTimeout(()=>{
    if(document.getElementById('chara_series_'+idx)) document.getElementById('chara_series_'+idx).value = ch.series||'';
    if(ch.original){
      const ob = document.getElementById('chara_orig_'+idx);
      if(ob && !ob.classList.contains('active')) ob.click();
    }
    if(document.getElementById('chara_name_'+idx)) document.getElementById('chara_name_'+idx).value = ch.name||'';
    const gRow = document.querySelector(`#chara_${idx} .chara-attr-btns.gender-row`);
    if(gRow) gRow.querySelectorAll('.gender-btn').forEach(b=>b.classList.toggle('active', b.dataset.g===ch.gender));
    const aRow = document.querySelector(`#chara_${idx} .chara-attr-btns.age-row`);
    if(aRow) aRow.querySelectorAll('.age-btn').forEach(b=>b.classList.toggle('active', b.dataset.a===ch.age));
    ['action','hair','hairstyle','hairstyle_lm','haircolor','eyes','skin','body','misc'].forEach(f=>{
      const el = document.getElementById(`chara_${f}_${idx}`);
      if(el) el.value = ch[f]||'';
    });
    ['bust','face','eyestate','mouth','effect','ears','tail','wings','acc','item','posv','posh'].forEach(f=>{
      const el = document.getElementById(`chara_${f}_${idx}`);
      if(el) el.value = ch[f]||'';
    });
    // 衣装復元（outfit_catがある場合はボタンUI、なければoutfit_freeに流す）
    if(ch.outfit_cat){
      const catBtn = document.querySelector(`#chara_${idx} [data-outcat="${ch.outfit_cat}"]`);
      if(catBtn) catBtn.click();
      if(ch.outfit_color){
        const oColorSel = document.querySelector(`#chara_${idx} [data-ocolor]`);
        if(oColorSel){ oColorSel.value=ch.outfit_color; oColorSel.dataset.ocolor=ch.outfit_color; const found=OUTFIT_COLORS.find(c=>c.v===ch.outfit_color); if(found){oColorSel.style.backgroundColor=found.bg;oColorSel.style.color=found.fg;} }
      }
      if(ch.outfit_item)  document.querySelectorAll(`#chara_${idx} [data-oitem]`).forEach(b=>b.classList.toggle('active',b.dataset.oitem===ch.outfit_item));
    }
    // outfit_freeまたはoutfit（タグ文字列）を自由入力欄に
    const outfitFreeEl = document.getElementById(`chara_outfit_free_${idx}`);
    if(outfitFreeEl){
      outfitFreeEl.value = ch.outfit_free || ch.outfit || '';
    }
    // 髪型ボタン復元
    if(ch.hairstyle){
      const hsVals = ch.hairstyle.split(',').map(v=>v.trim()).filter(Boolean);
      document.querySelector(`#chara_${idx}`)?.querySelectorAll('[data-hs]').forEach(b=>{
        b.classList.toggle('active', hsVals.includes(b.dataset.hs));
      });
      const hsHid = document.getElementById(`chara_hairstyle_${idx}`);
      if(hsHid) hsHid.value = ch.hairstyle;
    }
    // multiボタン復元（face/eyestate/mouth/effect）
    ['face','eyestate','mouth','effect'].forEach(f=>{
      const hid = document.getElementById(`chara_${f}_${idx}`);
      if(hid && ch[f]){
        const vals = ch[f].split(',').map(v=>v.trim()).filter(Boolean);
        document.querySelector(`#chara_${idx}`)?.querySelectorAll(`[data-${f}]`).forEach(b=>{
          b.classList.toggle('active', vals.includes(b.dataset[f]));
        });
      }
    });
    // bustボタン復元
    const bustHid2 = document.getElementById(`chara_bust_${idx}`);
    if(bustHid2 && ch.bust){
      bustHid2.value = ch.bust;
      const bustRow2 = document.getElementById(`chara_bust_row_${idx}`);
      if(bustRow2) bustRow2.querySelectorAll('.age-btn').forEach(b=>b.classList.toggle('active', b.dataset.bust===ch.bust));
    }
    // 髪色select復元
    const hairSelEl = document.querySelector(`#chara_${idx} select[id^=""][id=""]`) || (() => {
      // hairSelはidがないのでhairHiddenの前のselectを探す
      const hcHid = document.getElementById(`chara_haircolor_${idx}`);
      return hcHid?.previousElementSibling?.tagName==='INPUT' ? hcHid?.parentElement?.querySelector('select') : hcHid?.previousElementSibling;
    })();
    if(hairSelEl && ch.haircolor){
      hairSelEl.value = ch.haircolor;
      const hcFound = HAIR_COLORS.find(c=>c.v===ch.haircolor);
      if(hcFound){ hairSelEl.style.backgroundColor=hcFound.bg||'white'; hairSelEl.style.color=hcFound.fg||'var(--ink)'; }
      document.getElementById(`chara_haircolor_${idx}`).value = ch.haircolor;
    }
    // 肌色復元
    const skinHid = document.getElementById(`chara_skin_${idx}`);
    if(skinHid){
      skinHid.value = ch.skin||'';
      const skinSelEl = skinHid.parentElement?.querySelector('select');
      if(skinSelEl){ skinSelEl.value=ch.skin||''; const f=SKIN_OPTIONS.find(c=>c.v===(ch.skin||'')); if(f?.bg){skinSelEl.style.backgroundColor=f.bg;skinSelEl.style.color=f.fg||'var(--ink)';} }
    }
    const skinOtherEl = document.getElementById(`chara_skin_other_${idx}`);
    if(skinOtherEl) skinOtherEl.value = ch.skinOther||''
    // 自由入力欄復元
    const hsf = document.getElementById(`chara_hairstyle_free_${idx}`);
    if(hsf && ch.hairstyle_free) hsf.value = ch.hairstyle_free;
    const hof = document.getElementById(`chara_hairother_${idx}`);
    if(hof && ch.hairother) hof.value = ch.hairother;
    const acf = document.getElementById(`chara_action_free_${idx}`);
    if(acf && ch.action_free) acf.value = ch.action_free;
    const itf = document.getElementById(`chara_item_free_${idx}`);
    if(itf && ch.item_free) itf.value = ch.item_free;
    // 瞳色select復元
    const eyeHid2 = document.getElementById(`chara_eyes_${idx}`);
    if(eyeHid2 && ch.eyes){
      eyeHid2.value=ch.eyes;
      const eyeWrapEl = eyeHid2.parentElement;
      const eyeSelEl2 = eyeWrapEl?.querySelector('select');
      if(eyeSelEl2){ eyeSelEl2.value=ch.eyes; const f=EYE_COLORS.find(c=>c.v===ch.eyes); if(f){eyeSelEl2.style.backgroundColor=f.bg||'white';eyeSelEl2.style.color=f.fg||'var(--ink)';} }
    }
    // 詳細欄を自動展開
    const hasDetail = ['outfit','action','hair','eyes','skin','body','misc','bust'].some(f=>ch[f]);
    if(hasDetail){
      const opt = document.getElementById('chara_opt_'+idx);
      const btn = opt?.previousElementSibling?.querySelector('.chara-expand');
      if(opt && opt.style.display==='none'){ opt.style.display='block'; if(btn) btn.textContent='－ 詳細'; }
    }
  }, 50);
}
let selectedW=1024, selectedH=1024;
let selectedFmt='png';
let selectedCount=1;

function selectFmt(el){
  document.querySelectorAll('[data-fmt]').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  selectedFmt=el.dataset.fmt;
}


function applyPreset(val){
  const [w,h]=val.split('x').map(Number);
  selectedW=w; selectedH=h;
  document.getElementById('widthInput').value=w;
  document.getElementById('heightInput').value=h;
}

const PLACE_CATEGORIES = __OPT__.place_categories;

// カテゴリごとのサブ選択肢（屋外/屋上/室内）
const PLACE_SUB = __OPT__.place_sub;

let placeActiveCat = null;
function showPlaceCat(cat, btnEl){
  const itemRow = document.getElementById('place_item_row');
  const subRow  = document.getElementById('place_sub_row');
  const outdoorHid = document.getElementById('f_outdoor');
  if(placeActiveCat === cat){
    placeActiveCat = null;
    document.querySelectorAll('[data-placecat]').forEach(b=>b.classList.remove('active'));
    itemRow.style.display = 'none';
    subRow.style.display  = 'none';
    outdoorHid.value = '';
    return;
  }
  placeActiveCat = cat;
  document.querySelectorAll('[data-placecat]').forEach(b=>{
    b.classList.toggle('active', b.dataset.placecat===cat);
  });

  // サブ行（屋外/屋上/室内）
  subRow.innerHTML = '';
  outdoorHid.value = '';
  (PLACE_SUB[cat]||[]).forEach(({v,label})=>{
    const btn = document.createElement('div');
    btn.className = 'period-btn';
    btn.textContent = label;
    btn.addEventListener('click',function(){
      subRow.querySelectorAll('.period-btn').forEach(b=>b.classList.remove('active'));
      this.classList.add('active');
      outdoorHid.value = v;
    });
    subRow.appendChild(btn);
  });
  // 屋内は室内を自動選択
  if(cat==='屋内'){
    const indoorBtn = [...subRow.querySelectorAll('.period-btn')].find(b=>b.textContent==='室内');
    if(indoorBtn){ indoorBtn.classList.add('active'); outdoorHid.value='indoors'; }
  }
  subRow.style.display = (PLACE_SUB[cat]||[]).length > 0 ? 'flex' : 'none';

  // 場所選択肢
  itemRow.innerHTML = '';
  (PLACE_CATEGORIES[cat]||[]).forEach(({v,label})=>{
    const btn = document.createElement('div');
    btn.className = 'period-btn';
    btn.dataset.placeval = v;
    btn.textContent = label;
    btn.addEventListener('click',function(){
      const isActive = this.classList.contains('active');
      itemRow.querySelectorAll('.period-btn').forEach(b=>b.classList.remove('active'));
      if(!isActive){
        this.classList.add('active');
        document.getElementById('f_place').value = label;
      } else {
        document.getElementById('f_place').value = '';
      }
    });
    itemRow.appendChild(btn);
  });
  itemRow.style.display = 'flex';
}

// LLMプラットフォームの選択肢定義
// PFごとのデフォルト値（初回選択時のみ補完）
const LLM_PLATFORM_PRESETS = {
  lmstudio: {
    url:   'http://localhost:1234',
    token: '',
    model: 'qwen/qwen3.5-9b-uncensored-hauhaucs-aggressive',
  },
  gemini: {
    url:   'https://generativelanguage.googleapis.com/v1beta/openai',
    token: '',
    model: 'gemini-2.5-flash',
  },
  custom: {
    url:   '',
    token: '',
    model: '',
  },
};

// PFごとの入力値をメモリに保持（切り替え時に退避・復元）
const _llmPlatValues = {};  // { 'lmstudio': {url, token, model}, ... }
let _currentPlat = '';

function _savePlatFields(plat){
  if(!plat) return;
  _llmPlatValues[plat] = {
    url:   document.getElementById('lmsUrlInput').value,
    token: document.getElementById('tokenInput').value,
    model: document.getElementById('modelInput').value,
  };
}

function _restorePlatFields(plat){
  const saved  = _llmPlatValues[plat];
  const preset = LLM_PLATFORM_PRESETS[plat];
  // 保存値があればそれを、なければプリセットのデフォルトを使う
  const val = saved || preset || {url:'', token:'', model:''};
  document.getElementById('lmsUrlInput').value = val.url   || '';
  document.getElementById('tokenInput').value  = val.token || '';
  document.getElementById('modelInput').value  = val.model || '';
}

function selLLMPlatform(el){
  // 切り替え前に現在の入力値を退避
  _savePlatFields(_currentPlat);
  document.querySelectorAll('#llmPlatformBtns .period-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  _currentPlat = el.dataset.plat;
  const fields = document.getElementById('llmDetailFields');
  if(_currentPlat){
    fields.style.display = '';
    _restorePlatFields(_currentPlat);
  } else {
    fields.style.display = 'none';
  }
}

function toggleSettings(){
  settingsOpen=!settingsOpen;
  document.getElementById('sbody').classList.toggle('open',settingsOpen);
  document.getElementById('sarrow').textContent=settingsOpen?'▼':'▶';
}

async function loadSettings(){
  try{
    const cfg=await(await fetch('/config')).json();
    // LLMプラットフォーム：保存値をメモリに展開してから復元
    const plat = cfg.llm_platform||'';
    _currentPlat = plat;
    if(plat){
      _llmPlatValues[plat] = {
        url:   cfg.llm_url   || '',
        token: cfg.llm_token || '',
        model: cfg.llm_model || '',
      };
    }
    document.querySelectorAll('#llmPlatformBtns .period-btn').forEach(b=>{
      b.classList.toggle('active', b.dataset.plat===plat);
    });
    document.getElementById('llmDetailFields').style.display = plat ? '' : 'none';
    if(plat) _restorePlatFields(plat);
    // フォールバック（platなしでも個別フィールドは読み込んでおく）
    if(!plat){
      document.getElementById('lmsUrlInput').value = cfg.llm_url   || '';
      document.getElementById('tokenInput').value  = cfg.llm_token || '';
      document.getElementById('modelInput').value  = cfg.llm_model || '';
    }
    if(cfg.tool_danbooru_rag!==undefined) document.getElementById('tool_danbooru_rag').checked=cfg.tool_danbooru_rag;
    if(cfg.tool_danbooru_api!==undefined) document.getElementById('tool_danbooru_api').checked=cfg.tool_danbooru_api;
    if(cfg.tool_duckduckgo!==undefined)   document.getElementById('tool_duckduckgo').checked=cfg.tool_duckduckgo;
    document.getElementById('modelInput').value=cfg.llm_model||'';
    document.getElementById('lmsUrlInput').value=cfg.llm_url||'';
    document.getElementById('comfyUrlInput').value=cfg.comfyui_url||'';
    document.getElementById('workflowInput').value=cfg.workflow_json_path||'';
    document.getElementById('posNodeInput').value=cfg.positive_node_id||'';
    document.getElementById('negNodeInput').value=cfg.negative_node_id||'';
    document.getElementById('outputDirInput').value=cfg.comfyui_output_dir||'';
  }catch(e){console.warn(e);}
}

async function testConnection(target){
  const resultEl = document.getElementById('testResult');
  resultEl.style.display = 'block';
  resultEl.style.background = '#f5f5f5';
  resultEl.style.color = 'var(--ink)';
  resultEl.textContent = (target==='comfyui' ? 'ComfyUI' : 'LLM') + ' 接続テスト中...';
  try{
    const res = await fetch('/test_connection?target='+target);
    const data = await res.json();
    if(data.ok){
      resultEl.style.background = '#f0fff4';
      resultEl.style.color = '#2d7a4f';
      resultEl.textContent = '✓ ' + data.message;
    } else {
      resultEl.style.background = '#fff5f5';
      resultEl.style.color = '#c0392b';
      resultEl.textContent = '✗ ' + data.message;
    }
  } catch(e){
    resultEl.style.background = '#fff5f5';
    resultEl.style.color = '#c0392b';
    resultEl.textContent = '✗ 接続エラー: ' + e.message;
  }
}

async function saveSettings(){
  // 保存前に現在の入力値をメモリに退避
  _savePlatFields(_currentPlat);
  const cfg={
    llm_platform: _currentPlat||'',
    llm_token:document.getElementById('tokenInput').value,
    tool_danbooru_rag:document.getElementById('tool_danbooru_rag').checked,
    tool_danbooru_api:document.getElementById('tool_danbooru_api').checked,
    tool_duckduckgo:document.getElementById('tool_duckduckgo').checked,
    llm_model:document.getElementById('modelInput').value,
    llm_url:document.getElementById('lmsUrlInput').value,
    comfyui_url:document.getElementById('comfyUrlInput').value,
    workflow_json_path:document.getElementById('workflowInput').value,
    comfyui_output_dir:document.getElementById('outputDirInput').value,
    positive_node_id:document.getElementById('posNodeInput').value,
    negative_node_id:document.getElementById('negNodeInput').value,
  };
  await fetch('/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});
  const n=document.getElementById('saveNotice');
  n.style.display='block';
  setTimeout(()=>{n.style.display='none';},3000);
}

function copyPrompt(elId, btn){
  const text = document.getElementById(elId).textContent;
  navigator.clipboard.writeText(text).then(()=>{
    btn.textContent = '✓ コピー済';
    btn.classList.add('copied');
    setTimeout(()=>{ btn.textContent='コピー'; btn.classList.remove('copied'); }, 2000);
  }).catch(()=>{
    // fallback
    const ta = document.createElement('textarea');
    ta.value = text; document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); document.body.removeChild(ta);
    btn.textContent = '✓ コピー済'; btn.classList.add('copied');
    setTimeout(()=>{ btn.textContent='コピー'; btn.classList.remove('copied'); }, 2000);
  });
}

function setStep(steps,id,state,text){
  let el=document.getElementById(id);
  if(!el){el=document.createElement('div');el.id=id;steps.appendChild(el);}
  el.className='step '+state;
  el.innerHTML=(state==='active'?'<div class="spinner"></div>':'<div class="dot"></div>')+text;
}

// ===== セッション保存・読み込み =====
function collectSessionData(){
  // キャラ情報収集
  const count = Math.max(1, Math.min(6, parseInt(document.getElementById('f_charcount').value)||1));
  const chars = [];
  for(let i=0;i<count;i++){
    const ch = {
      series: (document.getElementById('chara_series_'+i)||{value:''}).value,
      original: document.getElementById('chara_orig_'+i)?.classList.contains('active')||false,
      name:   (document.getElementById('chara_name_'+i)||{value:''}).value,
      gender: document.querySelector(`#chara_${i} .gender-btn.active`)?.dataset.g||'female',
      age:    document.querySelector(`#chara_${i} .age-btn.active`)?.dataset.a||'unset',
    };
    ['outfit','action','hair','hairstyle','hairstyle_lm','haircolor','eyes','skin','body','misc'].forEach(f=>{
      ch[f] = (document.getElementById(`chara_${f}_${i}`)||{value:''}).value;
    });
    ch['bust'] = (document.getElementById(`chara_bust_${i}`)||{value:''}).value;
    ch['face'] = (document.getElementById(`chara_face_${i}`)||{value:''}).value;
    ch['eyestate'] = (document.getElementById(`chara_eyestate_${i}`)||{value:''}).value;
    ch['mouth'] = (document.getElementById(`chara_mouth_${i}`)||{value:''}).value;
    ch['effect'] = (document.getElementById(`chara_effect_${i}`)||{value:''}).value;
    ch['ears']   = (document.getElementById(`chara_ears_${i}`)||{value:''}).value;
    ch['tail']   = (document.getElementById(`chara_tail_${i}`)||{value:''}).value;
    ch['wings']  = (document.getElementById(`chara_wings_${i}`)||{value:''}).value;
    ch['acc']    = (document.getElementById(`chara_acc_${i}`)||{value:''}).value;
    ch['item']  = (document.getElementById(`chara_item_${i}`)||{value:''}).value;
    ch['posv'] = (document.getElementById(`chara_posv_${i}`)||{value:''}).value;
    ch['posh'] = (document.getElementById(`chara_posh_${i}`)||{value:''}).value;
    ch['outfit_cat']   = document.querySelector(`#chara_${i} [data-cat].active`)?.dataset.cat||'';
    ch['outfit_color'] = document.querySelector(`#chara_${i} [data-ocolor]`)?.dataset.ocolor||'';
    ch['outfit_item']  = document.querySelector(`#chara_${i} [data-oitem].active`)?.dataset.oitem||'';
    ch['outfit_free']  = document.querySelector(`#chara_${i} #chara_outfit_${i}`)?.value||'';
    ch['skin'] = (document.getElementById(`chara_skin_${i}`)||{value:''}).value;
    ch['skinOther'] = (document.getElementById(`chara_skin_other_${i}`)||{value:''}).value;
    ch['eyes'] = (document.getElementById(`chara_eyes_${i}`)||{value:''}).value;
    ch['hairstyle_free'] = (document.getElementById(`chara_hairstyle_free_${i}`)||{value:''}).value;
    ch['hairother']      = (document.getElementById(`chara_hairother_${i}`)||{value:''}).value;
    ch['action_free']    = (document.getElementById(`chara_action_free_${i}`)||{value:''}).value;
    ch['item_free']      = (document.getElementById(`chara_item_free_${i}`)||{value:''}).value;
    chars.push(ch);
  }
  return {
    version: 1,
    series:    document.getElementById('f_series').value,
    charcount: count,
    characters: chars,
    place:     document.getElementById('f_place').value,
    misc:      document.getElementById('f_misc').value,
    world:     document.getElementById('f_world')?.value||'',
    outdoor:   document.getElementById('f_outdoor')?.value||'',
    tod:       document.getElementById('f_tod')?.value||'',
    weather:   document.getElementById('f_weather')?.value||'',
    extraNoteJa: document.getElementById('extraNoteJa').value,
    extraNoteEn: document.getElementById('extraNoteEn').value,
    extraTags:   Array.from(extraTags),
    styleTags,
    stylePresetList,
    negExtraTags: Array.from(negExtraTags),
    negExtraPresetList,
    negStyleTags,
    negStylePresetList,
    selectedNegSafety,
    negExtraNoteEn: (document.getElementById('negExtraNoteEn')||{}).value||'',
    selectedPeriod,
    year:      document.getElementById('yearInput').value,
    selectedSafety,
    qualityHuman: collectCheckedTags('qualityHuman'),
    qualityPony:  collectCheckedTags('qualityPony'),
    metaTags:     collectCheckedTags('metaTags'),
    lmPrompt:     document.getElementById('promptOutput').textContent||'',
    finalPrompt:  document.getElementById('promptFinal').textContent||'',
    negFinalPrompt: document.getElementById('promptNegFinal').textContent||'',
    imgW: selectedW, imgH: selectedH, imgFmt: selectedFmt, imgCount: selectedCount,
    savedAt: new Date().toISOString(),
  };
}

async function autoSaveSession(){
  try{
    const data = collectSessionData();
    await fetch('/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  }catch(e){ console.warn('自動保存失敗:',e); }
}

async function loadLastSession(){
  try{
    const res = await fetch('/session');
    const data = await res.json();
    if(data && Object.keys(data).length > 0){
      applySession(data);
    }
  }catch(e){ console.warn('セッション読み込み失敗:',e); }
}

function saveSession(){
  const data = collectSessionData();
  const now = new Date();
  const pad = n=>String(n).padStart(2,'0');
  const ts = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}`;
  const filename = `Anima Pipeline_${ts}.json`;
  const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
  // サーバーにも保存
  autoSaveSession();
}

async function loadSession(input){
  const file = input.files[0];
  if(!file) return;
  try{
    const text = await file.text();
    const data = JSON.parse(text);
    applySession(data);
    document.getElementById('loadedFileNameText').textContent = file.name;
    document.getElementById('loadedFileName').style.display = 'block';
  }catch(e){
    alert('読み込みエラー: '+e.message);
  }
  input.value='';
}

function applySession(data){
  // シリーズ
  document.getElementById('f_series').value = data.series||'';
  // キャラ数・ブロック
  const count = data.charcount||1;
  document.getElementById('f_charcount').value = count;
  updateCharaBlocks();
  // 少し遅延してDOMが生成されてから値をセット
  setTimeout(()=>{
    (data.characters||[]).forEach((ch,i)=>{
      if(document.getElementById('chara_series_'+i))
        document.getElementById('chara_series_'+i).value = ch.series||'';
      // オリジナル復元
      if(ch.original){
        const ob = document.getElementById('chara_orig_'+i);
        if(ob && !ob.classList.contains('active')) ob.click();
      }
      if(document.getElementById('chara_name_'+i))
        document.getElementById('chara_name_'+i).value = ch.name||'';
      // 性別
      const gRow = document.querySelector(`#chara_${i} .chara-attr-btns.gender-row`);
      if(gRow) gRow.querySelectorAll('.gender-btn').forEach(b=>{
        b.classList.toggle('active', b.dataset.g===ch.gender);
      });
      // 年齢
      const aRow = document.querySelector(`#chara_${i} .chara-attr-btns.age-row`);
      if(aRow) aRow.querySelectorAll('.age-btn').forEach(b=>{
        b.classList.toggle('active', b.dataset.a===ch.age);
      });
      // 任意フィールド
      ['outfit','action','hair','hairstyle','hairstyle_lm','haircolor','eyes','skin','body','misc'].forEach(f=>{
        const el = document.getElementById(`chara_${f}_${i}`);
        if(el) el.value = ch[f]||'';
      });
      // 動作ボタン復元
      const actionHidEl = document.getElementById(`chara_action_${i}`);
      if(actionHidEl && ch['action']!==undefined){
        actionHidEl.value = ch['action']||'';
        const actVals = ch['action'] ? ch['action'].split(',') : [];
        document.getElementById(`chara_${i}`)?.querySelectorAll('[data-act]').forEach(b=>{
          b.classList.toggle('active', actVals.includes(b.dataset.act));
        });
        // 「持つ」が含まれていれば持ち物行を表示
        if(actVals.includes('holding')){
          const hr = document.getElementById(`chara_${i}`)?.querySelector('.opt-row[style*="display:none"]');
          // holdingRowを特定してdisplay:flex
          document.getElementById(`chara_${i}`)?.querySelectorAll('.opt-row').forEach(r=>{
            if(r.querySelector('#chara_item_'+i)) r.style.display='flex';
          });
        }
        // 自由入力復元（選択式に含まれない値の場合）
        const freeEl = document.getElementById(`chara_action_free_${i}`);
        if(freeEl){
          const isPresetOnly = actVals.every(v=>ACTION_OPTIONS.some(o=>o.v===v));
          freeEl.value = (ch['action'] && !isPresetOnly) ? ch['action'] : '';
        }
      }
      // バストボタン復元
      let bustHid = document.getElementById(`chara_bust_${i}`);
      if(bustHid){
        bustHid.value = ch['bust']||'';
        let bustRow = document.getElementById(`chara_bust_row_${i}`);
        if(bustRow) bustRow.querySelectorAll('.age-btn').forEach(b=>{
          b.classList.toggle('active', b.dataset.bust===(ch['bust']||''));
        });
      }
      // 持ち物復元
      const itemHidEl = document.getElementById(`chara_item_${i}`);
      if(itemHidEl && ch['item']!==undefined){
        itemHidEl.value = ch['item']||'';
      }
      // 位置復元
      ['posv','posh'].forEach(f=>{
        const hid = document.getElementById(`chara_${f}_${i}`);
        if(hid && ch[f]!==undefined){
          hid.value = ch[f];
          hid.closest('.opt-row')?.querySelectorAll('.age-btn').forEach(b=>{
            b.classList.toggle('active', b.dataset.val===(ch[f]||''));
          });
        }
      });
      // 衣装復元
      if(ch['outfit_cat']!==undefined){
        const charEl = document.getElementById(`chara_${i}`);
        if(charEl){
          const cat = ch['outfit_cat']||'';
          // カテゴリボタンをクリックでUI再現
          const catBtn = charEl.querySelector(`[data-outcat="${cat}"]`);
          if(catBtn) catBtn.click();
          // 色
          if(ch['outfit_color']){
            charEl.querySelectorAll('[data-ocolor]').forEach(b=>{
              b.classList.toggle('active', b.dataset.ocolor===ch['outfit_color']);
            });
          }
          // 種類
          if(ch['outfit_item']){
            charEl.querySelectorAll('[data-oitem]').forEach(b=>{
              b.classList.toggle('active', b.dataset.oitem===ch['outfit_item']);
            });
          }
          // 自由入力
          const freeIn = document.getElementById(`chara_outfit_free_${i}`);
          if(freeIn && ch['outfit_free']) freeIn.value = ch['outfit_free'];
        }
      }
      // 髪型復元
      const hairstyleEl = document.getElementById(`chara_hairstyle_${i}`);
      if(hairstyleEl && ch['hairstyle']!==undefined){
        hairstyleEl.value = ch['hairstyle']||'';
        const hsVals = ch['hairstyle'] ? ch['hairstyle'].split(',') : [];
        const hsBtns = hairstyleEl.closest('.opt-row')?.querySelectorAll('[data-hs]');
        if(hsBtns) hsBtns.forEach(b=>b.classList.toggle('active', hsVals.includes(b.dataset.hs)));
      }
      // 付属復元
      ['ears','tail','wings'].forEach(f=>{
        const hid = document.getElementById(`chara_${f}_${i}`);
        if(hid && ch[f]!==undefined){
          hid.value = ch[f];
          const row = hid.closest('div');
          if(row) row.querySelectorAll('.age-btn').forEach(b=>{
            b.classList.toggle('active', b.dataset.val===(ch[f]||''));
          });
        }
      });
      const accHid = document.getElementById(`chara_acc_${i}`);
      if(accHid && ch['acc']!==undefined){
        accHid.value = ch['acc'];
        const accVals = ch['acc'] ? ch['acc'].split(',') : [];
        const accRow = accHid.closest('div');
        if(accRow) accRow.querySelectorAll('.multi-btn').forEach(b=>{
          b.classList.toggle('active', accVals.includes(b.dataset.val));
        });
      }
      // エフェクト復元
      let efHid = document.getElementById(`chara_effect_${i}`);
      if(efHid && ch['effect']!==undefined){
        efHid.value = ch['effect'];
        let efVals = ch['effect'] ? ch['effect'].split(',') : [];
        let efRow = efHid.closest('.opt-row');
        if(efRow) efRow.querySelectorAll('.multi-btn').forEach(b=>{
          if(b.dataset.effect==='') b.classList.toggle('active', efVals.length===0);
          else b.classList.toggle('active', efVals.includes(b.dataset.effect));
        });
      }
      // 口の状態復元
      let mHid = document.getElementById(`chara_mouth_${i}`);
      if(mHid && ch['mouth']!==undefined){
        mHid.value = ch['mouth'];
        let mVals = ch['mouth'] ? ch['mouth'].split(',') : [];
        let mRow = mHid.closest('.opt-row');
        if(mRow) mRow.querySelectorAll('.multi-btn').forEach(b=>{
          if(b.dataset.mouth==='') b.classList.toggle('active', mVals.length===0);
          else b.classList.toggle('active', mVals.includes(b.dataset.mouth));
        });
      }
      // 目の状態復元
      let esHid = document.getElementById(`chara_eyestate_${i}`);
      if(esHid && ch['eyestate']!==undefined){
        esHid.value = ch['eyestate'];
        let esVals = ch['eyestate'] ? ch['eyestate'].split(',') : [];
        let esRow = esHid.closest('.opt-row');
        if(esRow) esRow.querySelectorAll('.multi-btn').forEach(b=>{
          if(b.dataset.es==='') b.classList.toggle('active', esVals.length===0);
          else b.classList.toggle('active', esVals.includes(b.dataset.es));
        });
      }
      // 表情復元
      let faceHid = document.getElementById(`chara_face_${i}`);
      if(faceHid && ch['face']!==undefined){
        faceHid.value = ch['face'];
        let faceVals = ch['face'] ? ch['face'].split(',') : [];
        let faceRow2 = faceHid.closest('.opt-row');
        if(faceRow2) faceRow2.querySelectorAll('.multi-btn').forEach(b=>{
          if(b.dataset.face==='') b.classList.toggle('active', faceVals.length===0);
          else b.classList.toggle('active', faceVals.includes(b.dataset.face));
        });
      }
      // 髪色select復元
      const hcHid = document.getElementById(`chara_haircolor_${i}`);
      if(hcHid && ch['haircolor']){
        hcHid.value = ch['haircolor'];
        const hcWrap = hcHid.parentElement;
        const hcSel = hcWrap?.querySelector('select');
        if(hcSel){ hcSel.value=ch['haircolor']; const f=HAIR_COLORS.find(c=>c.v===ch['haircolor']); if(f){hcSel.style.backgroundColor=f.bg||'white';hcSel.style.color=f.fg||'var(--ink)';} }
      }
      // 瞳の色復元
      let eyeHid = document.getElementById(`chara_eyes_${i}`);
      if(eyeHid && ch['eyes']){
        eyeHid.value = ch['eyes'];
        const eyeWrapEl2 = eyeHid.parentElement;
        const eyeSelEl3 = eyeWrapEl2?.querySelector('select');
        if(eyeSelEl3){ eyeSelEl3.value=ch['eyes']; const f=EYE_COLORS.find(c=>c.v===ch['eyes']); if(f){eyeSelEl3.style.backgroundColor=f.bg||'white';eyeSelEl3.style.color=f.fg||'var(--ink)';} }
      }
      // 肌色復元
      let skinHid = document.getElementById(`chara_skin_${i}`);
      if(skinHid){
        skinHid.value = ch['skin']||'';
        const skinSelEl2 = skinHid.parentElement?.querySelector('select');
        if(skinSelEl2){ skinSelEl2.value=ch['skin']||''; const f=SKIN_OPTIONS.find(c=>c.v===(ch['skin']||'')); if(f?.bg){skinSelEl2.style.backgroundColor=f.bg;skinSelEl2.style.color=f.fg||'var(--ink)';} }
        let skinOtherEl = document.getElementById(`chara_skin_other_${i}`);
        let isPreset = SKIN_OPTIONS.some(o=>o.v===ch['skin']);
        if(isPreset){
          document.querySelectorAll(`#chara_${i} [data-skin]`).forEach(b=>{
            b.classList.toggle('active', b.dataset.skin===(ch['skin']||''));
          });
          if(skinOtherEl) skinOtherEl.value = '';
        } else if(ch['skin']){
          if(skinOtherEl) skinOtherEl.value = ch['skinOther']||ch['skin']||'';
          document.querySelectorAll(`#chara_${i} [data-skin]`).forEach(b=>b.classList.remove('active'));
        }
      }
      // 詳細欄を自動展開（入力があれば）
      const hasDetail = ['outfit','action','hair','eyes','skin','body','misc','bust'].some(f=>ch[f]);
      if(hasDetail){
        const opt = document.getElementById('chara_opt_'+i);
        const btn = opt?.previousElementSibling?.querySelector('.chara-expand');
        if(opt && opt.style.display==='none'){ opt.style.display='block'; if(btn) btn.textContent='－ 詳細'; }
      }
      // 自由入力欄の復元
      const hairStyleFreeEl = document.getElementById(`chara_hairstyle_free_${i}`);
      if(hairStyleFreeEl && ch['hairstyle_free']) hairStyleFreeEl.value = ch['hairstyle_free'];
      const hairOtherEl = document.getElementById(`chara_hairother_${i}`);
      if(hairOtherEl && ch['hairother']) hairOtherEl.value = ch['hairother'];
      const actionFreeEl = document.getElementById(`chara_action_free_${i}`);
      if(actionFreeEl && ch['action_free']) actionFreeEl.value = ch['action_free'];
      const itemFreeEl = document.getElementById(`chara_item_free_${i}`);
      if(itemFreeEl && ch['item_free']) itemFreeEl.value = ch['item_free'];
    });
    // シーン
    document.getElementById('f_place').value = data.place||'';
    document.getElementById('f_misc').value  = data.misc||'';
    ['world','outdoor','tod','weather'].forEach(g=>{
      const val = data[g]||'';
      const hid = document.getElementById('f_'+g);
      if(hid) hid.value = val;
      document.querySelectorAll(`[data-${g}]`).forEach(b=>{
        b.classList.toggle('active', (b.dataset[g]||'')=== val);
      });
    });
    // 補足・英語追記
    document.getElementById('extraNoteJa').value = data.extraNoteJa||'';
    document.getElementById('extraNoteEn').value = data.extraNoteEn||'';
    // Extraタグ
    extraTags = new Set(data.extraTags||[]);
    if(data.negExtraPresetList){ negExtraPresetList = data.negExtraPresetList; }
    negExtraTags = new Set(data.negExtraTags||[]);
    renderNegExtraPresets();
    renderNegExtraBadges();
    if(data.negExtraNoteEn !== undefined){ const el=document.getElementById('negExtraNoteEn'); if(el) el.value=data.negExtraNoteEn; }
    if(data.negStylePresetList){ negStylePresetList = data.negStylePresetList; }
    negStyleTags = data.negStyleTags||[];
    renderNegStylePresets();
    renderNegStyleBadges();
    if(data.selectedNegSafety !== undefined){
      selectedNegSafety = data.selectedNegSafety;
      document.querySelectorAll('#neg_safety_btns .safety-btn').forEach(b=>{
        b.classList.toggle('active', b.dataset.ns===selectedNegSafety);
      });
    }
    renderExtraBadges();
    // スタイル
    styleTags = data.styleTags||[];
    if(data.stylePresetList) stylePresetList = data.stylePresetList;
    renderStylePresets();
    renderStyleBadges();
    // 期間
    selectedPeriod = data.selectedPeriod||'';
    document.querySelectorAll('.period-btn[data-p]').forEach(b=>{
      b.classList.toggle('active', b.dataset.p===selectedPeriod);
    });
    if(data.year) document.getElementById('yearInput').value = data.year;
    // 安全タグ
    selectedSafety = data.selectedSafety||'';
    document.querySelectorAll('.safety-btn').forEach(b=>{
      b.classList.toggle('active', b.dataset.s===selectedSafety);
    });
    // 品質・メタタグ（チェックボックス）
    function applyChecks(containerId, checked){
      document.querySelectorAll(`#${containerId} input[type=checkbox]`).forEach(cb=>{
        cb.checked = checked.includes(cb.dataset.tag);
      });
    }
    if(data.qualityHuman) applyChecks('qualityHuman', data.qualityHuman);
    if(data.qualityPony)  applyChecks('qualityPony',  data.qualityPony);
    if(data.metaTags)     applyChecks('metaTags',     data.metaTags);
    // 生成済みプロンプトを復元
    if(data.lmPrompt){
      lastPositivePrompt = data.lmPrompt;
      document.getElementById('lmLabel').style.display='block';
      const po = document.getElementById('promptOutput');
      po.textContent = data.lmPrompt;
      po.classList.add('show');
      document.getElementById('statusBox').classList.add('show');
    }
    if(data.finalPrompt){
      document.getElementById('finalLabel').style.display='block';
      const pf = document.getElementById('promptFinal');
      pf.textContent = data.finalPrompt;
      pf.style.display='block';
    }
    if(data.negFinalPrompt){
      document.getElementById('negFinalLabel').style.display='block';
      const nf = document.getElementById('promptNegFinal');
      nf.textContent = data.negFinalPrompt;
      nf.style.display='block';
    }
    if(data.lmPrompt){ document.getElementById('regenBtn').classList.add('show'); running=false; document.getElementById('btn').disabled=false; }
    // 画像サイズ・フォーマット・枚数
    if(data.imgW){ selectedW=data.imgW; document.getElementById('widthInput').value=data.imgW; }
    if(data.imgH){ selectedH=data.imgH; document.getElementById('heightInput').value=data.imgH; }
    if(data.imgFmt){ selectedFmt=data.imgFmt; document.querySelectorAll('.fmt-btn').forEach(b=>b.classList.toggle('active',b.dataset.fmt===data.imgFmt)); }
    if(data.imgCount){ selectedCount=data.imgCount; const ce=document.getElementById('countInput'); if(ce) ce.value=data.imgCount; }
  }, 50);
}

// ===== 品質・メタ・安全タグ管理 =====
const QUALITY_HUMAN = __OPT__.quality_human.tags;
const QUALITY_HUMAN_DEFAULT = new Set(__OPT__.quality_human.default);
const QUALITY_PONY = __OPT__.quality_pony.tags;
const QUALITY_PONY_DEFAULT = new Set(__OPT__.quality_pony.default);
const META_TAGS = __OPT__.meta_tags.tags;
const META_DEFAULT = new Set(__OPT__.meta_tags.default);
let selectedSafety = '';

function makeTagCheck(tag, checked){
  const wrap = document.createElement('label');
  wrap.className = 'tag-check';
  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.checked = checked;
  cb.dataset.tag = tag;
  wrap.appendChild(cb);
  wrap.appendChild(document.createTextNode(tag));
  return wrap;
}

function initQualityMeta(){
  const qh = document.getElementById('qualityHuman');
  QUALITY_HUMAN.forEach(t=> qh.appendChild(makeTagCheck(t, QUALITY_HUMAN_DEFAULT.has(t))));
  const qp = document.getElementById('qualityPony');
  QUALITY_PONY.forEach(t=> qp.appendChild(makeTagCheck(t, QUALITY_PONY_DEFAULT.has(t))));
  const mt = document.getElementById('metaTags');
  META_TAGS.forEach(t=> mt.appendChild(makeTagCheck(t, META_DEFAULT.has(t))));
  // 安全タグ初期「なし」選択
  document.querySelector('.safety-btn[data-s=""]')?.classList.add('active');
}

function initQualityMetaNeg(){
  const NEG_HUMAN = __OPT__.quality_human_neg ? __OPT__.quality_human_neg.tags : ['normal quality','low quality','worst quality'];
  const NEG_HUMAN_DEF = new Set(__OPT__.quality_human_neg ? __OPT__.quality_human_neg.default : ['normal quality','low quality','worst quality']);
  const qhn = document.getElementById('qualityHumanNeg');
  if(qhn) NEG_HUMAN.forEach(t=> qhn.appendChild(makeTagCheck(t, NEG_HUMAN_DEF.has(t))));
  // Ponyネガティブ（score_4〜score_1をデフォルトON、ui_options.jsonで変更可）
  const NEG_PONY_DEFAULT = new Set(__OPT__.quality_pony_neg ? __OPT__.quality_pony_neg.default : ['score_4','score_3','score_2','score_1']);
  const NEG_PONY_TAGS = __OPT__.quality_pony_neg ? __OPT__.quality_pony_neg.tags : QUALITY_PONY;
  const qpn = document.getElementById('qualityPonyNeg');
  if(qpn) NEG_PONY_TAGS.forEach(t=> qpn.appendChild(makeTagCheck(t, NEG_PONY_DEFAULT.has(t))));
  // メタネガティブ（デフォルト全OFF）
  const mtn = document.getElementById('metaTagsNeg');
  if(mtn) META_TAGS.forEach(t=> mtn.appendChild(makeTagCheck(t, false)));
}

function selSafety(el){
  document.querySelectorAll('.safety-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  selectedSafety = el.dataset.s;
}

function collectCheckedTags(containerId){
  return Array.from(document.querySelectorAll(`#${containerId} input[type=checkbox]:checked`))
    .map(cb=>cb.dataset.tag);
}

function collectPromptPrefix(){
  // Animaタグ順: [year] [period] [quality] [meta] [safety] [@style]
  const parts = [];
  const year = document.getElementById('yearInput')?.value.trim();
  if(year) parts.push('year '+year);
  if(selectedPeriod) parts.push(selectedPeriod);
  const qh = collectCheckedTags('qualityHuman');
  const qp = collectCheckedTags('qualityPony');
  parts.push(...qh, ...qp);
  const mt = collectCheckedTags('metaTags');
  parts.push(...mt);
  if(selectedSafety) parts.push(selectedSafety);
  parts.push(...styleTags);
  return parts;
}

// ===== スタイル・期間タグ管理 =====
// スタイルタグ: presetList=保存済一覧, styleTags=現在選択中
let stylePresetList = [];
let styleTags = [];
let selectedPeriod = '';

async function saveStylePresetsToServer(){
  try{ await fetch('/style_tags',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tags:stylePresetList})}); }catch(e){}
}

async function loadStyleTagsFromServer(){
  try{
    const r = await fetch('/style_tags');
    const d = await r.json();
    stylePresetList = d.tags||[];
    renderStylePresets();
    renderStyleBadges();
  }catch(e){}
}

function addStyle(){
  const input = document.getElementById('styleInput');
  const raw = input.value.trim();
  if(!raw) return;
  const tag = raw.startsWith('@') ? raw : '@'+raw;
  // プリセット一覧に追加（未登録なら）
  if(!stylePresetList.includes(tag)){
    stylePresetList.push(tag);
    saveStylePresetsToServer();
  }
  // 現在選択にも追加
  if(!styleTags.includes(tag)) styleTags.push(tag);
  input.value = '';
  renderStylePresets();
  renderStyleBadges();
}

function renderStylePresets(){
  const container = document.getElementById('stylePresets');
  if(!container) return;
  container.innerHTML = '';
  stylePresetList.forEach(tag=>{
    const btn = document.createElement('div');
    const isActive = styleTags.includes(tag);
    btn.className = 'extra-preset-btn' + (isActive ? ' active' : '');
    btn.textContent = tag;
    // 左クリック: ON/OFF
    btn.addEventListener('click', ()=>{
      if(styleTags.includes(tag)){
        styleTags = styleTags.filter(t=>t!==tag);
      } else {
        styleTags.push(tag);
      }
      renderStylePresets();
      renderStyleBadges();
    });
    // 右クリック: プリセットから削除
    btn.addEventListener('contextmenu', e=>{
      e.preventDefault();
      stylePresetList = stylePresetList.filter(t=>t!==tag);
      styleTags = styleTags.filter(t=>t!==tag);
      saveStylePresetsToServer();
      renderStylePresets();
      renderStyleBadges();
    });
    container.appendChild(btn);
  });
}

function renderStyleBadges(){
  const container = document.getElementById('styleBadges');
  if(!container) return;
  container.innerHTML = '';
  styleTags.forEach(tag=>{
    const badge = document.createElement('div');
    badge.className = 'style-badge';
    badge.innerHTML = tag + ' <span style="cursor:pointer;">×</span>';
    badge.querySelector('span').addEventListener('click', e=>{
      e.stopPropagation();
      styleTags = styleTags.filter(t=>t!==tag);
      renderStylePresets();
      renderStyleBadges();
    });
    container.appendChild(badge);
  });
}

// ===== ネガティブ 安全タグ =====
let selectedNegSafety = '';

function initNegSafetyButtons(){
  const container = document.getElementById('neg_safety_btns');
  if(!container) return;
  (__OPT__.safety_options||[]).forEach(({v,label})=>{
    const btn = document.createElement('div');
    btn.className = 'safety-btn' + (v==='' ? ' active' : '');
    btn.dataset.ns = v;
    btn.textContent = label;
    btn.addEventListener('click', ()=>selNegSafety(btn));
    container.appendChild(btn);
  });
}

function selNegSafety(el){
  document.querySelectorAll('#neg_safety_btns .safety-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  selectedNegSafety = el.dataset.ns;
}

// ===== ネガティブ スタイルタグ =====
let negStylePresetList = [];
let negStyleTags = [];

async function loadNegStyleTagsFromServer(){
  try{
    const r = await fetch('/neg_style_tags');
    const d = await r.json();
    negStylePresetList = d.tags||[];
    renderNegStylePresets();
    renderNegStyleBadges();
  }catch(e){}
}

async function saveNegStylePresetsToServer(){
  try{ await fetch('/neg_style_tags',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tags:negStylePresetList})}); }catch(e){}
}

function addNegStyle(){
  const input = document.getElementById('negStyleInput');
  const raw = (input.value||'').trim();
  if(!raw) return;
  const tag = raw.startsWith('@') ? raw : '@'+raw;
  if(!negStylePresetList.includes(tag)){
    negStylePresetList.push(tag);
    saveNegStylePresetsToServer();
  }
  if(!negStyleTags.includes(tag)) negStyleTags.push(tag);
  input.value = '';
  renderNegStylePresets();
  renderNegStyleBadges();
}

function renderNegStylePresets(){
  const container = document.getElementById('negStylePresets');
  if(!container) return;
  container.innerHTML = '';
  negStylePresetList.forEach(tag=>{
    const btn = document.createElement('div');
    const isActive = negStyleTags.includes(tag);
    btn.className = 'extra-preset-btn' + (isActive ? ' active' : '');
    btn.textContent = tag;
    btn.addEventListener('click', ()=>{
      if(negStyleTags.includes(tag)) negStyleTags = negStyleTags.filter(t=>t!==tag);
      else negStyleTags.push(tag);
      renderNegStylePresets();
      renderNegStyleBadges();
    });
    btn.addEventListener('contextmenu', e=>{
      e.preventDefault();
      negStylePresetList = negStylePresetList.filter(t=>t!==tag);
      negStyleTags = negStyleTags.filter(t=>t!==tag);
      saveNegStylePresetsToServer();
      renderNegStylePresets();
      renderNegStyleBadges();
    });
    container.appendChild(btn);
  });
}

function renderNegStyleBadges(){
  const container = document.getElementById('negStyleBadges');
  if(!container) return;
  container.innerHTML = '';
  negStyleTags.forEach(tag=>{
    const badge = document.createElement('div');
    badge.className = 'style-badge';
    badge.innerHTML = tag + ' <span style="cursor:pointer;">×</span>';
    badge.querySelector('span').addEventListener('click', e=>{
      e.stopPropagation();
      negStyleTags = negStyleTags.filter(t=>t!==tag);
      renderNegStylePresets();
      renderNegStyleBadges();
    });
    container.appendChild(badge);
  });
}

function toggleNegContent(){
  const el = document.getElementById('negContent');
  const open = el.style.display === 'none';
  el.style.display = open ? '' : 'none';
  document.getElementById('negContentArrow').textContent = open ? '▼' : '▶';
}

// ===== ネガティブ Extraタグ管理 =====
let negExtraTags = new Set();
let negExtraPresetList = [];

async function loadNegExtraTagsFromServer(){
  try{
    const r = await fetch('/neg_extra_tags');
    const d = await r.json();
    const tags = d.tags||[];
    negExtraPresetList = tags;
    // extra_tags_negative.jsonが存在しない初回のみ全タグON
    if(d.is_default){
      tags.forEach(t => negExtraTags.add(t));
    }
    renderNegExtraPresets();
    renderNegExtraBadges();
  }catch(e){}
}

async function saveNegExtraTagsToServer(){
  try{ await fetch('/neg_extra_tags',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tags:negExtraPresetList})}); }catch(e){}
}

function initNegExtraPresets(){
  loadNegExtraTagsFromServer();
  const inp = document.getElementById('negExtraCustomInput');
  if(inp) inp.addEventListener('keydown', e=>{ if(e.key==='Enter') addNegCustomTag(); });
}

function addNegCustomTag(){
  const inp = document.getElementById('negExtraCustomInput');
  const tag = (inp.value||'').trim();
  if(!tag) return;
  if(!negExtraPresetList.includes(tag)){
    negExtraPresetList.push(tag);
    saveNegExtraTagsToServer();
  }
  negExtraTags.add(tag);
  inp.value = '';
  renderNegExtraPresets();
  renderNegExtraBadges();
}

function renderNegExtraPresets(){
  const container = document.getElementById('negExtraPresets');
  if(!container) return;
  container.innerHTML = '';
  negExtraPresetList.forEach(tag=>{
    const btn = document.createElement('div');
    btn.className = 'extra-preset-btn' + (negExtraTags.has(tag) ? ' active' : '');
    btn.textContent = tag;
    btn.addEventListener('click', ()=>{
      negExtraTags.has(tag) ? negExtraTags.delete(tag) : negExtraTags.add(tag);
      renderNegExtraPresets();
      renderNegExtraBadges();
    });
    btn.addEventListener('contextmenu', e=>{
      e.preventDefault();
      negExtraPresetList = negExtraPresetList.filter(t=>t!==tag);
      negExtraTags.delete(tag);
      saveNegExtraTagsToServer();
      renderNegExtraPresets();
      renderNegExtraBadges();
    });
    container.appendChild(btn);
  });
}

function renderNegExtraBadges(){
  const container = document.getElementById('negExtraBadges');
  if(!container) return;
  container.innerHTML = '';
  negExtraTags.forEach(tag=>{
    const badge = document.createElement('div');
    badge.className = 'extra-badge';
    badge.innerHTML = tag + ' <span style="cursor:pointer;">×</span>';
    badge.querySelector('span').addEventListener('click', e=>{
      e.stopPropagation();
      negExtraTags.delete(tag);
      renderNegExtraPresets();
      renderNegExtraBadges();
    });
    container.appendChild(badge);
  });
}

// ===== ネガティブプロンプト組み立て =====
function collectNegativePrompt(){
  const parts = [];
  // ① 期間タグ（ポジティブと共通）
  if(selectedPeriod) parts.push(selectedPeriod);
  // ② 品質タグ
  function collectCheckedNeg(id){ return Array.from(document.querySelectorAll(`#${id} input[type=checkbox]:checked`)).map(cb=>cb.dataset.tag); }
  parts.push(...collectCheckedNeg('qualityHumanNeg'));
  parts.push(...collectCheckedNeg('qualityPonyNeg'));
  // ③ メタタグ
  parts.push(...collectCheckedNeg('metaTagsNeg'));
  // ④ 安全タグ（ネガティブ独立）
  if(selectedNegSafety) parts.push(selectedNegSafety);
  // ⑤ スタイル（ネガティブ独立）
  parts.push(...negStyleTags);
  // ⑥ Extraタグ
  parts.push(...negExtraTags);
  // ⑦ 追記文
  const note = (document.getElementById('negExtraNoteEn')||{}).value||'';
  if(note.trim()) parts.push(note.trim());
  return parts.filter(Boolean).join(', ');
}

function selPeriod(el){
  document.querySelectorAll('.period-btn[data-p]').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  selectedPeriod = el.dataset.p;
}

document.addEventListener('DOMContentLoaded', ()=>{
  document.getElementById('styleInput')?.addEventListener('keydown', e=>{ if(e.key==='Enter') addStyle(); });
  document.getElementById('negStyleInput')?.addEventListener('keydown', e=>{ if(e.key==='Enter') addNegStyle(); });
  // 「なし」を初期選択
  document.querySelector('.period-btn[data-p=""]')?.classList.add('active');
});

// ===== Extraタグ管理 =====
let extraTags = new Set();
let extraPresetList = [];

function buildPresetButtons(){
  const container = document.getElementById('extraPresets');
  container.innerHTML = '';
  extraPresetList.forEach(tag=>{
    const btn = document.createElement('div');
    btn.className = 'preset-btn' + (extraTags.has(tag)?' active':'');
    btn.textContent = tag;
    btn.addEventListener('click', ()=>{
      if(extraTags.has(tag)){
        extraTags.delete(tag);
        btn.classList.remove('active');
      } else {
        extraTags.add(tag);
        btn.classList.add('active');
      }
      renderExtraBadges();
    });
    // 右クリックで削除
    btn.addEventListener('contextmenu', e=>{
      e.preventDefault();
      if(confirm(`"${tag}" をリストから削除しますか？`)){
        extraPresetList = extraPresetList.filter(t=>t!==tag);
        extraTags.delete(tag);
        saveExtraTagsToServer();
        buildPresetButtons();
        renderExtraBadges();
      }
    });
    container.appendChild(btn);
  });
}

async function initExtraPresets(){
  try{
    const res = await fetch('/extra_tags');
    const data = await res.json();
    extraPresetList = data.tags || [];
  } catch(e){
    extraPresetList = [];
  }
  buildPresetButtons();
}

async function saveExtraTagsToServer(){
  await fetch('/extra_tags',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({tags: extraPresetList})
  });
}

function addCustomTag(){
  const input = document.getElementById('extraCustomInput');
  const tag = input.value.trim().toLowerCase().replace(/\s+/g,'_');
  if(!tag) return;
  // プリセットになければ追加して保存
  if(!extraPresetList.includes(tag)){
    extraPresetList.push(tag);
    saveExtraTagsToServer();
    buildPresetButtons();
  }
  extraTags.add(tag);
  input.value = '';
  renderExtraBadges();
}

function renderExtraBadges(){
  const container = document.getElementById('extraBadges');
  container.innerHTML = '';
  extraTags.forEach(tag=>{
    const badge = document.createElement('div');
    badge.className = 'extra-badge';
    badge.innerHTML = tag + ' <span>×</span>';
    badge.addEventListener('click', ()=>{
      extraTags.delete(tag);
      // プリセットボタンのactiveも解除
      document.querySelectorAll('.preset-btn').forEach(b=>{
        if(b.textContent===tag) b.classList.remove('active');
      });
      renderExtraBadges();
    });
    container.appendChild(badge);
  });
}



document.getElementById('extraCustomInput')?.addEventListener('keydown', e=>{
  if(e.key==='Enter') addCustomTag();
});

// ===== キャラブロック管理 =====
const OPT_FIELDS = [
  // outfit, hair, body, eyes, skin, action は専用UIで処理
  {id:'misc',   label:'その他',        ph:'例: 頬を染めている、笑顔'},
];
const HAIR_COLORS = __OPT__.hair_colors;
const ACTION_OPTIONS = __OPT__.action_options;

const POS_VERTICAL   = __OPT__.pos_vertical;
const POS_HORIZONTAL = __OPT__.pos_horizontal;
const POS_CAMERA     = __OPT__.pos_camera;

const BODY_HEIGHT = __OPT__.body_height;
const BODY_BUILD  = __OPT__.body_build;
const BODY_LEGS   = __OPT__.body_legs;
// Danbooruタグ直接変換マップ
// 年齢直接タグ（LMチェックOFF時: gender+ageで決定）
// female+child→loli, male+child→shota, adult→no tag (モデル依存なので空)
const AGE_TAG_MAP = {
  female: {adult:'', child:'loli'},
  male:   {adult:'', child:'shota'},
  other:  {adult:'', child:''},
};

const FACE_OPTIONS = __OPT__.face_options;

const EYE_STATE_OPTIONS = __OPT__.eye_state_options;

const MOUTH_OPTIONS = __OPT__.mouth_options;

const EFFECT_OPTIONS = __OPT__.effect_options;

const HAIRSTYLE_OPTIONS = __OPT__.hairstyle_options;

const ITEM_CATEGORIES = __OPT__.item_categories;

const EARS_OPTIONS = __OPT__.ears_options;
const TAIL_OPTIONS = __OPT__.tail_options;
const WINGS_OPTIONS = __OPT__.wings_options;
const ACCESSORY_OPTIONS = __OPT__.accessory_options;

const BUST_OPTIONS = __OPT__.bust_options;
const SKIN_OPTIONS = __OPT__.skin_options;
const EYE_COLORS = __OPT__.eye_colors;

function makeLabelDiv(text){
  const d = document.createElement('div');
  d.style.fontFamily = 'DM Mono, monospace';
  d.style.fontSize = '0.72rem';
  d.style.color = 'var(--muted)';
  d.style.marginBottom = '0.2rem';
  d.textContent = text;
  return d;
}

function makeCharaBlock(idx){
  const n = idx+1;
  const div = document.createElement('div');
  div.className = 'chara-block';
  div.id = 'chara_'+idx;

  // ヘッダー（2行構造）
  const header = document.createElement('div');
  header.className = 'chara-header';

  // --- 1行目: キャラ番号 / キャラ名 / 作品名 / 詳細ボタン ---
  const row1 = document.createElement('div');
  row1.className = 'chara-header-row1';

  const num = document.createElement('span');
  num.className = 'chara-num';
  num.textContent = 'キャラ '+n;

  // キャラ名
  const nameWrap = document.createElement('div');
  nameWrap.appendChild(makeLabelDiv('キャラ名 *'));
  const nameInput = document.createElement('input');
  nameInput.type = 'text';
  nameInput.id = 'chara_name_'+idx;
  nameInput.placeholder = '例: スペシャルウィーク';
  nameInput.className = 'inp-ja';
  nameInput.style.cssText = 'width:100%;background:#f8f4ff;border:1px solid var(--accent);border-radius:5px;padding:0.45rem 0.6rem;font-family:DM Mono,monospace;font-size:0.78rem;color:var(--ink);outline:none;box-sizing:border-box;';
  nameWrap.appendChild(nameInput);

  // 作品名
  const seriesWrap = document.createElement('div');
  seriesWrap.appendChild(makeLabelDiv('作品名'));
  const seriesInnerWrap = document.createElement('div');
  seriesInnerWrap.style.cssText = 'display:flex;gap:0.3rem;align-items:center;';
  const seriesInput = document.createElement('input');
  seriesInput.type = 'text';
  seriesInput.id = 'chara_series_'+idx;
  seriesInput.placeholder = '例: ウマ娘、ブルアカ';
  seriesInput.className = 'inp-ja';
  seriesInput.style.cssText = 'flex:1;min-width:0;background:white;border:1px solid var(--border);border-radius:5px;padding:0.45rem 0.6rem;font-family:DM Mono,monospace;font-size:0.78rem;color:var(--ink);outline:none;box-sizing:border-box;';

  // オリジナルボタン
  const origBtn = document.createElement('div');
  origBtn.className = 'age-btn';
  origBtn.id = 'chara_orig_'+idx;
  origBtn.textContent = 'オリジナル';
  origBtn.style.cssText = 'flex-shrink:0;font-size:0.7rem;white-space:nowrap;';
  origBtn.addEventListener('click', function(){
    const isOrig = !this.classList.contains('active');
    this.classList.toggle('active', isOrig);
    // 作品名欄
    seriesInput.disabled = isOrig;
    seriesInput.style.opacity = isOrig ? '0.4' : '1';
    if(isOrig) seriesInput.value = '';
    // LLMチェック欄を一括ON/OFF＋表示切替
    div.querySelectorAll('.lm-check-wrap').forEach(w=>{
      const cb = w.querySelector('input[type="checkbox"]');
      if(cb) cb.checked = false;
      w.style.display = isOrig ? 'none' : '';
    });
  });

  seriesInnerWrap.appendChild(seriesInput);
  seriesInnerWrap.appendChild(origBtn);
  seriesWrap.appendChild(seriesInnerWrap);

  // 詳細ボタン
  const expandBtn = document.createElement('button');
  expandBtn.className = 'chara-expand';
  expandBtn.textContent = '＋ 詳細';

  row1.appendChild(num);
  row1.appendChild(nameWrap);
  row1.appendChild(seriesWrap);
  row1.appendChild(expandBtn);

  // --- 2行目: 性別 / 年齢 ---
  const row2 = document.createElement('div');
  row2.className = 'chara-header-row2';

  // 性別
  const genderGroup = document.createElement('div');
  genderGroup.className = 'chara-attr-group';
  const genderLabelWrap = document.createElement('div');
  genderLabelWrap.style.cssText = 'display:flex;align-items:center;gap:0.25rem;';
  const genderLabel = document.createElement('div');
  genderLabel.className = 'chara-attr-label';
  genderLabel.textContent = '性別 *';
  const genderLMcb = document.createElement('input');
  genderLMcb.type = 'checkbox';
  genderLMcb.id = 'chara_gender_lm_'+idx;
  genderLMcb.checked = true;
  genderLMcb.style.cssText = 'width:10px;height:10px;accent-color:var(--multi);cursor:pointer;margin:0;';
  const genderLMlbl = document.createElement('label');
  genderLMlbl.htmlFor = 'chara_gender_lm_'+idx;
  genderLMlbl.style.cssText = 'font-family:DM Mono,monospace;font-size:0.6rem;color:var(--muted);cursor:pointer;user-select:none;';
  genderLMlbl.textContent = 'LLM';
  genderLabelWrap.appendChild(genderLabel);
  genderLabelWrap.appendChild(genderLMcb);
  genderLabelWrap.appendChild(genderLMlbl);
  const genderRow = document.createElement('div');
  genderRow.className = 'gender-row chara-attr-btns';
  (__OPT__.gender_options||[['female','女'],['male','男'],['other','不明']].map(([v,label])=>({v,label}))).forEach(({v:g,label},i)=>{
    const btn = document.createElement('div');
    btn.className = 'gender-btn' + (i===0?' active':'');
    btn.dataset.g = g;
    btn.textContent = label;
    btn.addEventListener('click', function(){
      this.closest('.chara-attr-btns').querySelectorAll('.gender-btn').forEach(b=>b.classList.remove('active'));
      this.classList.add('active');
    });
    genderRow.appendChild(btn);
  });
  genderGroup.appendChild(genderLabelWrap);
  genderGroup.appendChild(genderRow);

  // 年齢
  const ageGroup = document.createElement('div');
  ageGroup.className = 'chara-attr-group';
  const ageLabelWrap = document.createElement('div');
  ageLabelWrap.style.cssText = 'display:flex;align-items:center;gap:0.25rem;';
  const ageLabel = document.createElement('div');
  ageLabel.className = 'chara-attr-label';
  ageLabel.textContent = '年齢';
  const ageLMcb = document.createElement('input');
  ageLMcb.type = 'checkbox';
  ageLMcb.id = 'chara_age_lm_'+idx;
  ageLMcb.checked = true;
  ageLMcb.style.cssText = 'width:10px;height:10px;accent-color:var(--multi);cursor:pointer;margin:0;';
  const ageLMlbl = document.createElement('label');
  ageLMlbl.htmlFor = 'chara_age_lm_'+idx;
  ageLMlbl.style.cssText = 'font-family:DM Mono,monospace;font-size:0.6rem;color:var(--muted);cursor:pointer;user-select:none;';
  ageLMlbl.textContent = 'LLM';
  ageLabelWrap.appendChild(ageLabel);
  ageLabelWrap.appendChild(ageLMcb);
  ageLabelWrap.appendChild(ageLMlbl);
  const ageRow = document.createElement('div');
  ageRow.className = 'age-row chara-attr-btns';
  (__OPT__.age_options||[['unset','未選択'],['adult','大人'],['child','子供']].map(([v,label])=>({v,label}))).forEach(({v:a,label},i)=>{
    const btn = document.createElement('div');
    btn.className = 'age-btn' + (i===0?' active':'');
    btn.dataset.a = a;
    btn.textContent = label;
    btn.addEventListener('click', function(){
      this.closest('.chara-attr-btns').querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
      this.classList.add('active');
    });
    ageRow.appendChild(btn);
  });
  ageGroup.appendChild(ageLabelWrap);
  ageGroup.appendChild(ageRow);

  row2.appendChild(genderGroup);
  row2.appendChild(ageGroup);

  // --- プリセット行（キャラブロック内）---
  const charaPresetRow = document.createElement('div');
  charaPresetRow.style.cssText = 'margin-bottom:0.4rem;';
  // 1行: キャラN + select + 読込 + 保存
  const cpRow1 = document.createElement('div');
  cpRow1.style.cssText = 'display:flex;gap:0.3rem;align-items:center;';
  const cpNumLbl = document.createElement('span');
  cpNumLbl.style.cssText = 'font-family:DM Mono,monospace;font-size:0.7rem;color:var(--muted);white-space:nowrap;';
  cpNumLbl.textContent = 'キャラ'+n;
  const charaPresetSel = document.createElement('select');
  charaPresetSel.id = 'chara_preset_sel_'+idx;
  charaPresetSel.style.cssText = 'flex:1;min-width:0;font-family:DM Mono,monospace;font-size:0.72rem;border:1px solid var(--accent);border-radius:5px;padding:0.28rem 0.45rem;background:white;color:var(--ink);cursor:pointer;';
  charaPresetSel.innerHTML = '<option value="">── プリセット選択 ──</option>';
  charaPresets.forEach((p,i)=>{ const o=document.createElement('option'); o.value=i; o.textContent=p.name; charaPresetSel.appendChild(o); });
  const charaPresetLoadBtn = document.createElement('button');
  charaPresetLoadBtn.textContent = '読込';
  charaPresetLoadBtn.style.cssText = 'font-family:DM Mono,monospace;font-size:0.7rem;padding:0.28rem 0;width:2.8rem;text-align:center;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;';
  charaPresetLoadBtn.onclick = ()=>loadCharaPreset(idx);
  const charaPresetSaveBtn = document.createElement('button');
  charaPresetSaveBtn.textContent = '保存';
  charaPresetSaveBtn.style.cssText = 'font-family:DM Mono,monospace;font-size:0.7rem;padding:0.28rem 0;width:2.8rem;text-align:center;border:1px solid var(--accent);border-radius:5px;background:white;color:var(--accent);cursor:pointer;';
  charaPresetSaveBtn.onclick = ()=>saveCharaPreset(idx);
  const charaPresetAutoBtn = document.createElement('button');
  charaPresetAutoBtn.textContent = '🔍';
  charaPresetAutoBtn.title = 'Danbooru Wiki+LLMでプリセット自動生成';
  charaPresetAutoBtn.style.cssText = 'font-family:DM Mono,monospace;font-size:0.7rem;padding:0.28rem 0;width:2.8rem;text-align:center;border:1px solid #3a8c5c;border-radius:5px;background:white;color:#3a8c5c;cursor:pointer;';
  charaPresetAutoBtn.onclick = ()=>generateCharaPreset(idx);
  cpRow1.appendChild(cpNumLbl);
  cpRow1.appendChild(charaPresetSel);
  cpRow1.appendChild(charaPresetLoadBtn);
  cpRow1.appendChild(charaPresetSaveBtn);
  cpRow1.appendChild(charaPresetAutoBtn);
  charaPresetRow.appendChild(cpRow1);

  header.appendChild(charaPresetRow);
  header.appendChild(row1);
  header.appendChild(row2);
  div.appendChild(header);

  // 任意フィールド（初期非表示）
  const opt = document.createElement('div');
  opt.className = 'chara-optional';
  opt.id = 'chara_opt_'+idx;
  opt.style.display = 'none';
  OPT_FIELDS.forEach(f=>{
    const row = document.createElement('div');
    row.className = 'opt-row';
    const label = document.createElement('label');
    label.className = 'opt-label';
    label.textContent = f.label;
    const input = document.createElement('input');
    input.type = 'text';
    input.id = 'chara_'+f.id+'_'+idx;
    input.placeholder = f.ph;
    row.appendChild(label);
    row.appendChild(input);
    //rows appended below
  });

  // バスト行（女性のみ表示）
  const bustRow = document.createElement('div');
  bustRow.className = 'opt-row';
  bustRow.id = 'chara_bust_row_'+idx;
  const bustLabel = document.createElement('label');
  bustLabel.className = 'opt-label';
  bustLabel.textContent = '⑨ バスト';
  const bustLabelWrap = document.createElement('div');
  bustLabelWrap.className = 'opt-label-wrap';
  bustLabelWrap.appendChild(bustLabel);
  bustLabelWrap.appendChild(makeLMCheckbox('chara_bust_lm_'+idx, false));
  const bustBtns = document.createElement('div');
  bustBtns.style.cssText = 'display:flex;gap:0.25rem;flex-wrap:wrap;';
  BUST_OPTIONS.forEach(({v,label})=>{
    const btn = document.createElement('div');
    btn.className = 'age-btn' + (v===''?' active':'');
    btn.dataset.bust = v;
    btn.textContent = label;
    btn.addEventListener('click', function(){
      bustBtns.querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
      this.classList.add('active');
      document.getElementById('chara_bust_'+idx).value = v;
    });
    bustBtns.appendChild(btn);
  });
  // hidden input for value collection
  const bustHidden = document.createElement('input');
  bustHidden.type = 'hidden';
  bustHidden.id = 'chara_bust_'+idx;
  bustHidden.value = '';
  bustRow.appendChild(bustLabelWrap);
  bustRow.appendChild(bustBtns);
  bustRow.appendChild(bustHidden);

  // 肌の色行（ボタン＋その他テキスト）
  const skinRow = document.createElement('div');
  skinRow.className = 'opt-row';
  const skinLabel = document.createElement('label');
  skinLabel.className = 'opt-label';
  skinLabel.textContent = '⑦ 肌の色';
  const skinLabelWrap = document.createElement('div');
  skinLabelWrap.className = 'opt-label-wrap';
  skinLabelWrap.appendChild(skinLabel);
  skinLabelWrap.appendChild(makeLMCheckbox('chara_skin_lm_'+idx, false));
  const skinWrap = document.createElement('div');
  skinWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.3rem;width:100%;';
  const skinHidden = document.createElement('input');
  skinHidden.type = 'hidden';
  skinHidden.id = 'chara_skin_'+idx;
  skinHidden.value = '';
  const skinSel = document.createElement('select');
  skinSel.style.cssText = 'font-family:DM Mono,monospace;font-size:0.75rem;border:1px solid var(--border);border-radius:5px;padding:0.3rem 0.5rem;background:white;color:var(--ink);cursor:pointer;width:100%;';
  SKIN_OPTIONS.forEach(({v,label,bg,fg})=>{
    const opt = document.createElement('option');
    opt.value = v; opt.textContent = label;
    if(bg){ opt.style.backgroundColor=bg; opt.style.color=fg||'#444'; }
    skinSel.appendChild(opt);
  });
  skinSel.addEventListener('change',function(){
    skinHidden.value = this.value;
    const found = SKIN_OPTIONS.find(c=>c.v===this.value);
    this.style.backgroundColor = found?.bg||'white';
    this.style.color = found?.fg||'var(--ink)';
    skinOther.value = '';
  });
  const skinOther = document.createElement('input');
  skinOther.type = 'text';
  skinOther.id = 'chara_skin_other_'+idx;
  skinOther.placeholder = '日本語入力可（例: 青肌、緑肌）';
  skinOther.className = 'inp-ja';
  skinOther.style.cssText = 'width:100%;border-radius:5px;padding:0.35rem 0.6rem;font-family:DM Mono,monospace;font-size:0.75rem;outline:none;box-sizing:border-box;';
  skinOther.addEventListener('input', function(){
    if(this.value.trim()){
      skinSel.value = ''; skinSel.style.backgroundColor='white'; skinSel.style.color='var(--ink)';
      skinHidden.value = this.value.trim();
    } else {
      skinHidden.value = skinSel.value;
    }
  });
  skinWrap.appendChild(skinSel);
  skinWrap.appendChild(skinOther);
  skinWrap.appendChild(skinHidden);
  skinRow.appendChild(skinLabelWrap);
  skinRow.appendChild(skinWrap);

  // 瞳の色行
  const eyeRow = document.createElement('div');
  eyeRow.className = 'opt-row';
  eyeRow.style.alignItems = 'start';
  const eyeLabel = document.createElement('label');
  eyeLabel.className = 'opt-label';
  eyeLabel.style.paddingTop = '0.3rem';
  eyeLabel.textContent = '④ 瞳の色';
  const eyeLabelWrap = document.createElement('div');
  eyeLabelWrap.className = 'opt-label-wrap';
  eyeLabelWrap.appendChild(eyeLabel);
  eyeLabelWrap.appendChild(makeLMCheckbox('chara_eyes_lm_'+idx, false));
  const eyeWrap = document.createElement('div');
  eyeWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.35rem;width:100%;';

  // 通常カラーselect行
  const eyeSel = document.createElement('select');
  eyeSel.style.cssText = 'font-family:DM Mono,monospace;font-size:0.75rem;border:1px solid var(--border);border-radius:5px;padding:0.3rem 0.5rem;background:white;color:var(--ink);cursor:pointer;width:100%;';
  EYE_COLORS.forEach(({v,label,bg,fg})=>{
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = label;
    if(bg){ opt.style.backgroundColor=bg; opt.style.color=fg||'#fff'; }
    eyeSel.appendChild(opt);
  });
  eyeSel.addEventListener('change',function(){
    if(oddBtn.dataset.odd==='0'){
      const sel = EYE_COLORS.find(c=>c.v===this.value);
      this.style.backgroundColor = sel?.bg||'white';
      this.style.color = sel?.fg||'var(--ink)';
      updateEyeValue();
    }
  });
  const eyeBtns = eyeSel; // 後続コードの互換性のためalias
  const eyeHidden = document.createElement('input');
  eyeHidden.type = 'hidden';
  eyeHidden.id = 'chara_eyes_'+idx;
  eyeHidden.value = '';

  // オッドアイ切替ボタン
  const oddBtn = document.createElement('div');
  oddBtn.className = 'age-btn odd-eye-btn';
  oddBtn.style.cssText = 'width:2.8rem;text-align:center;flex-shrink:0;font-size:0.7rem;padding:0.28rem 0;';
  oddBtn.innerHTML = '<span class="odd-long">オッドアイ</span><span class="odd-short">odd</span>';
  oddBtn.dataset.odd = '0';

  // オッドアイ選択UI（初期非表示）
  const oddWrap = document.createElement('div');
  oddWrap.style.cssText = 'display:none;gap:0.5rem;flex-wrap:wrap;align-items:center;';
  const oddLabels = ['左目','右目'];
  const oddSelects = oddLabels.map((lbl,oi)=>{
    const g = document.createElement('div');
    g.style.cssText = 'display:flex;flex-direction:column;gap:0.15rem;flex:1;';
    const gl = document.createElement('div');
    gl.style.cssText = 'font-family:DM Mono,monospace;font-size:0.65rem;color:var(--muted);';
    gl.textContent = lbl;
    const sel = document.createElement('select');
    sel.style.cssText = 'font-family:DM Mono,monospace;font-size:0.75rem;border:1px solid var(--border);border-radius:5px;padding:0.3rem 0.5rem;background:white;color:var(--ink);cursor:pointer;width:100%;';
    sel.dataset['odd'+oi] = '';
    EYE_COLORS.filter(c=>c.v!=='').forEach(({v,label,bg,fg})=>{
      const opt = document.createElement('option');
      opt.value = v;
      opt.textContent = label;
      if(bg){ opt.style.backgroundColor=bg; opt.style.color=fg||'#fff'; }
      sel.appendChild(opt);
    });
    sel.addEventListener('change',function(){
      const found = EYE_COLORS.find(c=>c.v===this.value);
      this.style.backgroundColor = found?.bg||'white';
      this.style.color = found?.fg||'var(--ink)';
      sel.dataset['odd'+oi] = this.value;
      updateEyeValue();
    });
    g.appendChild(gl); g.appendChild(sel);
    return g;
  });
  oddSelects.forEach(g=>oddWrap.appendChild(g));

  // oddBtnが詰まったらcompactクラスで短縮
  const oddResizeObs = new ResizeObserver(entries=>{
    for(const e of entries){
      oddBtn.classList.toggle('compact', e.contentRect.width < 52);
    }
  });
  oddResizeObs.observe(oddBtn);

  function updateEyeValue(){
    if(oddBtn.dataset.odd==='1'){
      const l = oddSelects[0].querySelector('select').value||'';
      const r = oddSelects[1].querySelector('select').value||'';
      eyeHidden.value = l&&r ? l+', '+r+', heterochromia' : (l||r||'');
    } else {
      eyeHidden.value = eyeSel.value||'';
    }
  }

  const eyeSelRow = document.createElement('div');
  eyeSelRow.style.cssText = 'display:flex;gap:0.3rem;align-items:center;';
  eyeSel.style.flex = '1';
  eyeSel.style.width = '';
  eyeSelRow.appendChild(eyeSel);
  eyeSelRow.appendChild(oddBtn);

  oddBtn.addEventListener('click',function(){
    const isOdd = this.dataset.odd==='0';
    this.dataset.odd = isOdd?'1':'0';
    this.classList.toggle('active', isOdd);
    oddWrap.style.display = isOdd?'flex':'none';
    eyeSel.style.display = isOdd?'none':'';
    if(!isOdd){ eyeSel.value=''; eyeSel.style.backgroundColor='white'; eyeSel.style.color='var(--ink)'; }
    updateEyeValue();
  });

  eyeWrap.appendChild(eyeSelRow);
  eyeWrap.appendChild(oddWrap);
  eyeWrap.appendChild(eyeHidden);
  eyeRow.appendChild(eyeLabelWrap);
  eyeRow.appendChild(eyeWrap);

  // 性別変更時にバスト行の表示切替
  function updateBustVisibility(){
    const activeGender = genderRow.querySelector('.gender-btn.active')?.dataset.g || 'female';
    bustRow.style.display = (activeGender === 'male') ? 'none' : '';
  }
  genderRow.querySelectorAll('.gender-btn').forEach(btn=>{
    btn.addEventListener('click', ()=>setTimeout(updateBustVisibility, 0));
  });
  updateBustVisibility();
  // 衣装行（サブカテゴリ展開式）
  const outfitRow = document.createElement('div');
  outfitRow.className = 'opt-row';
  outfitRow.style.alignItems = 'start';
  const outfitLabel = document.createElement('label');
  outfitLabel.className = 'opt-label';
  outfitLabel.style.paddingTop = '0.3rem';
  outfitLabel.textContent = '⑧ 衣装';
  const outfitLabelWrap = document.createElement('div');
  outfitLabelWrap.className = 'opt-label-wrap';
  outfitLabelWrap.appendChild(outfitLabel);
  outfitLabelWrap.appendChild(makeLMCheckbox('chara_outfit_lm_'+idx, true));

  const outfitHidden = document.createElement('input');
  outfitHidden.type = 'hidden';
  outfitHidden.id = 'chara_outfit_'+idx;
  outfitHidden.value = '';

  const OUTFIT_DATA = __OPT__.outfit_data;
  const OUTFIT_COLORS = __OPT__.outfit_colors;

  // 上半身・下半身はそれぞれ独立した状態を持つ
  const outfitState = { top: {color:'', item:''}, bottom: {color:'', item:''} };
  let outfitActiveCat = null; // 全裸/半裸/全身/上半身/下半身/null

  function buildOutfitValue(){
    if(outfitActiveCat==='全裸'){ outfitHidden.value='nude'; return; }
    if(outfitActiveCat==='半裸'){ outfitHidden.value='partially_nude'; return; }
    if(!outfitActiveCat){ outfitHidden.value=''; return; }
    const parts=[];
    if(outfitActiveCat==='全身'){
      if(outfitState.top.color) parts.push(outfitState.top.color);
      if(outfitState.top.item)  parts.push(outfitState.top.item);
    } else {
      // 上半身
      const tc=[outfitState.top.color, outfitState.top.item].filter(Boolean);
      if(tc.length) parts.push(...tc);
      // 下半身
      const bc=[outfitState.bottom.color, outfitState.bottom.item].filter(Boolean);
      if(bc.length) parts.push(...bc);
    }
    outfitHidden.value=parts.join(' ');
  }

  const outfitWrap = document.createElement('div');
  outfitWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.3rem;width:100%;';

  const outfitCatRow = document.createElement('div');
  outfitCatRow.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';

  // 上半身用 色・種類行
  const outfitTopColorRow = document.createElement('div');
  outfitTopColorRow.style.cssText = 'display:none;gap:0.2rem;flex-wrap:wrap;';
  const outfitTopItemRow = document.createElement('div');
  outfitTopItemRow.style.cssText = 'display:none;gap:0.2rem;flex-wrap:wrap;';

  // 下半身用 色・種類行
  const outfitBotColorRow = document.createElement('div');
  outfitBotColorRow.style.cssText = 'display:none;gap:0.2rem;flex-wrap:wrap;';
  const outfitBotItemRow = document.createElement('div');
  outfitBotItemRow.style.cssText = 'display:none;gap:0.2rem;flex-wrap:wrap;';

  // 小ラベル
  function makeSubLabel(text){
    const d=document.createElement('div');
    d.style.cssText='font-family:DM Mono,monospace;font-size:0.62rem;color:var(--muted);width:100%;display:none;';
    d.textContent=text;
    return d;
  }
  const topLabel = makeSubLabel('上半身');
  const botLabel = makeSubLabel('下半身');

  function makeColorBtns(row, stateKey){
    const sel = document.createElement('select');
    sel.style.cssText = 'font-family:DM Mono,monospace;font-size:0.75rem;border:1px solid var(--border);border-radius:5px;padding:0.3rem 0.5rem;background:white;color:var(--ink);cursor:pointer;width:100%;';
    sel.dataset.ocolor = '';
    OUTFIT_COLORS.forEach(({v,label,bg,fg})=>{
      const opt=document.createElement('option');
      opt.value=v; opt.textContent=label;
      if(bg){ opt.style.backgroundColor=bg; opt.style.color=fg||'#fff'; }
      sel.appendChild(opt);
    });
    sel.addEventListener('change',function(){
      const found=OUTFIT_COLORS.find(c=>c.v===this.value);
      this.style.backgroundColor=found?.bg||'white';
      this.style.color=found?.fg||'var(--ink)';
      sel.dataset.ocolor=this.value;
      outfitState[stateKey].color=this.value;
      buildOutfitValue();
    });
    row.appendChild(sel);
  }
  function makeItemBtns(row, stateKey, items){
    row.innerHTML='';
    items.forEach(({v,label})=>{
      const btn=document.createElement('div');
      btn.className='age-btn';
      btn.dataset.oitem=v;
      btn.textContent=label;
      btn.addEventListener('click',function(){
        row.querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
        this.classList.add('active');
        outfitState[stateKey].item=v;
        buildOutfitValue();
      });
      row.appendChild(btn);
    });
  }
  makeColorBtns(outfitTopColorRow, 'top');
  makeColorBtns(outfitBotColorRow, 'bottom');

  // 自由入力
  const outfitFree = document.createElement('input');
  outfitFree.type = 'text';
  outfitFree.id = 'chara_outfit_free_'+idx;
  outfitFree.placeholder = '日本語入力可（例: 白 ドレス、maid_apron）';
  outfitFree.className = 'inp-en';
  outfitFree.className = 'inp-ja';
  outfitFree.style.cssText = 'width:100%;border-radius:5px;padding:0.35rem 0.6rem;font-family:DM Mono,monospace;font-size:0.75rem;outline:none;box-sizing:border-box;';
  outfitFree.addEventListener('input',function(){
    if(this.value.trim()) outfitHidden.value=this.value.trim();
    else buildOutfitValue();
  });

  function showOutfitCat(cat){
    if(outfitActiveCat===cat){
      outfitActiveCat=null;
      outfitState.top={color:'',item:''}; outfitState.bottom={color:'',item:''};
      outfitCatRow.querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
      [topLabel,outfitTopColorRow,outfitTopItemRow,botLabel,outfitBotColorRow,outfitBotItemRow].forEach(r=>r.style.display='none');
      buildOutfitValue(); return;
    }
    outfitActiveCat=cat;
    outfitState.top={color:'',item:''}; outfitState.bottom={color:'',item:''};
    outfitCatRow.querySelectorAll('.age-btn').forEach(b=>b.classList.toggle('active',b.dataset.outcat===cat));
    [topLabel,outfitTopColorRow,outfitTopItemRow,botLabel,outfitBotColorRow,outfitBotItemRow].forEach(r=>r.style.display='none');
    outfitTopColorRow.querySelectorAll('.age-btn').forEach(b=>b.classList.toggle('active',b.dataset.ocolor===''));
    outfitBotColorRow.querySelectorAll('.age-btn').forEach(b=>b.classList.toggle('active',b.dataset.ocolor===''));

    if(cat==='全身'){
      makeItemBtns(outfitTopItemRow,'top',OUTFIT_DATA['全身'].items);
      topLabel.style.display=''; outfitTopColorRow.style.display='flex'; outfitTopItemRow.style.display='flex';
    } else if(cat==='上半身' || cat==='下半身'){
      // 上半身・下半身は両方表示
      makeItemBtns(outfitTopItemRow,'top',OUTFIT_DATA['上半身'].items);
      makeItemBtns(outfitBotItemRow,'bottom',OUTFIT_DATA['下半身'].items);
      topLabel.style.display=''; outfitTopColorRow.style.display='flex'; outfitTopItemRow.style.display='flex';
      botLabel.style.display=''; outfitBotColorRow.style.display='flex'; outfitBotItemRow.style.display='flex';
    }
    buildOutfitValue();
  }

  // カテゴリボタン生成（上半身・下半身はひとつのボタン「上下」にまとめる）
  ['全裸','半裸','全身','上下'].forEach(cat=>{
    const btn=document.createElement('div');
    btn.className='age-btn';
    btn.dataset.outcat = cat==='上下'?'上半身':cat;
    btn.textContent=cat;
    btn.addEventListener('click',()=>showOutfitCat(cat==='上下'?'上半身':cat));
    outfitCatRow.appendChild(btn);
  });

  outfitWrap.appendChild(outfitCatRow);
  outfitWrap.appendChild(topLabel);
  outfitWrap.appendChild(outfitTopColorRow);
  outfitWrap.appendChild(outfitTopItemRow);
  outfitWrap.appendChild(botLabel);
  outfitWrap.appendChild(outfitBotColorRow);
  outfitWrap.appendChild(outfitBotItemRow);
  outfitWrap.appendChild(outfitFree);
  outfitWrap.appendChild(outfitHidden);
  outfitRow.appendChild(outfitLabelWrap);
  outfitRow.appendChild(outfitWrap);

  // 髪型行（選択式＋自由入力）
  const hairRow = document.createElement('div');
  hairRow.className = 'opt-row';
  hairRow.style.alignItems = 'start';
  const hairStyleLabelWrap = document.createElement('div');
  hairStyleLabelWrap.className = 'opt-label-wrap';
  const hairStyleLabel = document.createElement('label');
  hairStyleLabel.className = 'opt-label';
  hairStyleLabel.textContent = '① 髪型';
  hairStyleLabelWrap.appendChild(hairStyleLabel);
  hairStyleLabelWrap.appendChild(makeLMCheckbox('chara_hairstyle_lm_'+idx, true));
  const hairStyleHidden = document.createElement('input');
  hairStyleHidden.type = 'hidden';
  hairStyleHidden.id = 'chara_hairstyle_'+idx;
  hairStyleHidden.value = '';
  const hairStyleWrap = document.createElement('div');
  hairStyleWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.2rem;width:100%;';
  const hairStyleBtns = document.createElement('div');
  hairStyleBtns.style.cssText = 'display:flex;flex-direction:column;gap:0.15rem;';
  // グループごとに単一選択
  function updateHairStyleValue(){
    const sel = [...hairStyleBtns.querySelectorAll('.age-btn.active')].map(b=>b.dataset.hs).filter(Boolean);
    hairStyleHidden.value = sel.join(',');
  }
  const hsGroups = [...new Set(HAIRSTYLE_OPTIONS.map(o=>o.group))];
  hsGroups.forEach(group=>{
    const sep = document.createElement('div');
    sep.style.cssText = 'font-family:DM Mono,monospace;font-size:0.62rem;color:var(--muted);margin-top:0.1rem;';
    sep.textContent = group;
    hairStyleBtns.appendChild(sep);
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
    row.dataset.hsgroup = group;
    const items = HAIRSTYLE_OPTIONS.filter(o=>o.group===group);
    // 先頭に「－」
    const noneBtn = document.createElement('div');
    noneBtn.className = 'age-btn active';
    noneBtn.dataset.hs = '';
    noneBtn.textContent = '－';
    noneBtn.addEventListener('click',function(){
      row.querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
      this.classList.add('active');
      updateHairStyleValue();
      hairStyleFree.value='';
    });
    row.appendChild(noneBtn);
    items.forEach(({v,label})=>{
      const btn = document.createElement('div');
      btn.className = 'age-btn';
      btn.dataset.hs = v;
      btn.textContent = label;
      btn.addEventListener('click',function(){
        row.querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
        this.classList.add('active');
        updateHairStyleValue();
        hairStyleFree.value='';
      });
      row.appendChild(btn);
    });
    hairStyleBtns.appendChild(row);
  });
  const hairStyleFree = document.createElement('input');
  hairStyleFree.type = 'text';
  hairStyleFree.id = 'chara_hairstyle_free_'+idx;
  hairStyleFree.placeholder = '日本語入力可（例: お団子、ドレッド）';
  hairStyleFree.className = 'inp-ja';
  hairStyleFree.style.cssText = 'width:100%;border-radius:5px;padding:0.35rem 0.6rem;font-family:DM Mono,monospace;font-size:0.75rem;outline:none;box-sizing:border-box;';
  hairStyleFree.addEventListener('input',function(){
    if(this.value.trim()){
      hairStyleBtns.querySelectorAll('.multi-btn').forEach(b=>b.classList.remove('active'));
      hairStyleHidden.value = this.value.trim();
    } else {
      updateHairStyleValue();
    }
  });
  hairStyleWrap.appendChild(hairStyleBtns);
  hairStyleWrap.appendChild(hairStyleFree);
  hairStyleWrap.appendChild(hairStyleHidden);
  hairRow.appendChild(hairStyleLabelWrap);
  hairRow.appendChild(hairStyleWrap);

  // 髪色行（LLM=false）
  const hairColorRow = document.createElement('div');
  hairColorRow.className = 'opt-row';
  hairColorRow.style.alignItems = 'start';
  const hairColorLabelWrap = document.createElement('div');
  hairColorLabelWrap.className = 'opt-label-wrap';
  const hairColorLabel = document.createElement('label');
  hairColorLabel.className = 'opt-label';
  hairColorLabel.textContent = '② 髪色';
  hairColorLabelWrap.appendChild(hairColorLabel);
  hairColorLabelWrap.appendChild(makeLMCheckbox('chara_haircolor_lm_'+idx, false));
  const hairHidden = document.createElement('input');
  hairHidden.type = 'hidden';
  hairHidden.id = 'chara_haircolor_'+idx;
  hairHidden.value = '';
  const hairSel = document.createElement('select');
  hairSel.style.cssText = 'font-family:DM Mono,monospace;font-size:0.75rem;border:1px solid var(--border);border-radius:5px;padding:0.3rem 0.5rem;background:white;color:var(--ink);cursor:pointer;width:100%;';
  HAIR_COLORS.forEach(({v,label,bg,fg})=>{
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = label;
    if(bg){ opt.style.backgroundColor=bg; opt.style.color=fg||'#fff'; }
    hairSel.appendChild(opt);
  });
  hairSel.addEventListener('change',function(){
    hairHidden.value = this.value;
    const sel = HAIR_COLORS.find(c=>c.v===this.value);
    this.style.backgroundColor = sel?.bg||'white';
    this.style.color = sel?.fg||'var(--ink)';
  });
  const hairOther = document.createElement('input');
  hairOther.type = 'text';
  hairOther.id = 'chara_hairother_'+idx;
  hairOther.placeholder = '日本語入力可（例: グラデーション、メッシュ）';
  hairOther.className = 'inp-ja';
  hairOther.style.cssText = 'width:100%;border-radius:5px;padding:0.35rem 0.6rem;font-family:DM Mono,monospace;font-size:0.75rem;outline:none;box-sizing:border-box;';
  hairOther.addEventListener('input', function(){
    if(this.value.trim()){
      hairSel.value = '';
      hairSel.style.backgroundColor='white'; hairSel.style.color='var(--ink)';
      hairHidden.value = this.value.trim();
    } else {
      hairHidden.value = hairSel.value;
    }
  });
  const hairColorWrap = document.createElement('div');
  hairColorWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.2rem;width:100%;';
  hairColorWrap.appendChild(hairSel);
  hairColorWrap.appendChild(hairOther);
  hairColorWrap.appendChild(hairHidden);
  hairColorRow.appendChild(hairColorLabelWrap);
  hairColorRow.appendChild(hairColorWrap);

  // ① 体格行
  function makeLMCheckbox(fieldId, defaultChecked){
    const wrap = document.createElement('div');
    wrap.className = 'lm-check-wrap';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.id = fieldId+'_lm';
    cb.checked = defaultChecked;
    const lbl = document.createElement('label');
    lbl.htmlFor = fieldId+'_lm';
    lbl.textContent = 'LLM';
    wrap.appendChild(cb);
    wrap.appendChild(lbl);
    return wrap;
  }
  function makeOptLabel(labelText){
    const wrap = document.createElement('div');
    wrap.className = 'opt-label-wrap';
    const lbl = document.createElement('label');
    lbl.className = 'opt-label';
    lbl.textContent = labelText;
    wrap.appendChild(lbl);
    return wrap;
  }
  function makeOptLabelWithCheck(labelText, fieldId, defaultChecked){
    const wrap = document.createElement('div');
    wrap.className = 'opt-label-wrap';
    const lbl = document.createElement('label');
    lbl.className = 'opt-label';
    lbl.textContent = labelText;
    wrap.appendChild(lbl);
    wrap.appendChild(makeLMCheckbox(fieldId, defaultChecked));
    return wrap;
  }
  function makeAttrRow(labelText, options, hiddenId, useLM=false){
    const row = document.createElement('div');
    row.className = 'opt-row';
    row.appendChild(useLM ? makeOptLabelWithCheck(labelText, hiddenId, false) : makeOptLabel(labelText));
    const btns = document.createElement('div');
    btns.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
    const hid = document.createElement('input');
    hid.type = 'hidden';
    hid.id = hiddenId;
    hid.value = '';
    options.forEach(({v,label})=>{
      const btn = document.createElement('div');
      btn.className = 'age-btn'+(v===''?' active':'');
      btn.dataset.val = v;
      btn.textContent = label;
      btn.addEventListener('click',function(){
        btns.querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
        this.classList.add('active');
        hid.value = v;
      });
      btns.appendChild(btn);
    });
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-direction:column;gap:0.2rem;width:100%;';
    wrap.appendChild(btns);
    wrap.appendChild(hid);
    row.appendChild(wrap);
    return row;
  }
  const posVRow  = makeAttrRow('⑯ 画面上下', POS_VERTICAL,   'chara_posv_'+idx,  false);
  const posHRow  = makeAttrRow('⑰ 画面左右', POS_HORIZONTAL, 'chara_posh_'+idx,  false);
  const posCRow  = makeAttrRow('⑱ カメラ',   POS_CAMERA,     'chara_posc_'+idx,  false);
  const heightRow = makeAttrRow('⑧ 背丈', BODY_HEIGHT, 'chara_height_'+idx, false);
  const buildRow  = makeAttrRow('⑨ 体型',  BODY_BUILD,  'chara_build_'+idx,  false);
  const legsRow   = makeAttrRow('⑩ 脚',    BODY_LEGS,   'chara_legs_'+idx,   false);

  // 表情行（LLMチェックOFFデフォルト）
  // 表情行（複数選択）
  const faceRow = document.createElement('div');
  faceRow.className = 'opt-row';
  faceRow.appendChild(makeOptLabel('⑥ 表情'));
  const faceBtns = document.createElement('div');
  faceBtns.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
  const faceHidden = document.createElement('input');
  faceHidden.type = 'hidden';
  faceHidden.id = 'chara_face_'+idx;
  faceHidden.value = '';
  function updateFaceValue(){
    const selected = [...faceBtns.querySelectorAll('.multi-btn.active')].map(b=>b.dataset.face).filter(v=>v!=='');
    faceHidden.value = selected.join(',');
  }
  FACE_OPTIONS.forEach(({v,label})=>{
    const btn = document.createElement('div');
    btn.className = 'multi-btn'+(v===''?' active':'');
    btn.dataset.face = v;
    btn.textContent = label;
    btn.addEventListener('click',function(){
      if(v===''){
        // －を押したら全解除してこれだけ
        faceBtns.querySelectorAll('.multi-btn').forEach(b=>b.classList.remove('active'));
        this.classList.add('active');
      } else {
        faceBtns.querySelector('[data-face=""]').classList.remove('active');
        this.classList.toggle('active');
        if(!faceBtns.querySelector('.multi-btn.active')) {
          faceBtns.querySelector('[data-face=""]').classList.add('active');
        }
      }
      updateFaceValue();
    });
    faceBtns.appendChild(btn);
  });
  const faceWrap = document.createElement('div');
  faceWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.2rem;width:100%;';
  faceWrap.appendChild(faceBtns);
  faceWrap.appendChild(faceHidden);
  faceRow.appendChild(faceWrap);

  // 目の状態行（複数選択）
  const eyeStateRow = document.createElement('div');
  eyeStateRow.className = 'opt-row';
  eyeStateRow.style.alignItems = 'start';
  eyeStateRow.appendChild(makeOptLabel('③ 目の状態'));
  const eyeStateBtns = document.createElement('div');
  eyeStateBtns.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
  const eyeStateHidden = document.createElement('input');
  eyeStateHidden.type = 'hidden';
  eyeStateHidden.id = 'chara_eyestate_'+idx;
  eyeStateHidden.value = '';
  function updateEyeStateValue(){
    const selected = [...eyeStateBtns.querySelectorAll('.multi-btn.active')].map(b=>b.dataset.es).filter(v=>v!=='');
    eyeStateHidden.value = selected.join(',');
  }
  // グループごとに行を分けて生成
  const eyeGroupRows = {};
  ['open','dir','state'].forEach(g=>{
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;align-items:center;';
    eyeGroupRows[g] = row;
    eyeStateBtns.appendChild(row);
  });
  // グループラベル（dir・stateの前に小さく）
  const dirLbl = document.createElement('div');
  dirLbl.style.cssText = 'font-family:DM Mono,monospace;font-size:0.62rem;color:var(--muted);margin-top:0.1rem;width:100%;';
  dirLbl.textContent = '向き';
  eyeStateBtns.insertBefore(dirLbl, eyeGroupRows['dir']);
  const stateLbl = document.createElement('div');
  stateLbl.style.cssText = 'font-family:DM Mono,monospace;font-size:0.62rem;color:var(--muted);margin-top:0.1rem;width:100%;';
  stateLbl.textContent = '状態';
  eyeStateBtns.insertBefore(stateLbl, eyeGroupRows['state']);

  function refreshDirBtns(){
    const isClosed = eyeStateBtns.querySelector('[data-es="closed_eyes"]')?.classList.contains('active');
    eyeGroupRows['dir'].querySelectorAll('.multi-btn').forEach(b=>{
      if(isClosed){
        b.classList.remove('active');
        b.style.opacity = '0.3';
        b.style.pointerEvents = 'none';
      } else {
        b.style.opacity = '';
        b.style.pointerEvents = '';
      }
    });
    if(isClosed) updateEyeStateValue();
  }

  EYE_STATE_OPTIONS.forEach(({v,label,group})=>{
    const btn = document.createElement('div');
    // 開閉グループは単一選択（age-btn=緑）、向き・状態は複数選択（multi-btn=紫）
    btn.className = group==='open'
      ? ('age-btn'+(v===''?' active':''))
      : ('multi-btn'+(v===''?' active':''));
    btn.dataset.es = v;
    btn.textContent = label;
    if(group==='open') btn.style.minWidth = '3rem';
    btn.addEventListener('click',function(){
      if(group==='open'){
        // 単一選択
        eyeGroupRows['open'].querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
        this.classList.add('active');
        refreshDirBtns();
      } else if(v===''){
        // 向き・状態の「－」は全解除
        eyeGroupRows[group].querySelectorAll('.multi-btn').forEach(b=>b.classList.remove('active'));
        this.classList.add('active');
      } else {
        eyeGroupRows[group].querySelector('[data-es=""]')?.classList.remove('active');
        this.classList.toggle('active');
        if(!eyeGroupRows[group].querySelector('.multi-btn.active')){
          eyeGroupRows[group].querySelector('[data-es=""]')?.classList.add('active');
        }
      }
      updateEyeStateValue();
    });
    eyeGroupRows[group].appendChild(btn);
  });
  const eyeStateWrap = document.createElement('div');
  eyeStateWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.2rem;width:100%;';
  eyeStateWrap.appendChild(eyeStateBtns);
  eyeStateWrap.appendChild(eyeStateHidden);
  eyeStateRow.appendChild(eyeStateWrap);

  // 口の状態行（複数選択）
  const mouthRow = document.createElement('div');
  mouthRow.className = 'opt-row';
  mouthRow.style.alignItems = 'start';
  mouthRow.appendChild(makeOptLabelWithCheck('⑤ 口', 'chara_mouth_'+idx, false));
  const mouthBtns = document.createElement('div');
  mouthBtns.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
  const mouthHidden = document.createElement('input');
  mouthHidden.type = 'hidden';
  mouthHidden.id = 'chara_mouth_'+idx;
  mouthHidden.value = '';
  function updateMouthValue(){
    const selected = [...mouthBtns.querySelectorAll('.multi-btn.active')].map(b=>b.dataset.mouth).filter(v=>v!=='');
    mouthHidden.value = selected.join(',');
  }
  MOUTH_OPTIONS.forEach(({v,label})=>{
    const btn = document.createElement('div');
    btn.className = 'multi-btn'+(v===''?' active':'');
    btn.dataset.mouth = v;
    btn.textContent = label;
    btn.addEventListener('click',function(){
      if(v===''){
        mouthBtns.querySelectorAll('.multi-btn').forEach(b=>b.classList.remove('active'));
        this.classList.add('active');
      } else {
        mouthBtns.querySelector('[data-mouth=""]').classList.remove('active');
        this.classList.toggle('active');
        if(!mouthBtns.querySelector('.multi-btn.active')){
          mouthBtns.querySelector('[data-mouth=""]').classList.add('active');
        }
      }
      updateMouthValue();
    });
    mouthBtns.appendChild(btn);
  });
  const mouthWrap = document.createElement('div');
  mouthWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.2rem;width:100%;';
  mouthWrap.appendChild(mouthBtns);
  mouthWrap.appendChild(mouthHidden);
  mouthRow.appendChild(mouthWrap);

  // エフェクト行（複数選択）
  const effectRow = document.createElement('div');
  effectRow.className = 'opt-row';
  effectRow.style.alignItems = 'start';
  effectRow.appendChild(makeOptLabel('⑬ エフェクト'));
  const effectBtns = document.createElement('div');
  effectBtns.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
  const effectHidden = document.createElement('input');
  effectHidden.type = 'hidden';
  effectHidden.id = 'chara_effect_'+idx;
  effectHidden.value = '';
  function updateEffectValue(){
    const selected = [...effectBtns.querySelectorAll('.multi-btn.active')].map(b=>b.dataset.effect).filter(v=>v!=='');
    effectHidden.value = selected.join(',');
  }
  EFFECT_OPTIONS.forEach(({v,label})=>{
    const btn = document.createElement('div');
    btn.className = 'multi-btn'+(v===''?' active':'');
    btn.dataset.effect = v;
    btn.textContent = label;
    btn.addEventListener('click',function(){
      if(v===''){
        effectBtns.querySelectorAll('.multi-btn').forEach(b=>b.classList.remove('active'));
        this.classList.add('active');
      } else {
        effectBtns.querySelector('[data-effect=""]').classList.remove('active');
        this.classList.toggle('active');
        if(!effectBtns.querySelector('.multi-btn.active')){
          effectBtns.querySelector('[data-effect=""]').classList.add('active');
        }
      }
      updateEffectValue();
    });
    effectBtns.appendChild(btn);
  });
  const effectWrap = document.createElement('div');
  effectWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.2rem;width:100%;';
  effectWrap.appendChild(effectBtns);
  effectWrap.appendChild(effectHidden);
  effectRow.appendChild(effectWrap);

  // 付属行
  const attachRow = document.createElement('div');
  attachRow.className = 'opt-row';
  attachRow.style.alignItems = 'start';
  attachRow.appendChild(makeOptLabel('⑫ 付属'));
  const attachWrap = document.createElement('div');
  attachWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.4rem;width:100%;';

  // 単一選択グループを作る関数
  function makeSingleGroup(groupLabel, options, hiddenId){
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-direction:column;gap:0.15rem;';
    const lbl = document.createElement('div');
    lbl.style.cssText = 'font-family:DM Mono,monospace;font-size:0.65rem;color:var(--muted);';
    lbl.textContent = groupLabel;
    const btns = document.createElement('div');
    btns.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
    const hid = document.createElement('input');
    hid.type = 'hidden';
    hid.id = hiddenId;
    hid.value = '';
    options.forEach(({v,label})=>{
      const btn = document.createElement('div');
      btn.className = 'age-btn'+(v===''?' active':'');
      btn.dataset.val = v;
      btn.textContent = label;
      btn.addEventListener('click',function(){
        btns.querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
        this.classList.add('active');
        hid.value = v;
      });
      btns.appendChild(btn);
    });
    wrap.appendChild(lbl);
    wrap.appendChild(btns);
    wrap.appendChild(hid);
    return wrap;
  }

  // 複数選択グループ（アクセサリー）
  function makeMultiGroup(groupLabel, options, hiddenId){
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-direction:column;gap:0.15rem;';
    const lbl = document.createElement('div');
    lbl.style.cssText = 'font-family:DM Mono,monospace;font-size:0.65rem;color:var(--muted);';
    lbl.textContent = groupLabel;
    const btns = document.createElement('div');
    btns.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
    const hid = document.createElement('input');
    hid.type = 'hidden';
    hid.id = hiddenId;
    hid.value = '';
    function updateVal(){
      hid.value = [...btns.querySelectorAll('.multi-btn.active')].map(b=>b.dataset.val).join(',');
    }
    options.forEach(({v,label})=>{
      const btn = document.createElement('div');
      btn.className = 'multi-btn';
      btn.dataset.val = v;
      btn.textContent = label;
      btn.addEventListener('click',function(){
        this.classList.toggle('active');
        updateVal();
      });
      btns.appendChild(btn);
    });
    wrap.appendChild(lbl);
    wrap.appendChild(btns);
    wrap.appendChild(hid);
    return wrap;
  }

  (__OPT__.attach_groups||[
    {key:'ears',  label:'耳',          options_key:'ears_options',      multi:false},
    {key:'tail',  label:'尻尾',        options_key:'tail_options',      multi:false},
    {key:'wings', label:'翼',          options_key:'wings_options',     multi:false},
    {key:'acc',   label:'アクセサリー',options_key:'accessory_options', multi:true},
  ]).forEach(({key,label,options_key,multi})=>{
    const opts = __OPT__[options_key]||[];
    attachWrap.appendChild(
      multi ? makeMultiGroup(label, opts, 'chara_'+key+'_'+idx)
            : makeSingleGroup(label, opts, 'chara_'+key+'_'+idx)
    );
  });

  attachRow.appendChild(attachWrap);

  // 持ち物行（カテゴリ展開式）
  const holdingRow = document.createElement('div');
  holdingRow.className = 'opt-row';
  holdingRow.style.cssText = 'align-items:start;display:none;';
  holdingRow.appendChild(makeOptLabel('⑮ 持ち物'));
  const itemHidden = document.createElement('input');
  itemHidden.type = 'hidden';
  itemHidden.id = 'chara_item_'+idx;
  itemHidden.value = '';
  const itemWrap = document.createElement('div');
  itemWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.3rem;width:100%;';

  // カテゴリタブ行
  const itemCatRow = document.createElement('div');
  itemCatRow.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
  // 選択肢表示エリア
  const itemBtnArea = document.createElement('div');
  itemBtnArea.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;display:none;';

  let activeItemCat = null;
  function updateItemValue(){
    itemHidden.value = [...itemWrap.querySelectorAll('[data-item].active')].map(b=>b.dataset.item).join(',');
  }
  function showItemCat(cat){
    if(activeItemCat === cat){
      // 同じカテゴリ→閉じる
      itemBtnArea.style.display = 'none';
      itemCatRow.querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
      activeItemCat = null;
      return;
    }
    activeItemCat = cat;
    itemCatRow.querySelectorAll('.age-btn').forEach(b=>{
      b.classList.toggle('active', b.dataset.itemcat===cat);
    });
    itemBtnArea.innerHTML = '';
    (ITEM_CATEGORIES[cat]||[]).forEach(({v,label})=>{
      const btn = document.createElement('div');
      btn.className = 'multi-btn';
      btn.dataset.item = v;
      btn.textContent = label;
      // 既選択を反映
      const cur = itemHidden.value.split(',');
      if(cur.includes(v)) btn.classList.add('active');
      btn.addEventListener('click',function(){
        this.classList.toggle('active');
        updateItemValue();
      });
      itemBtnArea.appendChild(btn);
    });
    itemBtnArea.style.display = 'flex';
  }

  Object.keys(ITEM_CATEGORIES).forEach(cat=>{
    const btn = document.createElement('div');
    btn.className = 'age-btn';
    btn.dataset.itemcat = cat;
    btn.textContent = cat;
    btn.addEventListener('click',()=>showItemCat(cat));
    itemCatRow.appendChild(btn);
  });

  // 自由入力
  const itemFreeInput = document.createElement('input');
  itemFreeInput.type = 'text';
  itemFreeInput.id = 'chara_item_free_'+idx;
  itemFreeInput.placeholder = '英語タグのみ（例: magic_wand, baseball_bat）';
  itemFreeInput.className = 'inp-en';
  itemFreeInput.className = 'inp-en';
  itemFreeInput.style.cssText = 'width:100%;border-radius:5px;padding:0.35rem 0.6rem;font-family:DM Mono,monospace;font-size:0.75rem;outline:none;box-sizing:border-box;';

  itemWrap.appendChild(itemCatRow);
  itemWrap.appendChild(itemBtnArea);
  itemWrap.appendChild(itemFreeInput);
  itemWrap.appendChild(itemHidden);
  holdingRow.appendChild(itemWrap);

  // --- 動作・ポーズ行（選択式＋テキスト）---
  const actionRow = document.createElement('div');
  actionRow.className = 'opt-row';
  actionRow.style.alignItems = 'start';
  const actionLabelWrap = makeOptLabel('⑭ 動作・ポーズ');
  const actionHidden = document.createElement('input');
  actionHidden.type = 'hidden';
  actionHidden.id = 'chara_action_'+idx;
  actionHidden.value = '';
  const actionWrap = document.createElement('div');
  actionWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.3rem;width:100%;';

  // グループごとにボタン生成
  let actionCurrentGroup = null;
  let actionBtnRow = null;
  function updateActionValue(){
    actionHidden.value = [...actionWrap.querySelectorAll('.multi-btn.active')].map(b=>b.dataset.act).join(',');
  }
  ACTION_OPTIONS.forEach(({v,label,group})=>{
    if(group !== actionCurrentGroup){
      actionCurrentGroup = group;
      const sep = document.createElement('div');
      sep.style.cssText = 'font-family:DM Mono,monospace;font-size:0.62rem;color:var(--muted);margin-top:0.15rem;';
      sep.textContent = group;
      actionWrap.appendChild(sep);
      actionBtnRow = document.createElement('div');
      actionBtnRow.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
      actionWrap.appendChild(actionBtnRow);
    }
    const btn = document.createElement('div');
    btn.className = 'multi-btn';
    btn.dataset.act = v;
    btn.textContent = label;
    btn.addEventListener('click',function(){
      this.classList.toggle('active');
      updateActionValue();
      // 「持つ」選択時に持ち物行を自動展開
      if(v==='holding'){
        const isActive = this.classList.contains('active');
        holdingRow.style.display = isActive ? 'flex' : 'none';
        holdingRow.style.outline = isActive ? '2px solid var(--accent)' : '';
        // カテゴリが未選択なら先頭カテゴリを自動展開
        if(isActive && !activeItemCat){
          const firstCatBtn = itemCatRow.querySelector('.age-btn');
          if(firstCatBtn) firstCatBtn.click();
        }
        if(isActive) holdingRow.scrollIntoView({behavior:'smooth', block:'nearest'});
      }
    });
    actionBtnRow.appendChild(btn);
  });
  // 自由入力
  const actionFreeInput = document.createElement('input');
  actionFreeInput.type = 'text';
  actionFreeInput.id = 'chara_action_free_'+idx;
  actionFreeInput.placeholder = '英語タグのみ（例: standing, arms_crossed）';
  actionFreeInput.className = 'inp-en';
  actionFreeInput.className = 'inp-en';
  actionFreeInput.style.cssText = 'width:100%;border-radius:5px;padding:0.35rem 0.6rem;font-family:DM Mono,monospace;font-size:0.75rem;outline:none;box-sizing:border-box;';
  actionFreeInput.addEventListener('input',function(){
    // 自由入力があればhiddenに上書き
    if(this.value.trim()) actionHidden.value = this.value.trim();
    else updateActionValue();
  });
  actionWrap.appendChild(actionFreeInput);
  actionWrap.appendChild(actionHidden);
  actionRow.appendChild(actionLabelWrap);
  actionRow.appendChild(actionWrap);

  // --- その他行をIDから取得 ---
  const miscRow = opt.querySelector('[id="chara_misc_'+idx+'"]')?.closest('.opt-row');

  // --- 頭から下の順に一括追加 ---
  [hairRow, hairColorRow,   // ① 髪型・髪色
   eyeStateRow,             // ② 目の状態
   eyeRow,                  // ③ 瞳の色
   mouthRow,                // ④ 口
   faceRow,                 // ⑤ 表情
   skinRow,                 // ⑥ 肌の色
   outfitRow,               // ⑦ 衣装・外見
   bustRow,                 // ⑧ バスト
   heightRow, buildRow, legsRow, // ⑨⑩⑪ 背丈・体型・脚
   attachRow,               // ⑫ 付属
   effectRow,               // ⑬ エフェクト
   actionRow,               // ⑭ 動作・ポーズ
   holdingRow,              // ⑮ 持ち物（持つ選択時に展開）
   posVRow, posHRow, posCRow, // ⑯⑰⑱ 画面位置
   miscRow                  // その他
  ].forEach(r=>{ if(r) opt.appendChild(r); });

  div.appendChild(opt);

  // 詳細ボタンのトグル
  expandBtn.addEventListener('click', ()=>{
    const open = opt.style.display === 'none';
    opt.style.display = open ? 'block' : 'none';
    expandBtn.textContent = open ? '－ 詳細' : '＋ 詳細';
  });

  return div;
}

function toggleExtraContent(){
  const el = document.getElementById('extraContent');
  const open = el.style.display === 'none';
  el.style.display = open ? 'block' : 'none';
  document.getElementById('extraContentArrow').textContent = open ? '▼' : '▶';
}

function toggleBlock(id, arrowId){
  const el = document.getElementById(id);
  const open = el.style.display === 'none';
  el.style.display = open ? 'block' : 'none';
  document.getElementById(arrowId).textContent = open ? '▼' : '▶';
}

function selScene(group, el){
  // 同じgroupのボタンだけ非アクティブにする
  document.querySelectorAll(`[data-scenegroup="${group}"]`).forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('f_'+group).value = el.dataset[group]||'';
}
function toggleScene(){
  const opt = document.getElementById('sceneOptional');
  const open = opt.style.display === 'none';
  opt.style.display = open ? 'block' : 'none';
  document.getElementById('sceneArrow').textContent = open ? '▼' : '▶';
}

function updateCharaBlocks(){
  const count = Math.max(1, Math.min(6, parseInt(document.getElementById('f_charcount').value)||1));
  const container = document.getElementById('charaContainer');
  const current = container.children.length;
  if(count > current){
    for(let i=current; i<count; i++) container.appendChild(makeCharaBlock(i));
  } else {
    while(container.children.length > count) container.removeChild(container.lastChild);
  }
}

function collectInput(){
  const series = document.getElementById('f_series').value.trim();
  const count = Math.max(1, Math.min(6, parseInt(document.getElementById('f_charcount').value)||1));
  const characters = [];
  let boys=0, girls=0, others=0;
  for(let i=0; i<count; i++){
    const name = (document.getElementById('chara_name_'+i)||{value:''}).value.trim();
    const genderEl = document.querySelector(`#chara_${i} .gender-btn.active`);
    const gender = genderEl ? genderEl.dataset.g : 'female';
    if(gender==='male') boys++;
    else if(gender==='female') girls++;
    else others++;
    const ageEl = document.querySelector(`#chara_${i} .age-btn.active`);
    const age = ageEl ? ageEl.dataset.a : 'unset';
    const isOriginal = document.getElementById('chara_orig_'+i)?.classList.contains('active')||false;
    const charaSeries = isOriginal ? '' : (document.getElementById('chara_series_'+i)||{value:''}).value.trim();
    let directTags = [];
    const ch = {name, gender, age, series: charaSeries || series};
    if(isOriginal) ch['original'] = true;
    OPT_FIELDS.forEach(f=>{
      const v = (document.getElementById(`chara_${f.id}_${i}`)||{value:''}).value.trim();
      if(v) ch[f.id] = v;
    });
    // 動作（選択式+自由入力）
    const actionVal = (document.getElementById(`chara_action_${i}`)||{value:''}).value.trim();
    if(actionVal){
      if((document.getElementById(`chara_action_lm_${i}_lm`)||{checked:true}).checked) ch['action']=actionVal;
      else actionVal.split(',').forEach(tag=>{ if(tag.trim()) addDirect(tag.trim()); });
    }
    function isLM(fieldId){ return (document.getElementById(fieldId+'_lm')||{checked:false}).checked; }
    // 性別: LLMチェックOFF→直接タグ化
    if(!isLM(`chara_gender_lm_${i}`)){
      const gTag = {female:'1girl',male:'1boy',other:''}[gender]||'';
      if(gTag) directTags.push(gTag);
      ch['gender'] = 'other';
    }
    // 年齢: LMチェックOFF→直接タグ化
    if(!isLM(`chara_age_lm_${i}`)){
      const ageMap = AGE_TAG_MAP[gender]||AGE_TAG_MAP['other'];
      const ageTag = ageMap[age]||'';
      if(ageTag) directTags.push(ageTag);
      ch['age'] = 'unset'; // LMには渡さない
    }
    function addDirect(tag){ if(tag) directTags.push(tag); }

    // バスト
    let bustVal = (document.getElementById(`chara_bust_${i}`)||{value:''}).value.trim();
    if(bustVal){ if(isLM(`chara_bust_lm_${i}`)) ch['bust']=bustVal; else addDirect(bustVal); }
    // 肌
    let skinVal = (document.getElementById(`chara_skin_${i}`)||{value:''}).value.trim();
    if(skinVal){ if(isLM(`chara_skin_lm_${i}`)) ch['skin']=skinVal; else addDirect(skinVal); }
    // 瞳
    let eyeVal = (document.getElementById(`chara_eyes_${i}`)||{value:''}).value.trim();
    if(eyeVal){ if(isLM(`chara_eyes_lm_${i}`)) ch['eyes']=eyeVal; else addDirect(eyeVal); } // heterochromia等はそのまま
    // 衣装
    let outfitVal = (document.getElementById(`chara_outfit_${i}`)||{value:''}).value.trim();
    if(isLM(`chara_outfit_lm_${i}`)) ch['outfit'] = outfitVal || 'default';
    else if(outfitVal) addDirect(outfitVal);
    // 髪
    let hairColor = (document.getElementById(`chara_haircolor_${i}`)||{value:''}).value.trim();
    let hairOther = (document.getElementById(`chara_hairother_${i}`)||{value:''}).value.trim();
    let hairStyle = (document.getElementById(`chara_hairstyle_${i}`)||{value:''}).value.trim();
    let hairColorFinal = hairOther || hairColor;
    if(isLM(`chara_haircolor_lm_${i}`)){
      if(hairColorFinal || hairStyle) ch['hair'] = [hairStyle, hairColorFinal].filter(Boolean).join('、');
    } else {
      if(hairColorFinal) addDirect(hairColorFinal);
      if(hairStyle) ch['hair'] = hairStyle; // 髪型は常にLMへ
    }
    // 体格
    let heightVal = (document.getElementById(`chara_height_${i}`)||{value:''}).value.trim();
    let buildVal  = (document.getElementById(`chara_build_${i}`)||{value:''}).value.trim();
    let legsVal   = (document.getElementById(`chara_legs_${i}`)||{value:''}).value.trim();
    if(isLM(`chara_height_${i}_lm`)||document.getElementById(`chara_height_${i}_lm`)?.checked===undefined){
      // makeAttrRowのチェック参照
    }
    // 持ち物（直接タグ化）
    const itemVal=(document.getElementById(`chara_item_${i}`)||{value:''}).value.trim();
    if(itemVal) itemVal.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });
    const itemFreeVal=(document.getElementById(`chara_item_free_${i}`)||{value:''}).value.trim();
    if(itemFreeVal) itemFreeVal.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });
    // 画面位置
    const posvVal = (document.getElementById(`chara_posv_${i}`)||{value:''}).value.trim();
    const poshVal = (document.getElementById(`chara_posh_${i}`)||{value:''}).value.trim();
    const poscVal = (document.getElementById(`chara_posc_${i}`)||{value:''}).value.trim();
    if(posvVal) addDirect(posvVal);
    if(poshVal) addDirect(poshVal);
    if(poscVal) addDirect(poscVal);
    // 付属
    ['ears','tail','wings'].forEach(f=>{
      const v=(document.getElementById(`chara_${f}_${i}`)||{value:''}).value.trim();
      if(v) addDirect(v);
    });
    const accVal=(document.getElementById(`chara_acc_${i}`)||{value:''}).value.trim();
    if(accVal) accVal.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });

    // 表情
    let effectVal = (document.getElementById(`chara_effect_${i}`)||{value:''}).value.trim();
    if(effectVal){
      if(isLM(`chara_effect_${i}`)) ch['effect']=effectVal;
      else effectVal.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });
    }
    let mouthVal = (document.getElementById(`chara_mouth_${i}`)||{value:''}).value.trim();
    if(mouthVal){
      if(isLM(`chara_mouth_${i}`)) ch['mouth']=mouthVal;
      else mouthVal.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });
    }
    let eyeStateVal = (document.getElementById(`chara_eyestate_${i}`)||{value:''}).value.trim();
    if(eyeStateVal){
      if(isLM(`chara_eyestate_${i}`)) ch['eye_state']=eyeStateVal;
      else eyeStateVal.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });
    }
    let faceVal = (document.getElementById(`chara_face_${i}`)||{value:''}).value.trim();
    if(faceVal){
      if(isLM(`chara_face_${i}`)) ch['face']=faceVal;
      else faceVal.split(',').forEach(f=>{ if(f.trim()) addDirect(f.trim()); });
    }

    let bodyLM_h = isLM(`chara_height_${i}`);
    let bodyLM_b = isLM(`chara_build_${i}`);
    let bodyLM_l = isLM(`chara_legs_${i}`);
    let bodyLMparts=[]; const bodyDirectTags=[];
    if(heightVal){ if(bodyLM_h) bodyLMparts.push(heightVal); else addDirect(heightVal); }
    if(buildVal){  if(bodyLM_b) bodyLMparts.push(buildVal);  else { if(buildVal) addDirect(buildVal); } }
    if(legsVal){   if(bodyLM_l) bodyLMparts.push(legsVal);   else { if(legsVal) addDirect(legsVal); } }
    if(bodyLMparts.length) ch['body'] = bodyLMparts.join('、');
    ch['_directTags'] = directTags;
    characters.push(ch);
  }
  const genderSummary = [boys?boys+'boy'+(boys>1?'s':''):'', girls?girls+'girl'+(girls>1?'s':''):'', others?others+'other'+(others>1?'s':''):''].filter(Boolean).join(', ');
  const place   = document.getElementById('f_place').value.trim();
  const misc    = document.getElementById('f_misc').value.trim();
  const world   = document.getElementById('f_world')?.value.trim()||'';
  const outdoor = document.getElementById('f_outdoor')?.value.trim()||'';
  const tod     = document.getElementById('f_tod')?.value.trim()||'';
  const weather = document.getElementById('f_weather')?.value.trim()||'';
  const sceneParts = [world, outdoor, place, tod, weather, misc].filter(Boolean);
  const payload = {global_series: series, characters, gender_summary: genderSummary,
    place: sceneParts.join('、'), mood: misc};
  // キャラごとのdirectTagsをまとめてextraに合流
  const charDirectTags = characters.flatMap(c=>{ const t=c._directTags||[]; delete c._directTags; return t; });
  const extraTagList = Array.from(extraTags);
  return {valid: !!(series || characters.some(c=>c.name)), payload, genderSummary, extraTagList, charDirectTags};
}

// ===== 初期化 =====
function initSizePresets(){
  const sel = document.getElementById('sizePreset');
  if(!sel) return;
  (__OPT__.image_size_presets||[]).forEach(({v,label},i)=>{
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = label;
    sel.appendChild(opt);
  });
  // 最初のプリセットを適用
  if(sel.options.length > 0) applyPreset(sel.options[0].value);
}

function initSceneButtons(){
  // 世界観
  const worldContainer = document.getElementById('world_btns');
  (__OPT__.scene_world||[]).forEach(({v,label},i)=>{
    const btn = document.createElement('div');
    btn.className = 'period-btn' + (i===0?' active':'');
    btn.dataset.world = v;
    btn.dataset.scenegroup = 'world';
    btn.textContent = label;
    btn.addEventListener('click', ()=>selScene('world',btn));
    worldContainer.appendChild(btn);
  });
  // 時間帯
  const todContainer = document.getElementById('tod_btns');
  (__OPT__.scene_tod||[]).forEach(({v,label},i)=>{
    const btn = document.createElement('div');
    btn.className = 'period-btn' + (i===0?' active':'');
    btn.dataset.tod = v;
    btn.dataset.scenegroup = 'tod';
    btn.textContent = label;
    btn.addEventListener('click', ()=>selScene('tod',btn));
    todContainer.appendChild(btn);
  });
  // 天気
  const weatherContainer = document.getElementById('weather_btns');
  (__OPT__.scene_weather||[]).forEach(({v,label},i)=>{
    const btn = document.createElement('div');
    btn.className = 'period-btn' + (i===0?' active':'');
    btn.dataset.weather = v;
    btn.dataset.scenegroup = 'weather';
    btn.textContent = label;
    btn.addEventListener('click', ()=>selScene('weather',btn));
    weatherContainer.appendChild(btn);
  });
  // 安全タグ
  const safetyContainer = document.getElementById('safety_btns');
  (__OPT__.safety_options||[]).forEach(({v,label})=>{
    const btn = document.createElement('div');
    btn.className = 'safety-btn';
    btn.dataset.s = v;
    btn.textContent = label;
    btn.addEventListener('click', ()=>selSafety(btn));
    safetyContainer.appendChild(btn);
  });
}

function initCharaAttrButtons(idx){
  // 性別ボタン動的生成（makeCharaBlock呼び出し時に使用）
}

document.addEventListener('DOMContentLoaded', ()=>{ loadCharaPresets().then(()=>updateCharaBlocks()); loadSettings(); initExtraPresets(); initQualityMeta(); initQualityMetaNeg(); initNegExtraPresets(); initNegSafetyButtons(); loadNegStyleTagsFromServer(); initSceneButtons(); initSizePresets(); loadLastSession(); loadStyleTagsFromServer(); });

async function generate(){
  if(running)return;
  const {valid, payload, charDirectTags} = collectInput();
  if(!valid){alert('シリーズまたはいずれかのキャラ名を入力してください');return;}
  // 生成開始時に設定を自動保存
  await saveSettings();
  payload.extra_tags = Array.from(extraTags);
  payload.prompt_prefix = collectPromptPrefix();
  payload.negative_prompt = collectNegativePrompt();
  const extraNoteJa = document.getElementById('extraNoteJa').value.trim();
  const extraNoteEn = document.getElementById('extraNoteEn').value.trim();
  if(extraNoteJa) payload.extra_note_ja = extraNoteJa;
  if(extraNoteEn) payload.extra_note_en = extraNoteEn;
  const input = JSON.stringify(payload);
  running=true;
  document.getElementById('btn').disabled=true;
  document.getElementById('cancelBtn').classList.add('show');
  document.getElementById('statusBox').classList.add('show');
  const steps=document.getElementById('steps');
  const promptOutput=document.getElementById('promptOutput');
  steps.innerHTML='';
  promptOutput.classList.remove('show');
  document.getElementById('lmLabel').style.display='none';
  document.getElementById('finalLabel').style.display='none';
  document.getElementById('promptFinal').style.display='none';
  document.getElementById('negFinalLabel').style.display='none';
  document.getElementById('promptNegFinal').style.display='none';

  try{
    const useLLM = document.getElementById('useLLM').checked;
    if(!useLLM){ setStep(steps,'s1','done','LLM: スキップ'); }
    else { setStep(steps,'s1','active','LLM: プロンプト生成中...'); }
    const res=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input,use_llm:document.getElementById('useLLM').checked,width:selectedW,height:selectedH,fmt:selectedFmt,count:selectedCount,extra_tags:Array.from(extraTags),char_direct_tags:charDirectTags,prompt_prefix:collectPromptPrefix(),extra_note_en:document.getElementById('extraNoteEn').value.trim()})});
    const data=await res.json();
    if(data.error){
      setStep(steps,'s1','error','エラー: '+data.error);
    }else{
      setStep(steps,'s1','done','LLM: 完了');
      lastPositivePrompt=data.positive_prompt;
      // LLM生成部
      document.getElementById('lmLabel').style.display='block';
      promptOutput.textContent=data.positive_prompt.replace(/\\n/g,'\n');
      promptOutput.classList.add('show');
      // ComfyUI送信ポジティブプロンプト（final）
      if(data.final_prompt){
        document.getElementById('finalLabel').style.display='block';
        const finalEl = document.getElementById('promptFinal');
        finalEl.textContent = data.final_prompt;
        finalEl.style.display = 'block';
      }
      // ComfyUI送信ネガティブプロンプト
      if(data.negative_prompt){
        document.getElementById('negFinalLabel').style.display='block';
        const negFinalEl = document.getElementById('promptNegFinal');
        negFinalEl.textContent = data.negative_prompt;
        negFinalEl.style.display = 'block';
      }
      if(data.comfyui_sent){
        const ids=(data.prompt_ids||[data.prompt_id]).join(', ');
        const n=data.prompt_ids?data.prompt_ids.length:1;
        setStep(steps,'s2','done',`ComfyUI: ${n}枚キューに追加`);
        // ⑤ ComfyUI生成完了まで生成開始を無効化
        setStep(steps,'s3','active','ComfyUI: 生成中...');
        pollComfyUIComplete(data.prompt_ids||[data.prompt_id], steps);
        return; // running解除はpoll完了後
      }else{
        setStep(steps,'s2','error','ComfyUI: 送信失敗 — '+(data.comfyui_error||'不明なエラー'));
      }
    }
  }catch(e){
    setStep(steps,'s1','error','ネットワークエラー: '+e.message);
    running=false;
    document.getElementById('btn').disabled=false;
    document.getElementById('cancelBtn').classList.remove('show');
    if(lastPositivePrompt){ document.getElementById('regenBtn').classList.add('show'); }
  }
}

async function cancelGenerate(){
  try{
    await fetch('/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  }catch(e){}
  running=false;
  document.getElementById('btn').disabled=false;
  document.getElementById('cancelBtn').classList.remove('show');
  setStep(document.getElementById('steps'),'s_cancel','error','■ 生成中止しました');
  if(lastPositivePrompt){ document.getElementById('regenBtn').classList.add('show'); }
}

async function pollComfyUIComplete(promptIds, steps){
  // Pipelineサーバー経由でComfyUI /historyを確認（CORS回避）
  const pending = new Set(promptIds);
  let tries = 0;
  while(pending.size > 0 && tries < 300){
    await new Promise(r=>setTimeout(r, 2000));
    tries++;
    try{
      const ids = [...pending].join(',');
      const res = await fetch(`/poll_status?ids=${encodeURIComponent(ids)}`).catch(()=>null);
      if(!res) continue;
      const data = await res.json();
      for(const pid of (data.completed||[])) pending.delete(pid);
      const done = promptIds.length - pending.size;
      const q = data.queue||{};
      let queueStr = '';
      if(q.position != null){
        queueStr = ` — キュー待機中 (${q.position}番目)`;
      } else if(q.running > 0 || q.pending > 0){
        queueStr = ` — キュー: 実行中${q.running}件 / 待機${q.pending}件`;
      }
      setStep(steps,'s3','active',`ComfyUI: 生成中 (${done}/${promptIds.length}枚完了)${queueStr}`);
    }catch(e){}
  }
  setStep(steps,'s3','done',`ComfyUI: 生成完了 (${promptIds.length}枚)`);
  running=false;
  document.getElementById('btn').disabled=false;
  document.getElementById('cancelBtn').classList.remove('show');
  if(lastPositivePrompt){ document.getElementById('regenBtn').classList.add('show'); }
  autoSaveSession();
}

async function regenPrompt(){
  if(running||!lastPositivePrompt)return;
  running=true;
  document.getElementById('btn').disabled=true;
  document.getElementById('regenBtn').classList.remove('show');
  document.getElementById('cancelBtn').classList.add('show');
  document.getElementById('statusBox').classList.add('show');
  const steps=document.getElementById('steps');
  steps.innerHTML='';
  try{
    setStep(steps,'s_regen','active','ComfyUI: 再画像生成中...');
    const regenExtraTags = Array.from(extraTags);
    const regenExtraEn = document.getElementById('extraNoteEn').value.trim();
    const res=await fetch('/regen',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt:lastPositivePrompt,width:selectedW,height:selectedH,fmt:selectedFmt,count:selectedCount,
        extra_tags:regenExtraTags, extra_note_en:regenExtraEn,
        prompt_prefix:collectPromptPrefix(),
        negative_prompt:collectNegativePrompt()})});
    const data=await res.json();
    if(data.error){
      setStep(steps,'s_regen','error','エラー: '+data.error);
      running=false;
      document.getElementById('btn').disabled=false;
      document.getElementById('cancelBtn').classList.remove('show');
      document.getElementById('regenBtn').classList.add('show');
    }else{
      const promptIds = data.prompt_ids || [data.prompt_id];
      setStep(steps,'s_regen','done','ComfyUI: キューに追加 ('+promptIds.length+'枚)');
      // 送信ポジティブ・ネガティブ表示を更新
      if(data.final_prompt){
        document.getElementById('finalLabel').style.display='block';
        const finalEl = document.getElementById('promptFinal');
        finalEl.textContent = data.final_prompt;
        finalEl.style.display = 'block';
      }
      if(data.negative_prompt){
        document.getElementById('negFinalLabel').style.display='block';
        const negFinalEl = document.getElementById('promptNegFinal');
        negFinalEl.textContent = data.negative_prompt;
        negFinalEl.style.display = 'block';
      }
      pollComfyUIComplete(promptIds, steps);
      return;
    }
  }catch(e){
    setStep(steps,'s_regen','error','エラー: '+e.message);
    running=false;
    document.getElementById('btn').disabled=false;
    document.getElementById('cancelBtn').classList.remove('show');
    document.getElementById('regenBtn').classList.add('show');
  }
}

document.addEventListener('keydown',e=>{
  if(e.key==='Enter'&&e.ctrlKey) generate();
});
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    cancel_event = __import__('threading').Event()
    lm_session = None
    def log_message(self,fmt,*args):pass

    def do_GET(self):
        if self.path=='/':
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers()
            ui_opts = load_ui_options()
            injected = HTML.replace(
                '<script>',
                '<script>\nconst __OPT__ = ' + json.dumps(ui_opts, ensure_ascii=False) + ';\n',
                1  # 最初の<script>タグだけ
            )
            self.wfile.write(injected.encode('utf-8'))
        elif self.path=='/config':
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_config(),ensure_ascii=False).encode('utf-8'))
        elif self.path.startswith('/test_connection'):
            from urllib.parse import urlparse, parse_qs
            import urllib.request as _ureq
            qs = parse_qs(urlparse(self.path).query)
            target = qs.get('target',[''])[0]
            cfg = load_config()
            result = {'ok': False, 'message': '不明なターゲット'}
            if target == 'comfyui':
                comfy = cfg.get('comfyui_url','http://127.0.0.1:8188').rstrip('/')
                try:
                    with _ureq.urlopen(comfy+'/system_stats', timeout=5) as r:
                        stats = json.loads(r.read())
                    python_ver = stats.get('system',{}).get('python_version','?')
                    result = {'ok': True, 'message': f'ComfyUI 接続OK (Python {python_ver})'}
                except Exception as e:
                    result = {'ok': False, 'message': f'ComfyUI 接続失敗: {e}'}
            elif target == 'llm':
                platform = cfg.get('llm_platform','')
                url = cfg.get('llm_url','').rstrip('/')
                token = cfg.get('llm_token','').strip()
                model = cfg.get('llm_model','')
                if not url:
                    result = {'ok': False, 'message': 'LLM URLが未設定です'}
                else:
                    try:
                        if platform == 'gemini':
                            # Gemini OpenAI互換のmodelsエンドポイント
                            test_url = url + '/models'
                        else:
                            base = url.removesuffix('/v1')
                            test_url = base + '/v1/models'
                        headers = {'Content-Type': 'application/json'}
                        if token:
                            headers['Authorization'] = f'Bearer {token}'
                        req = _ureq.Request(test_url, headers=headers)
                        with _ureq.urlopen(req, timeout=5) as r:
                            r.read()
                        result = {'ok': True, 'message': f'LLM 接続OK ({platform or "カスタム"}: {url})'}
                    except Exception as e:
                        result = {'ok': False, 'message': f'LLM 接続失敗: {e}'}
            print(f"[接続テスト] {'OK' if result['ok'] else 'NG'}: {result['message']}")
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
        elif self.path.startswith('/poll_status'):
            from urllib.parse import urlparse, parse_qs
            import urllib.request as _ureq
            qs = parse_qs(urlparse(self.path).query)
            ids = qs.get('ids',[''])[0].split(',')
            cfg = load_config()
            comfy = cfg.get('comfyui_url','http://127.0.0.1:8188').rstrip('/')
            completed = []
            queue_info = {'running': 0, 'pending': 0, 'position': None}
            try:
                with _ureq.urlopen(comfy+'/history',timeout=3) as r:
                    hist = json.loads(r.read())
                for pid in ids:
                    if pid and pid in hist and hist[pid].get('status',{}).get('completed'):
                        completed.append(pid)
            except Exception:
                pass
            try:
                with _ureq.urlopen(comfy+'/queue',timeout=3) as r:
                    q = json.loads(r.read())
                running_list = q.get('queue_running', [])
                pending_list = q.get('queue_pending', [])
                queue_info['running'] = len(running_list)
                queue_info['pending'] = len(pending_list)
                # 自分のジョブがキュー内の何番目か
                for pid in ids:
                    if pid not in completed:
                        for i, item in enumerate(pending_list):
                            if len(item) > 1 and item[1] == pid:
                                queue_info['position'] = i + 1
                                break
            except Exception:
                pass
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'completed':completed,'total':len(ids),'queue':queue_info},ensure_ascii=False).encode('utf-8'))
        elif self.path=='/session':
            sf=_sf('anima_session_last.json')
            data={}
            if os.path.exists(sf):
                with open(sf,encoding='utf-8') as f: data=json.load(f)
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data,ensure_ascii=False).encode('utf-8'))
        elif self.path.startswith('/generate_preset'):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            chara_name = qs.get('name',[''])[0].strip()
            chara_series = qs.get('series',[''])[0].strip()
            if not chara_name:
                self.send_response(400)
                self.send_header('Content-Type','application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error':'キャラ名が必要です'}).encode())
            else:
                import urllib.request as _ureq
                cfg = load_config()
                wiki_text = ''
                tag_guess = chara_name.lower().replace(' ','_').replace('\u30fb','_').replace('\u3000','_')
                try:
                    from urllib.parse import quote
                    wiki_url = 'https://danbooru.donmai.us/wiki_pages/'+quote(tag_guess)+'.json'
                    req = _ureq.Request(wiki_url, headers={'User-Agent':'anima-pipeline/1.0'})
                    with _ureq.urlopen(req, timeout=10) as r:
                        wiki_data = json.loads(r.read())
                        wiki_text = wiki_data.get('body','')[:2000]
                    print('[プリセット生成] Wiki取得: '+tag_guess+' ('+str(len(wiki_text))+'文字)')
                except Exception as e:
                    print('[プリセット生成] Wiki取得失敗: '+str(e))
                _tpl = load_preset_gen_prompt()
                preset_prompt = _tpl.replace('{chara_name}', chara_name).replace('{chara_series}', chara_series or 'unknown').replace('{wiki_text}', wiki_text or 'Not found. Use your training knowledge.')
                try:
                    result_json = call_llm(preset_prompt, cfg)
                    import re as _re
                    result_json = _re.sub(r'```[a-z]*','',result_json).strip().strip('`').strip()
                    preset_data = json.loads(result_json)
                    preset = {
                        'name': chara_name,
                        'data': {
                            'name': chara_name,
                            'series': chara_series,
                            'gender': preset_data.get('gender','female'),
                            'age': preset_data.get('age','adult'),
                            'original': False,
                            'hairstyle': preset_data.get('hairstyle',''),
                            'hairstyle_lm': '',
                            'haircolor': preset_data.get('haircolor',''),
                            'eyes': preset_data.get('eyes',''),
                            'skin': preset_data.get('skin',''),
                            'bust': preset_data.get('bust',''),
                            'outfit': '',  # outfit_freeに入れるためここは空
                            'outfit_free': preset_data.get('outfit',''),
                            'body': '', 'misc': '', 'action': '', 'hair': '',
                            'face': '', 'eyestate': '', 'mouth': '', 'effect': '',
                            'ears': '', 'tail': '', 'wings': '', 'acc': '',
                            'item': '', 'posv': '', 'posh': '',
                            'outfit_cat': '', 'outfit_color': '', 'outfit_item': '',
                            'skinOther': '', 'hairstyle_free': '', 'hairother': '',
                            'action_free': '', 'item_free': '',
                        },
                        'savedAt': __import__('datetime').datetime.now().isoformat(),
                    }
                    os.makedirs(CHARA_PRESETS_DIR, exist_ok=True)
                    existing = sorted([f for f in os.listdir(CHARA_PRESETS_DIR) if f.endswith('.json')])
                    n = len(existing) + 1
                    safe_name = chara_name.replace('/','_').replace('\\','_')[:30]
                    filename = '{:03d}_{}.json'.format(n, safe_name)
                    with open(os.path.join(CHARA_PRESETS_DIR, filename),'w',encoding='utf-8') as f:
                        json.dump(preset, f, ensure_ascii=False, indent=2)
                    preset['_filename'] = filename
                    print('[プリセット生成] 保存: '+filename)
                    self.send_response(200)
                    self.send_header('Content-Type','application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'ok':True,'preset':preset},ensure_ascii=False).encode())
                except Exception as e:
                    print('[プリセット生成] エラー: '+str(e))
                    self.send_response(500)
                    self.send_header('Content-Type','application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error':str(e)}).encode())
        elif self.path=='/chara_presets':
            presets = []
            if os.path.exists(CHARA_PRESETS_DIR):
                for fn in sorted(os.listdir(CHARA_PRESETS_DIR)):
                    if fn.endswith('.json'):
                        try:
                            with open(os.path.join(CHARA_PRESETS_DIR,fn),'r',encoding='utf-8') as f:
                                p = json.load(f)
                                p['_filename'] = fn
                                presets.append(p)
                        except: pass
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(presets,ensure_ascii=False).encode('utf-8'))
        elif self.path=='/extra_tags':
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"tags":load_extra_tags()},ensure_ascii=False).encode('utf-8'))
        elif self.path=='/style_tags':
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"tags":load_style_tags()},ensure_ascii=False).encode('utf-8'))
        elif self.path=='/neg_extra_tags':
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            import os as _os
            _is_default = not _os.path.exists(NEG_EXTRA_TAGS_FILE)
            self.wfile.write(json.dumps({"tags":load_neg_extra_tags(),"is_default":_is_default},ensure_ascii=False).encode('utf-8'))
        elif self.path=='/neg_style_tags':
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"tags":load_neg_style_tags()},ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length=int(self.headers.get('Content-Length',0))
        body=json.loads(self.rfile.read(length))

        if self.path=='/config':
            save_config(body)
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        elif self.path=='/session':
            sf=_sf('anima_session_last.json')
            with open(sf,'w',encoding='utf-8') as f: json.dump(body,f,ensure_ascii=False,indent=2)
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        elif self.path=='/chara_presets':
            # body: {action:'save'|'delete', preset:{name,data}, filename?}
            action = body.get('action','save')
            os.makedirs(CHARA_PRESETS_DIR, exist_ok=True)
            result = {'ok': True}
            try:
                if action == 'save':
                    preset = body.get('preset',{})
                    # ファイル名: 連番_名前.json
                    existing = sorted([f for f in os.listdir(CHARA_PRESETS_DIR) if f.endswith('.json')])
                    n = len(existing) + 1
                    safe_name = preset.get('name','preset').replace('/','_').replace('\\','_')[:30]
                    filename = f'{n:03d}_{safe_name}.json'
                    # 同名上書き
                    if body.get('filename'):
                        filename = body['filename']
                    filepath = os.path.join(CHARA_PRESETS_DIR, filename)
                    with open(filepath,'w',encoding='utf-8') as f:
                        json.dump(preset, f, ensure_ascii=False, indent=2)
                    result['filename'] = filename
                    print(f'[プリセット] 保存: {filename}')
                elif action == 'delete':
                    filename = body.get('filename','')
                    if filename:
                        filepath = os.path.join(CHARA_PRESETS_DIR, filename)
                        if os.path.exists(filepath):
                            os.remove(filepath)
                            print(f'[プリセット] 削除: {filename}')
            except Exception as e:
                result = {'ok': False, 'error': str(e)}
                print(f'[プリセット] エラー: {e}')
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result,ensure_ascii=False).encode('utf-8'))
        elif self.path=='/extra_tags':
            save_extra_tags(body.get("tags",[]))
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        elif self.path=='/style_tags':
            save_style_tags(body.get("tags",[]))
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        elif self.path=='/neg_extra_tags':
            save_neg_extra_tags(body.get("tags",[]))
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        elif self.path=='/neg_style_tags':
            save_neg_style_tags(body.get("tags",[]))
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        elif self.path=='/regen':
            try:
                cfg=load_config()
                prompt=body.get('prompt','')
                regen_extra_tags=body.get('extra_tags',[])
                regen_extra_en=body.get('extra_note_en','').strip()
                regen_prompt_prefix=body.get('prompt_prefix',[])
                regen_negative=body.get('negative_prompt','').strip()
                width=body.get('width',1024)
                height=body.get('height',1024)
                fmt=body.get('fmt','png')
                if not prompt:
                    raise ValueError('プロンプトが空です')
                # Extraタグ・英語追記を適用
                prompt_flat = prompt.replace("\\n"," ").replace("\n"," ")
                if regen_prompt_prefix:
                    prompt_flat=", ".join(str(t) for t in regen_prompt_prefix)+", "+prompt_flat
                if regen_extra_tags:
                    extra_str=", ".join(str(t) for t in regen_extra_tags)
                    if "masterpiece" in prompt_flat:
                        prompt_flat=prompt_flat.replace("masterpiece", extra_str+", masterpiece",1)
                    else:
                        prompt_flat=prompt_flat+", "+extra_str
                if regen_extra_en:
                    prompt_flat=prompt_flat.rstrip(". ").rstrip(",")+", "+regen_extra_en
                prompt=prompt_flat
                Handler.cancel_event.clear()
                count=max(1,int(body.get('count',1)))
                import datetime
                date_folder=datetime.date.today().strftime('%Y-%m-%d')
                output_dir=cfg.get('comfyui_output_dir','').strip()
                if not output_dir:
                    wf_path=cfg.get('workflow_json_path','')
                    if wf_path and not os.path.isabs(wf_path):
                        wf_path=os.path.join(_base_dir, wf_path)
                    wf_path=wf_path.replace(os.sep,'/')
                    parts=wf_path.split('/')
                    output_dir=''
                    for i,p in enumerate(parts):
                        if p.lower()=='comfyui':
                            output_dir=os.path.normpath('/'.join(parts[:i+1])+'/output')
                            break
                    if not output_dir:
                        output_dir=os.path.normpath(os.path.join(os.path.dirname(wf_path),'..','..',  'output'))
                comfyui_url=cfg.get('comfyui_url','http://127.0.0.1:8188')
                prompt_ids=[]
                for i in range(count):
                    if Handler.cancel_event.is_set(): break
                    cid=str(uuid.uuid4())
                    pid=send_to_comfyui(prompt,cfg,width,height,fmt,cid,negative_prompt=regen_negative)
                    prompt_ids.append(pid)
                    print(f"[ComfyUI] 再生成キュー ({i+1}/{count}): {pid}")
                    if fmt=='webp':
                        watch_and_convert(comfyui_url,output_dir,date_folder,pid,cid)
                result={'prompt_ids':prompt_ids,'prompt_id':prompt_ids[0] if prompt_ids else '','final_prompt':prompt,'negative_prompt':regen_negative}
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result,ensure_ascii=False).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type','application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error':str(e)}).encode())
            return

        elif self.path=='/cancel':
            try:
                cfg=load_config()
                comfyui_url=cfg.get('comfyui_url','http://127.0.0.1:8188')
                import urllib.request as _ur
                # 実行中ジョブを中断
                req=_ur.Request(comfyui_url.rstrip('/')+'/interrupt',data=b'',method='POST')
                _ur.urlopen(req)
                # キュー待機中もクリア
                req2=_ur.Request(
                    comfyui_url.rstrip('/')+'/queue',
                    data=json.dumps({'clear':True}).encode(),
                    headers={'Content-Type':'application/json'},
                    method='POST'
                )
                _ur.urlopen(req2)
                Handler.cancel_event.set()
                if Handler.lm_session:
                    try: Handler.lm_session.close()
                    except: pass
                print('[ComfyUI] 生成中止')
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.end_headers()
                self.wfile.write(b'{"ok":true}')
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type','application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error':str(e)}).encode())

        elif self.path=='/generate':
            user_input=body.get('input','')
            use_llm=body.get('use_llm',True)
            extra_tags=body.get('extra_tags',[])
            char_direct_tags=body.get('char_direct_tags',[])
            extra_note_en=body.get('extra_note_en','').strip()
            prompt_prefix=body.get('prompt_prefix',[])
            negative_prompt=body.get('negative_prompt','').strip()
            img_width=body.get('width',1024)
            img_height=body.get('height',1024)
            img_fmt=body.get('fmt','png')
            img_count=max(1,int(body.get('count',1)))
            print(f"[DEBUG] 受信: fmt={img_fmt} width={body.get('width')} height={body.get('height')} count={img_count}")
            cfg=load_config()
            Handler.cancel_event.clear()
            result={"positive_prompt":"","comfyui_sent":False,"prompt_id":"","error":"","comfyui_error":""}

            try:
                if use_llm:
                    print(f"\n[LLM] 生成開始: {user_input}")
                    raw=call_llm(user_input,cfg)
                    positive=extract_positive_prompt(raw)
                    if Handler.cancel_event.is_set():
                        result["error"]="中止されました"
                        return
                    print(f"[LLM] 完了: {positive}")
                    result["positive_prompt"]=positive
                    positive_flat=positive.replace("\\n"," ").replace("\n"," ")
                else:
                    print("[LLM] スキップ")
                    result["positive_prompt"]=""
                    positive_flat=""
                # prefix（品質・メタ・安全・スタイル・期間）をプロンプト先頭に挿入
                if prompt_prefix:
                    positive_flat=", ".join(str(t) for t in prompt_prefix)+("", ", "+positive_flat)[bool(positive_flat)]
                if extra_tags:
                    extra_str=", ".join(str(t) for t in extra_tags)
                    quality_marker="masterpiece"
                    if quality_marker in positive_flat:
                        positive_flat=positive_flat.replace(quality_marker, extra_str+", "+quality_marker,1)
                    else:
                        positive_flat=(positive_flat+", "+extra_str).strip(", ")
                if char_direct_tags:
                    direct_str=", ".join(str(t) for t in char_direct_tags if t)
                    positive_flat=(positive_flat+", "+direct_str).strip(", ")
                if extra_note_en:
                    positive_flat=positive_flat.rstrip(". ").rstrip(",")+", "+extra_note_en
                result["final_prompt"]=positive_flat
                result["negative_prompt"]=negative_prompt

                try:
                    print("[ComfyUI] 送信中...")
                    # WebP用output_dir計算（共通）
                    import datetime
                    date_folder = datetime.date.today().strftime("%Y-%m-%d")
                    output_dir = cfg.get("comfyui_output_dir","").strip()
                    if not output_dir:
                        wf_path = cfg.get("workflow_json_path","")
                        if wf_path and not os.path.isabs(wf_path):
                            wf_path = os.path.join(_base_dir, wf_path)
                        wf_path = wf_path.replace(os.sep, "/")
                        parts = wf_path.split("/")
                        output_dir = ""
                        for i, p in enumerate(parts):
                            if p.lower() == "comfyui":
                                output_dir = os.path.normpath("/".join(parts[:i+1]) + "/output")
                                break
                        if not output_dir:
                            output_dir = os.path.normpath(os.path.join(
                                os.path.dirname(wf_path), "..", "..", "output"))
                    comfyui_url = cfg.get('comfyui_url','http://127.0.0.1:8188')
                    prompt_ids = []
                    for i in range(img_count):
                        if Handler.cancel_event.is_set():
                            break
                        cid = str(uuid.uuid4())
                        pid = send_to_comfyui(positive_flat, cfg, img_width, img_height, img_fmt, cid, negative_prompt=negative_prompt)
                        prompt_ids.append(pid)
                        print(f"[ComfyUI] キューに追加 ({i+1}/{img_count}): {pid}")
                        if img_fmt == "webp":
                            watch_and_convert(comfyui_url, output_dir, date_folder, pid, cid)
                    result["comfyui_sent"] = True
                    result["prompt_ids"] = prompt_ids
                    result["prompt_id"] = prompt_ids[0] if prompt_ids else ""
                except Exception as e:
                    result["comfyui_error"]=str(e)
                    print(f"[ComfyUI] エラー: {e}")

            except requests.exceptions.HTTPError as e:
                bt=e.response.text[:400] if e.response else ""
                result["error"]=f"{e} | {bt}"
                print(f"[エラー] {e} | {bt}")
            except Exception as e:
                result["error"]=str(e)
                print(f"[エラー] {e}")

            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result,ensure_ascii=False).encode('utf-8'))


def check_server(name,url,path="/"):
    try:
        requests.get(url+path,timeout=3)
        print(f"  ✓ {name}: 接続OK ({url})")
    except Exception as e:
        print(f"  ✗ {name}: 接続失敗 ({url}) → {e}")

def main():
    cfg=load_config()
    print("="*55)
    print("  Anima Pipeline")
    print("="*55)
    print("\n[接続確認]")
    check_server("LLM",cfg["llm_url"],"/api/v1/models")
    check_server("ComfyUI  ",cfg["comfyui_url"],"/system_stats")
    print()
    print(f"  UI:           http://localhost:{UI_PORT}")
    print(f"  LM Studio:    {cfg['llm_url']}")
    print(f"  モデル:       {cfg['llm_model']}")
    print(f"  ComfyUI:      {cfg['comfyui_url']}")
    print(f"  ワークフロー: {cfg.get('workflow_json_path','未設定')}")
    print(f"  設定ファイル: {CONFIG_FILE}")
    print("="*55)
    print("\nCtrl+C で停止\n")
    server=HTTPServer(('0.0.0.0',UI_PORT),Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました。")

if __name__=='__main__':
    main()
