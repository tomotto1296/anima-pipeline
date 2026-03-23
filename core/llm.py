import os

import requests


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_DIR = os.path.join(BASE_DIR, "settings")


def _sf(name: str) -> str:
    return os.path.join(SETTINGS_DIR, name)


SYSTEM_PROMPT_FILE = _sf("llm_system_prompt.txt")
PRESET_GEN_PROMPT_FILE = _sf("preset_gen_prompt.txt")


def load_preset_gen_prompt():
    try:
        with open(PRESET_GEN_PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return (
            "Generate a character preset JSON for anime image generation.\n"
            "Character: {chara_name}\nSeries: {chara_series}\nDanbooru Wiki: {wiki_text}\n\n"
            'Output ONLY a valid JSON object: {"gender":"female or male or other","age":"adult or child or unset",'
            '"hairstyle":"hair style tags e.g. long_hair,ponytail","haircolor":"single hair color tag e.g. purple_hair",'
            '"eyes":"single eye color tag e.g. red_eyes","skin":"skin tag or empty","bust":"bust tag or empty",'
            '"outfit":"default outfit tags comma separated"}\n'
            "IMPORTANT: Be accurate about hair/eye colors.\nRules: lowercase underscore Danbooru tags only. Output ONLY the JSON."
        )


def load_system_prompt():
    try:
        with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[WARNING] {SYSTEM_PROMPT_FILE} not found. Using empty system prompt.")
        return ""



def make_call_llm(set_session):
    def _call(user_input: str, cfg: dict) -> str:
        return call_llm(user_input, cfg, set_session=set_session)

    return _call
def call_llm(user_input: str, cfg: dict, set_session=None) -> str:
    _raw = cfg["llm_url"].rstrip("/")
    platform = cfg.get("llm_platform", "")
    if platform == "gemini":
        url = f"{_raw}/chat/completions"
    else:
        _base = _raw.removesuffix("/v1")
        url = f"{_base}/v1/chat/completions"
    print(f"[LLM] 送信先URL: {url}")
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

    if platform == "lmstudio" or platform == "":
        integrations = [
            i
            for i in [
                {"type": "plugin", "id": "mcp/danbooru-rag"} if cfg.get("tool_danbooru_rag", True) else None,
                {"type": "plugin", "id": "mcp/danbooru-api"} if cfg.get("tool_danbooru_api", True) else None,
                {"type": "plugin", "id": "danielsig/duckduckgo"} if cfg.get("tool_duckduckgo", True) else None,
            ]
            if i
        ]
        if integrations:
            payload["integrations"] = integrations

    headers = {"Content-Type": "application/json"}
    token = cfg.get("llm_token", "").strip()
    print(f"[LLM] プラットフォーム: {platform or 'なし'}")
    print(f"[LLM] URL: {cfg.get('llm_url', '')}")
    print(f"[LLM] token={'設定済み(' + str(len(token)) + '文字)' if token else '未設定・空'}")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    session = requests.Session()
    if callable(set_session):
        try:
            set_session(session)
        except Exception:
            pass
    try:
        resp = session.post(url, json=payload, headers=headers, timeout=300)
    finally:
        if callable(set_session):
            try:
                set_session(None)
            except Exception:
                pass
    print(f"[LLM] status={resp.status_code}")
    resp.raise_for_status()
    data = resp.json()
    if "choices" in data and data["choices"]:
        msg = data["choices"][0].get("message", {})
        content = msg.get("content")
        if content:
            return content
        finish_reason = data["choices"][0].get("finish_reason", "")
        print(f"[LLM] contentなし finish_reason={finish_reason!r} → フィルターブロックの可能性")
        raise ValueError(
            f"LLMがコンテンツを返しませんでした (finish_reason={finish_reason!r}). システムプロンプトを確認してください。"
        )
    if "output" in data:
        blocks = [i.get("content", "") for i in data["output"] if i.get("type") == "message" and i.get("content", "").strip()]
        return blocks[-1].strip() if blocks else ""
    return ""

