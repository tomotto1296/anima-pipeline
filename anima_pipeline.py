#!/usr/bin/env python3
"""
Anima Pipeline
ブラウザUI → LLM → ComfyUI 自動連携スクリプト
"""

import requests
import json
import uuid
import os
import locale
import io
import re
import sys
import zipfile
import threading
import datetime
import traceback
import builtins
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler

UI_PORT = 7860
_base_dir     = os.path.dirname(os.path.abspath(__file__))
_settings_dir = os.path.join(_base_dir, 'settings')
_workflows_dir = os.path.join(_base_dir, 'workflows')
os.makedirs(_settings_dir, exist_ok=True)
os.makedirs(_workflows_dir, exist_ok=True)

__version__ = "1.4.730"

def _sf(name): return os.path.join(_settings_dir, name)

CONFIG_FILE        = _sf('pipeline_config.json')
EXTRA_TAGS_FILE    = _sf('extra_tags.json')
STYLE_TAGS_FILE    = _sf('style_tags.json')
NEG_EXTRA_TAGS_FILE  = _sf('extra_tags_negative.json')
NEG_STYLE_TAGS_FILE  = _sf('style_tags_negative.json')
UI_OPTIONS_FILE      = _sf('ui_options.json')
CHARA_PRESETS_DIR    = os.path.join(_base_dir, 'chara')
DEFAULT_LOGS_DIR     = os.path.join(_base_dir, 'logs')

_ORIG_PRINT = builtins.print
_LOG_LOCK = threading.Lock()
_LOG_FP = None
_LOG_FH = None
_LOG_LEVEL = "normal"  # normal / debug
_LOG_DIR = DEFAULT_LOGS_DIR
_FILE_HASH_CACHE = {}
_BASENAME_PATH_CACHE = {}

def _mask_sensitive(text: str) -> str:
    s = str(text or "")
    # key=value / key: value style masks
    s = re.sub(r'(?i)\b(token|api[_ -]?key|authorization)\b(\s*[:=]\s*)([^\s,;]+)', r'\1\2***', s)
    # Bearer tokens
    s = re.sub(r'(?i)\bBearer\s+[A-Za-z0-9._\-+/=]+', 'Bearer ***', s)
    return s

def _resolve_log_dir(cfg: dict | None = None) -> str:
    c = cfg or {}
    raw = str(c.get("log_dir", "logs") or "logs").strip()
    if not raw:
        raw = "logs"
    if os.path.isabs(raw):
        return os.path.normpath(raw)
    return os.path.normpath(os.path.join(_base_dir, raw))

def _cleanup_old_logs(log_dir: str, retention_days: int):
    if retention_days <= 0:
        return
    cutoff = datetime.datetime.now() - datetime.timedelta(days=retention_days)
    try:
        for fn in os.listdir(log_dir):
            if not fn.lower().endswith(".log"):
                continue
            fp = os.path.join(log_dir, fn)
            try:
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fp))
                if mtime < cutoff:
                    os.remove(fp)
            except Exception:
                pass
    except Exception:
        pass

def _log_write(level: str, message: str):
    global _LOG_FH
    if level == "DEBUG" and _LOG_LEVEL != "debug":
        return
    if not _LOG_FH:
        return
    line = _mask_sensitive(message).replace("\r", "")
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _LOG_LOCK:
        try:
            _LOG_FH.write(f"[{ts}] [{level}] {line}\n")
            _LOG_FH.flush()
        except Exception:
            pass

def _apply_log_config(cfg: dict):
    global _LOG_FP, _LOG_FH, _LOG_LEVEL, _LOG_DIR
    _LOG_LEVEL = "debug" if str(cfg.get("log_level", "normal")).lower() == "debug" else "normal"
    _LOG_DIR = _resolve_log_dir(cfg)
    os.makedirs(_LOG_DIR, exist_ok=True)
    try:
        retention = int(cfg.get("log_retention_days", 30))
    except Exception:
        retention = 30
    if retention < 0:
        retention = 0
    _cleanup_old_logs(_LOG_DIR, retention)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    fp = os.path.join(_LOG_DIR, f"anima_{today}.log")
    if _LOG_FP != fp or _LOG_FH is None:
        try:
            if _LOG_FH:
                _LOG_FH.close()
        except Exception:
            pass
        _LOG_FP = fp
        _LOG_FH = open(_LOG_FP, "a", encoding="utf-8")

def _patched_print(*args, **kwargs):
    try:
        _ORIG_PRINT(*args, **kwargs)
    except Exception:
        pass
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    try:
        msg = sep.join(str(a) for a in args) + ("" if end == "\n" else str(end))
    except Exception:
        msg = " ".join(str(a) for a in args)
    _log_write("INFO", msg.rstrip("\n"))

builtins.print = _patched_print

def _install_exception_logging():
    def _hook(exc_type, exc, tb):
        _log_write("ERROR", "".join(traceback.format_exception(exc_type, exc, tb)))
        sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = _hook
    try:
        def _thread_hook(args):
            _log_write("ERROR", "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))
        threading.excepthook = _thread_hook
    except Exception:
        pass

def load_neg_extra_tags():
    if os.path.exists(NEG_EXTRA_TAGS_FILE):
        try:
            with open(NEG_EXTRA_TAGS_FILE, "r", encoding="utf-8-sig") as f:
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
            with open(NEG_STYLE_TAGS_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except: pass
    return []

def save_neg_style_tags(tags: list):
    with open(NEG_STYLE_TAGS_FILE, "w", encoding="utf-8") as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)

def load_ui_options() -> dict:
    if os.path.exists(UI_OPTIONS_FILE):
        try:
            with open(UI_OPTIONS_FILE, encoding='utf-8-sig') as f:
                return json.load(f)
        except Exception as e:
            print(f'[ui_options] 読み込みエラー: {e}')
    return {}

def detect_os_ui_lang() -> str:
    # Prefer native OS UI language on Windows.
    if os.name == 'nt':
        try:
            import ctypes
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if lang_id:
                try:
                    lang_name = locale.windows_locale.get(lang_id, '')
                    if lang_name:
                        lang_name = lang_name.lower()
                        return 'ja' if lang_name.startswith('ja') else 'en'
                except Exception:
                    pass
        except Exception:
            pass
    try:
        lang, _ = locale.getdefaultlocale()
    except Exception:
        lang = None
    if not lang:
        try:
            lang = locale.getlocale()[0]
        except Exception:
            lang = None
    lang = (lang or '').lower()
    return 'ja' if lang.startswith('ja') else 'en'

def load_style_tags():
    if os.path.exists(STYLE_TAGS_FILE):
        with open(STYLE_TAGS_FILE, encoding='utf-8-sig') as f:
            return json.load(f).get('tags', [])
    return []

def save_style_tags(tags):
    with open(STYLE_TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'tags': tags}, f, ensure_ascii=False, indent=2)

def load_extra_tags():
    if os.path.exists(EXTRA_TAGS_FILE):
        try:
            with open(EXTRA_TAGS_FILE, "r", encoding="utf-8-sig") as f:
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
    "workflow_json_path": "workflows/image_anima_preview.json",
    "positive_node_id": "11",
    "negative_node_id": "12",
    "comfyui_output_dir": "",
    "clip_node_id": "45",
    "ksampler_node_id": "19",
    "seed_mode": "random",   # random / fixed / increment
    "seed_value": 0,
    "steps": 30,
    "cfg": 4.0,
    "sampler_name": "er_sde",
    "scheduler": "simple",
    "output_format": "png",  # png / webp
    "embed_metadata": True,
    "console_lang": "ja",   # ja / en
    "log_dir": "logs",
    "log_retention_days": 30,
    "log_level": "normal",  # normal / debug
    "history_db_path": "history/history.db",
    "history_thumb_dir": "history/thumbs",
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            cfg = DEFAULT_CONFIG.copy()
            saved = json.load(open(CONFIG_FILE, "r", encoding="utf-8-sig"))
            migrated = False
            # 旧キー（lm_studio_*）からの移行フォールバック
            for old_key, new_key in [("lm_studio_url","llm_url"),("lm_studio_token","llm_token"),("lm_studio_model","llm_model")]:
                if old_key in saved and new_key not in saved:
                    saved[new_key] = saved.pop(old_key)
                    migrated = True
            # OUTPUT-4: 新規キーの補完
            for k in ("output_format", "embed_metadata"):
                if k not in saved:
                    saved[k] = DEFAULT_CONFIG[k]
                    migrated = True
            cfg.update(saved)
            if str(cfg.get("output_format", "png")).lower() not in ("png", "webp"):
                cfg["output_format"] = "png"
                migrated = True
            else:
                cfg["output_format"] = str(cfg.get("output_format", "png")).lower()
            cfg["embed_metadata"] = bool(cfg.get("embed_metadata", True))
            if migrated:
                json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            _apply_log_config(cfg)
            return cfg
        except Exception as e:
            print(f"[設定] 読み込みエラー: {e}")
    cfg = DEFAULT_CONFIG.copy()
    _apply_log_config(cfg)
    return cfg

def save_config(cfg: dict):
    try:
        base = DEFAULT_CONFIG.copy()
        base.update(cfg or {})
        cfg = base
        try:
            cfg["log_retention_days"] = max(0, int(cfg.get("log_retention_days", 30)))
        except Exception:
            cfg["log_retention_days"] = 30
        cfg["output_format"] = str(cfg.get("output_format", "png")).lower()
        if cfg["output_format"] not in ("png", "webp"):
            cfg["output_format"] = "png"
        cfg["embed_metadata"] = bool(cfg.get("embed_metadata", True))
        cfg["log_level"] = "debug" if str(cfg.get("log_level", "normal")).lower() == "debug" else "normal"
        cfg["log_dir"] = str(cfg.get("log_dir", "logs") or "logs").strip() or "logs"
        json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        _apply_log_config(cfg)
        print(f"[設定] 保存: {CONFIG_FILE}")
    except Exception as e:
        print(f"[設定] 保存エラー: {e}")

def _resolve_history_db_path(cfg: dict) -> str:
    raw = str((cfg or {}).get("history_db_path", DEFAULT_CONFIG["history_db_path"]) or "").strip()
    if not raw:
        raw = DEFAULT_CONFIG["history_db_path"]
    if os.path.isabs(raw):
        return os.path.normpath(raw)
    return os.path.normpath(os.path.join(_base_dir, raw))


def _resolve_history_thumb_dir(cfg: dict) -> str:
    raw = str((cfg or {}).get("history_thumb_dir", DEFAULT_CONFIG["history_thumb_dir"]) or "").strip()
    if not raw:
        raw = DEFAULT_CONFIG["history_thumb_dir"]
    if os.path.isabs(raw):
        return os.path.normpath(raw)
    return os.path.normpath(os.path.join(_base_dir, raw))


def _ensure_history_db(cfg: dict):
    db_path = _resolve_history_db_path(cfg)
    thumb_dir = _resolve_history_thumb_dir(cfg)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(thumb_dir, exist_ok=True)
    con = sqlite3.connect(db_path, timeout=5)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                prompt_id TEXT,
                thumbnail_path TEXT,
                image_path TEXT NOT NULL,
                prompt TEXT,
                negative_prompt TEXT,
                seed INTEGER,
                steps INTEGER,
                cfg REAL,
                sampler TEXT,
                scheduler TEXT,
                workflow_name TEXT,
                loras TEXT,
                session_snapshot TEXT,
                favorite INTEGER DEFAULT 0,
                tags TEXT DEFAULT '',
                width INTEGER,
                height INTEGER,
                model TEXT,
                model_hash TEXT
            )
            """
        )
        # Schema migration for existing users (older table without new columns).
        cols = set()
        for r in con.execute("PRAGMA table_info(generation_history)").fetchall():
            if len(r) >= 2:
                cols.add(str(r[1]))
        add_cols = [
            ("prompt_id", "TEXT"),
            ("thumbnail_path", "TEXT"),
            ("image_path", "TEXT"),
            ("prompt", "TEXT"),
            ("negative_prompt", "TEXT"),
            ("seed", "INTEGER"),
            ("steps", "INTEGER"),
            ("cfg", "REAL"),
            ("sampler", "TEXT"),
            ("scheduler", "TEXT"),
            ("workflow_name", "TEXT"),
            ("loras", "TEXT"),
            ("session_snapshot", "TEXT"),
            ("favorite", "INTEGER DEFAULT 0"),
            ("tags", "TEXT DEFAULT ''"),
            ("width", "INTEGER"),
            ("height", "INTEGER"),
            ("model", "TEXT"),
            ("model_hash", "TEXT"),
        ]
        for name, ddl in add_cols:
            if name not in cols:
                con.execute(f"ALTER TABLE generation_history ADD COLUMN {name} {ddl}")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_history_prompt_image ON generation_history(prompt_id, image_path)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_history_created_at ON generation_history(created_at DESC)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_history_favorite ON generation_history(favorite)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_history_workflow ON generation_history(workflow_name)")
        con.commit()
    finally:
        con.close()


def _load_session_snapshot_text() -> str:
    sf = _sf('anima_session_last.json')
    if not os.path.exists(sf):
        return "{}"
    try:
        with open(sf, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "{}"


def _create_history_thumb(src_path: str, thumb_path: str):
    from PIL import Image
    with Image.open(src_path) as im:
        im.thumbnail((256, 256), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        im.save(thumb_path, "WEBP", quality=80, method=6)


def _resolve_image_path_with_webp_fallback(path: str) -> str:
    p = os.path.normpath(str(path or ""))
    if not p:
        return p
    if os.path.exists(p):
        return p
    root, ext = os.path.splitext(p)
    if ext.lower() == ".png":
        wp = root + ".webp"
        if os.path.exists(wp):
            return os.path.normpath(wp)
    return p


def _save_history_record(cfg: dict, prompt_id: str, image_path: str, meta: dict) -> bool:
    try:
        _ensure_history_db(cfg)
    except Exception as e:
        print(f"[OUTPUT-3] DB init error: {e}")
        return False

    db_path = _resolve_history_db_path(cfg)
    thumb_dir = _resolve_history_thumb_dir(cfg)
    created_at = datetime.datetime.now().isoformat(timespec="seconds")
    loras = []
    for pair in (meta or {}).get("lora", []) or []:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            loras.append({"name": str(pair[0]), "weight": float(pair[1])})
    loras_json = json.dumps(loras, ensure_ascii=False)
    session_snapshot = _load_session_snapshot_text()

    resolved_image_path = _resolve_image_path_with_webp_fallback(str(image_path))
    con = sqlite3.connect(db_path, timeout=5)
    try:
        cur = con.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO generation_history (
                created_at, prompt_id, thumbnail_path, image_path,
                prompt, negative_prompt, seed, steps, cfg,
                sampler, scheduler, workflow_name, loras,
                session_snapshot, favorite, tags, width, height, model, model_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '', ?, ?, ?, ?)
            """,
            (
                created_at,
                str(prompt_id or ""),
                "",
                str(resolved_image_path or "").replace("\\", "/"),
                str((meta or {}).get("positive_prompt", "") or ""),
                str((meta or {}).get("negative_prompt", "") or ""),
                int((meta or {}).get("seed", 0) or 0),
                int((meta or {}).get("steps", 0) or 0),
                float((meta or {}).get("cfg", 0) or 0),
                str((meta or {}).get("sampler", "") or ""),
                str((meta or {}).get("scheduler", "") or ""),
                str((meta or {}).get("workflow_version", "") or ""),
                loras_json,
                session_snapshot,
                int((meta or {}).get("width", 0) or 0),
                int((meta or {}).get("height", 0) or 0),
                str((meta or {}).get("model", "") or ""),
                str((meta or {}).get("model_hash", "") or ""),
            ),
        )
        if cur.rowcount <= 0:
            con.commit()
            return False
        row_id = int(cur.lastrowid)
        thumb_abs = os.path.join(thumb_dir, f"{row_id}.webp")
        thumb_val = ""
        try:
            _create_history_thumb(str(resolved_image_path), thumb_abs)
            thumb_val = thumb_abs.replace("\\", "/")
        except Exception as te:
            print(f"[OUTPUT-3] Thumb create error: {te}")
        cur.execute("UPDATE generation_history SET thumbnail_path=? WHERE id=?", (thumb_val, row_id))
        con.commit()
        return True
    except Exception as e:
        print(f"[OUTPUT-3] DB write error: {e}")
        return False
    finally:
        con.close()

def _console_lang(cfg: dict | None = None) -> str:
    try:
        c = cfg or load_config()
        lang = str(c.get("console_lang", "ja")).lower()
        return "en" if lang == "en" else "ja"
    except Exception:
        return "ja"

def _ct(ja: str, en: str, cfg: dict | None = None) -> str:
    return en if _console_lang(cfg) == "en" else ja


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


def _workflow_version_label(workflow_path: str) -> str:
    if not workflow_path:
        return "unknown"
    return os.path.basename(workflow_path.replace("\\", "/")) or "unknown"


def _extract_checkpoint_name(api_prompt: dict) -> str:
    keys = ("ckpt_name", "model_name", "unet_name", "checkpoint", "name")
    for _, node in api_prompt.items():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {}) or {}
        for k in keys:
            v = inputs.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return "unknown"


def _infer_comfy_root_candidates(cfg: dict, workflow_path: str = "") -> list[str]:
    roots = []
    out_dir = str(cfg.get("comfyui_output_dir", "") or "").strip()
    if out_dir:
        roots.extend([
            os.path.abspath(out_dir),
            os.path.abspath(os.path.join(out_dir, "..")),
            os.path.abspath(os.path.join(out_dir, "..", "..")),
        ])
    wf_path = workflow_path or str(cfg.get("workflow_json_path", "") or "").strip()
    if wf_path:
        if not os.path.isabs(wf_path):
            wf_path = os.path.join(_base_dir, wf_path)
        wf_abs = os.path.abspath(wf_path)
        roots.extend([
            os.path.abspath(os.path.join(os.path.dirname(wf_abs), "..", "..")),
            os.path.abspath(os.path.join(os.path.dirname(wf_abs), "..")),
        ])
    uniq = []
    seen = set()
    for p in roots:
        p2 = os.path.normpath(p)
        if p2 in seen:
            continue
        seen.add(p2)
        uniq.append(p2)
    return uniq


def _sha256_hex(fp: str) -> str:
    import hashlib
    fp = os.path.abspath(fp)
    try:
        mtime = os.path.getmtime(fp)
        size = os.path.getsize(fp)
        key = (fp, mtime, size)
        cached = _FILE_HASH_CACHE.get(key)
        if cached:
            return cached
    except Exception:
        key = None
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()
    if key:
        _FILE_HASH_CACHE[key] = digest
    return digest


def _resolve_model_file(model_name: str, roots: list[str]) -> str:
    if not model_name or model_name == "unknown":
        return ""
    rel = model_name.replace("\\", "/").lstrip("/")
    cands = []
    for r in roots:
        cands.extend([
            os.path.join(r, "models", "checkpoints", rel),
            os.path.join(r, "models", "unet", rel),
            os.path.join(r, "checkpoints", rel),
            os.path.join(r, rel),
        ])
    for p in cands:
        if os.path.isfile(p):
            return p
    # フォールバック: basename一致で探索（extra_model_paths.yaml等の分散配置対策）
    base = os.path.basename(rel).lower()
    search_dirs = []
    for r in roots:
        search_dirs.extend([
            os.path.join(r, "models", "checkpoints"),
            os.path.join(r, "models", "unet"),
            os.path.join(r, "models", "diffusion_models"),
            r,
        ])
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        key = (os.path.abspath(d), base)
        cached = _BASENAME_PATH_CACHE.get(key)
        if cached and os.path.isfile(cached):
            return cached
        for root, _dirs, files in os.walk(d):
            for fn in files:
                if fn.lower() == base:
                    fp = os.path.join(root, fn)
                    _BASENAME_PATH_CACHE[key] = fp
                    return fp
    return ""


def _resolve_lora_file(lora_name: str, roots: list[str]) -> str:
    if not lora_name:
        return ""
    rel = lora_name.replace("\\", "/").lstrip("/")
    cands = []
    for r in roots:
        cands.extend([
            os.path.join(r, "models", "loras", rel),
            os.path.join(r, "loras", rel),
            os.path.join(r, rel),
        ])
    for p in cands:
        if os.path.isfile(p):
            return p
    base = os.path.basename(rel).lower()
    for r in roots:
        for d in (os.path.join(r, "models", "loras"), os.path.join(r, "loras"), r):
            if not os.path.isdir(d):
                continue
            key = (os.path.abspath(d), base)
            cached = _BASENAME_PATH_CACHE.get(key)
            if cached and os.path.isfile(cached):
                return cached
            for root, _dirs, files in os.walk(d):
                for fn in files:
                    if fn.lower() == base:
                        fp = os.path.join(root, fn)
                        _BASENAME_PATH_CACHE[key] = fp
                        return fp
    return ""


def _build_parameters_text(meta: dict) -> str:
    def _autov2(h: str) -> str:
        return str(h or "")[:10].upper()

    positive_prompt = str(meta.get("positive_prompt", "") or "")
    loras = meta.get("lora", []) or []
    for name, strength in loras:
        base = os.path.basename(str(name).replace("\\", "/"))
        stem = base.rsplit(".", 1)[0] if "." in base else base
        tag = f"<lora:{stem}:{float(strength):g}>"
        if tag.lower() not in positive_prompt.lower():
            positive_prompt = (positive_prompt + ", " + tag).strip(", ")

    model_hash_full = str(meta.get("model_hash", "") or "")
    model_hash_short = _autov2(model_hash_full) if model_hash_full else ""
    lora_auto_pairs = []
    for name, h in meta.get("lora_hashes", []) or []:
        if not h:
            continue
        base = os.path.basename(str(name).replace("\\", "/"))
        stem = base.rsplit(".", 1)[0] if "." in base else base
        lora_auto_pairs.append(f"{stem}: {_autov2(h)}")

    params = (
        f"Steps: {meta.get('steps', 30)}, "
        f"Sampler: {meta.get('sampler', 'er_sde')}, "
        f"CFG scale: {meta.get('cfg', 4.0)}, "
        f"Seed: {meta.get('seed', 0)}, "
        f"Size: {meta.get('width', 1024)}x{meta.get('height', 1024)}"
    )
    if model_hash_short:
        params += f", Model hash: {model_hash_short}"
    params += f", Model: {meta.get('model', 'unknown')}"
    if lora_auto_pairs:
        params += f", Lora hashes: \"{', '.join(lora_auto_pairs)}\""
    params += f", Version: Anima Pipeline {__version__}"

    return (
        f"{positive_prompt}\n"
        f"Negative prompt: {meta.get('negative_prompt', '')}\n"
        f"{params}"
    )


def _cdata_escape(text: str) -> str:
    return str(text or "").replace("]]>", "]]]]><![CDATA[>")


def _build_webp_xmp(parameters_text: str, prompt_json: str = "", workflow_json: str = "") -> bytes:
    xmp = (
        '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description xmlns:anima="https://anima-pipeline/metadata/1.0/">'
        f'<anima:parameters><![CDATA[{_cdata_escape(parameters_text)}]]></anima:parameters>'
        f'<anima:prompt><![CDATA[{_cdata_escape(prompt_json)}]]></anima:prompt>'
        f'<anima:workflow><![CDATA[{_cdata_escape(workflow_json)}]]></anima:workflow>'
        '</rdf:Description>'
        '</rdf:RDF>'
        '</x:xmpmeta>'
        '<?xpacket end="w"?>'
    )
    return xmp.encode("utf-8")


def _embed_png_metadata(png_path: str, parameters_text: str, prompt_json: str = "", workflow_json: str = ""):
    from PIL import Image, PngImagePlugin
    with Image.open(png_path) as img:
        pnginfo = PngImagePlugin.PngInfo()
        for k, v in (img.info or {}).items():
            if isinstance(v, str) and k not in ("parameters", "prompt", "workflow"):
                pnginfo.add_text(k, v)
        pnginfo.add_text("parameters", parameters_text)
        if prompt_json:
            pnginfo.add_text("prompt", prompt_json)
        if workflow_json:
            pnginfo.add_text("workflow", workflow_json)
        img.save(png_path, format="PNG", pnginfo=pnginfo)


def _embed_webp_metadata(webp_path: str, parameters_text: str, quality: int = 90, xmp_blob: bytes = b""):
    from PIL import Image
    with Image.open(webp_path) as img:
        exif = img.getexif()
        exif[0x9286] = b"ASCII\x00\x00\x00" + parameters_text.encode("utf-8", errors="ignore")
        img.save(
            webp_path,
            format="WEBP",
            quality=quality,
            exif=exif.tobytes(),
            xmp=(xmp_blob or _build_webp_xmp(parameters_text)),
        )


def convert_png_to_webp(
    png_path: str,
    quality: int = 90,
    parameters_text: str = "",
    xmp_blob: bytes = b"",
) -> tuple[bool, str]:
    """PNGをWebPに変換。成功時はPNGを削除、失敗時はPNGを維持。"""
    try:
        from PIL import Image
        webp_path = os.path.splitext(png_path)[0] + ".webp"
        with Image.open(png_path) as img:
            save_kwargs = {"format": "WEBP", "quality": quality}
            if parameters_text:
                exif = img.getexif()
                exif[0x9286] = b"ASCII\x00\x00\x00" + parameters_text.encode("utf-8", errors="ignore")
                save_kwargs["exif"] = exif.tobytes()
                save_kwargs["xmp"] = xmp_blob or _build_webp_xmp(parameters_text)
            img.save(webp_path, **save_kwargs)
        os.remove(png_path)
        print(f"[WebP] 変換完了: {webp_path}")
        return True, webp_path
    except Exception as e:
        print(f"[OUTPUT-4] WebP conversion error: {e}")
        return False, png_path


def _postprocess_generated_files(
    comfyui_url: str,
    output_dir: str,
    date_folder: str,
    prompt_id: str,
    output_format: str = "png",
    embed_metadata: bool = True,
    parameters_text: str = "",
    prompt_json: str = "",
    workflow_json: str = "",
    quality: int = 90,
):
    import json as _json, urllib.request
    target_dir = os.path.join(output_dir, date_folder)
    hist_url = comfyui_url.rstrip("/") + f"/history/{prompt_id}"
    with urllib.request.urlopen(hist_url) as r:
        hist = _json.loads(r.read())
    outputs = hist.get(prompt_id, {}).get("outputs", {})
    for node_out in outputs.values():
        for img in node_out.get("images", []):
            fname = img.get("filename", "")
            subfolder = img.get("subfolder", "")
            fpath = os.path.join(output_dir, subfolder, fname) if subfolder else os.path.join(target_dir, fname)
            if not os.path.exists(fpath):
                continue
            ext = os.path.splitext(fpath)[1].lower()
            try:
                if output_format == "webp":
                    if ext == ".png":
                        if embed_metadata and parameters_text:
                            _embed_png_metadata(fpath, parameters_text, prompt_json=prompt_json, workflow_json=workflow_json)
                        ok, _ = convert_png_to_webp(
                            fpath,
                            quality=quality,
                            parameters_text=(parameters_text if embed_metadata else ""),
                            xmp_blob=_build_webp_xmp(parameters_text, prompt_json=prompt_json, workflow_json=workflow_json) if embed_metadata else b"",
                        )
                        if not ok:
                            print("WebP変換に失敗しました。PNGで保存します。")
                    elif ext == ".webp" and embed_metadata and parameters_text:
                        _embed_webp_metadata(
                            fpath, parameters_text, quality=quality,
                            xmp_blob=_build_webp_xmp(parameters_text, prompt_json=prompt_json, workflow_json=workflow_json),
                        )
                else:
                    if ext == ".png" and embed_metadata and parameters_text:
                        _embed_png_metadata(fpath, parameters_text, prompt_json=prompt_json, workflow_json=workflow_json)
            except Exception as e:
                print(f"[OUTPUT-4] Metadata embed error: {e}")


def watch_and_postprocess(
    comfyui_url: str,
    output_dir: str,
    date_folder: str,
    prompt_id: str,
    client_id: str = None,
    output_format: str = "png",
    embed_metadata: bool = True,
    parameters_text: str = "",
    prompt_json: str = "",
    workflow_json: str = "",
    quality: int = 90,
):
    """ComfyUI WebSocketで完了検知し、履歴API経由で保存画像を後処理する。"""
    import threading, json as _json, urllib.parse
    print(f"[OUTPUT-4] 監視開始: prompt_id={prompt_id}")
    _client_id = client_id if client_id is not None else str(uuid.uuid4())

    def _watch():
        import time, socket, struct, base64, ssl as _ssl
        ws_url = comfyui_url.replace("http://", "ws://").replace("https://", "wss://") + f"/ws?clientId={_client_id}"
        parsed = urllib.parse.urlparse(ws_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        path = (parsed.path or "/ws") + ("?" + parsed.query if parsed.query else "")
        try:
            sock = socket.create_connection((host, port), timeout=300)
            if parsed.scheme == "wss":
                sock = _ssl.wrap_socket(sock, server_hostname=host)
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
            resp = b""
            while b"\r\n\r\n" not in resp:
                resp += sock.recv(1024)
            deadline = time.time() + 300
            buf = b""
            while time.time() < deadline:
                try:
                    sock.settimeout(5)
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    while len(buf) >= 2:
                        opcode = buf[0] & 0x0F
                        masked = (buf[1] & 0x80) != 0
                        plen = buf[1] & 0x7F
                        offset = 2
                        if plen == 126:
                            if len(buf) < 4:
                                break
                            plen = struct.unpack(">H", buf[2:4])[0]
                            offset = 4
                        elif plen == 127:
                            if len(buf) < 10:
                                break
                            plen = struct.unpack(">Q", buf[2:10])[0]
                            offset = 10
                        if masked:
                            offset += 4
                        if len(buf) < offset + plen:
                            break
                        payload = buf[offset:offset + plen]
                        buf = buf[offset + plen:]
                        if opcode != 1:
                            continue
                        try:
                            data = _json.loads(payload.decode("utf-8"))
                            if (
                                data.get("type") == "executing"
                                and data.get("data", {}).get("prompt_id") == prompt_id
                                and data.get("data", {}).get("node") is None
                            ):
                                sock.close()
                                time.sleep(1)
                                _postprocess_generated_files(
                                    comfyui_url=comfyui_url,
                                    output_dir=output_dir,
                                    date_folder=date_folder,
                                    prompt_id=prompt_id,
                                    output_format=output_format,
                                    embed_metadata=embed_metadata,
                                    parameters_text=parameters_text,
                                    prompt_json=prompt_json,
                                    workflow_json=workflow_json,
                                    quality=quality,
                                )
                                return
                        except Exception:
                            pass
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[OUTPUT-4] WebSocket受信エラー: {e}")
                    break
            print("[OUTPUT-4] 完了監視タイムアウト")
            sock.close()
        except Exception as e:
            print(f"[OUTPUT-4] WebSocket接続エラー: {e}")

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


def send_to_comfyui(
    positive_prompt: str,
    cfg: dict,
    width: int = 1024,
    height: int = 1024,
    fmt: str = 'png',
    client_id: str = None,
    negative_prompt: str = '',
    lora_slots: list = None,
):
    workflow_path = cfg.get("workflow_json_path", "").strip()
    if workflow_path and not os.path.isabs(workflow_path):
        workflow_path = os.path.join(_base_dir, workflow_path)
    if not workflow_path or not os.path.exists(workflow_path):
        raise FileNotFoundError(f"ワークフローJSONが見つかりません: {workflow_path}")

    workflow_data = json.load(open(workflow_path, "r", encoding="utf-8"))
    # API形式（Save (API Format)）か保存形式かを判定
    # API形式: キーが数字文字列でclass_typeを持つ dict
    # 保存形式: "nodes"キーを持つ dict
    if "nodes" in workflow_data:
        api_prompt = workflow_to_api(workflow_data)
    else:
        # すでにAPI形式 → そのまま使用（キーを文字列に統一）
        api_prompt = {str(k): v for k, v in workflow_data.items()}

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

    # SaveImage系ノードのfilename_prefixに日付フォルダを設定
    import datetime, random
    date_folder = datetime.date.today().strftime("%Y-%m-%d")
    for nid, node in api_prompt.items():
        if node.get("class_type") in ("SaveImage", "SaveImageExtended", "Image Save", "WAS_Save_Images"):
            ts = datetime.datetime.now().strftime("%H%M%S%f")[:10]
            node["inputs"]["filename_prefix"] = f"{date_folder}/{ts}_"
            print(f"[ComfyUI] 保存先: output/{date_folder}/{ts}_ (node {nid})")

    # KSamplerのseed/steps/cfg/samplerを設定
    seed_mode = cfg.get('seed_mode', 'random')
    seed_value = int(cfg.get('seed_value', 0))
    steps_val = int(cfg.get('steps', 30))
    cfg_val = float(cfg.get('cfg', 4.0))
    sampler_val = cfg.get('sampler_name', 'er_sde')
    scheduler_val = cfg.get('scheduler', 'simple')
    ksampler_id = cfg.get('ksampler_node_id', '')
    effective_seed = 0
    for nid, node in api_prompt.items():
        if node.get("class_type") == "KSampler" and (not ksampler_id or nid == ksampler_id):
            if seed_mode == 'fixed':
                node["inputs"]["seed"] = seed_value
            elif seed_mode == 'increment':
                node["inputs"]["seed"] = seed_value
                # increment: 呼び出し元でseed_valueを+1する
            else:
                node["inputs"]["seed"] = random.randint(0, 2**32 - 1)
            node["inputs"]["steps"] = steps_val
            node["inputs"]["cfg"] = cfg_val
            node["inputs"]["sampler_name"] = sampler_val
            node["inputs"]["scheduler"] = scheduler_val
            effective_seed = int(node["inputs"]["seed"])
            print(f"[ComfyUI] KSampler設定: seed={node['inputs']['seed']} steps={steps_val} cfg={cfg_val} sampler={sampler_val} (node {nid})")

    # LoraLoaderノードにlora_slotsを注入
    active_lora_pairs = []
    if lora_slots:
        active_slots = [s for s in lora_slots if s.get('name','').strip()]
        active_lora_pairs = [(s.get("name", "").strip(), float(s.get("strength", 1.0))) for s in active_slots]
        lora_nodes = [(nid, node) for nid, node in api_prompt.items()
                      if node.get('class_type') == 'LoraLoader']
        lora_nodes.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)

        def bypass_lora_node(nid, node):
            """LoraLoaderノードを削除して上流と下流を直接繋ぐ"""
            model_src = node['inputs'].get('model')
            clip_src  = node['inputs'].get('clip')
            for other_nid, other_node in api_prompt.items():
                for inp_name, inp_val in list(other_node['inputs'].items()):
                    if isinstance(inp_val, list) and inp_val[0] == nid:
                        if inp_val[1] == 0 and model_src:
                            other_node['inputs'][inp_name] = model_src
                        elif inp_val[1] == 1 and clip_src:
                            other_node['inputs'][inp_name] = clip_src
            del api_prompt[nid]

        for i, (nid, node) in enumerate(lora_nodes):
            if i < len(active_slots):
                slot = active_slots[i]
                lora_name = slot['name'].strip()
                strength = float(slot.get('strength', 1.0))
                node['inputs']['lora_name'] = lora_name
                node['inputs']['strength_model'] = strength
                node['inputs']['strength_clip'] = strength
            else:
                # 余りLoraLoaderはバイパス削除
                bypass_lora_node(nid, node)

    if client_id is None:
        client_id = str(uuid.uuid4())
    payload = {"prompt": api_prompt, "client_id": client_id}
    resp = requests.post(f"{cfg['comfyui_url']}/prompt", json=payload, timeout=30)
    print(f"[ComfyUI] status={resp.status_code} body={resp.text[:200]}")
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ComfyUI error: {data['error']}")
    model_name = _extract_checkpoint_name(api_prompt)
    root_candidates = _infer_comfy_root_candidates(cfg, workflow_path=workflow_path)
    model_hash = ""
    try:
        model_fp = _resolve_model_file(model_name, root_candidates)
        if model_fp:
            model_hash = _sha256_hex(model_fp)
        else:
            print(f"[OUTPUT-4] Model file not found for hash: {model_name}")
    except Exception as e:
        print(f"[OUTPUT-4] Model hash compute error: {e}")
    lora_hashes = []
    for lora_name, _strength in active_lora_pairs:
        h = ""
        try:
            lora_fp = _resolve_lora_file(lora_name, root_candidates)
            if lora_fp:
                h = _sha256_hex(lora_fp)
        except Exception as e:
            print(f"[OUTPUT-4] LoRA hash compute error: {e}")
        lora_hashes.append((lora_name, h))
    meta = {
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "steps": steps_val,
        "cfg": cfg_val,
        "sampler": sampler_val,
        "scheduler": scheduler_val,
        "seed": effective_seed,
        "width": width,
        "height": height,
        "model": model_name,
        "model_hash": model_hash,
        "lora": active_lora_pairs,
        "lora_hashes": lora_hashes,
        "workflow_version": _workflow_version_label(workflow_path),
        "prompt_json": json.dumps(api_prompt, ensure_ascii=False),
        "workflow_json": json.dumps(workflow_data, ensure_ascii=False),
    }
    return data.get("prompt_id", "unknown"), meta


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
    min-height:100vh;padding:2rem;
    background-image:
      radial-gradient(ellipse at 15% 20%, rgba(179,136,216,0.12) 0%, transparent 50%),
      radial-gradient(ellipse at 85% 75%, rgba(240,168,200,0.10) 0%, transparent 50%),
      repeating-linear-gradient(0deg,transparent,transparent 31px,rgba(221,214,240,0.5) 31px,rgba(221,214,240,0.5) 32px);
  }
  .container{width:100%;max-width:680px;margin:0 auto;background:rgba(255,255,255,0.85);
    border:1px solid var(--border);
    box-shadow:0 4px 24px rgba(124,77,191,0.08), 0 1px 3px rgba(124,77,191,0.12);
    border-radius:12px;padding:2.5rem;backdrop-filter:blur(8px);}
  h1{font-size:0.85rem;font-weight:300;letter-spacing:0.35em;text-transform:uppercase;color:var(--muted);margin-bottom:0.3rem;}
  h2{font-size:1.7rem;font-weight:700;margin-bottom:1.8rem;
    background:linear-gradient(120deg, var(--ink) 0%, #7c4dbf 100%);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
    border-bottom:1.5px solid var(--border);padding-bottom:0.8rem;}
  .lang-switch{display:flex;justify-content:flex-end;gap:0.35rem;margin:-0.3rem 0 0.8rem 0;}
  .lang-btn{
    border:1px solid var(--border);background:white;color:var(--muted);
    border-radius:999px;padding:0.2rem 0.55rem;cursor:pointer;
    font-family:'DM Mono',monospace;font-size:0.64rem;letter-spacing:0.08em;
    margin-top:0;width:auto;text-transform:none;box-shadow:none;
  }
  .lang-btn:hover{background:var(--highlight);color:var(--multi);border-color:var(--accent);transform:none;box-shadow:none;}
  .lang-btn.active{border-color:var(--multi);color:var(--multi);background:var(--highlight);}
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
  .progress-bar-wrap{width:100%;background:#e8e4f0;border-radius:4px;height:6px;margin-top:0.3rem;overflow:hidden;display:none;}
  .progress-bar{height:6px;background:linear-gradient(90deg,var(--multi),var(--accent));border-radius:4px;width:0%;transition:width 0.3s ease;}
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
  .opt-label-wrap{display:flex;align-items:center;justify-content:flex-end;gap:0;cursor:pointer;user-select:none;}
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
  .size-inputs{display:flex;align-items:center;gap:0.5rem;}
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
  .chara-preset-row-wrap{display:flex;gap:0.3rem;align-items:center;}
  .chara-preset-row-wrap .chara-preset-btns{margin-top:0;}
  /* PC: プリセット行を横並び */
  #charaContainer .chara-preset-btns{display:inline-flex;}
  .chara-header > div:first-child{display:flex;gap:0.3rem;align-items:center;flex-wrap:wrap;}
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
  .chara-preset-btns{margin-top:0.2rem;}
  .chara-expand{background:none;border:1px solid var(--border);padding:0.3rem 0.6rem;
    font-family:'DM Mono',monospace;font-size:0.7rem;color:var(--muted);cursor:pointer;white-space:nowrap;}
  .chara-expand:hover{border-color:var(--ink);color:var(--ink);}
  .chara-optional{margin-top:0.5rem;border-top:1px solid var(--border);padding-top:0.5rem;}
  .opt-row{display:flex;flex-direction:column;gap:0.15rem;align-items:flex-start;margin-bottom:0.3rem;}
  .opt-label{font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);white-space:nowrap;font-weight:600;}
  /* prompt-section-labelトグル */
  .prompt-section-label{ cursor:pointer; user-select:none; }
  .prompt-section-label.collapsed span::before{ content:''; }
  /* opt-rowトグル */
  .opt-label-wrap::before{ content:'▼'; font-size:0.55rem; margin-right:0.2rem; display:inline-block; transition:transform 0.15s; }
  .opt-row.collapsed .opt-label-wrap::before{ transform:rotate(-90deg); }
  .opt-row.collapsed .opt-row-body{ display:none; }
  .opt-row .opt-row-body{ width:100%; }
  .opt-row input{background:white;border:1px solid var(--border);padding:0.45rem 0.6rem;
    font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;
    width:100%;box-sizing:border-box;}
  .opt-row input:focus{border-color:var(--ink);}
  /* シーン */
  .scene-block{margin-top:0.8rem;}
  .scene-toggle{font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--muted);
    background:#f4f0fa;padding:0.3rem 0.5rem;border-radius:5px;
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
    border-radius:5px;font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--ink);cursor:pointer;user-select:none;white-space:nowrap;}
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

  /* ===== モバイル対応 ===== */
  @media (max-width: 700px){
    body{ padding:0.5rem; padding-bottom:5rem; overflow-x:hidden; }
    .container{ padding:1.2rem 1rem; border-radius:8px; overflow-x:clip; }
    h1{ font-size:0.72rem; letter-spacing:0.2em; }
    h2{ font-size:1.2rem; margin-bottom:1.2rem; }

    /* ボタンのタップ領域を広げる */
    button, .period-btn, .scene-toggle, .fmt-btn, .size-btn{
      min-height:40px;
    }

    /* period-btnの縦書き防止 */
    .period-btn{
      white-space:nowrap;
      writing-mode:horizontal-tb;
      min-width:3rem;
    }

    /* グリッドを縦並びに */
    .field-row{ flex-direction:column; }
    .size-row{ display:flex; flex-direction:column; gap:0.4rem; }
    .size-row select{ width:100%; }
    .size-inputs{ display:flex; align-items:center; gap:0.4rem; }
    .size-inputs input[type=number]{ width:5.5rem; flex:0 0 auto; }
    .size-sep{ align-self:center; }

    /* プリセット選択を全幅にして改行 */
    #charaContainer .chara-preset-btns{ margin-top:0; }
    [id^="chara_preset_sel_"]{ width:100%; flex-basis:100%; }

    /* キャラ名・作品名行: モバイルは2行に */
    .chara-header-row1{
      display:grid !important;
      grid-template-columns:auto auto !important;
      grid-template-rows:auto auto !important;
    }
    .chara-header-row1 > :nth-child(1){ grid-column:1; grid-row:1; align-self:center; }
    .chara-header-row1 > :nth-child(2){ grid-column:1 / 3; grid-row:2; }
    .chara-header-row1 > :nth-child(3){ grid-column:1 / 3; grid-row:3; }
    .chara-header-row1 > :nth-child(4){ grid-column:2; grid-row:1; justify-self:end; }
    .chara-header-row2{
      grid-template-columns:1fr !important;
      gap:0.45rem;
    }
    .chara-attr-group{min-width:0;}
    .chara-attr-btns{
      flex-wrap:wrap;
      gap:0.22rem;
    }
    .chara-attr-btns .gender-btn,
    .chara-attr-btns .age-btn{
      flex:1 1 calc(50% - 0.22rem);
      min-width:4.7rem;
      padding:0.42rem 0.24rem;
      font-size:0.66rem;
      letter-spacing:0;
    }
    .chara-attr-label{
      font-size:0.62rem;
      letter-spacing:0.03em;
    }
    #presetThumbControlRow{
      flex-wrap:wrap !important;
      align-items:stretch !important;
    }
    #presetThumbTargetSel{
      flex:1 1 100% !important;
      min-width:0 !important;
      width:100% !important;
    }
    #presetThumbAddBtn{
      flex:1 1 100% !important;
      width:100% !important;
      text-align:center;
    }

    /* プリセット一覧（サムネイル）: モバイルでもPCと同じ文書フロー内に表示 */
    #presetThumbToggle{
      min-height:46px;
      padding:0.6rem 0.3rem;
      touch-action:manipulation;
    }
    #presetThumbBody{
      position:static;
      left:auto;
      right:auto;
      bottom:auto;
      z-index:auto;
      width:100%;
      padding:0;
      background:transparent;
      border-radius:0;
      box-shadow:none;
      max-height:none;
      overflow:visible;
      display:block;
    }
    #presetThumbSheetTop{
      display:none !important;
    }
    #presetThumbGrid{
      max-height:280px !important;
      overflow-y:auto !important;
      grid-template-columns:repeat(2,1fr) !important;
    }

    /* セッションボタン行 */
    .session-row{ flex-wrap:wrap; gap:0.4rem; }

    /* キャラ名・作品名入力欄を広げる */
    .inp-ja, .inp-en{
      min-width:0;
      width:100%;
      box-sizing:border-box;
    }

    /* フローティングナビをモバイルでは画面下部に横並び */
    #floatNav{
      right:auto !important;
      left:0 !important;
      top:auto !important;
      bottom:0 !important;
      transform:none !important;
      width:100% !important;
      flex-direction:row !important;
      flex-wrap:nowrap;
      justify-content:space-around;
      border-radius:0;
      border-left:none;
      border-right:none;
      border-bottom:none;
      border-top:1px solid var(--border);
      padding:0.3rem 0.2rem;
      gap:0.1rem;
      background:rgba(255,255,255,0.98);
      box-shadow:0 -2px 12px rgba(0,0,0,0.1);
      z-index:500;
      overflow-x:auto;
    }
    #floatNav button{
      font-size:0.58rem;
      padding:0.25rem 0.3rem;
      min-height:36px;
      flex:1;
      min-width:2.8rem;
      max-width:4.5rem;
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
    }
    #floatNav > div:first-child{ display:none; } /* NAVラベル非表示 */

    /* STATUSの長文がスマホで極端に崩れないよう調整 */
    .step{
      gap:0.42rem;
      font-size:0.69rem;
      line-height:1.35;
      align-items:flex-start;
      overflow-wrap:anywhere;
      word-break:break-word;
    }
    .status-label{font-size:0.64rem;}


    /* LoRAグリッドをモバイルで3列固定 */
    #loraCardGrid{
      grid-template-columns: repeat(3, 1fr) !important;
      max-height: 240px;
    }
    #loraCardGrid > div{
      min-height: 90px;
    }


    /* struct-fields */
    .struct-row{ flex-direction:column; }
    .struct-label{ text-align:left !important; padding-right:0 !important; }

    /* カラムグリッドを縦に */
    [style*="grid-template-columns:1fr 1fr"]{
      grid-template-columns:1fr !important;
    }
    [style*="grid-template-columns:1fr 1fr 1fr"]{
      grid-template-columns:1fr 1fr !important;
    }

    /* ギャラリーモーダルのボタン縦書き防止 */
    #galleryModal button{
      white-space:nowrap;
      font-size:0.65rem;
      padding:0.4rem 0.5rem;
    }
    #galleryModal .modalBtnRow{
      flex-wrap:wrap;
      gap:0.3rem;
    }
  }
</style>
</head>
<body>
<div class="container">
  <h1>Anima Pipeline <span id="versionBadge" style="font-weight:300;letter-spacing:0.2em;color:var(--muted);"></span></h1>
  <div class="lang-switch">
    <button id="langBtnJa" class="lang-btn" onclick="setLang('ja')" type="button">日本語</button>
    <button id="langBtnEn" class="lang-btn" onclick="setLang('en')" type="button">English</button>
  </div>
  <h2>キャラクター生成（プロンプト+画像）</h2>

  <div class="stoggle" onclick="toggleSettings()">
    <span id="sarrow">▶</span> 設定
  </div>
  <div class="sbody" id="sbody">
    <div class="settings-section-header" data-target="sectionRequired" style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#c0392b;font-weight:bold;margin-bottom:0.4rem;letter-spacing:0.05em;cursor:pointer;user-select:none;">▼ ■ 必須</div>
    <div id="sectionRequired" style="border:1.5px solid #e74c3c;border-radius:7px;padding:0.8rem;margin-bottom:0.8rem;background:#fff9f9;">
      <div class="field">
        <label>① ワークフローJSONパス（フォールバック）</label>
        <input type="text" id="workflowInput" placeholder="C:\ComfyUI\...\image_anima_preview.json">
      </div>
      <div class="field">
        <label>　 workflows/ フォルダから選択（優先）</label>
        <div style="display:flex;flex-direction:row;gap:0.4rem;align-items:center;">
          <select id="workflowSelect"
            onchange="applyWorkflowNodeIds(this.value)"
            style="flex:1;background:white;border:1px solid var(--border);border-radius:6px;padding:0.4rem 0.6rem;
            font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;box-sizing:border-box;cursor:pointer;">
            <option value="">— Unset (use path in ①) —</option>
          </select>
          <button onclick="loadWorkflowList()" title="Reload"
            style="font-family:'DM Mono',monospace;font-size:0.68rem;padding:0.3rem 0.5rem;border:1px solid var(--border);
            border-radius:5px;background:white;color:var(--muted);cursor:pointer;white-space:nowrap;flex-shrink:0;width:auto;">🔄 Reload</button>
        </div>
        <div id="workflowNodeNotice" style="display:none;font-family:'DM Mono',monospace;font-size:0.65rem;color:#2d7a4f;margin-top:0.2rem;"></div>
        <div style="font-family:'DM Mono',monospace;font-size:0.65rem;color:var(--muted);margin-top:0.2rem;">anima_pipeline/workflows/ にJSONを置くと表示されます。選択時にNode IDを自動検出します（ControlNet等が挟まる場合は手動確認を）</div>
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
      <div class="field-row">
        <div class="field">
          <label>④ KSampler Node ID</label>
          <input type="text" id="ksamplerNodeInput" placeholder="19">
        </div>
        <div class="field">
          <label>⑤ ComfyUI URL</label>
          <input type="text" id="comfyUrlInput" placeholder="http://127.0.0.1:8188">
        </div>
      </div>
    </div>
    <div class="settings-section-header" data-target="sectionLLM" style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#e67e22;font-weight:bold;margin-bottom:0.4rem;letter-spacing:0.05em;cursor:pointer;user-select:none;">▼ ■ LLMを使うなら必須</div>
    <div id="sectionLLM" style="border:1.5px solid #e67e22;border-radius:7px;padding:0.8rem;margin-bottom:0.8rem;background:#fffaf5;">
      <div class="field">
        <label>⑥ LLMプラットフォーム</label>
        <div style="display:flex;gap:0.4rem;flex-wrap:wrap;margin-top:0.3rem;" id="llmPlatformBtns">
          <div class="period-btn active" data-plat="" onclick="selLLMPlatform(this)">なし</div>
          <div class="period-btn" data-plat="lmstudio" onclick="selLLMPlatform(this)">LM Studio</div>
          <div class="period-btn" data-plat="gemini" onclick="selLLMPlatform(this)">Gemini</div>
          <div class="period-btn" data-plat="custom" onclick="selLLMPlatform(this)">Custom</div>
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
    <div class="settings-section-header" data-target="sectionOptional" style="font-family:'DM Mono',monospace;font-size:0.65rem;color:#27ae60;font-weight:bold;margin-bottom:0.4rem;letter-spacing:0.05em;cursor:pointer;user-select:none;">▼ ■ 任意</div>
    <div id="sectionOptional" style="border:1.5px solid #27ae60;border-radius:7px;padding:0.8rem;margin-bottom:0.8rem;background:#f9fff9;">
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
        <label>⑨ COMFYUI OUTPUT FOLDER (for WEBP conversion, <strong style="color:#e74c3c">absolute path recommended</strong>)</label>
        <input type="text" id="outputDirInput" placeholder="例: D:\ComfyUI_Portable\ComfyUI_windows_portable\ComfyUI\output">
      </div>
      <div class="field">
        <label>⑩ LOG DIRECTORY</label>
        <input type="text" id="logDirInput" placeholder="logs">
      </div>
      <div class="field-row">
        <div class="field">
          <label>⑪ LOG RETENTION DAYS</label>
          <input type="number" id="logRetentionInput" min="0" max="3650" step="1" value="30">
        </div>
        <div class="field">
          <label>⑫ LOG LEVEL</label>
          <select id="logLevelInput">
            <option value="normal">normal</option>
            <option value="debug">debug</option>
          </select>
        </div>
      </div>
      <div style="display:flex;gap:0.5rem;margin-top:0.5rem;">
        <button class="sl-btn" style="flex:1" onclick="openLogsFolder()">📂 Open Logs</button>
        <button class="sl-btn" style="flex:1" onclick="downloadLogsZip()">🗜 Export Logs ZIP</button>
      </div>
    </div>
    <button class="save-btn" onclick="saveSettings()">💾 設定を保存</button>
    <div class="save-notice" id="saveNotice">✓ pipeline_config.json saved</div>
    <div style="display:flex;gap:0.5rem;margin-top:0.5rem;">
      <button class="sl-btn" style="flex:1" onclick="testConnection('comfyui')">🔌 ComfyUI 接続テスト</button>
      <button class="sl-btn" style="flex:1" onclick="testConnection('llm')">🤖 LLM 接続テスト</button>
    </div>
    <div id="testResult" style="display:none;font-family:'DM Mono',monospace;font-size:0.75rem;margin-top:0.4rem;padding:0.4rem 0.6rem;border-radius:5px;"></div>
    <div style="margin-top:0.8rem;padding:0.6rem 0.7rem;background:#fff5f5;border:1px solid #e0779a;border-radius:7px;">
      <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:#c0392b;font-weight:bold;margin-bottom:0.4rem;">📋 キャラプリセット削除</div>
      <div style="display:flex;gap:0.4rem;align-items:center;">
        <select id="presetDeleteSel" style="flex:1;min-width:0;font-family:'DM Mono',monospace;font-size:0.72rem;border:1px solid #e0779a;border-radius:5px;padding:0.3rem 0.5rem;background:white;color:var(--ink);cursor:pointer;">
          <option value="">── プリセットを選択 ──</option>
        </select>
        <button onclick="deleteCharaPresetFromSettings()" style="font-family:'DM Mono',monospace;font-size:0.72rem;padding:0.3rem 0;width:2.8rem;text-align:center;border:1px solid #e0779a;border-radius:5px;background:white;color:#c0392b;cursor:pointer;">DEL</button>
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

  <div class="scene-toggle" id="navA" onclick="toggleBlock('blockA','arrowA')" style="margin-bottom:0.5rem;">
    <span id="arrowA">▶</span> 画像設定
  </div>
  <div id="blockA" style="display:none;border:1px solid var(--border);border-radius:8px;padding:1rem;background:rgba(255,255,255,0.9);margin-bottom:1rem;">
    <div style="margin-bottom:0.8rem;">
      <label>画像サイズ（Anima推奨）</label>
      <div class="size-row">
        <select id="sizePreset" onchange="applyPreset(this.value)" style="min-width:0;"></select>
        <div class="size-inputs">
          <input type="number" id="widthInput" value="1024" min="1" max="8192" step="1" oninput="selectedW=parseInt(this.value)||1024">
          <span class="size-sep">×</span>
          <input type="number" id="heightInput" value="1024" min="1" max="8192" step="1" oninput="selectedH=parseInt(this.value)||1024">
        </div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;align-items:start;">
      <div>
        <label>保存形式</label>
        <div class="fmt-row" style="margin-top:0.2rem;">
          <div class="fmt-btn active" data-fmt="png" onclick="selectFmt(this)">PNG生成</div>
          <div class="fmt-btn" data-fmt="webp" onclick="selectFmt(this)">WebP変換</div>
        </div>
        <label style="display:flex;gap:0.35rem;align-items:center;margin-top:0.55rem;letter-spacing:0.02em;text-transform:none;">
          <input type="checkbox" id="embedMetadataToggle" checked onchange="embedMetadata=this.checked">
          メタデータを埋め込む
        </label>
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

  <div class="scene-toggle" id="navA2" onclick="toggleBlock('blockA2','arrowA2')" style="margin-bottom:0.5rem;">
    <span id="arrowA2">▶</span> 生成パラメータ
  </div>
  <div id="blockA2" style="display:none;border:1px solid var(--border);border-radius:8px;padding:1rem;background:rgba(255,255,255,0.9);margin-bottom:1rem;">
    <div style="margin-bottom:0.8rem;">
      <label style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);">Seed（シード値）</label>
      <div style="display:flex;gap:0.4rem;align-items:center;margin-top:0.3rem;flex-wrap:wrap;">
        <div id="seedModeBtns" style="display:flex;gap:0.2rem;">
          <div class="period-btn active" data-smode="random" onclick="selectSeedMode(this)">ランダム</div>
          <div class="period-btn" data-smode="fixed" onclick="selectSeedMode(this)">固定</div>
          <div class="period-btn" data-smode="increment" onclick="selectSeedMode(this)">連番</div>
        </div>
        <input type="number" id="seedValueInput" value="0" min="0"
          style="width:9rem;background:white;border:1px solid var(--border);border-radius:6px;padding:0.35rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.82rem;color:var(--ink);outline:none;box-sizing:border-box;">
        <button onclick="document.getElementById('seedValueInput').value=Math.floor(Math.random()*2**32)"
          title="ランダムな値を生成"
          style="font-family:'DM Mono',monospace;font-size:0.7rem;padding:0.3rem 0.5rem;width:2.8rem;text-align:center;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;">🎲</button>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;margin-bottom:0.8rem;">
      <div>
        <label style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);">Steps</label>
        <input type="number" id="stepsInput" value="30" min="1" max="200" step="1"
          style="width:100%;background:white;border:1px solid var(--border);border-radius:6px;padding:0.55rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.82rem;color:var(--ink);outline:none;box-sizing:border-box;margin-top:0.3rem;">
      </div>
      <div>
        <label style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);">CFG</label>
        <input type="number" id="cfgInput" value="4" min="0" max="30" step="0.5"
          style="width:100%;background:white;border:1px solid var(--border);border-radius:6px;padding:0.55rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.82rem;color:var(--ink);outline:none;box-sizing:border-box;margin-top:0.3rem;">
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;">
      <div>
        <label style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);">Sampler</label>
        <select id="samplerInput"
          style="width:100%;background:white;border:1px solid var(--border);border-radius:6px;padding:0.55rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--ink);outline:none;box-sizing:border-box;margin-top:0.3rem;cursor:pointer;">
        </select>
      </div>
      <div>
        <label style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);">Scheduler</label>
        <select id="schedulerInput"
          style="width:100%;background:white;border:1px solid var(--border);border-radius:6px;padding:0.55rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--ink);outline:none;box-sizing:border-box;margin-top:0.3rem;cursor:pointer;">
        </select>
      </div>
    </div>
  </div>

  <div class="scene-toggle" id="navB" onclick="toggleBlock('blockB','arrowB')" style="margin-bottom:0.5rem;">
    <span id="arrowB">▼</span> キャラクター
  </div>
  <div id="blockB">
    <div style="border:1px solid var(--border);border-radius:8px;padding:1rem;background:rgba(255,255,255,0.9);margin-bottom:1rem;">
      <div class="struct-fields" style="margin-bottom:0.8rem;">
        <div class="struct-row required">
          <label class="struct-label">A. 共通作品（任意）</label>
          <input type="text" id="f_series" class="inp-ja" placeholder="ウマ娘（複数作品の場合はキャラごとに入力）">
        </div>
      </div>
      <div style="margin-bottom:0.5rem;display:grid;grid-template-columns:9rem 1fr;gap:0.5rem;align-items:center;">
        <label class="struct-label" style="text-align:right;padding-right:0.5rem;font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--muted);">B. キャラ数 *</label>
        <input type="number" id="f_charcount" value="1" min="0" max="6" step="1"
          style="width:80px;background:#f8f4ff;border:1px solid var(--accent);border-radius:6px;padding:0.55rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.82rem;color:var(--ink);outline:none;"
          oninput="updateCharaBlocks()">
      </div>
      <div id="presetThumbPanel" style="margin-bottom:0.9rem;border:1px solid var(--border);border-radius:8px;padding:0.65rem;background:#fbfafc;">
        <div id="presetThumbToggle" onclick="togglePresetThumbPanel()" style="display:flex;justify-content:space-between;align-items:center;gap:0.5rem;flex-wrap:wrap;cursor:pointer;">
          <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);font-weight:bold;"><span id="presetThumbArrow">▶</span> 🖼 プリセット一覧（サムネイル）</div>
          <div style="font-family:'DM Mono',monospace;font-size:0.66rem;color:var(--muted);">対象プリセット: <span id="presetThumbTargetName">-</span></div>
        </div>
        <div id="presetThumbBody" style="display:none;">
          <div id="presetThumbSheetTop" style="display:none;">
            <button id="presetThumbCloseBtn" onclick="event.stopPropagation();togglePresetThumbPanel(false)"
              style="font-family:'DM Mono',monospace;font-size:0.68rem;padding:0.32rem 0.6rem;
              border:1px solid var(--border);border-radius:8px;background:white;color:var(--ink);cursor:pointer;white-space:nowrap;">
              ✕ 閉じる
            </button>
            <div id="presetThumbSheetTitle" style="flex:1;text-align:center;font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);font-weight:bold;">
              プリセット一覧
            </div>
            <div id="presetThumbSheetTargetWrap" style="font-family:'DM Mono',monospace;font-size:0.64rem;color:var(--muted);white-space:nowrap;">
              対象:<span id="presetThumbSheetTargetName">-</span>
            </div>
          </div>
          <div style="font-family:'DM Mono',monospace;font-size:0.64rem;color:var(--muted);margin-top:0.2rem;">ギャラリー画像を拡大表示してから「プリセットのサムネイル作成」を押してください</div>
          <div id="presetThumbControlRow" style="margin-top:0.35rem;display:flex;align-items:center;gap:0.4rem;">
            <div style="font-family:'DM Mono',monospace;font-size:0.64rem;color:var(--muted);white-space:nowrap;">更新先:</div>
            <select id="presetThumbTargetSel" onclick="event.stopPropagation()" onchange="onPresetThumbTargetChange(this.value)"
              style="flex:1 1 180px;min-width:120px;background:white;border:1px solid var(--border);border-radius:6px;padding:0.35rem 0.45rem;font-family:'DM Mono',monospace;font-size:0.68rem;color:var(--ink);outline:none;cursor:pointer;">
              <option value="">-- Select Preset --</option>
            </select>
            <button id="presetThumbAddBtn" onclick="event.stopPropagation();addCharaFromSelectedPreset();" style="font-family:'DM Mono',monospace;font-size:0.68rem;padding:0.32rem 0.55rem;border:1px solid var(--accent);border-radius:6px;background:white;color:var(--accent);cursor:pointer;white-space:nowrap;">＋ キャラ追加</button>
          </div>
          <div id="presetThumbGrid" style="margin-top:0.5rem;display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:0.4rem;max-height:300px;overflow-y:auto;border:1px solid var(--border);border-radius:8px;padding:0.4rem;background:#fafaf8;"></div>
        </div>
      </div>
      <div id="charaContainer"></div>
    </div>
  </div>
  <div id="navC" class="scene-toggle" onclick="toggleBlock('blockC','arrowC')" style="margin-bottom:0.5rem;">
    <span id="arrowC">▶</span> シーン・雰囲気（任意）
  </div>
  <div id="blockC" style="display:none;border:1px solid var(--border);border-radius:8px;padding:1rem;background:rgba(255,255,255,0.9);margin-bottom:1rem;">
      <div class="scene-optional" id="sceneOptional" style="padding-top:0.4rem;">
          <div class="opt-row">
            <div class="opt-label-wrap"><span class="opt-label">C-1. 世界観</span></div>
            <div style="display:flex;gap:0.25rem;flex-wrap:wrap;">
              <div id="world_btns" style="display:flex;gap:0.25rem;flex-wrap:wrap;"></div>
            </div>
          </div>
          <div class="opt-row" style="margin-top:0.4rem;align-items:start;">
            <div class="opt-label-wrap"><span class="opt-label">C-2. 場所</span></div>
            <div style="display:flex;flex-direction:column;gap:0.3rem;width:100%;">
              <div id="place_cat_row" style="display:flex;gap:0.2rem;flex-wrap:wrap;">
                <div class="period-btn" data-placecat="屋外" onclick="showPlaceCat('屋外',this)">屋外</div>
                <div class="period-btn" data-placecat="屋内" onclick="showPlaceCat('屋内',this)">屋内</div>
                <div class="period-btn" data-placecat="特殊" onclick="showPlaceCat('特殊',this)">特殊</div>
              </div>
              <div id="place_sub_row" style="display:none;gap:0.2rem;flex-wrap:wrap;"></div>
              <div id="place_item_row" style="display:none;gap:0.2rem;flex-wrap:wrap;"></div>
              <input type="text" id="f_place" class="inp-ja" placeholder="場所を自由入力（例: 競馬場、魔法学校）">
              <input type="hidden" id="f_outdoor" value="">
            </div>
          </div>
          <div class="opt-row" style="margin-top:0.4rem;">
            <div class="opt-label-wrap"><span class="opt-label">C-3. 時間帯</span></div>
            <div style="display:flex;gap:0.25rem;flex-wrap:wrap;">
              <div id="tod_btns" style="display:flex;gap:0.25rem;flex-wrap:wrap;"></div>
            </div>
          </div>
          <div class="opt-row" style="margin-top:0.4rem;">
            <div class="opt-label-wrap"><span class="opt-label">C-4. 天気</span></div>
            <div style="display:flex;gap:0.25rem;flex-wrap:wrap;">
              <div id="weather_btns" style="display:flex;gap:0.25rem;flex-wrap:wrap;"></div>
            </div>
          </div>
          <div class="opt-row" style="margin-top:0.4rem;">
            <div class="opt-label-wrap"><span class="opt-label">C-5. その他</span></div>
            <input type="text" id="f_misc" class="inp-ja" placeholder="例: 緊張感、幻想的な雰囲気">
          </div>
          <input type="hidden" id="f_world" value="">
          <input type="hidden" id="f_outdoor" value="">
          <input type="hidden" id="f_tod" value="">
          <input type="hidden" id="f_weather" value="">
        </div>
      </div>
      <div style="margin-top:0.6rem;">
        <div style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.2rem;">D. 補足メモ（日本語）→ LLMに渡す（1回目のプロンプト生成のみ）</div>
        <textarea id="extraNoteJa" class="inp-ja" rows="2" placeholder="例: お姉さんが弟分を甘やかしている雰囲気、ドキドキしている"
          style="width:100%;background:white;border:1px solid var(--border);border-radius:6px;padding:0.5rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;
          resize:vertical;box-sizing:border-box;"></textarea>
      </div>
  <div id="navLora" class="scene-toggle" onclick="toggleBlock('blockLora','arrowLora')" style="margin-bottom:0.5rem;">
    <span id="arrowLora">▶</span> LoRA
  </div>
  <div id="blockLora" style="display:none;border:1px solid var(--border);border-radius:8px;padding:1rem;background:rgba(255,255,255,0.9);margin-bottom:1rem;">
    <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:var(--muted);margin-bottom:0.6rem;">ワークフロー内の LoraLoader ノードに順番に注入されます。空欄はスキップ。</div>
    <div id="loraSlots"></div>
  </div>

  <div style="display:flex;align-items:center;justify-content:center;gap:0.5rem;margin-bottom:0.5rem;">
    <input type="checkbox" id="useLLM" checked style="width:14px;height:14px;accent-color:var(--multi);cursor:pointer;">
    <label for="useLLM" style="font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--muted);cursor:pointer;user-select:none;">LLMを使用する</label>
  </div>
  <button id="btn" onclick="generate()">▶ 生成開始　(Ctrl+Enter)</button>
  <button class="btn-cancel" id="cancelBtn" onclick="cancelGenerate()">■ 生成中止</button>

  <div class="extra-block" id="extraBlock" style="margin-top:0.8rem;border:1px solid var(--border);padding:0.8rem;background:#fafaf8;">
    <div class="scene-toggle" id="navExtra" onclick="toggleExtraContent()" style="cursor:pointer;margin-bottom:0.5rem;">
      <span id="extraContentArrow">▶</span> プロンプト調整・追加（再生成に反映されます）
    </div>
    <div id="extraContent" style="display:none;">

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ① 期間タグ</div>
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

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ② 品質タグ（人間ベース）</div>
      <div class="tag-check-group" id="qualityHuman"></div>
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin:0.4rem 0 0.3rem;">▼ ② 品質タグ（PonyV7 aestheticベース）</div>
      <div class="tag-check-group" id="qualityPony"></div>
    </div>

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ③ メタタグ</div>
      <div class="tag-check-group" id="metaTags"></div>
    </div>

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ④ 安全タグ（単一選択）</div>
      <div style="display:flex;gap:0.3rem;">
        <div id="safety_btns" style="display:flex;gap:0.25rem;flex-wrap:wrap;"></div>
      </div>
    </div>

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ⑤ Style (@Artist Name)<span style="color:#c0392b;"> *Input in English (e.g.: takeuchi naoko)</span></div>
      <div class="extra-presets" id="stylePresets"></div>
      <div class="style-row" style="margin-top:0.4rem;">
        <input type="text" id="styleInput" class="inp-en" placeholder="Add New (e.g.: takeuchi naoko)"
          style="flex:1;min-width:0;background:white;border:1px solid var(--border);padding:0.45rem 0.6rem;
          font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;">
        <button onclick="addStyle()"
          style="flex-shrink:0;width:4rem;border:1px solid var(--border);background:white;
          padding:0.45rem 0;font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--ink);
          cursor:pointer;text-align:center;">追加</button>
      </div>
      <div id="styleBadges" style="display:flex;flex-wrap:wrap;gap:0.3rem;margin-top:0.4rem;min-height:1rem;"></div>
    </div>

    <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ⑥ Extra Tags (add after Chara/Scene tags)</div>
    <div class="extra-presets" id="extraPresets"></div>
    <div class="extra-custom" style="margin-top:0.5rem;">
      <input type="text" id="extraCustomInput" class="inp-en" placeholder="カスタムタグを入力（例: breast_grab）">
      <button onclick="addCustomTag()">追加</button>
    </div>
    <div class="extra-badges" id="extraBadges"></div>
    <div style="margin-top:0.6rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.2rem;">▼ ⑦ 追記文（英語）→ プロンプト末尾に直接追加</div>
      <textarea id="extraNoteEn" class="inp-en" rows="2" placeholder="e.g. she gently strokes his hair with a warm smile"
        style="width:100%;background:white;border:1px solid var(--border);border-radius:6px;padding:0.5rem 0.6rem;
        font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;
        resize:vertical;box-sizing:border-box;"></textarea>
    </div>
    </div><!-- /extraContent -->
  </div>

  <div style="margin-top:0.6rem;border:1px solid #e8c4c4;border-radius:8px;padding:0.8rem;background:#fff9f9;">
    <div class="scene-toggle" id="navNeg" onclick="toggleNegContent()" style="cursor:pointer;margin-bottom:0.5rem;color:#c0392b;">
      <span id="negContentArrow">▶</span> ネガティブプロンプト調整
    </div>
    <div id="negContent" style="display:none;">

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ① Period Tags (shared with Positive)</div>
      <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:#aaa;">ポジティブの期間タグ設定がネガティブにも反映されます</div>
    </div>

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ② 品質タグ（人間ベース: NORMAL/LOW/WORST）</div>
      <div class="tag-check-group" id="qualityHumanNeg"></div>
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin:0.4rem 0 0.3rem;">▼ ② 品質タグ（Pony）</div>
      <div class="tag-check-group" id="qualityPonyNeg"></div>
    </div>

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ③ メタタグ</div>
      <div class="tag-check-group" id="metaTagsNeg"></div>
    </div>

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ④ 安全タグ（単一選択）</div>
      <div id="neg_safety_btns" style="display:flex;gap:0.25rem;flex-wrap:wrap;"></div>
    </div>

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ⑤ スタイル（@アーティスト名・ネガティブ専用）<span style="color:#c0392b;"> ※英語表記</span></div>
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

    <div style="margin-bottom:0.7rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.3rem;">▼ ⑥ Extraタグ（ネガティブ専用・右クリックで削除）</div>
      <div class="extra-presets" id="negExtraPresets"></div>
      <div class="extra-custom" style="margin-top:0.5rem;">
        <input type="text" id="negExtraCustomInput" class="inp-en" placeholder="タグを追加（例: bad anatomy）">
        <button onclick="addNegCustomTag()">追加</button>
      </div>
      <div class="extra-badges" id="negExtraBadges"></div>
    </div>

    <div style="margin-top:0.6rem;">
      <div class="toggle-section-header" style="font-family:'DM Mono',monospace;font-size:0.72rem;color:var(--muted);margin-bottom:0.2rem;">▼ ⑦ 追記文（英語）→ ネガティブプロンプト末尾に直接追加</div>
      <textarea id="negExtraNoteEn" class="inp-en" rows="2" placeholder="e.g. cropped, out of frame"
        style="width:100%;background:white;border:1px solid #e8c4c4;border-radius:6px;padding:0.5rem 0.6rem;
        font-family:'DM Mono',monospace;font-size:0.78rem;color:var(--ink);outline:none;
        resize:vertical;box-sizing:border-box;"></textarea>
    </div>

    </div><!-- /negContent -->
  </div>

  <button class="btn-regen" id="regenBtn" onclick="regenPrompt()">↺ 再画像生成</button>
  <div id="navStatus"></div>

  <div class="status-box" id="statusBox">
    <div class="status-label">処理状況</div>
    <div id="steps"></div>
    <div class="progress-bar-wrap" id="progressBarWrap">
      <div class="progress-bar" id="progressBar"></div>
    </div>
    <div id="wsNotice" style="display:none;font-family:'DM Mono',monospace;font-size:0.62rem;color:var(--muted);margin-top:0.2rem;">※ 起動直後は進捗%が表示されない場合があります（初回WS接続のタイミングによる）</div>
    <div class="prompt-section-label" id="lmLabel" style="display:none;" onclick="togglePromptSection('promptOutput',this)">
      <span>▸ LLM生成ポジティブプロンプト</span>
      <button class="copy-btn" onclick="event.stopPropagation();copyPrompt('promptOutput',this)">コピー</button>
    </div>
    <div class="prompt-output" id="promptOutput"></div>
    <div class="prompt-section-label" id="finalLabel" style="display:none;" onclick="togglePromptSection('promptFinal',this)">
      <span>▸ ComfyUI Sent Positive Prompt (Generated + Added Tags)</span>
      <button class="copy-btn" onclick="event.stopPropagation();copyPrompt('promptFinal',this)">コピー</button>
    </div>
    <div class="prompt-final" id="promptFinal" style="display:none;font-family:'DM Mono',monospace;font-size:0.8rem;color:var(--ink);"></div>
    <div class="prompt-section-label" id="negFinalLabel" style="display:none;" onclick="togglePromptSection('promptNegFinal',this)">
      <span>▸ ComfyUI 送信ネガティブプロンプト</span>
      <button class="copy-btn" onclick="event.stopPropagation();copyPrompt('promptNegFinal',this)">コピー</button>
    </div>
    <div class="prompt-final" id="promptNegFinal" style="display:none;font-family:'DM Mono',monospace;font-size:0.8rem;color:#c0392b;"></div>
  </div>

  <div id="gallerySection" style="display:none;margin-top:1rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;gap:0.5rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--muted);font-weight:bold;white-space:nowrap;">📷 生成履歴（このセッション）</div>
      <button onclick="clearGallery()" style="font-family:'DM Mono',monospace;font-size:0.7rem;padding:0.2rem 0.8rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--muted);cursor:pointer;white-space:nowrap;flex-shrink:0;width:auto;">クリア</button>
    </div>
    <div style="display:flex;gap:0.4rem;margin-bottom:0.5rem;">
      <button id="galleryTabSession" onclick="setGalleryTab('session')" style="margin:0;width:auto;padding:0.25rem 0.7rem;border:1px solid var(--border);border-radius:999px;background:var(--highlight);color:var(--multi);font-family:'DM Mono',monospace;font-size:0.68rem;cursor:pointer;">セッション履歴</button>
      <button id="galleryTabAll" onclick="setGalleryTab('all')" style="margin:0;width:auto;padding:0.25rem 0.7rem;border:1px solid var(--border);border-radius:999px;background:white;color:var(--muted);font-family:'DM Mono',monospace;font-size:0.68rem;cursor:pointer;">全履歴</button>
    </div>
    <div id="galleryGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:0.5rem;"></div>
    <div id="galleryGridAll" style="display:none;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:0.5rem;"></div>
    <div id="historyPager" style="display:none;margin-top:0.5rem;justify-content:flex-end;align-items:center;gap:0.4rem;">
      <button onclick="changeHistoryPage(-1)" style="margin:0;width:auto;padding:0.2rem 0.6rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);font-family:'DM Mono',monospace;font-size:0.68rem;cursor:pointer;">Prev</button>
      <div id="historyPageLabel" style="font-family:'DM Mono',monospace;font-size:0.68rem;color:var(--muted);min-width:4.5rem;text-align:center;">1/1</div>
      <button onclick="changeHistoryPage(1)" style="margin:0;width:auto;padding:0.2rem 0.6rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);font-family:'DM Mono',monospace;font-size:0.68rem;cursor:pointer;">Next</button>
    </div>
  </div>

  <div id="galleryModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:1000;display:none;align-items:center;justify-content:center;padding:1rem;" onclick="closeGalleryModal(event)">
    <div style="max-width:860px;width:100%;max-height:90vh;overflow-y:auto;padding:1rem;background:white;border-radius:12px;" onclick="event.stopPropagation()">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.8rem;flex-wrap:wrap;gap:0.4rem;">
        <div style="font-family:'DM Mono',monospace;font-size:0.8rem;color:var(--muted);" id="modalTitle">生成結果</div>
        <div class="modalBtnRow" style="display:flex;gap:0.4rem;flex-wrap:wrap;">
          <button id="modalThumbBtn" onclick="createPresetThumbnailFromModal()" style="font-family:'DM Mono',monospace;font-size:0.72rem;padding:0.3rem 0.7rem;border:1px solid #3a8c5c;border-radius:5px;background:white;color:#2f7a50;cursor:pointer;white-space:nowrap;">🖼 プリセットのサムネイル作成</button>
          <button id="modalReuseBtn" onclick="reusePromptFromModal()" style="font-family:'DM Mono',monospace;font-size:0.72rem;padding:0.3rem 0.7rem;border:1px solid var(--accent);border-radius:5px;background:white;color:var(--accent);cursor:pointer;white-space:nowrap;">↺ プロンプト再利用</button>
          <button id="modalFolderBtn" onclick="openFolderFromModal()" style="font-family:'DM Mono',monospace;font-size:0.72rem;padding:0.3rem 0.7rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;white-space:nowrap;">📁 フォルダを開く</button>
          <button onclick="document.getElementById('galleryModal').style.display='none'" style="font-family:'DM Mono',monospace;font-size:0.72rem;padding:0.3rem 0.7rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;white-space:nowrap;">✕ 閉じる</button>
        </div>
      </div>
      <img id="modalImg" src="" style="width:100%;border-radius:8px;margin-bottom:0.8rem;">
      <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:var(--muted);margin-bottom:0.3rem;">▸ Sent Positive Prompt</div>
      <div id="modalPositive" style="font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--ink);background:#f8f8f8;border-radius:6px;padding:0.6rem;margin-bottom:0.6rem;white-space:pre-wrap;word-break:break-all;"></div>
      <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:var(--muted);margin-bottom:0.3rem;">▸ 送信ネガティブプロンプト</div>
      <div id="modalNegative" style="font-family:'DM Mono',monospace;font-size:0.75rem;color:#c0392b;background:#fff5f5;border-radius:6px;padding:0.6rem;white-space:pre-wrap;word-break:break-all;"></div>
    </div>
</div>
</div>

<script>
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
  'オリジナル': 'Original',
  'プリセット選択': 'Preset',
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

let running=false, settingsOpen=false, lastPositivePrompt=null;
window._comfyClientId = 'anima-' + Math.random().toString(36).slice(2,10);
window._comfyWs = null;
window._comfyWsReady = false;

window._comfyWsHandler = null; // pollComfyUICompleteがセットするハンドラ

function initComfyWs(){
  const comfyUrlRaw = (document.getElementById('comfyUrlInput')?.value||'http://127.0.0.1:8188').trim();
  const comfyPort = new URL(comfyUrlRaw).port || '8188';
  const reqHost = location.hostname;
  const wsHost = (reqHost !== '127.0.0.1' && reqHost !== 'localhost')
    ? reqHost + ':' + comfyPort
    : new URL(comfyUrlRaw).host;
  const wsUrl = 'ws://' + wsHost + '/ws?clientId=' + encodeURIComponent(window._comfyClientId);
  try{
    if(window._comfyWs){ try{ window._comfyWs.close(); }catch(_){} }
    window._comfyWs = new WebSocket(wsUrl);
    window._comfyWs.onopen = ()=>{
      window._comfyWsReady = true;
      // 再接続時に最新のハンドラを再セット
      if(window._comfyWsHandler) window._comfyWs.onmessage = window._comfyWsHandler;
    };
    window._comfyWs.onerror = ()=>{ window._comfyWsReady = false; };
    window._comfyWs.onclose = ()=>{ window._comfyWsReady = false; setTimeout(initComfyWs, 5000); };
    window._comfyWs.onmessage = ()=>{};
  }catch(e){}
}
let lastFinalPrompt='', lastNegativePrompt='';

// ===== ギャラリー =====
let galleryItems = []; // {imagePaths:[], positivePrompt:'', negativePrompt:'', timestamp:''}
let modalItemIndex = -1;
let modalCurrentImgUrl = '';
let currentGalleryTab = 'session';
let historyPage = 1;
let historyTotalPages = 1;
const historyPerPage = 20;
let selectedPresetFilename = '';
let presetThumbOpen = false;
let _updatingPresetThumbTargetSel = false;

function addGalleryItems(imagePaths, positivePrompt, negativePrompt){
  if(!imagePaths || imagePaths.length===0) return;
  const item = {
    imagePaths,
    positivePrompt: positivePrompt||'',
    negativePrompt: negativePrompt||'',
    timestamp: new Date().toLocaleTimeString(currentLang==='ja'?'ja-JP':'en-US',{hour:'2-digit',minute:'2-digit',second:'2-digit'})
  };
  galleryItems.push(item);
  renderGalleryItem(item, galleryItems.length-1);
  document.getElementById('gallerySection').style.display='block';
  if(currentGalleryTab === 'all'){
    loadAllHistory(1);
  }
}

function renderGalleryItem(item, idx){
  const grid = document.getElementById('galleryGrid');
  item.imagePaths.forEach((imgPath, pi)=>{
    const card = document.createElement('div');
    card.style.cssText = 'position:relative;cursor:pointer;border-radius:8px;overflow:hidden;background:#f0f0f0;aspect-ratio:1;';
    const img = document.createElement('img');
    img.src = buildGalleryImageSrc(imgPath);
    img.style.cssText = 'width:100%;height:100%;object-fit:cover;display:block;';
    img.onerror = ()=>{ img.style.display='none'; card.style.background='#e0e0e0'; };
    const ts = document.createElement('div');
    ts.style.cssText = 'position:absolute;bottom:0;left:0;right:0;background:rgba(0,0,0,0.5);color:white;font-family:DM Mono,monospace;font-size:0.6rem;padding:0.2rem 0.4rem;';
    ts.textContent = item.timestamp;
    card.appendChild(img);
    card.appendChild(ts);
    card.onclick = ()=>openGalleryModal(idx, imgPath, item);
    grid.insertBefore(card, grid.firstChild);
  });
}

function openGalleryModal(idx, imgPath, item){
  modalItemIndex = idx;
  const modal = document.getElementById('galleryModal');
  if(modal.parentElement !== document.body) document.body.appendChild(modal);
  modal.style.display='flex';
  const candidates = [];
  const pushCandidate = (p)=>{
    const v = String(p||'').trim();
    if(!v) return;
    if(candidates.includes(v)) return;
    candidates.push(v);
  };
  pushCandidate(imgPath);
  if(item && Array.isArray(item.imagePaths)){
    item.imagePaths.forEach(pushCandidate);
  }
  modalCurrentImgUrl = candidates[0] || '';
  const modalImg = document.getElementById('modalImg');
  let candidateIdx = 0;
  let retry = 0;
  const maxRetryPerCandidate = 2;
  const loadModal = ()=>{
    const cur = candidates[candidateIdx] || '';
    if(!cur){
      modalImg.removeAttribute('src');
      return;
    }
    modalCurrentImgUrl = cur;
    modalImg.src = buildGalleryImageSrc(cur);
  };
  modalImg.onerror = ()=>{
    if(retry < maxRetryPerCandidate){
      retry += 1;
      setTimeout(loadModal, 120);
      return;
    }
    retry = 0;
    candidateIdx += 1;
    if(candidateIdx < candidates.length){
      setTimeout(loadModal, 60);
    }
  };
  loadModal();
  document.getElementById('modalTitle').textContent = '生成結果 ' + item.timestamp;
  document.getElementById('modalPositive').textContent = item.positivePrompt||'（なし）';
  document.getElementById('modalNegative').textContent = item.negativePrompt||'（なし）';
  updateThumbActionState();
}

function closeGalleryModal(event){
  document.getElementById('galleryModal').style.display='none';
}

function buildGalleryImageSrc(imgPath){
  if(String(imgPath||'').startsWith('http')) return imgPath;
  const nonce = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  return '/get_image?path=' + encodeURIComponent(imgPath) + '&_=' + nonce;
}

function getPresetThumbPath(preset){
  if(!preset || !preset._filename) return '';
  if(preset._thumb_path) return preset._thumb_path;
  return '';
}

function updateThumbActionState(){
  const btn = document.getElementById('modalThumbBtn');
  if(!btn) return;
  const canRun = !!selectedPresetFilename && !!modalCurrentImgUrl;
  btn.disabled = !canRun;
  btn.style.opacity = canRun ? '1' : '0.45';
  btn.style.cursor = canRun ? 'pointer' : 'not-allowed';
}

function togglePresetThumbPanel(forceOpen=null){
  if(forceOpen === null) presetThumbOpen = !presetThumbOpen;
  else presetThumbOpen = !!forceOpen;

  const body = document.getElementById('presetThumbBody');
  const arrow = document.getElementById('presetThumbArrow');

  if(body) body.style.display = presetThumbOpen ? 'block' : 'none';

  if(arrow) arrow.textContent = presetThumbOpen ? '▼' : '▶';

  if(presetThumbOpen){
    renderPresetThumbList();
    setTimeout(()=>{
      const grid = document.getElementById('presetThumbGrid');
      if(grid) grid.scrollTop = 0;
    }, 0);
  }
}

function updatePresetThumbTargetSelect(){
  const sel = document.getElementById('presetThumbTargetSel');
  if(!sel) return;
  _updatingPresetThumbTargetSel = true;
  const cur = selectedPresetFilename;
  sel.innerHTML = '<option value="">-- Select Preset --</option>';
  charaPresets.forEach((p)=>{
    const opt = document.createElement('option');
    opt.value = p._filename || '';
    opt.textContent = p.name || p._filename || '(unnamed)';
    sel.appendChild(opt);
  });
  if(cur && charaPresets.some(p=>p._filename===cur)){
    sel.value = cur;
  }
  _updatingPresetThumbTargetSel = false;
}

function onPresetThumbTargetChange(filename){
  if(_updatingPresetThumbTargetSel) return;
  if(!filename) return;
  if(filename === selectedPresetFilename) return;
  selectedPresetFilename = filename;
  renderPresetThumbList();
}

function addCharaFromSelectedPreset(){
  if(!selectedPresetFilename){
    alert('先に対象プリセットを選択してください');
    return;
  }
  const presetIndex = charaPresets.findIndex(p => p._filename === selectedPresetFilename);
  if(presetIndex < 0){
    alert('対象プリセットが見つかりません');
    return;
  }
  const countEl = document.getElementById('f_charcount');
  const current = Math.max(0, Math.min(6, parseInt(countEl?.value)||0));
  if(current >= 6){
    alert('キャラ数は最大6です');
    return;
  }
  if(countEl) countEl.value = String(current + 1);
  updateCharaBlocks();
  const newIdx = current;
  const sel = document.getElementById('chara_preset_sel_' + newIdx);
  if(sel){
    sel.value = String(presetIndex);
  }
}

function renderPresetThumbList(){
  const grid = document.getElementById('presetThumbGrid');
  const targetEl = document.getElementById('presetThumbTargetName');
  const sheetTargetEl = document.getElementById('presetThumbSheetTargetName');
  if(!grid) return;
  if(presetThumbOpen) updatePresetThumbTargetSelect();
  if(targetEl){
    const curName = charaPresets.find(p=>p._filename===selectedPresetFilename)?.name
      || charaPresets[0]?.name
      || '-';
    targetEl.textContent = curName;
  }
  if(!presetThumbOpen) return;
  if(!selectedPresetFilename || !charaPresets.some(p=>p._filename===selectedPresetFilename)){
    selectedPresetFilename = charaPresets[0]?._filename || '';
    updatePresetThumbTargetSelect();
  }
  grid.innerHTML = '';
  if(charaPresets.length===0){
    const empty = document.createElement('div');
    empty.style.cssText = 'grid-column:1/-1;font-family:DM Mono,monospace;font-size:0.68rem;color:var(--muted);padding:0.4rem;';
    empty.textContent = 'サムネイル未設定';
    grid.appendChild(empty);
    if(targetEl) targetEl.textContent = '-';
    if(sheetTargetEl) sheetTargetEl.textContent = '-';
    updateThumbActionState();
    return;
  }
  const shown = charaPresets.filter(p=>!!p._thumb_path);
  if(shown.length===0){
    const empty = document.createElement('div');
    empty.style.cssText = 'grid-column:1/-1;font-family:DM Mono,monospace;font-size:0.68rem;color:var(--muted);padding:0.4rem;';
    empty.textContent = 'サムネイル未設定';
    grid.appendChild(empty);
    if(sheetTargetEl) sheetTargetEl.textContent = '-';
    updateThumbActionState();
    return;
  }
  shown.forEach((p)=>{
    const active = p._filename===selectedPresetFilename;
    const card = document.createElement('div');
    card.style.cssText = 'position:relative;border:2px solid '+(active?'var(--multi)':'var(--border)')+';border-radius:8px;overflow:hidden;cursor:pointer;background:#f0f0f0;aspect-ratio:1;transition:border-color 0.15s;';
    card.title = p.name || p._filename;
    card.onclick = ()=>{
      selectedPresetFilename = p._filename;
      renderPresetThumbList();
    };
    const imgWrap = document.createElement('div');
    imgWrap.style.cssText = 'width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:#ececf2;';
    const img = document.createElement('img');
    img.src = '/chara_thumb?file=' + encodeURIComponent(p._filename) + '&_ts=' + Date.now();
    // iOS/Safari では fixed + overflow の組み合わせで lazy が効きすぎることがあるため、
    // スマホ幅では eager に切り替える（すぐサムネが見える）
    img.loading = (window.innerWidth <= 700) ? 'eager' : 'lazy';
    img.decoding = 'async';
    img.style.cssText = 'width:100%;height:100%;object-fit:cover;display:block;';
    img.onerror = ()=>{ img.remove(); };
    imgWrap.appendChild(img);
    const name = document.createElement('div');
    name.style.cssText = 'position:absolute;bottom:0;left:0;right:0;background:rgba(0,0,0,0.65);color:white;font-family:DM Mono,monospace;font-size:0.58rem;padding:0.2rem 0.3rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    name.textContent = (p.name || p._filename);
    card.appendChild(imgWrap);
    card.appendChild(name);
    grid.appendChild(card);
  });
  const cur = charaPresets.find(p=>p._filename===selectedPresetFilename);
  const displayName = cur ? (cur.name || cur._filename) : '-';
  if(targetEl) targetEl.textContent = displayName;
  if(sheetTargetEl) sheetTargetEl.textContent = displayName;
  updateThumbActionState();
}

async function createPresetThumbnailFromModal(){
  if(!selectedPresetFilename){
    alert('サムネ作成対象のプリセットを選択してください');
    return;
  }
  if(!modalCurrentImgUrl){
    alert('ギャラリー画像を先に開いてください');
    return;
  }
  const preset = charaPresets.find(p=>p._filename===selectedPresetFilename);
  if(!preset) return;
  if(!confirm(`「${preset.name || preset._filename}」のサムネイルを更新しますか？`)) return;
  try{
    const res = await fetch('/chara_preset_thumb',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ filename:selectedPresetFilename, image_path:modalCurrentImgUrl })
    });
    const data = await res.json();
    if(!res.ok || !data.ok) throw new Error(data.error || 'unknown error');
    await loadCharaPresets();
    renderPresetThumbList();
    alert('サムネイル保存: ' + (data.thumb_file || 'OK'));
  }catch(e){
    alert('サムネイル作成失敗: ' + e.message);
  }
}

async function openFolderFromModal(){
  if(!modalCurrentImgUrl) return;
  await fetch('/open_folder?path='+encodeURIComponent(modalCurrentImgUrl));
}

function reusePromptFromModal(){
  if(modalItemIndex<0) return;
  const item = galleryItems[modalItemIndex];
  if(!item) return;
  lastPositivePrompt = item.positivePrompt;
  document.getElementById('galleryModal').style.display='none';
  document.getElementById('regenBtn').classList.add('show');
  alert('プロンプトを再利用モードに設定しました。「↺ 再画像生成」ボタンで送信できます。');
}

function updateNavPosition(){
  const nav = document.getElementById('floatNav');
  if(!nav) return;
  if(window.innerWidth <= 700){
    nav.style.removeProperty('right');
    nav.style.removeProperty('left');
    nav.style.removeProperty('top');
    nav.style.display = 'flex';
    // floatNavの実高さに合わせて、ボトムシートの bottom を自動調整する
    requestAnimationFrame(()=>{
      document.documentElement.style.setProperty('--floatNavH', nav.offsetHeight+'px');
    });
    return;
  }
  nav.style.right = '16px';
  nav.style.left = 'auto';
  nav.style.display = 'flex';
  document.documentElement.style.removeProperty('--floatNavH');
}
window.addEventListener('resize', updateNavPosition);

// ===== opt-rowトグル（PC/スマホ共通） =====
// ===== 設定パネル・ポジネガセクショントグル =====
function initSectionToggles(){
  document.querySelectorAll('.settings-section-header').forEach(header=>{
    if(header.dataset.toggleInit) return;
    header.dataset.toggleInit = '1';
    const targetId = header.dataset.target;
    const target = document.getElementById(targetId);
    if(!target) return;
    header.addEventListener('click', ()=>{
      const collapsed = target.style.display === 'none';
      target.style.display = collapsed ? '' : 'none';
      header.textContent = header.textContent.replace(collapsed ? '▶' : '▼', collapsed ? '▼' : '▶');
    });
  });

  document.querySelectorAll('.toggle-section-header').forEach(header=>{
    if(header.dataset.toggleInit) return;
    header.dataset.toggleInit = '1';
    header.style.cursor = 'pointer';
    header.style.userSelect = 'none';

    // ラベルから次のtoggle-section-headerまでの要素をopt-section-bodyでラップ
    if(!header.nextElementSibling || header.nextElementSibling.classList.contains('opt-section-body')){
    } else {
      const body = document.createElement('div');
      body.className = 'opt-section-body';
      const siblings = [];
      let next = header.nextElementSibling;
      while(next && !next.classList.contains('toggle-section-header')){
        siblings.push(next);
        next = next.nextElementSibling;
      }
      if(siblings.length > 0){
        header.parentNode.insertBefore(body, siblings[0]);
        siblings.forEach(s => body.appendChild(s));
      }
    }

    header.addEventListener('click', ()=>{
      const body = header.nextElementSibling;
      if(!body || !body.classList.contains('opt-section-body')) return;
      const collapsed = body.style.display === 'none';
      body.style.display = collapsed ? '' : 'none';
      const text = header.textContent;
      header.textContent = text.replace(collapsed ? '▶' : '▼', collapsed ? '▼' : '▶');
    });
  });
}

function togglePromptSection(targetId, labelEl){
  const target = document.getElementById(targetId);
  if(!target) return;
  const collapsed = labelEl.classList.toggle('collapsed');
  if(collapsed){
    target.dataset.prevDisplay = target.style.display || '';
    target.style.display = 'none';
  } else {
    target.style.display = target.dataset.prevDisplay || 'block';
  }
}

function initOptRows(root){
  const target = root || document;
  target.querySelectorAll('.opt-row').forEach(row=>{
    const labelWrap = row.querySelector('.opt-label-wrap');
    if(!labelWrap) return;
    if(labelWrap.dataset.toggleInit) return;
    labelWrap.dataset.toggleInit = '1';
    if(!row.querySelector('.opt-row-body')){
      const body = document.createElement('div');
      body.className = 'opt-row-body';
      const children = [...row.children].filter(c => !c.classList.contains('opt-label-wrap'));
      children.forEach(c => body.appendChild(c));
      row.appendChild(body);
    }
    if(window.innerWidth <= 700) row.classList.add('collapsed');
    labelWrap.addEventListener('click', ()=>{
      row.classList.toggle('collapsed');
    });
  });
}

function navScrollTo(id){
  const el = document.getElementById(id);
  if(!el) return;
  el.scrollIntoView({behavior:'smooth', block:'start'});
}

function clearGallery(){
  galleryItems = [];
  document.getElementById('galleryGrid').innerHTML='';
  const allGrid = document.getElementById('galleryGridAll');
  const hasAll = !!(allGrid && allGrid.children && allGrid.children.length);
  document.getElementById('gallerySection').style.display = hasAll ? 'block' : 'none';
}

function setGalleryTab(tab){
  currentGalleryTab = (tab === 'all') ? 'all' : 'session';
  const btnSession = document.getElementById('galleryTabSession');
  const btnAll = document.getElementById('galleryTabAll');
  const gridSession = document.getElementById('galleryGrid');
  const gridAll = document.getElementById('galleryGridAll');
  const pager = document.getElementById('historyPager');
  if(btnSession){
    btnSession.style.background = (currentGalleryTab === 'session') ? 'var(--highlight)' : 'white';
    btnSession.style.color = (currentGalleryTab === 'session') ? 'var(--multi)' : 'var(--muted)';
  }
  if(btnAll){
    btnAll.style.background = (currentGalleryTab === 'all') ? 'var(--highlight)' : 'white';
    btnAll.style.color = (currentGalleryTab === 'all') ? 'var(--multi)' : 'var(--muted)';
  }
  if(gridSession) gridSession.style.display = (currentGalleryTab === 'session') ? 'grid' : 'none';
  if(gridAll) gridAll.style.display = (currentGalleryTab === 'all') ? 'grid' : 'none';
  if(pager) pager.style.display = (currentGalleryTab === 'all') ? 'flex' : 'none';
  if(currentGalleryTab === 'all'){
    loadAllHistory(historyPage);
  }
}

async function loadAllHistory(page = 1){
  historyPage = Math.max(1, parseInt(page) || 1);
  const grid = document.getElementById('galleryGridAll');
  if(!grid) return;
  try{
    const res = await fetch('/history_list?page=' + historyPage + '&per_page=' + historyPerPage, {cache:'no-store'});
    const data = await res.json();
    if(data.status !== 'ok'){
      throw new Error(data.error || 'history load failed');
    }
    const total = parseInt(data.total || 0);
    historyTotalPages = Math.max(1, Math.ceil(total / historyPerPage));
    if(historyPage > historyTotalPages){
      historyPage = historyTotalPages;
      return loadAllHistory(historyPage);
    }
    renderAllHistoryGrid(Array.isArray(data.items) ? data.items : []);
    const pageLabel = document.getElementById('historyPageLabel');
    if(pageLabel) pageLabel.textContent = historyPage + '/' + historyTotalPages;
    const sec = document.getElementById('gallerySection');
    if(sec && (total > 0 || galleryItems.length > 0)) sec.style.display = 'block';
  }catch(e){
    grid.innerHTML = '';
    const empty = document.createElement('div');
    empty.style.cssText = 'grid-column:1/-1;font-family:DM Mono,monospace;font-size:0.7rem;color:var(--muted);padding:0.4rem;';
    empty.textContent = '履歴の読み込みに失敗しました';
    grid.appendChild(empty);
  }
}

function renderAllHistoryGrid(items){
  const grid = document.getElementById('galleryGridAll');
  if(!grid) return;
  grid.innerHTML = '';
  if(!items || items.length === 0){
    const empty = document.createElement('div');
    empty.style.cssText = 'grid-column:1/-1;font-family:DM Mono,monospace;font-size:0.7rem;color:var(--muted);padding:0.4rem;';
    empty.textContent = '全履歴はまだありません';
    grid.appendChild(empty);
    return;
  }
  items.forEach((it)=>{
    const card = document.createElement('div');
    card.style.cssText = 'position:relative;cursor:pointer;border-radius:8px;overflow:hidden;background:#f0f0f0;aspect-ratio:1;';
    const img = document.createElement('img');
    img.src = buildGalleryImageSrc(it.thumbnail_path || it.image_path || '');
    img.style.cssText = 'width:100%;height:100%;object-fit:cover;display:block;';
    img.onerror = ()=>{ img.style.display='none'; card.style.background='#e0e0e0'; };
    const ts = document.createElement('div');
    ts.style.cssText = 'position:absolute;bottom:0;left:0;right:0;background:rgba(0,0,0,0.5);color:white;font-family:DM Mono,monospace;font-size:0.58rem;padding:0.2rem 0.35rem;';
    ts.textContent = String(it.created_at || '').replace('T', ' ').slice(0, 19);
    card.appendChild(img);
    card.appendChild(ts);
    card.onclick = ()=>openGalleryModal(
      -1,
      it.image_path || it.thumbnail_path || '',
      {
        timestamp: ts.textContent,
        positivePrompt: it.prompt || '',
        negativePrompt: it.negative_prompt || '',
        imagePaths: [it.image_path || '', it.thumbnail_path || '']
      }
    );
    grid.appendChild(card);
  });
}

function changeHistoryPage(delta){
  if(currentGalleryTab !== 'all') return;
  const next = historyPage + (parseInt(delta) || 0);
  if(next < 1 || next > historyTotalPages) return;
  loadAllHistory(next);
}
let charaPresets = [];  // キャラプリセット一覧

// ===== キャラプリセット管理 =====
async function loadCharaPresets(){
  try{
    const res = await fetch('/chara_presets', { cache: 'no-store' });
    charaPresets = await res.json();
    updateAllPresetSelects();
  }catch(e){
    charaPresets=[];
    updateAllPresetSelects();
  }
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
    alert(`Saved: ${preset.name}`);
  }
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
  renderPresetThumbList();
}

async function deleteCharaPresetFromSettings(){
  const sel = document.getElementById('presetDeleteSel');
  if(!sel || sel.value==='') return;
  const i = parseInt(sel.value);
  if(isNaN(i)) return;
  const preset = charaPresets[i];
  if(!preset) return;
  if(!confirm(`Delete preset "${preset.name}"?`)) return;
  await deleteCharaPresetFromServer(preset._filename);
  charaPresets.splice(i, 1);
  updateAllPresetSelects();
}

function loadCharaPreset(idx){
  const sel = document.getElementById('chara_preset_sel_'+idx);
  if(!sel || sel.value==='') return;
  const preset = charaPresets[parseInt(sel.value)];
  if(!preset) return;
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
    if(ch.outfit_cat){
      const catBtn = document.querySelector(`#chara_${idx} [data-outcat="${ch.outfit_cat}"]`);
      if(catBtn) catBtn.click();
      if(ch.outfit_color){
        const oColorSel = document.querySelector(`#chara_${idx} [data-ocolor]`);
        if(oColorSel){ oColorSel.value=ch.outfit_color; oColorSel.dataset.ocolor=ch.outfit_color; const found=OUTFIT_COLORS.find(c=>c.v===ch.outfit_color); if(found){oColorSel.style.backgroundColor=found.bg;oColorSel.style.color=found.fg;} }
      }
      if(ch.outfit_item)  document.querySelectorAll(`#chara_${idx} [data-oitem]`).forEach(b=>b.classList.toggle('active',b.dataset.oitem===ch.outfit_item));
    }
    const outfitFreeEl = document.getElementById(`chara_outfit_free_${idx}`);
    if(outfitFreeEl){
      outfitFreeEl.value = ch.outfit_free || ch.outfit || '';
    }
    if(ch.hairstyle){
      const hsVals = ch.hairstyle.split(',').map(v=>v.trim()).filter(Boolean);
      document.querySelector(`#chara_${idx}`)?.querySelectorAll('[data-hs]').forEach(b=>{
        b.classList.toggle('active', hsVals.includes(b.dataset.hs));
      });
      const hsHid = document.getElementById(`chara_hairstyle_${idx}`);
      if(hsHid) hsHid.value = ch.hairstyle;
    }
    ['face','eyestate','mouth','effect'].forEach(f=>{
      const hid = document.getElementById(`chara_${f}_${idx}`);
      if(hid && ch[f]){
        const vals = ch[f].split(',').map(v=>v.trim()).filter(Boolean);
        document.querySelector(`#chara_${idx}`)?.querySelectorAll(`[data-${f}]`).forEach(b=>{
          b.classList.toggle('active', vals.includes(b.dataset[f]));
        });
      }
    });
    const bustHid2 = document.getElementById(`chara_bust_${idx}`);
    if(bustHid2 && ch.bust){
      bustHid2.value = ch.bust;
      const bustRow2 = document.getElementById(`chara_bust_row_${idx}`);
      if(bustRow2) bustRow2.querySelectorAll('.age-btn').forEach(b=>b.classList.toggle('active', b.dataset.bust===ch.bust));
    }
    const hairSelEl = document.querySelector(`#chara_${idx} select[id^=""][id=""]`) || (() => {
      const hcHid = document.getElementById(`chara_haircolor_${idx}`);
      return hcHid?.previousElementSibling?.tagName==='INPUT' ? hcHid?.parentElement?.querySelector('select') : hcHid?.previousElementSibling;
    })();
    if(hairSelEl && ch.haircolor){
      hairSelEl.value = ch.haircolor;
      const hcFound = HAIR_COLORS.find(c=>c.v===ch.haircolor);
      if(hcFound){ hairSelEl.style.backgroundColor=hcFound.bg||'white'; hairSelEl.style.color=hcFound.fg||'var(--ink)'; }
      document.getElementById(`chara_haircolor_${idx}`).value = ch.haircolor;
    }
    const skinHid = document.getElementById(`chara_skin_${idx}`);
    if(skinHid){
      skinHid.value = ch.skin||'';
      const skinSelEl = skinHid.parentElement?.querySelector('select');
      if(skinSelEl){ skinSelEl.value=ch.skin||''; const f=SKIN_OPTIONS.find(c=>c.v===(ch.skin||'')); if(f?.bg){skinSelEl.style.backgroundColor=f.bg;skinSelEl.style.color=f.fg||'var(--ink)';} }
    }
    const skinOtherEl = document.getElementById(`chara_skin_other_${idx}`);
    if(skinOtherEl) skinOtherEl.value = ch.skinOther||''
    const hsf = document.getElementById(`chara_hairstyle_free_${idx}`);
    if(hsf && ch.hairstyle_free) hsf.value = ch.hairstyle_free;
    const hof = document.getElementById(`chara_hairother_${idx}`);
    if(hof && ch.hairother) hof.value = ch.hairother;
    const acf = document.getElementById(`chara_action_free_${idx}`);
    if(acf && ch.action_free) acf.value = ch.action_free;
    const itf = document.getElementById(`chara_item_free_${idx}`);
    if(itf && ch.item_free) itf.value = ch.item_free;
    const eyeHid2 = document.getElementById(`chara_eyes_${idx}`);
    if(eyeHid2 && ch.eyes){
      eyeHid2.value=ch.eyes;
      const eyeWrapEl = eyeHid2.parentElement;
      const eyeSelEl2 = eyeWrapEl?.querySelector('select');
      if(eyeSelEl2){ eyeSelEl2.value=ch.eyes; const f=EYE_COLORS.find(c=>c.v===ch.eyes); if(f){eyeSelEl2.style.backgroundColor=f.bg||'white';eyeSelEl2.style.color=f.fg||'var(--ink)';} }
    }
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
let selectedSeedMode='random';
let embedMetadata=true;

// ===== LoRAスロット =====
const LORA_SLOT_COUNT = 4;

// ===== ワークフロー選択 =====
async function loadWorkflowList(){
  const sel = document.getElementById('workflowSelect');
  if(!sel) return;
  try{
    const res = await fetch('/workflows');
    const data = await res.json();
    const current = sel.value;
    while(sel.options.length > 1) sel.remove(1);
    (data.files||[]).forEach(f=>{
      const opt = document.createElement('option');
      opt.value = f;
      opt.textContent = f.replace(/\.json$/i,'');
      sel.appendChild(opt);
    });
    if(current && [...sel.options].some(o=>o.value===current)) sel.value = current;
  }catch(e){ console.warn('[workflow] load failed:', e); }
}

async function applyWorkflowNodeIds(filename){
  if(!filename) return;
  try{
    const res = await fetch('/workflow_node_ids?file=' + encodeURIComponent(filename));
    const d = await res.json();
    const notify = [];
    if(d.pos_id)      { document.getElementById('posNodeInput').value = d.pos_id;      notify.push('Pos:'+d.pos_id); }
    if(d.neg_id)      { document.getElementById('negNodeInput').value = d.neg_id;      notify.push('Neg:'+d.neg_id); }
    if(d.ksampler_id) { document.getElementById('ksamplerNodeInput').value = d.ksampler_id; notify.push('KSampler:'+d.ksampler_id); }
    if(d.clip_id)     { document.getElementById('clipNodeInput').value = d.clip_id;    notify.push('CLIP:'+d.clip_id); }
    if(notify.length){
      const notice = document.getElementById('workflowNodeNotice');
      if(notice){ notice.textContent = '✓ Node ID自動設定: ' + notify.join(' / '); notice.style.display='block'; setTimeout(()=>notice.style.display='none', 4000); }
    }
  }catch(e){}
}

function getSelectedWorkflow(){
  const sel = document.getElementById('workflowSelect');
  return sel ? sel.value : '';
}

let _loraList = [];

async function loadLoraList(){
  try{
    const res = await fetch('/lora_list');
    const data = await res.json();
    _loraList = data.loras || [];
    for(let i=0; i<LORA_SLOT_COUNT; i++){
      const sel = document.getElementById(`lora_name_${i}`);
      if(!sel) continue;
      const current = sel.value;
      while(sel.options.length > 1) sel.remove(1);
      _loraList.forEach(name=>{
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name.replace(/\\/g,'/');
        sel.appendChild(opt);
      });
      if(current && [...sel.options].some(o=>o.value===current)) sel.value = current;
    }
    updateLoraCardGrid();
  }catch(e){ console.warn('[lora] load failed:', e); }
}

function updateLoraCardGrid(){
  const grid = document.getElementById('loraCardGrid');
  if(!grid) return;
  const loraOpen = document.getElementById('blockLora')?.style.display !== 'none';
  grid.innerHTML = '';
  _loraList.forEach(name=>{
    const card = document.createElement('div');
    card.style.cssText = 'position:relative;border:2px solid var(--border);border-radius:8px;overflow:hidden;cursor:pointer;background:#f0f0f0;aspect-ratio:1;transition:border-color 0.15s;';
    card.dataset.loraName = name;
    card.title = name.replace(/\\/g,'/');
    const img = document.createElement('img');
    img.style.cssText = 'width:100%;height:100%;object-fit:cover;display:none;';
    img.onload = ()=>{ img.style.display='block'; };
    img.onerror = ()=>{};
    img.dataset.src = '/lora_thumbnail?name=' + encodeURIComponent(name);
    if(loraOpen) img.src = img.dataset.src;
    card.appendChild(img);
    const label = document.createElement('div');
    const shortName = name.replace(/\\/g,'/').split('/').pop().replace(/\.(safetensors|ckpt|pt)$/i,'');
    label.textContent = shortName;
    label.style.cssText = 'position:absolute;bottom:0;left:0;right:0;background:rgba(0,0,0,0.65);color:white;font-family:DM Mono,monospace;font-size:0.58rem;padding:0.2rem 0.3rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
    card.appendChild(label);
    const badge = document.createElement('div');
    badge.className = 'lora-card-badge';
    badge.dataset.loraName = name;
    badge.style.cssText = 'display:none;position:absolute;top:3px;right:3px;background:var(--multi);color:white;font-family:DM Mono,monospace;font-size:0.6rem;padding:0.1rem 0.35rem;border-radius:4px;font-weight:bold;';
    card.appendChild(badge);
    card.addEventListener('click', ()=>assignLoraSlot(name));
    grid.appendChild(card);
  });
  updateLoraCardBadges();
}

function assignLoraSlot(name){
  for(let i=0; i<LORA_SLOT_COUNT; i++){
    const sel = document.getElementById(`lora_name_${i}`);
    if(sel && sel.value === name){ sel.value=''; updateLoraCardBadges(); return; }
  }
  for(let i=0; i<LORA_SLOT_COUNT; i++){
    const sel = document.getElementById(`lora_name_${i}`);
    if(sel && !sel.value){ sel.value=name; updateLoraCardBadges(); return; }
  }
  const sel = document.getElementById('lora_name_0');
  if(sel){ sel.value=name; updateLoraCardBadges(); }
}

function updateLoraCardBadges(){
  document.querySelectorAll('.lora-card-badge').forEach(b=>{ b.style.display='none'; });
  document.querySelectorAll('#loraCardGrid > div').forEach(c=>{ c.style.borderColor='var(--border)'; });
  for(let i=0; i<LORA_SLOT_COUNT; i++){
    const sel = document.getElementById(`lora_name_${i}`);
    if(!sel || !sel.value) continue;
    const card = [...document.querySelectorAll('#loraCardGrid > div')].find(c=>c.dataset.loraName===sel.value);
    if(card){
      card.style.borderColor='var(--multi)';
      const badge = card.querySelector('.lora-card-badge');
      if(badge){ badge.textContent=`S${i+1}`; badge.style.display='block'; }
    }
  }
}

function initLoraSlots(){
  const container = document.getElementById('loraSlots');
  if(!container) return;
  const header = document.createElement('div');
  header.style.cssText = 'display:flex;justify-content:flex-end;margin-bottom:0.5rem;';
  const reloadBtn = document.createElement('button');
  reloadBtn.textContent = '🔄 Fetch LORA List';
  reloadBtn.onclick = loadLoraList;
  reloadBtn.style.cssText = 'font-family:DM Mono,monospace;font-size:0.68rem;padding:0.25rem 0.5rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--muted);cursor:pointer;white-space:nowrap;';
  header.appendChild(reloadBtn);
  container.appendChild(header);
  const grid = document.createElement('div');
  grid.id = 'loraCardGrid';
  grid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:0.4rem;margin-bottom:0.6rem;max-height:300px;overflow-y:auto;border:1px solid var(--border);border-radius:8px;padding:0.4rem;background:#fafaf8;';
  container.appendChild(grid);
  const slotNote = document.createElement('div');
  slotNote.style.cssText = 'font-family:DM Mono,monospace;font-size:0.65rem;color:var(--muted);margin-bottom:0.3rem;';
  slotNote.textContent = 'カードをクリックでスロットに割り当て（再クリックで解除）';
  container.appendChild(slotNote);
  for(let i=0; i<LORA_SLOT_COUNT; i++){
    const row = document.createElement('div');
    row.style.cssText = 'display:grid;grid-template-columns:1fr auto auto;gap:0.4rem;align-items:center;margin-bottom:0.3rem;';
    const sel = document.createElement('select');
    sel.id = `lora_name_${i}`;
    sel.style.cssText = 'font-family:DM Mono,monospace;font-size:0.72rem;border:1px solid var(--border);border-radius:5px;padding:0.3rem 0.5rem;outline:none;background:white;color:var(--ink);cursor:pointer;';
    sel.addEventListener('change', updateLoraCardBadges);
    const emptyOpt = document.createElement('option');
    emptyOpt.value = '';
    emptyOpt.textContent = `— S${i+1} 未使用 —`;
    sel.appendChild(emptyOpt);
    const strLabel = document.createElement('span');
    strLabel.textContent = '強度';
    strLabel.style.cssText = 'font-family:DM Mono,monospace;font-size:0.7rem;color:var(--muted);white-space:nowrap;';
    const strInput = document.createElement('input');
    strInput.type = 'number';
    strInput.id = `lora_strength_${i}`;
    strInput.value = '1'; strInput.min = '0'; strInput.max = '2'; strInput.step = '0.05';
    strInput.style.cssText = 'font-family:DM Mono,monospace;font-size:0.75rem;border:1px solid var(--border);border-radius:5px;padding:0.3rem 0.4rem;outline:none;width:4.5rem;box-sizing:border-box;';
    row.appendChild(sel); row.appendChild(strLabel); row.appendChild(strInput);
    container.appendChild(row);
  }
  // LoRAセクションを開いた時に自動取得（toggleBlockから呼ばれる）
}

function collectLoraSlots(){
  const slots = [];
  for(let i=0; i<LORA_SLOT_COUNT; i++){
    const name = document.getElementById(`lora_name_${i}`)?.value.trim()||'';
    const strength = parseFloat(document.getElementById(`lora_strength_${i}`)?.value)||1.0;
    slots.push({name, strength});
  }
  return slots;
}

function applyLoraSlots(slots){
  if(!slots) return;
  slots.forEach((slot, i)=>{
    if(i >= LORA_SLOT_COUNT) return;
    const nameEl = document.getElementById(`lora_name_${i}`);
    const strEl = document.getElementById(`lora_strength_${i}`);
    if(nameEl){
      if(nameEl.tagName === 'SELECT' && slot.name){
        if(![...nameEl.options].some(o=>o.value===slot.name)){
          const opt = document.createElement('option');
          opt.value = slot.name;
          opt.textContent = slot.name.replace(/\\/g,'/').split('/').pop();
          opt.title = slot.name;
          nameEl.appendChild(opt);
        }
        nameEl.value = slot.name;
      } else {
        nameEl.value = slot.name||'';
      }
    }
    if(strEl) strEl.value = slot.strength !== undefined ? slot.strength : 1;
  });
}

function initGenParams(){
  const samplerSel = document.getElementById('samplerInput');
  const schedulerSel = document.getElementById('schedulerInput');
  (__OPT__.sampler_options||[]).forEach(({v,label})=>{
    const opt=document.createElement('option'); opt.value=v; opt.textContent=label; samplerSel.appendChild(opt);
  });
  (__OPT__.scheduler_options||[]).forEach(({v,label})=>{
    const opt=document.createElement('option'); opt.value=v; opt.textContent=label; schedulerSel.appendChild(opt);
  });
  samplerSel.value='er_sde';
  schedulerSel.value='simple';
}

function selectSeedMode(el){
  document.querySelectorAll('#seedModeBtns .period-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  selectedSeedMode = el.dataset.smode;
  document.getElementById('seedValueInput').disabled = (selectedSeedMode==='random');
}

function collectGenParams(){
  return {
    seed_mode: selectedSeedMode,
    seed_value: parseInt(document.getElementById('seedValueInput')?.value)||0,
    steps: parseInt(document.getElementById('stepsInput')?.value)||30,
    cfg: parseFloat(document.getElementById('cfgInput')?.value)||4.0,
    sampler_name: document.getElementById('samplerInput')?.value.trim()||'er_sde',
    scheduler: document.getElementById('schedulerInput')?.value.trim()||'simple',
  };
}

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
  if(cat==='屋内'){
    const indoorBtn = [...subRow.querySelectorAll('.period-btn')].find(b=>b.textContent==='室内');
    if(indoorBtn){ indoorBtn.classList.add('active'); outdoorHid.value='indoors'; }
  }
  subRow.style.display = (PLACE_SUB[cat]||[]).length > 0 ? 'flex' : 'none';

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
        document.getElementById('f_place').value = v; // 英語タグ
      } else {
        document.getElementById('f_place').value = '';
      }
    });
    itemRow.appendChild(btn);
  });
  itemRow.style.display = 'flex';
}

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
  const val = saved || preset || {url:'', token:'', model:''};
  document.getElementById('lmsUrlInput').value = val.url   || '';
  document.getElementById('tokenInput').value  = val.token || '';
  document.getElementById('modelInput').value  = val.model || '';
}

function selLLMPlatform(el){
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
  if(settingsOpen) setTimeout(initSectionToggles, 50);
}

async function loadSettings(){
  try{
    const cfg=await(await fetch('/config')).json();
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
    document.getElementById('ksamplerNodeInput').value=cfg.ksampler_node_id||'19';
    if(cfg.seed_mode){
      selectedSeedMode=cfg.seed_mode;
      document.querySelectorAll('#seedModeBtns .period-btn').forEach(b=>b.classList.toggle('active',b.dataset.smode===cfg.seed_mode));
      const seedEl=document.getElementById('seedValueInput'); if(seedEl){ seedEl.value=cfg.seed_value||0; seedEl.disabled=(cfg.seed_mode==='random'); }
    }
    if(cfg.steps!==undefined) { const el=document.getElementById('stepsInput'); if(el) el.value=cfg.steps; }
    if(cfg.cfg!==undefined) { const el=document.getElementById('cfgInput'); if(el) el.value=cfg.cfg; }
    if(cfg.sampler_name) { const el=document.getElementById('samplerInput'); if(el) el.value=cfg.sampler_name; }
    if(cfg.scheduler) { const el=document.getElementById('schedulerInput'); if(el) el.value=cfg.scheduler; }
    selectedSeedMode = cfg.seed_mode||'random';
    selectedFmt = (cfg.output_format||'png').toLowerCase()==='webp' ? 'webp' : 'png';
    document.querySelectorAll('.fmt-btn').forEach(b=>b.classList.toggle('active', b.dataset.fmt===selectedFmt));
    embedMetadata = cfg.embed_metadata !== false;
    const mdEl=document.getElementById('embedMetadataToggle'); if(mdEl) mdEl.checked = embedMetadata;
    document.getElementById('outputDirInput').value=cfg.comfyui_output_dir||'';
    document.getElementById('logDirInput').value=cfg.log_dir||'logs';
    document.getElementById('logRetentionInput').value=(cfg.log_retention_days ?? 30);
    document.getElementById('logLevelInput').value=(cfg.log_level||'normal');
  }catch(e){console.warn(e);}
}

async function testConnection(target){
  const resultEl = document.getElementById('testResult');
  resultEl.style.display = 'block';
  resultEl.style.background = '#f5f5f5';
  resultEl.style.color = 'var(--ink)';
  resultEl.textContent = i18nReplace((target==='comfyui' ? 'ComfyUI' : 'LLM') + ' 接続テスト中...');
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
    log_dir:document.getElementById('logDirInput').value||'logs',
    log_retention_days:parseInt(document.getElementById('logRetentionInput').value)||30,
    log_level:document.getElementById('logLevelInput').value||'normal',
    positive_node_id:document.getElementById('posNodeInput').value,
    negative_node_id:document.getElementById('negNodeInput').value,
    ksampler_node_id:document.getElementById('ksamplerNodeInput').value||'19',
    output_format:selectedFmt,
    embed_metadata:(document.getElementById('embedMetadataToggle')?.checked ?? true),
    console_lang: currentLang,
    ...collectGenParams(),
  };
  await fetch('/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});
  const n=document.getElementById('saveNotice');
  n.style.display='block';
  setTimeout(()=>{n.style.display='none';},3000);
}

function openLogsFolder(){
  const p = (document.getElementById('logDirInput')?.value||'logs').trim() || 'logs';
  fetch('/open_folder?path='+encodeURIComponent(p));
}

function downloadLogsZip(){
  window.location.href = '/logs_zip';
}

function copyPrompt(elId, btn){
  const el = document.getElementById(elId);
  const text = el ? el.textContent : '';
  if(!text) return;
  // iOS http環境でもコピーできるよう range選択方式を優先
  const tryRangeCopy = ()=>{
    try{
      const range = document.createRange();
      range.selectNodeContents(el);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      document.execCommand('copy');
      sel.removeAllRanges();
      return true;
    }catch(e){ return false; }
  };
  if(navigator.clipboard && window.isSecureContext){
    navigator.clipboard.writeText(text).then(()=>{
      btn.textContent='✓ コピー済'; btn.classList.add('copied');
      setTimeout(()=>{ btn.textContent='コピー'; btn.classList.remove('copied'); }, 2000);
    }).catch(()=>{
      tryRangeCopy();
      btn.textContent='✓ コピー済'; btn.classList.add('copied');
      setTimeout(()=>{ btn.textContent='コピー'; btn.classList.remove('copied'); }, 2000);
    });
  } else {
    const ok = tryRangeCopy();
    btn.textContent = ok ? '✓ コピー済' : '（長押しで選択）';
    btn.classList.add('copied');
    setTimeout(()=>{ btn.textContent='コピー'; btn.classList.remove('copied'); }, 2000);
  }
}

function setStep(steps,id,state,text){
  let el=document.getElementById(id);
  if(!el){el=document.createElement('div');el.id=id;steps.appendChild(el);}
  el.className='step '+state;
  const rendered = i18nReplace(text);
  el.innerHTML=(state==='active'?'<div class="spinner"></div>':'<div class="dot"></div>')+rendered;
}

// ===== セッション保存・読み込み =====
function collectSessionData(){
  const count = Math.max(0, Math.min(6, parseInt(document.getElementById('f_charcount').value)||0));
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
    placeActiveCat: placeActiveCat||'',
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
    preExtraPrompt: lastPositivePrompt||'',
    imgW: selectedW, imgH: selectedH, imgFmt: selectedFmt, imgCount: selectedCount,
    embedMetadata: embedMetadata,
    useLLM: document.getElementById('useLLM').checked,
    workflowFile: getSelectedWorkflow(),
    loraSlots: collectLoraSlots(),
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
  document.getElementById('f_series').value = data.series||'';
  const count = Math.max(0, Math.min(6, parseInt(data.charcount)||0));
  document.getElementById('f_charcount').value = count;
  updateCharaBlocks();
  setTimeout(()=>{
    (data.characters||[]).forEach((ch,i)=>{
      if(document.getElementById('chara_series_'+i))
        document.getElementById('chara_series_'+i).value = ch.series||'';
      if(ch.original){
        const ob = document.getElementById('chara_orig_'+i);
        if(ob && !ob.classList.contains('active')) ob.click();
      }
      if(document.getElementById('chara_name_'+i))
        document.getElementById('chara_name_'+i).value = ch.name||'';
      const gRow = document.querySelector(`#chara_${i} .chara-attr-btns.gender-row`);
      if(gRow) gRow.querySelectorAll('.gender-btn').forEach(b=>{
        b.classList.toggle('active', b.dataset.g===ch.gender);
      });
      const aRow = document.querySelector(`#chara_${i} .chara-attr-btns.age-row`);
      if(aRow) aRow.querySelectorAll('.age-btn').forEach(b=>{
        b.classList.toggle('active', b.dataset.a===ch.age);
      });
      ['outfit','action','hair','hairstyle','hairstyle_lm','haircolor','eyes','skin','body','misc'].forEach(f=>{
        const el = document.getElementById(`chara_${f}_${i}`);
        if(el) el.value = ch[f]||'';
      });
      const actionHidEl = document.getElementById(`chara_action_${i}`);
      if(actionHidEl && ch['action']!==undefined){
        actionHidEl.value = ch['action']||'';
        const actVals = ch['action'] ? ch['action'].split(',') : [];
        document.getElementById(`chara_${i}`)?.querySelectorAll('[data-act]').forEach(b=>{
          b.classList.toggle('active', actVals.includes(b.dataset.act));
        });
        if(actVals.includes('holding')){
          const hr = document.getElementById(`chara_${i}`)?.querySelector('.opt-row[style*="display:none"]');
          document.getElementById(`chara_${i}`)?.querySelectorAll('.opt-row').forEach(r=>{
            if(r.querySelector('#chara_item_'+i)) r.style.display='flex';
          });
        }
        const freeEl = document.getElementById(`chara_action_free_${i}`);
        if(freeEl){
          const isPresetOnly = actVals.every(v=>ACTION_OPTIONS.some(o=>o.v===v));
          freeEl.value = (ch['action'] && !isPresetOnly) ? ch['action'] : '';
        }
      }
      let bustHid = document.getElementById(`chara_bust_${i}`);
      if(bustHid){
        bustHid.value = ch['bust']||'';
        let bustRow = document.getElementById(`chara_bust_row_${i}`);
        if(bustRow) bustRow.querySelectorAll('.age-btn').forEach(b=>{
          b.classList.toggle('active', b.dataset.bust===(ch['bust']||''));
        });
      }
      const itemHidEl = document.getElementById(`chara_item_${i}`);
      if(itemHidEl && ch['item']!==undefined){
        itemHidEl.value = ch['item']||'';
      }
      ['posv','posh'].forEach(f=>{
        const hid = document.getElementById(`chara_${f}_${i}`);
        if(hid && ch[f]!==undefined){
          hid.value = ch[f];
          hid.closest('.opt-row')?.querySelectorAll('.age-btn').forEach(b=>{
            b.classList.toggle('active', b.dataset.val===(ch[f]||''));
          });
        }
      });
      if(ch['outfit_cat']!==undefined){
        const charEl = document.getElementById(`chara_${i}`);
        if(charEl){
          const cat = ch['outfit_cat']||'';
          const catBtn = charEl.querySelector(`[data-outcat="${cat}"]`);
          if(catBtn) catBtn.click();
          if(ch['outfit_color']){
            charEl.querySelectorAll('[data-ocolor]').forEach(b=>{
              b.classList.toggle('active', b.dataset.ocolor===ch['outfit_color']);
            });
          }
          if(ch['outfit_item']){
            charEl.querySelectorAll('[data-oitem]').forEach(b=>{
              b.classList.toggle('active', b.dataset.oitem===ch['outfit_item']);
            });
          }
          const freeIn = document.getElementById(`chara_outfit_free_${i}`);
          if(freeIn && ch['outfit_free']) freeIn.value = ch['outfit_free'];
        }
      }
      const hairstyleEl = document.getElementById(`chara_hairstyle_${i}`);
      if(hairstyleEl && ch['hairstyle']!==undefined){
        hairstyleEl.value = ch['hairstyle']||'';
        const hsVals = ch['hairstyle'] ? ch['hairstyle'].split(',') : [];
        const hsBtns = hairstyleEl.closest('.opt-row')?.querySelectorAll('[data-hs]');
        if(hsBtns) hsBtns.forEach(b=>b.classList.toggle('active', hsVals.includes(b.dataset.hs)));
      }
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
      const hcHid = document.getElementById(`chara_haircolor_${i}`);
      if(hcHid && ch['haircolor']){
        hcHid.value = ch['haircolor'];
        const hcWrap = hcHid.parentElement;
        const hcSel = hcWrap?.querySelector('select');
        if(hcSel){ hcSel.value=ch['haircolor']; const f=HAIR_COLORS.find(c=>c.v===ch['haircolor']); if(f){hcSel.style.backgroundColor=f.bg||'white';hcSel.style.color=f.fg||'var(--ink)';} }
      }
      let eyeHid = document.getElementById(`chara_eyes_${i}`);
      if(eyeHid && ch['eyes']){
        eyeHid.value = ch['eyes'];
        const eyeWrapEl2 = eyeHid.parentElement;
        const eyeSelEl3 = eyeWrapEl2?.querySelector('select');
        if(eyeSelEl3){ eyeSelEl3.value=ch['eyes']; const f=EYE_COLORS.find(c=>c.v===ch['eyes']); if(f){eyeSelEl3.style.backgroundColor=f.bg||'white';eyeSelEl3.style.color=f.fg||'var(--ink)';} }
      }
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
      const hasDetail = ['outfit','action','hair','eyes','skin','body','misc','bust'].some(f=>ch[f]);
      if(hasDetail){
        const opt = document.getElementById('chara_opt_'+i);
        const btn = opt?.previousElementSibling?.querySelector('.chara-expand');
        if(opt && opt.style.display==='none'){ opt.style.display='block'; if(btn) btn.textContent='－ 詳細'; }
      }
      const hairStyleFreeEl = document.getElementById(`chara_hairstyle_free_${i}`);
      if(hairStyleFreeEl && ch['hairstyle_free']) hairStyleFreeEl.value = ch['hairstyle_free'];
      const hairOtherEl = document.getElementById(`chara_hairother_${i}`);
      if(hairOtherEl && ch['hairother']) hairOtherEl.value = ch['hairother'];
      const actionFreeEl = document.getElementById(`chara_action_free_${i}`);
      if(actionFreeEl && ch['action_free']) actionFreeEl.value = ch['action_free'];
      const itemFreeEl = document.getElementById(`chara_item_free_${i}`);
      if(itemFreeEl && ch['item_free']) itemFreeEl.value = ch['item_free'];
    });
    if(data.place||data.world||data.tod||data.weather||data.placeActiveCat){
      const blockC = document.getElementById('blockC');
      const arrowC = document.getElementById('arrowC');
      if(blockC && blockC.style.display==='none'){ blockC.style.display='block'; if(arrowC) arrowC.textContent='▼'; }
    }
    document.getElementById('f_place').value = data.place||'';
    document.getElementById('f_misc').value  = data.misc||'';
    const _legacyMap = {
      '朝':'morning','昼':'day','夕方':'evening','夜':'night',
      '日常':'everyday_life','和風':'japanese_style','西洋':'western_style',
      '中華':'chinese_style','ファンタジー':'fantasy','SF':'science_fiction','ポストアポカリプス':'post-apocalyptic',
      '晴れ':'sunny','曇り':'cloudy','雨':'rain','雪':'snow',
      '公園':'park','海岸':'beach','海':'ocean','山':'mountain','森':'forest','草原':'field',
      '街中':'street','神社':'shrine','庭園':'garden','川':'river','湖':'lake',
      '校庭':'school_courtyard','競技場':'stadium','戦場':'battlefield',
      '教室':'classroom','寝室':'bedroom','リビング':'living_room','風呂':'bathroom',
      '図書館':'library','カフェ':'cafe','レストラン':'restaurant','体育館':'gym',
      '病院':'hospital','城内':'castle_interior','教会':'church','研究室':'laboratory',
      '廊下':'hallway','ステージ':'stage','ダンジョン':'dungeon',
      '宇宙':'space','水中':'underwater','空中':'sky','異世界':'fantasy_world',
      '廃墟':'ruins','神殿':'temple','天界':'heaven','地獄':'hell','虚空':'void','夢の中':'dream',
    };
    ['tod','world','weather'].forEach(g=>{ if(data[g] && _legacyMap[data[g]]) data[g]=_legacyMap[data[g]]; });
    if(data.place && _legacyMap[data.place]) data.place = _legacyMap[data.place];
    if(data.placeActiveCat){
      const catBtn = document.querySelector(`[data-placecat="${data.placeActiveCat}"]`);
      showPlaceCat(data.placeActiveCat, catBtn);
      if(data.place){
        const itemRow = document.getElementById('place_item_row');
        itemRow?.querySelectorAll('[data-placeval]').forEach(b=>{
          b.classList.toggle('active', b.textContent===data.place);
        });
      }
      if(data.outdoor){
        const subRow = document.getElementById('place_sub_row');
        if(subRow){
          const subOpts = PLACE_SUB[data.placeActiveCat]||[];
          const matchSub = subOpts.find(o=>o.v===data.outdoor);
          subRow.querySelectorAll('.period-btn').forEach(b=>{
            b.classList.toggle('active', matchSub ? b.textContent===matchSub.label : false);
          });
        }
        document.getElementById('f_outdoor').value = data.outdoor;
      }
    }
    ['world','outdoor','tod','weather'].forEach(g=>{
      const val = data[g]||'';
      const hid = document.getElementById('f_'+g);
      if(hid) hid.value = val;
      document.querySelectorAll(`[data-${g}]`).forEach(b=>{
        b.classList.toggle('active', (b.dataset[g]||'')=== val);
      });
    });
    document.getElementById('extraNoteJa').value = data.extraNoteJa||'';
    document.getElementById('extraNoteEn').value = data.extraNoteEn||'';
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
    styleTags = data.styleTags||[];
    if(data.stylePresetList) stylePresetList = data.stylePresetList;
    renderStylePresets();
    renderStyleBadges();
    selectedPeriod = data.selectedPeriod||'';
    document.querySelectorAll('.period-btn[data-p]').forEach(b=>{
      b.classList.toggle('active', b.dataset.p===selectedPeriod);
    });
    if(data.year) document.getElementById('yearInput').value = data.year;
    selectedSafety = data.selectedSafety||'';
    document.querySelectorAll('.safety-btn').forEach(b=>{
      b.classList.toggle('active', b.dataset.s===selectedSafety);
    });
    function applyChecks(containerId, checked){
      document.querySelectorAll(`#${containerId} input[type=checkbox]`).forEach(cb=>{
        cb.checked = checked.includes(cb.dataset.tag);
      });
    }
    if(data.qualityHuman) applyChecks('qualityHuman', data.qualityHuman);
    if(data.qualityPony)  applyChecks('qualityPony',  data.qualityPony);
    if(data.metaTags)     applyChecks('metaTags',     data.metaTags);
    if(data.lmPrompt){
      lastPositivePrompt = data.lmPrompt;
      document.getElementById('lmLabel').style.display='block'; document.getElementById('lmLabel').classList.remove('collapsed');
      const po = document.getElementById('promptOutput');
      po.textContent = data.lmPrompt;
      po.classList.add('show');
      document.getElementById('statusBox').classList.add('show');
    }
    if(data.finalPrompt){
      // preExtraPromptがあればそちらを優先（extra_tags・extra_note_en適用前）
      lastPositivePrompt = data.preExtraPrompt || lastPositivePrompt || data.finalPrompt;
      lastFinalPrompt = data.finalPrompt;
      document.getElementById('finalLabel').style.display='block'; document.getElementById('finalLabel').classList.remove('collapsed');
      const pf = document.getElementById('promptFinal');
      pf.textContent = data.finalPrompt;
      pf.style.display='block';
      document.getElementById('statusBox').classList.add('show');
    }
    if(data.negFinalPrompt){
      lastNegativePrompt = data.negFinalPrompt;
      document.getElementById('negFinalLabel').style.display='block'; document.getElementById('negFinalLabel').classList.remove('collapsed');
      const nf = document.getElementById('promptNegFinal');
      nf.textContent = data.negFinalPrompt;
      nf.style.display='block';
    }
    if(lastPositivePrompt){ document.getElementById('regenBtn').classList.add('show'); running=false; document.getElementById('btn').disabled=false; }
    if(data.imgW){ selectedW=data.imgW; document.getElementById('widthInput').value=data.imgW; }
    if(data.imgH){ selectedH=data.imgH; document.getElementById('heightInput').value=data.imgH; }
    if(data.imgFmt){ selectedFmt=data.imgFmt; document.querySelectorAll('.fmt-btn').forEach(b=>b.classList.toggle('active',b.dataset.fmt===data.imgFmt)); }
    if(data.embedMetadata !== undefined){
      embedMetadata = !!data.embedMetadata;
      const mdEl = document.getElementById('embedMetadataToggle');
      if(mdEl) mdEl.checked = embedMetadata;
    }
    if(data.imgCount){ selectedCount=data.imgCount; const ce=document.getElementById('countInput'); if(ce) ce.value=data.imgCount; }
    if(data.useLLM !== undefined){ const el=document.getElementById('useLLM'); if(el) el.checked=data.useLLM; }
    if(data.workflowFile){
      const sel = document.getElementById('workflowSelect');
      if(sel && [...sel.options].some(o=>o.value===data.workflowFile)) sel.value = data.workflowFile;
    }
    if(data.loraSlots) applyLoraSlots(data.loraSlots);
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
  if(!stylePresetList.includes(tag)){
    stylePresetList.push(tag);
    saveStylePresetsToServer();
  }
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
    btn.addEventListener('click', ()=>{
      if(styleTags.includes(tag)){
        styleTags = styleTags.filter(t=>t!==tag);
      } else {
        styleTags.push(tag);
      }
      renderStylePresets();
      renderStyleBadges();
    });
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
  if(open) setTimeout(initSectionToggles, 50);
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
  if(selectedPeriod) parts.push(selectedPeriod);
  function collectCheckedNeg(id){ return Array.from(document.querySelectorAll(`#${id} input[type=checkbox]:checked`)).map(cb=>cb.dataset.tag); }
  parts.push(...collectCheckedNeg('qualityHumanNeg'));
  parts.push(...collectCheckedNeg('qualityPonyNeg'));
  parts.push(...collectCheckedNeg('metaTagsNeg'));
  if(selectedNegSafety) parts.push(selectedNegSafety);
  parts.push(...negStyleTags);
  parts.push(...negExtraTags);
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

  const header = document.createElement('div');
  header.className = 'chara-header';

  const row1 = document.createElement('div');
  row1.className = 'chara-header-row1';

  const num = document.createElement('span');
  num.className = 'chara-num';
  num.textContent = 'キャラ '+n;

  const nameWrap = document.createElement('div');
  nameWrap.style.cssText = 'display:flex;flex-direction:column;min-width:0;';
  nameWrap.appendChild(makeLabelDiv('キャラ名 *'));
  const nameInput = document.createElement('input');
  nameInput.type = 'text';
  nameInput.id = 'chara_name_'+idx;
  nameInput.placeholder = '例: スペシャルウィーク';
  nameInput.className = 'inp-ja';
  nameInput.style.cssText = 'width:100%;background:#f8f4ff;border:1px solid var(--accent);border-radius:5px;padding:0.45rem 0.6rem;font-family:DM Mono,monospace;font-size:0.78rem;color:var(--ink);outline:none;box-sizing:border-box;';
  nameWrap.appendChild(nameInput);

  const seriesWrap = document.createElement('div');
  seriesWrap.style.cssText = 'display:flex;flex-direction:column;min-width:0;';
  seriesWrap.appendChild(makeLabelDiv('作品名'));
  const seriesInnerWrap = document.createElement('div');
  seriesInnerWrap.style.cssText = 'display:flex;gap:0.3rem;align-items:center;';
  const seriesInput = document.createElement('input');
  seriesInput.type = 'text';
  seriesInput.id = 'chara_series_'+idx;
  seriesInput.placeholder = 'Umamusume';
  seriesInput.className = 'inp-ja';
  seriesInput.style.cssText = 'flex:1;min-width:0;background:white;border:1px solid var(--border);border-radius:5px;padding:0.45rem 0.6rem;font-family:DM Mono,monospace;font-size:0.78rem;color:var(--ink);outline:none;box-sizing:border-box;';

  const origBtn = document.createElement('div');
  origBtn.className = 'age-btn';
  origBtn.id = 'chara_orig_'+idx;
  origBtn.textContent = 'オリジナル';
  origBtn.style.cssText = 'flex-shrink:0;font-size:0.7rem;white-space:nowrap;';
  origBtn.addEventListener('click', function(){
    const isOrig = !this.classList.contains('active');
    this.classList.toggle('active', isOrig);
    seriesInput.disabled = isOrig;
    seriesInput.style.opacity = isOrig ? '0.4' : '1';
    if(isOrig) seriesInput.value = '';
    div.querySelectorAll('.lm-check-wrap').forEach(w=>{
      const cb = w.querySelector('input[type="checkbox"]');
      if(cb) cb.checked = false;
      w.style.display = isOrig ? 'none' : '';
    });
  });

  seriesInnerWrap.appendChild(seriesInput);
  seriesInnerWrap.appendChild(origBtn);
  seriesWrap.appendChild(seriesInnerWrap);

  const expandBtn = document.createElement('button');
  expandBtn.className = 'chara-expand';
  expandBtn.textContent = '＋ 詳細';

  row1.appendChild(num);
  row1.appendChild(nameWrap);
  row1.appendChild(seriesWrap);
  row1.appendChild(expandBtn);

  const row2 = document.createElement('div');
  row2.className = 'chara-header-row2';

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

  const charaPresetRow = document.createElement('div');
  charaPresetRow.style.cssText = 'margin-bottom:0.4rem;display:flex;gap:0.3rem;align-items:center;flex-wrap:wrap;';
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
  charaPresetRow.appendChild(cpNumLbl);
  charaPresetRow.appendChild(charaPresetSel);
  const cpRow2 = document.createElement('div');
  cpRow2.className = 'chara-preset-btns';
  cpRow2.style.cssText = 'display:flex;gap:0.3rem;align-items:center;';
  cpRow2.appendChild(charaPresetLoadBtn);
  cpRow2.appendChild(charaPresetSaveBtn);
  cpRow2.appendChild(charaPresetAutoBtn);
  charaPresetRow.appendChild(cpRow2);

  header.appendChild(charaPresetRow);
  header.appendChild(row1);
  header.appendChild(row2);
  div.appendChild(header);

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
  });

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
  const bustHidden = document.createElement('input');
  bustHidden.type = 'hidden';
  bustHidden.id = 'chara_bust_'+idx;
  bustHidden.value = '';
  bustRow.appendChild(bustLabelWrap);
  bustRow.appendChild(bustBtns);
  bustRow.appendChild(bustHidden);

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

  const oddBtn = document.createElement('div');
  oddBtn.className = 'age-btn odd-eye-btn';
  oddBtn.style.cssText = 'width:2.8rem;text-align:center;flex-shrink:0;font-size:0.7rem;padding:0.28rem 0;';
  oddBtn.innerHTML = '<span class="odd-long">オッドアイ</span><span class="odd-short">odd</span>';
  oddBtn.dataset.odd = '0';

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

  function updateBustVisibility(){
    const activeGender = genderRow.querySelector('.gender-btn.active')?.dataset.g || 'female';
    bustRow.style.display = (activeGender === 'male') ? 'none' : '';
  }
  genderRow.querySelectorAll('.gender-btn').forEach(btn=>{
    btn.addEventListener('click', ()=>setTimeout(updateBustVisibility, 0));
  });
  updateBustVisibility();
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
      const tc=[outfitState.top.color, outfitState.top.item].filter(Boolean);
      if(tc.length) parts.push(...tc);
      const bc=[outfitState.bottom.color, outfitState.bottom.item].filter(Boolean);
      if(bc.length) parts.push(...bc);
    }
    outfitHidden.value=parts.join(' ');
  }

  const outfitWrap = document.createElement('div');
  outfitWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.3rem;width:100%;';

  const outfitCatRow = document.createElement('div');
  outfitCatRow.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';

  const outfitTopColorRow = document.createElement('div');
  outfitTopColorRow.style.cssText = 'display:none;gap:0.2rem;flex-wrap:wrap;';
  const outfitTopItemRow = document.createElement('div');
  outfitTopItemRow.style.cssText = 'display:none;gap:0.2rem;flex-wrap:wrap;';

  const outfitBotColorRow = document.createElement('div');
  outfitBotColorRow.style.cssText = 'display:none;gap:0.2rem;flex-wrap:wrap;';
  const outfitBotItemRow = document.createElement('div');
  outfitBotItemRow.style.cssText = 'display:none;gap:0.2rem;flex-wrap:wrap;';

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
      makeItemBtns(outfitTopItemRow,'top',OUTFIT_DATA['上半身'].items);
      makeItemBtns(outfitBotItemRow,'bottom',OUTFIT_DATA['下半身'].items);
      topLabel.style.display=''; outfitTopColorRow.style.display='flex'; outfitTopItemRow.style.display='flex';
      botLabel.style.display=''; outfitBotColorRow.style.display='flex'; outfitBotItemRow.style.display='flex';
    }
    buildOutfitValue();
  }

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
  const hairRowBody = document.createElement('div');
  hairRowBody.className = 'opt-row-body';
  const hairStyleHidden = document.createElement('input');
  hairStyleHidden.type = 'hidden';
  hairStyleHidden.id = 'chara_hairstyle_'+idx;
  hairStyleHidden.value = '';
  const hairStyleWrap = document.createElement('div');
  hairStyleWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.2rem;width:100%;';
  const hairStyleBtns = document.createElement('div');
  hairStyleBtns.style.cssText = 'display:flex;flex-direction:column;gap:0.15rem;';
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
    if(group === '全体' || group === '後ろ'){
      row.style.cssText = 'display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:0.2rem;';
      row.classList.add('hs-grid-row');
    }
    row.dataset.hsgroup = group;
    const items = HAIRSTYLE_OPTIONS.filter(o=>o.group===group);
    const noneBtn = document.createElement('div');
    noneBtn.className = 'age-btn active';
    if(row.classList.contains('hs-grid-row')) noneBtn.style.flex = 'unset';
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
      if(row.classList.contains('hs-grid-row')) btn.style.flex = 'unset';
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
  hairRowBody.appendChild(hairStyleWrap);
  hairRow.appendChild(hairStyleLabelWrap);
  hairRow.appendChild(hairRowBody);

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
  const posVRow  = makeAttrRow('⑰ 画面上下', POS_VERTICAL,   'chara_posv_'+idx,  false);
  const posHRow  = makeAttrRow('⑱ 画面左右', POS_HORIZONTAL, 'chara_posh_'+idx,  false);
  const posCRow  = makeAttrRow('⑲ カメラ',   POS_CAMERA,     'chara_posc_'+idx,  false);
  const heightRow = makeAttrRow('⑩ 背丈', BODY_HEIGHT, 'chara_height_'+idx, false);
  const buildRow  = makeAttrRow('⑪ 体型',  BODY_BUILD,  'chara_build_'+idx,  false);
  const legsRow   = makeAttrRow('⑫ 脚',    BODY_LEGS,   'chara_legs_'+idx,   false);

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
  const eyeGroupRows = {};
  ['open','dir','state'].forEach(g=>{
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;align-items:center;';
    eyeGroupRows[g] = row;
    eyeStateBtns.appendChild(row);
  });
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
    btn.className = group==='open'
      ? ('age-btn'+(v===''?' active':''))
      : ('multi-btn'+(v===''?' active':''));
    btn.dataset.es = v;
    btn.textContent = label;
    if(group==='open') btn.style.minWidth = '3rem';
    btn.addEventListener('click',function(){
      if(group==='open'){
        eyeGroupRows['open'].querySelectorAll('.age-btn').forEach(b=>b.classList.remove('active'));
        this.classList.add('active');
        refreshDirBtns();
      } else if(v===''){
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

  const effectRow = document.createElement('div');
  effectRow.className = 'opt-row';
  effectRow.style.alignItems = 'start';
  effectRow.appendChild(makeOptLabel('⑭ エフェクト'));
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

  const attachRow = document.createElement('div');
  attachRow.className = 'opt-row';
  attachRow.style.alignItems = 'start';
  attachRow.appendChild(makeOptLabel('⑬ 付属'));
  const attachWrap = document.createElement('div');
  attachWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.4rem;width:100%;';

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

  const holdingRow = document.createElement('div');
  holdingRow.className = 'opt-row';
  holdingRow.style.cssText = 'align-items:start;display:none;';
  holdingRow.appendChild(makeOptLabel('⑯ 持ち物'));
  const itemHidden = document.createElement('input');
  itemHidden.type = 'hidden';
  itemHidden.id = 'chara_item_'+idx;
  itemHidden.value = '';
  const itemWrap = document.createElement('div');
  itemWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.3rem;width:100%;';

  const itemCatRow = document.createElement('div');
  itemCatRow.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;';
  const itemBtnArea = document.createElement('div');
  itemBtnArea.style.cssText = 'display:flex;gap:0.2rem;flex-wrap:wrap;display:none;';

  let activeItemCat = null;
  function updateItemValue(){
    itemHidden.value = [...itemWrap.querySelectorAll('[data-item].active')].map(b=>b.dataset.item).join(',');
  }
  function showItemCat(cat){
    if(activeItemCat === cat){
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

  const actionRow = document.createElement('div');
  actionRow.className = 'opt-row';
  actionRow.style.alignItems = 'start';
  const actionLabelWrap = makeOptLabel('⑮ 動作・ポーズ');
  const actionHidden = document.createElement('input');
  actionHidden.type = 'hidden';
  actionHidden.id = 'chara_action_'+idx;
  actionHidden.value = '';
  const actionWrap = document.createElement('div');
  actionWrap.style.cssText = 'display:flex;flex-direction:column;gap:0.3rem;width:100%;';

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
      if(v==='holding'){
        const isActive = this.classList.contains('active');
        holdingRow.style.display = isActive ? 'flex' : 'none';
        holdingRow.style.outline = isActive ? '2px solid var(--accent)' : '';
        if(isActive && !activeItemCat){
          const firstCatBtn = itemCatRow.querySelector('.age-btn');
          if(firstCatBtn) firstCatBtn.click();
        }
        if(isActive) holdingRow.scrollIntoView({behavior:'smooth', block:'nearest'});
      }
    });
    actionBtnRow.appendChild(btn);
  });
  const actionFreeInput = document.createElement('input');
  actionFreeInput.type = 'text';
  actionFreeInput.id = 'chara_action_free_'+idx;
  actionFreeInput.placeholder = '英語タグのみ（例: standing, arms_crossed）';
  actionFreeInput.className = 'inp-en';
  actionFreeInput.className = 'inp-en';
  actionFreeInput.style.cssText = 'width:100%;border-radius:5px;padding:0.35rem 0.6rem;font-family:DM Mono,monospace;font-size:0.75rem;outline:none;box-sizing:border-box;';
  actionFreeInput.addEventListener('input',function(){
    if(this.value.trim()) actionHidden.value = this.value.trim();
    else updateActionValue();
  });
  actionWrap.appendChild(actionFreeInput);
  actionWrap.appendChild(actionHidden);
  actionRow.appendChild(actionLabelWrap);
  actionRow.appendChild(actionWrap);

  const miscRow = opt.querySelector('[id="chara_misc_'+idx+'"]')?.closest('.opt-row');

  [hairRow, hairColorRow,   // ① 髪型・髪色
   eyeStateRow,             // ② 目の状態
   eyeRow,                  // ③ 瞳の色
   mouthRow,                // ④ 口
   faceRow,                 // ⑤ 表情
   skinRow,                 // ⑥ 肌の色
   outfitRow,               // ⑦ 衣装・外見
   bustRow,                 // ⑧ バスト
   heightRow, buildRow, legsRow, // ⑩⑪⑫ 背丈・体型・脚
   attachRow,               // ⑬ 付属
   effectRow,               // ⑭ エフェクト
   actionRow,               // ⑮ 動作・ポーズ
   holdingRow,              // ⑯ 持ち物（持つ選択時に展開）
   posVRow, posHRow, posCRow, // ⑰⑱⑲ 画面位置
   miscRow                  // その他
  ].forEach(r=>{ if(r) opt.appendChild(r); });

  div.appendChild(opt);

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
  if(open) setTimeout(initSectionToggles, 50);
}

function toggleBlock(id, arrowId){
  const el = document.getElementById(id);
  const open = el.style.display === 'none';
  el.style.display = open ? 'block' : 'none';
  document.getElementById(arrowId).textContent = open ? '▼' : '▶';
  if(open){
    setTimeout(()=>{ initOptRows(el); initSectionToggles(); }, 50);
    // LoRAブロックを初めて開いた時だけ自動取得
    if(id === 'blockLora' && _loraList.length === 0) loadLoraList();
    if(id === 'blockLora' && _loraList.length > 0){
      document.querySelectorAll('#loraCardGrid img[data-src]').forEach(img=>{
        if(!img.src || img.src === window.location.href) img.src = img.dataset.src;
      });
    }
  }
}

function selScene(group, el){
  document.querySelectorAll(`[data-scenegroup="${group}"]`).forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('f_'+group).value = el.dataset[group]||'';
}

function updateCharaBlocks(){
  const count = Math.max(0, Math.min(6, parseInt(document.getElementById('f_charcount').value)||0));
  const container = document.getElementById('charaContainer');
  const current = container.children.length;
  if(count > current){
    for(let i=current; i<count; i++) container.appendChild(makeCharaBlock(i));
  } else {
    while(container.children.length > count) container.removeChild(container.lastChild);
  }
  setTimeout(initOptRows, 50);
}

function collectInput(useLLM=true){
  const series = document.getElementById('f_series').value.trim();
  const count = Math.max(0, Math.min(6, parseInt(document.getElementById('f_charcount').value)||0));
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
    const actionVal = (document.getElementById(`chara_action_${i}`)||{value:''}).value.trim();
    const actionFreeVal = (document.getElementById(`chara_action_free_${i}`)||{value:''}).value.trim();
    if(actionVal){
      if(useLLM && (document.getElementById(`chara_action_lm_${i}_lm`)||{checked:true}).checked) ch['action']=actionVal;
      else actionVal.split(',').forEach(tag=>{ if(tag.trim()) addDirect(tag.trim()); });
    }
    if(actionFreeVal) actionFreeVal.split(',').forEach(tag=>{ if(tag.trim()) addDirect(tag.trim()); });
    function isLM(fieldId){ return useLLM && (document.getElementById(fieldId+'_lm')||{checked:false}).checked; }
    if(!isLM(`chara_gender_lm_${i}`)){
      const gTag = {female:'1girl',male:'1boy',other:''}[gender]||'';
      if(gTag) directTags.push(gTag);
      ch['gender'] = 'other';
    }
    if(!isLM(`chara_age_lm_${i}`)){
      const ageMap = AGE_TAG_MAP[gender]||AGE_TAG_MAP['other'];
      const ageTag = ageMap[age]||'';
      if(ageTag) directTags.push(ageTag);
      ch['age'] = 'unset'; // LMには渡さない
    }
    function addDirect(tag){ if(tag) directTags.push(tag); }

    let bustVal = (document.getElementById(`chara_bust_${i}`)||{value:''}).value.trim();
    if(bustVal){ if(isLM(`chara_bust_lm_${i}`)) ch['bust']=bustVal; else addDirect(bustVal); }
    let skinVal = (document.getElementById(`chara_skin_${i}`)||{value:''}).value.trim();
    if(skinVal){ if(isLM(`chara_skin_lm_${i}`)) ch['skin']=skinVal; else addDirect(skinVal); }
    let eyeVal = (document.getElementById(`chara_eyes_${i}`)||{value:''}).value.trim();
    if(eyeVal){ if(isLM(`chara_eyes_lm_${i}`)) ch['eyes']=eyeVal; else addDirect(eyeVal); } // heterochromia等はそのまま
    let outfitVal = (document.getElementById(`chara_outfit_${i}`)||{value:''}).value.trim();
    let outfitFreeVal = (document.getElementById(`chara_outfit_free_${i}`)||{value:''}).value.trim();
    if(isLM(`chara_outfit_lm_${i}`)){
      ch['outfit'] = outfitFreeVal || outfitVal || 'default';
    } else {
      if(outfitFreeVal) outfitFreeVal.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });
      else if(outfitVal) addDirect(outfitVal);
    }
    let hairColor = (document.getElementById(`chara_haircolor_${i}`)||{value:''}).value.trim();
    let hairOther = (document.getElementById(`chara_hairother_${i}`)||{value:''}).value.trim();
    let hairStyle = (document.getElementById(`chara_hairstyle_${i}`)||{value:''}).value.trim();
    let hairStyleFree = (document.getElementById(`chara_hairstyle_free_${i}`)||{value:''}).value.trim();
    if(hairStyleFree && !hairStyle) hairStyle = hairStyleFree; // hiddenが空の場合のフォールバック
    let hairColorFinal = hairOther || hairColor;
    if(isLM(`chara_haircolor_lm_${i}`)){
      if(hairColorFinal || hairStyle) ch['hair'] = [hairStyle, hairColorFinal].filter(Boolean).join('、');
    } else {
      if(hairColorFinal) addDirect(hairColorFinal);
      if(hairStyle) hairStyle.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });
      if(hairStyleFree && hairStyle) hairStyleFree.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); }); // 日本語自由入力もdirect
    }
    let heightVal = (document.getElementById(`chara_height_${i}`)||{value:''}).value.trim();
    let buildVal  = (document.getElementById(`chara_build_${i}`)||{value:''}).value.trim();
    let legsVal   = (document.getElementById(`chara_legs_${i}`)||{value:''}).value.trim();
    if(isLM(`chara_height_${i}_lm`)||document.getElementById(`chara_height_${i}_lm`)?.checked===undefined){
    }
    const itemVal=(document.getElementById(`chara_item_${i}`)||{value:''}).value.trim();
    if(itemVal) itemVal.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });
    const itemFreeVal=(document.getElementById(`chara_item_free_${i}`)||{value:''}).value.trim();
    if(itemFreeVal) itemFreeVal.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });
    const posvVal = (document.getElementById(`chara_posv_${i}`)||{value:''}).value.trim();
    const poshVal = (document.getElementById(`chara_posh_${i}`)||{value:''}).value.trim();
    const poscVal = (document.getElementById(`chara_posc_${i}`)||{value:''}).value.trim();
    if(posvVal) addDirect(posvVal);
    if(poshVal) addDirect(poshVal);
    if(poscVal) addDirect(poscVal);
    ['ears','tail','wings'].forEach(f=>{
      const v=(document.getElementById(`chara_${f}_${i}`)||{value:''}).value.trim();
      if(v) addDirect(v);
    });
    const accVal=(document.getElementById(`chara_acc_${i}`)||{value:''}).value.trim();
    if(accVal) accVal.split(',').forEach(v=>{ if(v.trim()) addDirect(v.trim()); });

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
    ch['_directTagsBlock'] = directTags;
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
  const charDirectTags = []; // LLMなし時はifブロック内で組み立て、LLMあり時はflatMapで組み立て
  characters.forEach(c=>{ (c._directTagsBlock||[]).forEach(t=>charDirectTags.push(t)); });
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
  if(sel.options.length > 0) applyPreset(sel.options[0].value);
}

function initSceneButtons(){
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

document.addEventListener('DOMContentLoaded', ()=>{
  fetch('/version').then(r=>r.json()).then(d=>{
    const el = document.getElementById('versionBadge');
    if(el) el.textContent = 'v' + d.version;
  }).catch(()=>{});
  updateCharaBlocks();
  if(window.innerWidth <= 700){
    setTimeout(()=>{ loadCharaPresets().then(()=>updateCharaBlocks()); }, 350);
  }else{
    loadCharaPresets().then(()=>updateCharaBlocks());
  }
  togglePresetThumbPanel(false);
  loadSettings();
  // スマホのみページ表示と同時にWS接続開始
  if(window.innerWidth <= 700){
    const notice = document.createElement('div');
    notice.id = 'wsConnNotice';
    notice.style.cssText = 'position:fixed;bottom:70px;left:50%;transform:translateX(-50%);background:rgba(80,60,140,0.85);color:white;font-family:DM Mono,monospace;font-size:0.72rem;padding:0.4rem 1rem;border-radius:20px;z-index:9999;white-space:nowrap;';
    notice.textContent = '🔌 ComfyUI 接続中...';
    document.body.appendChild(notice);
    // 接続完了まで再生成ボタンをdisable
    const regenBtn = document.getElementById('regenBtn');
    if(regenBtn){ regenBtn.style.opacity='0.5'; regenBtn.style.pointerEvents='none'; }
    initComfyWs();
    const wsWait = setInterval(()=>{
      if(window._comfyWsReady){
        notice.textContent = '✓ ComfyUI 接続OK';
        if(regenBtn){ regenBtn.style.opacity=''; regenBtn.style.pointerEvents=''; }
        setTimeout(()=>notice.remove(), 1500);
        clearInterval(wsWait);
      }
    }, 200);
    setTimeout(()=>{
      clearInterval(wsWait);
      if(regenBtn){ regenBtn.style.opacity=''; regenBtn.style.pointerEvents=''; }
      notice.remove();
    }, 8000);
  }
  initSceneButtons();
  initSizePresets();
  initGenParams();
  initLoraSlots();
  loadWorkflowList();
  loadLastSession();
  // Ensure section toggles are ready immediately.
  initSectionToggles();
  setGalleryTab('session');
  loadAllHistory(1);
  // 少し遅らせて実行（スマホ表示速度改善）
  setTimeout(()=>{
    initExtraPresets();
    initQualityMeta();
    initQualityMetaNeg();
    initNegExtraPresets();
    initNegSafetyButtons();
    loadNegStyleTagsFromServer();
    loadStyleTagsFromServer();
    initSectionToggles();
  }, 200);
});

async function generate(){
  if(running)return;
  // WebSocket接続を生成開始時に確立（未接続または切断済みの場合）
  if(!window._comfyWsReady){
    initComfyWs();
    // 最大3秒待機
    for(let i=0;i<15;i++){
      await new Promise(r=>setTimeout(r,200));
      if(window._comfyWsReady) break;
    }
  }
  const useLLMflag = document.getElementById('useLLM').checked;
  const {valid, payload, charDirectTags} = collectInput(useLLMflag);
  if(!valid){alert('シリーズまたはいずれかのキャラ名を入力してください');return;}
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
    const useLLM = useLLMflag;
    // LLM未使用時: キャラブロック化（1girl/1boy, キャラ名, 属性タグの順）
    if(!useLLM){
      // charDirectTagsを一旦クリアしてブロック順で再構築
      charDirectTags.length = 0;
      payload.characters.forEach(ch=>{
        const directTags = ch._directTagsBlock || [];
        // 性別タグ
        const gender = ch.gender||'';
        const genderTag = gender==='female'||gender==='girl' ? '1girl'
                        : gender==='male'||gender==='boy'   ? '1boy' : '';
        // キャラ名タグ
        if(!ch.original && ch.name){
          const namePart = ch.name.toLowerCase().replace(/\s+/g,'_').replace(/[^\w]/g,'_');
          const seriesPart = (ch.series||'').toLowerCase().replace(/\s+/g,'_').replace(/[^\w]/g,'_');
          const charTag = seriesPart ? `${namePart}_(${seriesPart})` : namePart;
          if(genderTag) charDirectTags.push(genderTag);
          charDirectTags.push(charTag);
        } else {
          if(genderTag) charDirectTags.push(genderTag);
        }
        directTags.forEach(t=>charDirectTags.push(t));
      });
      const sceneVals = [
        document.getElementById('f_world')?.value,
        document.getElementById('f_outdoor')?.value,
        document.getElementById('f_tod')?.value,
        document.getElementById('f_weather')?.value,
        document.getElementById('f_misc')?.value,
      ].filter(v=>v && /^[a-zA-Z0-9_\-,\s()]+$/.test(v));
      sceneVals.forEach(v=>{ if(v) charDirectTags.push(v); });
      setStep(steps,'s1','done','LLM: Skipped');
    }
    else { setStep(steps,'s1','active','LLM: Generating prompt...'); }
    const res=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input,use_llm:document.getElementById('useLLM').checked,width:selectedW,height:selectedH,fmt:selectedFmt,embed_metadata:embedMetadata,count:selectedCount,extra_tags:Array.from(extraTags),char_direct_tags:charDirectTags,prompt_prefix:collectPromptPrefix(),extra_note_en:document.getElementById('extraNoteEn').value.trim(),negative_prompt:collectNegativePrompt(),gen_params:collectGenParams(),lora_slots:collectLoraSlots(),workflow_file:getSelectedWorkflow(),client_id:window._comfyClientId})});
    const data=await res.json();
    if(data.error){
      setStep(steps,'s1','error','Error: '+data.error);
    }else{
      setStep(steps,'s1','done','LLM: Done');
      lastPositivePrompt=data.pre_extra_prompt || data.positive_prompt || data.final_prompt || '';
      lastFinalPrompt=data.final_prompt||'';
      lastNegativePrompt=data.negative_prompt||'';
      document.getElementById('lmLabel').style.display='block'; document.getElementById('lmLabel').classList.remove('collapsed');
      promptOutput.textContent=data.positive_prompt.replace(/\\n/g,'\n');
      promptOutput.classList.add('show');
      if(data.final_prompt){
        document.getElementById('finalLabel').style.display='block'; document.getElementById('finalLabel').classList.remove('collapsed');
        const finalEl = document.getElementById('promptFinal');
        finalEl.textContent = data.final_prompt;
        finalEl.style.display = 'block';
      }
      if(data.negative_prompt){
        document.getElementById('negFinalLabel').style.display='block'; document.getElementById('negFinalLabel').classList.remove('collapsed');
        const negFinalEl = document.getElementById('promptNegFinal');
        negFinalEl.textContent = data.negative_prompt;
        negFinalEl.style.display = 'block';
      }
      if(data.comfyui_sent){
        const ids=(data.prompt_ids||[data.prompt_id]).join(', ');
        const n=data.prompt_ids?data.prompt_ids.length:1;
        setStep(steps,'s2','done',`ComfyUI: ${n} queued`);
        setStep(steps,'s3','active','ComfyUI: Generating...');
        pollComfyUIComplete(data.prompt_ids||[data.prompt_id], steps);
        return; // running解除はpoll完了後
      }else{
        setStep(steps,'s2','error','ComfyUI: Send failed - '+(data.comfyui_error||'Unknown error'));
      }
    }
  }catch(e){
    setStep(steps,'s1','error','Network error: '+e.message);
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
  setStep(document.getElementById('steps'),'s_cancel','error','Cancelled');
  if(lastPositivePrompt){ document.getElementById('regenBtn').classList.add('show'); }
}

async function pollComfyUIComplete(promptIds, steps, stepId='s3'){
  const pending = new Set(promptIds);
  const collectedPaths = [];
  const progressWrap = document.getElementById('progressBarWrap');
  const progressBar  = document.getElementById('progressBar');
  let percentShown = false;
  let fallbackPct = 0;

  progressWrap.style.display = 'block';
  progressBar.style.width = '0%';
  const wsNotice = document.getElementById('wsNotice');
  if(wsNotice && !window._comfyWsReady) wsNotice.style.display='block';

  // onmessageハンドラを定義してグローバルに保持（再接続時も有効）
  const applyProgressMessage = (msg)=>{
    try{
      if(!msg || typeof msg !== 'object') return;
      const type = msg.type;
      const d = msg.data || msg;
      if(type === 'progress' || (d && d.value != null && d.max != null)){
        const value = Number(d.value ?? 0);
        const maxv = Number(d.max ?? 0);
        const pct = maxv > 0 ? Math.max(0, Math.min(100, Math.round((value / maxv) * 100))) : 0;
        progressBar.style.width = pct + '%';
        percentShown = true;
        setStep(steps,stepId,'active',`ComfyUI: Generating... ${pct}%`);
      } else if(type === 'executing' && d.node){
        setStep(steps,stepId,'active',`ComfyUI: Generating... ${progressBar.style.width}`);
      }
    }catch(_e){}
  };
  const wsHandler = async (event)=>{
    try{
      if(typeof event?.data === 'string'){
        applyProgressMessage(JSON.parse(event.data));
        return;
      }
      if(event?.data && typeof event.data.text === 'function'){
        const txt = await event.data.text();
        if(txt) applyProgressMessage(JSON.parse(txt));
      }
    }catch(_e){}
  };
  window._comfyWsHandler = wsHandler;

  // 既存WSにすぐセット（未接続の場合はinitComfyWsのonopen内でセットされる）
  if(window._comfyWs && window._comfyWsReady) window._comfyWs.onmessage = wsHandler;

  // 完了検知はHTTPポーリングで確実に行う
  let tries = 0;
  while(pending.size > 0 && tries < 300){
    await new Promise(r=>setTimeout(r, 2000));
    tries++;
    // ポーリング中にWS確立されたらonmessageをセット
    if(window._comfyWsReady && window._comfyWs && window._comfyWs.onmessage !== wsHandler){
      window._comfyWs.onmessage = wsHandler;
    }
    if(!window._comfyWsReady && (tries % 5 === 0)){
      // 再接続を定期的に試みる（%表示の復帰を狙う）
      initComfyWs();
    }
    try{
      const ids = [...pending].join(',');
      const res = await fetch(`/poll_status?ids=${encodeURIComponent(ids)}`).catch(()=>null);
      if(!res) continue;
      const data = await res.json();
      if(data.image_paths){
        for(const [pid, info] of Object.entries(data.image_paths)){
          const files = info.file_paths || [];
          const urls = info.view_urls || [];
          // Prefer local file paths to avoid stale /view URLs after PNG->WebP conversion.
          if(Array.isArray(files) && files.length) collectedPaths.push(...files);
          else if(Array.isArray(urls) && urls.length) collectedPaths.push(...urls);
          else if(Array.isArray(info) && info.length) collectedPaths.push(...info);
        }
      }
      for(const pid of (data.completed||[])) pending.delete(pid);
      if(!percentShown){
        // WS進捗が来ない環境向けフォールバック（疑似進捗）
        const done = promptIds.length - pending.size;
        const doneRatio = promptIds.length > 0 ? (done / promptIds.length) : 0;
        fallbackPct = Math.max(fallbackPct, Math.min(95, Math.round(doneRatio * 100)));
        if(done === 0){
          fallbackPct = Math.min(95, Math.max(fallbackPct, Math.min(90, 5 + Math.floor(tries * 1.4))));
        }
        progressBar.style.width = fallbackPct + '%';
        setStep(steps,stepId,'active',`ComfyUI: Generating... ${fallbackPct}%`);
      } else if(!window._comfyWsReady){
        const done = promptIds.length - pending.size;
        const q = data.queue||{};
        let queueStr = '';
        if(q.position != null) queueStr = ` - Queue waiting (#${q.position})`;
        else if(q.running > 0 || q.pending > 0) queueStr = ` - Queue: running ${q.running} / pending ${q.pending}`;
        setStep(steps,stepId,'active',`ComfyUI: Generating (${done}/${promptIds.length} done)${queueStr}`);
      }
    }catch(e){}
  }

  // onmessageをデフォルトに戻す
  window._comfyWsHandler = null;
  if(window._comfyWs) window._comfyWs.onmessage = ()=>{};

  progressBar.style.width = '100%';
  progressWrap.style.display = 'none';
  progressBar.style.width = '0%';
  if(wsNotice) wsNotice.style.display='none';
  setStep(steps,stepId,'done',`ComfyUI: Done (${promptIds.length})`);
  if(collectedPaths.length > 0){
    const posPrompt = document.getElementById('promptFinal')?.textContent||lastFinalPrompt||'';
    const negPrompt = document.getElementById('promptNegFinal')?.textContent||lastNegativePrompt||'';
    addGalleryItems(collectedPaths, posPrompt, negPrompt);
  }
  running=false;
  document.getElementById('btn').disabled=false;
  document.getElementById('cancelBtn').classList.remove('show');
  if(lastPositivePrompt){ document.getElementById('regenBtn').classList.add('show'); }
  autoSaveSession();
}

async function regenPrompt(){
  if(running||!lastPositivePrompt)return;
  // WebSocket接続を生成開始時に確立（未接続または切断済みの場合）
  if(!window._comfyWsReady){
    initComfyWs();
    // 最大3秒待機
    for(let i=0;i<15;i++){
      await new Promise(r=>setTimeout(r,200));
      if(window._comfyWsReady) break;
    }
  }
  running=true;
  document.getElementById('btn').disabled=true;
  document.getElementById('regenBtn').classList.remove('show');
  document.getElementById('cancelBtn').classList.add('show');
  document.getElementById('statusBox').classList.add('show');
  const steps=document.getElementById('steps');
  steps.innerHTML='';
  try{
    setStep(steps,'s_regen','active','ComfyUI: Re-generating image...');
    const regenExtraTags = Array.from(extraTags);
    const regenExtraEn = document.getElementById('extraNoteEn').value.trim();
    const res=await fetch('/regen',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt:lastPositivePrompt,width:selectedW,height:selectedH,fmt:selectedFmt,embed_metadata:embedMetadata,count:selectedCount,
        extra_tags:regenExtraTags, extra_note_en:regenExtraEn,
        prompt_prefix:collectPromptPrefix(),
        negative_prompt:collectNegativePrompt(),
        gen_params:collectGenParams(),
        lora_slots:collectLoraSlots(),
        workflow_file:getSelectedWorkflow(),
        client_id:window._comfyClientId})});
    const data=await res.json();
    if(data.error){
      setStep(steps,'s_regen','error','エラー: '+data.error);
      running=false;
      document.getElementById('btn').disabled=false;
      document.getElementById('cancelBtn').classList.remove('show');
      document.getElementById('regenBtn').classList.add('show');
    }else{
      const promptIds = data.prompt_ids || [data.prompt_id];
      setStep(steps,'s_regen','done','ComfyUI: Queued ('+promptIds.length+')');
      if(data.final_prompt){
        document.getElementById('finalLabel').style.display='block'; document.getElementById('finalLabel').classList.remove('collapsed');
        const finalEl = document.getElementById('promptFinal');
        finalEl.textContent = data.final_prompt;
        finalEl.style.display = 'block';
      }
      if(data.negative_prompt){
        document.getElementById('negFinalLabel').style.display='block'; document.getElementById('negFinalLabel').classList.remove('collapsed');
        const negFinalEl = document.getElementById('promptNegFinal');
        negFinalEl.textContent = data.negative_prompt;
        negFinalEl.style.display = 'block';
      }
      pollComfyUIComplete(promptIds, steps, 's_regen');
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
  <div id="floatNav" style="position:fixed;right:16px;top:50%;transform:translateY(-50%);z-index:500;display:flex;flex-direction:column;gap:0.3rem;background:rgba(255,255,255,0.97);border:1px solid var(--border);border-radius:10px;padding:0.5rem 0.4rem;box-shadow:0 2px 12px rgba(0,0,0,0.12);width:fit-content;">
    <div style="font-family:'DM Mono',monospace;font-size:0.55rem;color:var(--muted);text-align:center;margin-bottom:0.2rem;letter-spacing:0.05em;">NAV</div>
    <button onclick="navScrollTo('navA')" title="画像設定" style="font-family:'DM Mono',monospace;font-size:0.62rem;padding:0.3rem 0.5rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;white-space:nowrap;">🖼 画像</button>
    <button onclick="navScrollTo('navA2')" title="生成パラメータ" style="font-family:'DM Mono',monospace;font-size:0.62rem;padding:0.3rem 0.5rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;white-space:nowrap;">⚙ パラメータ</button>
    <button onclick="navScrollTo('navB')" title="キャラクター" style="font-family:'DM Mono',monospace;font-size:0.62rem;padding:0.3rem 0.5rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;white-space:nowrap;">🎭 キャラ</button>
    <button onclick="navScrollTo('navC')" title="シーン・雰囲気" style="font-family:'DM Mono',monospace;font-size:0.62rem;padding:0.3rem 0.5rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;white-space:nowrap;">🌍 シーン</button>
    <button onclick="navScrollTo('navLora')" title="LoRA" style="font-family:'DM Mono',monospace;font-size:0.62rem;padding:0.3rem 0.5rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;white-space:nowrap;">🎴 LoRA</button>
    <button onclick="navScrollTo('navExtra')" title="プロンプト調整" style="font-family:'DM Mono',monospace;font-size:0.62rem;padding:0.3rem 0.5rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;white-space:nowrap;">✨ ポジ調整</button>
    <button onclick="navScrollTo('navNeg')" title="ネガティブ調整" style="font-family:'DM Mono',monospace;font-size:0.62rem;padding:0.3rem 0.5rem;border:1px solid #e0779a;border-radius:5px;background:white;color:#c0392b;cursor:pointer;white-space:nowrap;">🚫 ネガ調整</button>
    <button onclick="navScrollTo('navStatus')" title="処理状況" style="font-family:'DM Mono',monospace;font-size:0.62rem;padding:0.3rem 0.5rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--ink);cursor:pointer;white-space:nowrap;">📋 状況</button>
    <button onclick="window.scrollTo({top:0,behavior:'smooth'})" title="先頭へ" style="font-family:'DM Mono',monospace;font-size:0.62rem;padding:0.3rem 0.5rem;border:1px solid var(--border);border-radius:5px;background:white;color:var(--muted);cursor:pointer;white-space:nowrap;">↑ TOP</button>
  </div>

</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    cancel_event = __import__('threading').Event()
    lm_session = None
    history_pending = {}
    history_saved_paths = set()
    history_lock = threading.Lock()
    def log_message(self,fmt,*args):pass

    def do_GET(self):
        if self.path=='/':
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.end_headers()
            ui_opts = load_ui_options()
            os_lang = detect_os_ui_lang()
            injected = HTML.replace(
                '<script>',
                '<script>\nconst __OPT__ = ' + json.dumps(ui_opts, ensure_ascii=False) + ';\nconst __OS_LANG__ = ' + json.dumps(os_lang) + ';\n',
                1  # 最初の<script>タグだけ
            )
            self.wfile.write(injected.encode('utf-8'))
        elif self.path=='/config':
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_config(),ensure_ascii=False).encode('utf-8'))
        elif self.path=='/logs_info':
            cfg = load_config()
            info = {
                'log_dir': _resolve_log_dir(cfg),
                'log_file': _LOG_FP or '',
                'log_level': cfg.get('log_level', 'normal'),
                'log_retention_days': int(cfg.get('log_retention_days', 30) or 30),
            }
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(info, ensure_ascii=False).encode('utf-8'))
        elif self.path=='/logs_zip':
            cfg = load_config()
            log_dir = _resolve_log_dir(cfg)
            mem = io.BytesIO()
            with zipfile.ZipFile(mem, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                if os.path.isdir(log_dir):
                    for fn in sorted(os.listdir(log_dir)):
                        if not fn.lower().endswith('.log'):
                            continue
                        fp = os.path.join(log_dir, fn)
                        if os.path.isfile(fp):
                            try:
                                zf.write(fp, arcname=fn)
                            except Exception:
                                pass
            data = mem.getvalue()
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', 'attachment; filename="anima_logs.zip"')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
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
                    result = {'ok': False, 'message': 'LLM URL is not set'}
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
                        result = {'ok': True, 'message': f'LLM connected ({platform or "Custom"}: {url})'}
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
            from urllib.parse import unquote
            ids_raw = qs.get('ids',[''])[0]
            ids = unquote(ids_raw).split(',')
            cfg = load_config()
            comfy = cfg.get('comfyui_url','http://127.0.0.1:8188').rstrip('/')
            completed = []
            image_paths = {}
            queue_info = {'running': 0, 'pending': 0, 'position': None}
            try:
                with _ureq.urlopen(comfy+'/history',timeout=3) as r:
                    hist = json.loads(r.read())
                for pid in ids:
                    if pid and pid in hist and hist[pid].get('status',{}).get('completed'):
                        completed.append(pid)
                        # 画像ファイル名を取得
                        outputs = hist[pid].get('outputs', {})
                        for nid, out in outputs.items():
                            imgs = out.get('images', [])
                            if imgs:
                                # output_dirを特定してフルパスを組み立て
                                output_dir = cfg.get('comfyui_output_dir','').strip()
                                if not output_dir:
                                    wf_path = cfg.get('workflow_json_path','')
                                    if wf_path and not os.path.isabs(wf_path):
                                        wf_path = os.path.join(_base_dir, wf_path)
                                    wf_path = wf_path.replace(os.sep,'/')
                                    parts = wf_path.split('/')
                                    for i,p in enumerate(parts):
                                        if p.lower()=='comfyui':
                                            output_dir=os.path.normpath('/'.join(parts[:i+1])+'/output')
                                            break
                                    if not output_dir:
                                        output_dir=os.path.normpath(os.path.join(os.path.dirname(wf_path),'..','..','output'))
                                comfy_port = comfy.split('//')[-1].split(':')[-1].split('/')[0] if ':' in comfy.split('//')[-1] else '8188'
                                req_host = self.headers.get('Host','').split(':')[0] or '127.0.0.1'
                                comfy_base = f'http://{req_host}:{comfy_port}'
                                paths = []
                                view_urls = []
                                for img in imgs:
                                    subfolder = img.get('subfolder','')
                                    fname = img.get('filename','')
                                    if fname:
                                        actual_fname = fname
                                        full = os.path.normpath(os.path.join(output_dir, subfolder, actual_fname)) if subfolder else os.path.normpath(os.path.join(output_dir, actual_fname))
                                        if (not os.path.exists(full)) and fname.lower().endswith('.png'):
                                            webp_name = fname[:-4] + '.webp'
                                            webp_full = os.path.normpath(os.path.join(output_dir, subfolder, webp_name)) if subfolder else os.path.normpath(os.path.join(output_dir, webp_name))
                                            if os.path.exists(webp_full):
                                                actual_fname = webp_name
                                                full = webp_full
                                        paths.append(full.replace('\\', '/'))
                                        view_urls.append(f'{comfy_base}/view?filename={actual_fname}&subfolder={subfolder}&type=output')
                                if paths:
                                    # リクエスト元のホストからComfyUIポートでアクセスできるURLに変換
                                    image_paths[pid] = {
                                        'file_paths': paths,
                                        'view_urls': view_urls
                                    }
                                    with Handler.history_lock:
                                        pending_meta = Handler.history_pending.get(pid)
                                    if pending_meta:
                                        for pth in paths:
                                            key = (pid, str(pth))
                                            with Handler.history_lock:
                                                if key in Handler.history_saved_paths:
                                                    continue
                                            ok = _save_history_record(cfg, pid, pth, pending_meta)
                                            if ok:
                                                with Handler.history_lock:
                                                    Handler.history_saved_paths.add(key)
                                        with Handler.history_lock:
                                            Handler.history_pending.pop(pid, None)
                                break
            except Exception as _pe:
                pass
            try:
                with _ureq.urlopen(comfy+'/queue',timeout=3) as r:
                    q = json.loads(r.read())
                running_list = q.get('queue_running', [])
                pending_list = q.get('queue_pending', [])
                queue_info['running'] = len(running_list)
                queue_info['pending'] = len(pending_list)
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
            self.wfile.write(json.dumps({'completed':completed,'total':len(ids),'queue':queue_info,'image_paths':image_paths},ensure_ascii=False).encode('utf-8'))
        elif self.path=='/session':
            sf=_sf('anima_session_last.json')
            data={}
            if os.path.exists(sf):
                with open(sf,encoding='utf-8') as f: data=json.load(f)
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data,ensure_ascii=False).encode('utf-8'))
        elif self.path.startswith('/history_list'):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query, keep_blank_values=True)
            try:
                page = max(1, int(qs.get('page', ['1'])[0] or '1'))
            except Exception:
                page = 1
            try:
                per_page = int(qs.get('per_page', ['20'])[0] or '20')
            except Exception:
                per_page = 20
            per_page = max(1, min(100, per_page))
            favorite_only = str(qs.get('favorite', ['0'])[0] or '0') == '1'
            workflow = str(qs.get('workflow', [''])[0] or '').strip()
            tag = str(qs.get('tag', [''])[0] or '').strip()
            cfg = load_config()
            try:
                _ensure_history_db(cfg)
                db_path = _resolve_history_db_path(cfg)
                con = sqlite3.connect(db_path, timeout=5)
                con.row_factory = sqlite3.Row
                where = []
                params = []
                if favorite_only:
                    where.append("favorite=1")
                if workflow:
                    where.append("workflow_name LIKE ?")
                    params.append(f"%{workflow}%")
                if tag:
                    where.append("tags LIKE ?")
                    params.append(f"%{tag}%")
                where_sql = (" WHERE " + " AND ".join(where)) if where else ""
                total = int(con.execute("SELECT COUNT(*) FROM generation_history" + where_sql, params).fetchone()[0])
                offset = (page - 1) * per_page
                rows = con.execute(
                    "SELECT id, created_at, prompt_id, thumbnail_path, image_path, prompt, negative_prompt, seed, steps, cfg, sampler, scheduler, workflow_name, loras, favorite, tags, width, height, model, model_hash "
                    "FROM generation_history" + where_sql + " ORDER BY id DESC LIMIT ? OFFSET ?",
                    params + [per_page, offset]
                ).fetchall()
                items = []
                for r in rows:
                    item = dict(r)
                    try:
                        item["loras"] = json.loads(item.get("loras") or "[]")
                    except Exception:
                        item["loras"] = []
                    items.append(item)
                con.close()
                payload = {"status": "ok", "total": total, "page": page, "per_page": per_page, "items": items}
            except Exception as e:
                payload = {"status": "error", "error": str(e), "total": 0, "page": page, "per_page": per_page, "items": []}
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        elif self.path.startswith('/history_detail'):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query, keep_blank_values=True)
            try:
                history_id = int(qs.get('id', ['0'])[0] or '0')
            except Exception:
                history_id = 0
            payload = {"status": "error", "error": "not found"}
            if history_id > 0:
                cfg = load_config()
                try:
                    _ensure_history_db(cfg)
                    db_path = _resolve_history_db_path(cfg)
                    con = sqlite3.connect(db_path, timeout=5)
                    con.row_factory = sqlite3.Row
                    row = con.execute("SELECT * FROM generation_history WHERE id=?", (history_id,)).fetchone()
                    con.close()
                    if row:
                        item = dict(row)
                        try:
                            item["loras"] = json.loads(item.get("loras") or "[]")
                        except Exception:
                            item["loras"] = []
                        payload = {"status": "ok", "item": item}
                except Exception as e:
                    payload = {"status": "error", "error": str(e)}
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
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
                            with open(os.path.join(CHARA_PRESETS_DIR,fn),'r',encoding='utf-8-sig') as f:
                                p = json.load(f)
                                p['_filename'] = fn
                                thumb_fn = os.path.splitext(fn)[0] + '.webp'
                                thumb_path = os.path.join(CHARA_PRESETS_DIR, thumb_fn)
                                if os.path.exists(thumb_path):
                                    p['_thumb_path'] = thumb_path.replace('\\', '/')
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
        elif self.path=='/version':
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'version': __version__}).encode())

        elif self.path.startswith('/lora_thumbnail'):
            from urllib.parse import urlparse, parse_qs, unquote
            qs = parse_qs(urlparse(self.path).query)
            lora_name = unquote(qs.get('name',[''])[0])
            # lora_rootsを取得してサムネを直接読み込む
            cfg2 = load_config()
            comfy = cfg2.get('comfyui_url','http://127.0.0.1:8188').rstrip('/')
            lora_path = lora_name.replace('\\', '/').replace('\\\\', '/')
            # サブフォルダとベース名を分解
            if '/' in lora_path:
                subfolder, fname = lora_path.rsplit('/', 1)
            else:
                subfolder, fname = '', lora_path
            base = fname.rsplit('.',1)[0]
            # ComfyUIのLoRAルートフォルダを取得
            lora_roots = []
            try:
                import urllib.request as _ureq5
                with _ureq5.urlopen(comfy+'/object_info/LoraLoader', timeout=5) as r:
                    info5 = json.loads(r.read())
                # extra_modelpath等からLoRAフォルダを推測
                # ComfyUIのシステム情報から取得
                with _ureq5.urlopen(comfy+'/system_stats', timeout=5) as r:
                    sys_info = json.loads(r.read())
                comfyui_dir = sys_info.get('system',{}).get('comfyui_version','')
            except Exception:
                pass
            # lora_rootsが取れない場合はComfyUI設定のcomfyui_output_dirから推測
            comfyui_output = cfg2.get('comfyui_output_dir','')
            if comfyui_output:
                # output -> ComfyUI root -> models/loras
                import pathlib
                p = pathlib.Path(comfyui_output)
                for parent in [p, p.parent, p.parent.parent]:
                    candidate = parent / 'models' / 'loras'
                    if candidate.exists():
                        lora_roots.append(str(candidate))
                    candidate2 = parent / 'loras'
                    if candidate2.exists():
                        lora_roots.append(str(candidate2))
            import mimetypes
            found_data = None
            found_mime = 'image/jpeg'
            for root in lora_roots:
                sub_path = os.path.join(root, subfolder) if subfolder else root
                for sfx in ['', '.preview']:
                    for ext in ['jpg','jpeg','png','webp']:
                        img_path = os.path.join(sub_path, f'{base}{sfx}.{ext}')
                        if os.path.exists(img_path):
                            with open(img_path, 'rb') as f:
                                found_data = f.read()
                            found_mime = mimetypes.guess_type(img_path)[0] or 'image/jpeg'
                            break
                    if found_data:
                        break
                if found_data:
                    break
            if found_data:
                self.send_response(200)
                self.send_header('Content-Type', found_mime)
                self.send_header('Content-Length', str(len(found_data)))
                self.send_header('Cache-Control', 'public, max-age=3600')
                self.end_headers()
                self.wfile.write(found_data)
            else:
                self.send_response(204)
                self.end_headers()
            return

        elif self.path.startswith('/workflow_node_ids'):
            from urllib.parse import urlparse, parse_qs, unquote
            qs = parse_qs(urlparse(self.path).query)
            wf_file = unquote(qs.get('file',[''])[0])
            result = {'pos_id':'','neg_id':'','ksampler_id':'','clip_id':''}
            if wf_file:
                wf_path = os.path.join(_workflows_dir, wf_file)
                if not os.path.exists(wf_path):
                    wf_path = os.path.join(_base_dir, wf_file)
                if os.path.exists(wf_path):
                    try:
                        wf = json.load(open(wf_path, encoding='utf-8'))
                        # API形式か保存形式か判定
                        nodes = []
                        links = {}
                        if 'nodes' not in wf:
                            # API形式 → 保存形式に近い構造で解析
                            # class_typeからKSampler/CLIPTextEncodeを直接探す
                            for nid, node in wf.items():
                                if not isinstance(node, dict): continue
                                t = node.get('class_type','')
                                if t in ('KSampler','KSamplerAdvanced'):
                                    result['ksampler_id'] = str(nid)
                                elif t == 'CLIPLoader':
                                    result['clip_id'] = str(nid)
                                elif t == 'CLIPTextEncode':
                                    inp = node.get('inputs',{})
                                    # positiveはKSamplerのpositive入力から辿る
                                    # API形式では接続が[node_id, slot]形式
                                    pass
                            # KSamplerのpositive/negative入力から判別
                            for nid, node in wf.items():
                                if not isinstance(node, dict): continue
                                if node.get('class_type') in ('KSampler','KSamplerAdvanced'):
                                    inp = node.get('inputs',{})
                                    pos_ref = inp.get('positive')
                                    neg_ref = inp.get('negative')
                                    if isinstance(pos_ref, list): result['pos_id'] = str(pos_ref[0])
                                    if isinstance(neg_ref, list): result['neg_id'] = str(neg_ref[0])
                        else:
                            nodes = wf.get('nodes', [])
                            links = {lnk[0]: lnk for lnk in wf.get('links', [])}
                        for n in nodes:
                            nid = str(n['id'])
                            t = n.get('type','')
                            if t == 'KSampler' or t == 'KSamplerAdvanced':
                                result['ksampler_id'] = nid
                            elif t == 'CLIPLoader':
                                result['clip_id'] = nid
                            elif t == 'CLIPTextEncode':
                                title = n.get('title','').lower()
                                # タイトルで判別
                                if 'positive' in title or 'ポジ' in title:
                                    result['pos_id'] = nid
                                elif 'negative' in title or 'ネガ' in title:
                                    result['neg_id'] = nid
                                else:
                                    # KSamplerのpositive/negative入力から判別
                                    for other in nodes:
                                        if other.get('type') in ('KSampler','KSamplerAdvanced'):
                                            for inp in other.get('inputs',[]):
                                                link_id = inp.get('link')
                                                if link_id and link_id in links:
                                                    src_nid = str(links[link_id][1])
                                                    if src_nid == nid:
                                                        if inp['name'] == 'positive':
                                                            result['pos_id'] = nid
                                                        elif inp['name'] == 'negative':
                                                            result['neg_id'] = nid
                    except Exception as e:
                        pass
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            return

        elif self.path=='/lora_list':
            import urllib.request as _ureq
            cfg2 = load_config()
            comfy = cfg2.get('comfyui_url','http://127.0.0.1:8188').rstrip('/')
            loras = []
            try:
                with _ureq.urlopen(comfy+'/object_info/LoraLoader', timeout=5) as r:
                    info = json.loads(r.read())
                # ComfyUIのobject_infoのlora_nameは [[list], "default"] 形式
                lora_name_field = info.get('LoraLoader',{}).get('input',{}).get('required',{}).get('lora_name')
                print(f'[lora_list] lora_name_field type={type(lora_name_field)} len={len(lora_name_field) if lora_name_field else 0}')
                if isinstance(lora_name_field, list) and len(lora_name_field) > 0:
                    first = lora_name_field[0]
                    if isinstance(first, list):
                        loras = first  # [[lora1, lora2, ...], "LoraLoader"]
                    else:
                        loras = lora_name_field
                print(f'[lora_list] got {len(loras)} loras')
            except Exception as e:
                print(f'[lora_list] error: {e}')
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'loras': loras}, ensure_ascii=False).encode())

        elif self.path=='/workflows':
            # workflowsフォルダ内のJSONファイル一覧を返す
            files = []
            try:
                for f in sorted(os.listdir(_workflows_dir)):
                    if f.lower().endswith('.json'):
                        files.append(f)
            except Exception:
                pass
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'files': files}, ensure_ascii=False).encode())

        elif self.path=='/neg_style_tags':
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"tags":load_neg_style_tags()},ensure_ascii=False).encode('utf-8'))
        elif self.path.startswith('/open_folder'):
            from urllib.parse import urlparse, parse_qs, unquote
            qs = parse_qs(urlparse(self.path).query)
            url_or_path = unquote(qs.get('path',[''])[0].strip())
            folder_path = ''
            # ComfyUIの/view URLの場合はoutput_dirから組み立て
            if '/view?' in url_or_path or url_or_path.startswith('http'):
                cfg2 = load_config()
                output_dir = cfg2.get('comfyui_output_dir','').strip()
                if not output_dir:
                    wf_path = cfg2.get('workflow_json_path','')
                    if wf_path and not os.path.isabs(wf_path):
                        wf_path = os.path.join(_base_dir, wf_path)
                    parts = wf_path.replace(os.sep,'/').split('/')
                    for i,p in enumerate(parts):
                        if p.lower()=='comfyui':
                            output_dir=os.path.normpath('/'.join(parts[:i+1])+'/output')
                            break
                # subfolderをURLから取得
                try:
                    vqs = parse_qs(urlparse(url_or_path).query)
                    subfolder = unquote(vqs.get('subfolder',[''])[0])
                    folder_path = os.path.normpath(os.path.join(output_dir, subfolder)) if subfolder else os.path.normpath(output_dir)
                except Exception:
                    folder_path = os.path.normpath(output_dir) if output_dir else ''
            else:
                # ファイルパスの場合は親フォルダ
                p = url_or_path.replace('/', os.sep)
                folder_path = os.path.dirname(p) if os.path.isfile(p) else p
            result = {'ok': False, 'message': ''}
            print(f'[open_folder] folder_path={folder_path!r} exists={os.path.isdir(folder_path)}')
            if os.path.isdir(folder_path):
                try:
                    import subprocess, sys
                    if sys.platform == 'win32':
                        subprocess.Popen(['explorer', folder_path])
                    elif sys.platform == 'darwin':
                        subprocess.Popen(['open', folder_path])
                    else:
                        subprocess.Popen(['xdg-open', folder_path])
                    result = {'ok': True, 'message': folder_path}
                    print(f'[open_folder] opened: {folder_path}')
                except Exception as e:
                    result = {'ok': False, 'message': str(e)}
            else:
                result = {'ok': False, 'message': f'フォルダが見つかりません: {folder_path}'}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
            return

        elif self.path.startswith('/get_image'):
            from urllib.parse import urlparse, parse_qs
            raw_query = urlparse(self.path).query
            qs = parse_qs(raw_query, keep_blank_values=True)
            img_path = qs.get('path',[''])[0].strip().replace('/', os.sep)
            if not img_path:
                self.send_response(404)
                self.end_headers()
                return

            cfg2 = load_config()
            output_dir = cfg2.get('comfyui_output_dir', '').strip()
            if not output_dir:
                wf_path = cfg2.get('workflow_json_path', '')
                if wf_path and not os.path.isabs(wf_path):
                    wf_path = os.path.join(_base_dir, wf_path)
                wf_path = wf_path.replace(os.sep, '/')
                parts = wf_path.split('/')
                for i, p in enumerate(parts):
                    if p.lower() == 'comfyui':
                        output_dir = os.path.normpath('/'.join(parts[:i+1]) + '/output')
                        break
                if not output_dir and wf_path:
                    output_dir = os.path.normpath(os.path.join(os.path.dirname(wf_path), '..', '..', 'output'))

            allowed_roots = [os.path.realpath(_base_dir)]
            if output_dir:
                allowed_roots.append(os.path.realpath(output_dir))

            img_path = _resolve_image_path_with_webp_fallback(img_path)
            real_path = os.path.normcase(os.path.realpath(os.path.normpath(img_path)))
            is_allowed = False
            for root in allowed_roots:
                root_norm = os.path.normcase(root)
                if real_path == root_norm or real_path.startswith(root_norm + os.sep):
                    is_allowed = True
                    break
            if not is_allowed or (not os.path.exists(real_path)):
                self.send_response(404 if os.path.exists(real_path) is False else 403)
                self.end_headers()
                return

            import time as _time
            ext = os.path.splitext(real_path)[1].lower()
            mime = {'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp'}.get(ext.lstrip('.'), 'image/png')
            data = b''
            for _ in range(8):
                if not os.path.exists(real_path):
                    break
                try:
                    size1 = os.path.getsize(real_path)
                    with open(real_path, 'rb') as f:
                        buf = f.read()
                    size2 = os.path.getsize(real_path)
                    # 書き込み中ファイルの中途半端読み取りを避ける
                    if size1 > 0 and size1 == size2 and len(buf) == size1:
                        data = buf
                        break
                except Exception:
                    pass
                _time.sleep(0.06)
            if not data:
                self.send_response(503)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.end_headers()
            self.wfile.write(data)
            return

        elif self.path.startswith('/chara_thumb'):
            from urllib.parse import urlparse, parse_qs, unquote
            qs = parse_qs(urlparse(self.path).query, keep_blank_values=True)
            fn = unquote(qs.get('file', [''])[0]).strip()
            if (not fn) or (os.path.basename(fn) != fn) or (not fn.endswith('.json')):
                self.send_response(404)
                self.end_headers()
                return
            thumb_path = os.path.join(CHARA_PRESETS_DIR, os.path.splitext(fn)[0] + '.webp')
            if not os.path.exists(thumb_path):
                self.send_response(404)
                self.end_headers()
                return
            with open(thumb_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/webp')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

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
        elif self.path=='/history_update':
            cfg = load_config()
            payload = {"status": "error", "error": "invalid id"}
            try:
                history_id = int(body.get('id', 0) or 0)
            except Exception:
                history_id = 0
            if history_id > 0:
                try:
                    _ensure_history_db(cfg)
                    db_path = _resolve_history_db_path(cfg)
                    con = sqlite3.connect(db_path, timeout=5)
                    favorite = 1 if int(body.get('favorite', 0) or 0) else 0
                    tags = str(body.get('tags', '') or '')
                    con.execute("UPDATE generation_history SET favorite=?, tags=? WHERE id=?", (favorite, tags, history_id))
                    con.commit()
                    con.close()
                    payload = {"status": "ok"}
                except Exception as e:
                    payload = {"status": "error", "error": str(e)}
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        elif self.path=='/history_delete':
            cfg = load_config()
            deleted = 0
            try:
                _ensure_history_db(cfg)
                db_path = _resolve_history_db_path(cfg)
                con = sqlite3.connect(db_path, timeout=5)
                con.row_factory = sqlite3.Row
                keep_favorites = bool(body.get('keep_favorites', False))
                delete_all = bool(body.get('all', False))
                if delete_all:
                    if keep_favorites:
                        rows = con.execute("SELECT id, thumbnail_path FROM generation_history WHERE favorite=0").fetchall()
                        con.execute("DELETE FROM generation_history WHERE favorite=0")
                    else:
                        rows = con.execute("SELECT id, thumbnail_path FROM generation_history").fetchall()
                        con.execute("DELETE FROM generation_history")
                else:
                    history_id = int(body.get('id', 0) or 0)
                    rows = con.execute("SELECT id, thumbnail_path FROM generation_history WHERE id=?", (history_id,)).fetchall() if history_id > 0 else []
                    if history_id > 0:
                        con.execute("DELETE FROM generation_history WHERE id=?", (history_id,))
                deleted = len(rows)
                con.commit()
                con.close()
                for r in rows:
                    tp = str(r["thumbnail_path"] or "").strip()
                    if tp and os.path.exists(tp):
                        try:
                            os.remove(tp)
                        except Exception:
                            pass
                payload = {"status": "ok", "deleted": deleted}
            except Exception as e:
                payload = {"status": "error", "error": str(e), "deleted": deleted}
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
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
                        thumb_path = os.path.join(CHARA_PRESETS_DIR, os.path.splitext(filename)[0] + '.webp')
                        if os.path.exists(thumb_path):
                            os.remove(thumb_path)
                            print(f'[プリセット] サムネ削除: {os.path.basename(thumb_path)}')
            except Exception as e:
                result = {'ok': False, 'error': str(e)}
                print(f'[プリセット] エラー: {e}')
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result,ensure_ascii=False).encode('utf-8'))
        elif self.path=='/chara_preset_thumb':
            os.makedirs(CHARA_PRESETS_DIR, exist_ok=True)
            result = {'ok': True}
            try:
                filename = str(body.get('filename','')).strip()
                image_path_raw = str(body.get('image_path','')).strip()
                image_path = image_path_raw
                if (not filename) or (not filename.endswith('.json')) or (os.path.basename(filename) != filename):
                    raise ValueError('invalid preset filename')
                preset_path = os.path.join(CHARA_PRESETS_DIR, filename)
                if not os.path.exists(preset_path):
                    raise FileNotFoundError('preset not found')
                if not image_path:
                    raise ValueError('image path is empty')

                # If ComfyUI /view URL is passed, resolve to local output file path.
                if image_path.lower().startswith('http') and '/view?' in image_path:
                    from urllib.parse import urlparse, parse_qs, unquote
                    vqs = parse_qs(urlparse(image_path).query, keep_blank_values=True)
                    vf = unquote(vqs.get('filename',[''])[0]).strip()
                    vs = unquote(vqs.get('subfolder',[''])[0]).strip().replace('/', os.sep)
                    if vf:
                        cfg_tmp = load_config()
                        out_tmp = cfg_tmp.get('comfyui_output_dir', '').strip()
                        if not out_tmp:
                            wf_path = cfg_tmp.get('workflow_json_path', '')
                            if wf_path and not os.path.isabs(wf_path):
                                wf_path = os.path.join(_base_dir, wf_path)
                            wf_path = wf_path.replace(os.sep, '/')
                            parts = wf_path.split('/')
                            for i, p in enumerate(parts):
                                if p.lower() == 'comfyui':
                                    out_tmp = os.path.normpath('/'.join(parts[:i+1]) + '/output')
                                    break
                            if not out_tmp and wf_path:
                                out_tmp = os.path.normpath(os.path.join(os.path.dirname(wf_path), '..', '..', 'output'))
                        image_path = os.path.normpath(os.path.join(out_tmp, vs, vf) if vs else os.path.join(out_tmp, vf))
                else:
                    # Local path mode
                    image_path = image_path.replace('/', os.sep)

                cfg2 = load_config()
                output_dir = cfg2.get('comfyui_output_dir', '').strip()
                if not output_dir:
                    wf_path = cfg2.get('workflow_json_path', '')
                    if wf_path and not os.path.isabs(wf_path):
                        wf_path = os.path.join(_base_dir, wf_path)
                    wf_path = wf_path.replace(os.sep, '/')
                    parts = wf_path.split('/')
                    for i, p in enumerate(parts):
                        if p.lower() == 'comfyui':
                            output_dir = os.path.normpath('/'.join(parts[:i+1]) + '/output')
                            break
                    if not output_dir and wf_path:
                        output_dir = os.path.normpath(os.path.join(os.path.dirname(wf_path), '..', '..', 'output'))

                allowed_roots = [os.path.realpath(_base_dir)]
                if output_dir:
                    allowed_roots.append(os.path.realpath(output_dir))

                real_src = os.path.normcase(os.path.realpath(os.path.normpath(image_path)))
                is_allowed = False
                for root in allowed_roots:
                    root_norm = os.path.normcase(root)
                    if real_src == root_norm or real_src.startswith(root_norm + os.sep):
                        is_allowed = True
                        break
                if not is_allowed:
                    raise PermissionError('image path not allowed')
                if not os.path.exists(real_src):
                    raise FileNotFoundError('source image not found')

                thumb_file = os.path.splitext(filename)[0] + '.webp'
                thumb_path = os.path.join(CHARA_PRESETS_DIR, thumb_file)
                from PIL import Image
                img = Image.open(real_src)
                img.thumbnail((768, 768), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                img.save(thumb_path, 'WEBP', quality=88, method=6)
                result['thumb_file'] = thumb_file
                result['thumb_path'] = thumb_path.replace('\\', '/')
                print(f'[プリセット] サムネ保存: {thumb_file} <- {real_src}')
            except Exception as e:
                result = {'ok': False, 'error': str(e)}
                print(f'[プリセット] サムネエラー: {e}')
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
                fmt=body.get('fmt', cfg.get('output_format', 'png'))
                embed_metadata = bool(body.get('embed_metadata', cfg.get('embed_metadata', True)))
                gen_params=body.get('gen_params',{})
                if gen_params:
                    for k in ('seed_mode','seed_value','steps','cfg','sampler_name','scheduler'):
                        if k in gen_params: cfg[k]=gen_params[k]
                regen_lora_slots=body.get('lora_slots',[])
                regen_workflow_file=body.get('workflow_file','').strip()
                if regen_workflow_file:
                    cfg['workflow_json_path'] = os.path.join(_workflows_dir, regen_workflow_file)
                    print(f"[ComfyUI] ワークフロー選択（再生成）: {regen_workflow_file}")
                if not prompt:
                    raise ValueError('プロンプトが空です')
                # Extraタグ・英語追記を適用
                prompt_flat = prompt.replace("\\n"," ").replace("\n"," ")
                if regen_prompt_prefix:
                    # promptにすでにprefixが含まれている場合は除去してから付け直す
                    prefix_set = {t.strip().lower() for t in regen_prompt_prefix if t}
                    deduped = [t for t in prompt_flat.split(',') if t.strip().lower() not in prefix_set]
                    prompt_flat = ', '.join(t.strip() for t in deduped if t.strip())
                    prompt_flat=", ".join(str(t) for t in regen_prompt_prefix)+", "+prompt_flat
                if regen_extra_tags:
                    # promptにすでにextra_tagsが含まれている場合は除去してから追加
                    extra_set = {t.strip().lower() for t in regen_extra_tags if t}
                    deduped_flat = [t for t in prompt_flat.split(',') if t.strip().lower() not in extra_set]
                    prompt_flat = ', '.join(t.strip() for t in deduped_flat if t.strip())
                    extra_str=", ".join(str(t) for t in regen_extra_tags)
                    prompt_flat=(prompt_flat+", "+extra_str).strip(", ") if prompt_flat else extra_str
                if regen_extra_en:
                    # promptにすでにextra_note_enが含まれている場合は除去してから追加
                    prompt_flat = prompt_flat.replace(regen_extra_en, '').rstrip(', ')
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
                    cid=body.get('client_id', str(uuid.uuid4()))
                    pid, meta = send_to_comfyui(
                        prompt, cfg, width, height, fmt, cid,
                        negative_prompt=regen_negative, lora_slots=regen_lora_slots
                    )
                    with Handler.history_lock:
                        Handler.history_pending[pid] = meta
                    prompt_ids.append(pid)
                    print(f"[ComfyUI] 再生成キュー ({i+1}/{count}): {pid}")
                    watch_and_postprocess(
                        comfyui_url=comfyui_url,
                        output_dir=output_dir,
                        date_folder=date_folder,
                        prompt_id=pid,
                        client_id=cid,
                        output_format=fmt,
                        embed_metadata=embed_metadata,
                        parameters_text=_build_parameters_text(meta) if embed_metadata else "",
                        prompt_json=meta.get("prompt_json", "") if embed_metadata else "",
                        workflow_json=meta.get("workflow_json", "") if embed_metadata else "",
                    )
                result={
                    'prompt_ids':prompt_ids,
                    'prompt_id':prompt_ids[0] if prompt_ids else '',
                    'final_prompt':prompt,
                    'negative_prompt':regen_negative
                }
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

        elif self.path.startswith('/get_image'):
            from urllib.parse import urlparse, parse_qs, unquote
            raw_query = urlparse(self.path).query
            # parse_qsは自動デコードするのでそのまま使う
            qs = parse_qs(raw_query, keep_blank_values=True)
            img_path = qs.get('path',[''])[0].strip()
            # スラッシュをOSのセパレータに変換（Windows対応）
            img_path = img_path.replace('/', os.sep)
            if not img_path:
                self.send_response(404)
                self.end_headers()
                return

            cfg2 = load_config()
            output_dir = cfg2.get('comfyui_output_dir', '').strip()
            if not output_dir:
                wf_path = cfg2.get('workflow_json_path', '')
                if wf_path and not os.path.isabs(wf_path):
                    wf_path = os.path.join(_base_dir, wf_path)
                wf_path = wf_path.replace(os.sep, '/')
                parts = wf_path.split('/')
                for i, p in enumerate(parts):
                    if p.lower() == 'comfyui':
                        output_dir = os.path.normpath('/'.join(parts[:i+1]) + '/output')
                        break
                if not output_dir and wf_path:
                    output_dir = os.path.normpath(os.path.join(os.path.dirname(wf_path), '..', '..', 'output'))

            allowed_roots = [os.path.realpath(_base_dir)]
            if output_dir:
                allowed_roots.append(os.path.realpath(output_dir))

            img_path = _resolve_image_path_with_webp_fallback(img_path)
            real_path = os.path.normcase(os.path.realpath(os.path.normpath(img_path)))
            is_allowed = False
            for root in allowed_roots:
                root_norm = os.path.normcase(root)
                if real_path == root_norm or real_path.startswith(root_norm + os.sep):
                    is_allowed = True
                    break
            if not is_allowed:
                self.send_response(403)
                self.end_headers()
                return

            if not os.path.exists(real_path):
                self.send_response(404)
                self.end_headers()
                return

            ext = os.path.splitext(real_path)[1].lower()
            mime = {'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp'}.get(ext.lstrip('.'), 'image/png')
            with open(real_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        elif self.path.startswith('/chara_thumb'):
            from urllib.parse import urlparse, parse_qs, unquote
            qs = parse_qs(urlparse(self.path).query, keep_blank_values=True)
            fn = unquote(qs.get('file', [''])[0]).strip()
            if (not fn) or (os.path.basename(fn) != fn) or (not fn.endswith('.json')):
                self.send_response(404)
                self.end_headers()
                return
            thumb_path = os.path.join(CHARA_PRESETS_DIR, os.path.splitext(fn)[0] + '.webp')
            if not os.path.exists(thumb_path):
                self.send_response(404)
                self.end_headers()
                return
            with open(thumb_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/webp')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
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
            cfg=load_config()
            img_fmt=body.get('fmt', cfg.get('output_format', 'png'))
            img_count=max(1,int(body.get('count',1)))
            embed_metadata = bool(body.get('embed_metadata', cfg.get('embed_metadata', True)))
            print(f"[DEBUG] 受信: fmt={img_fmt} width={body.get('width')} height={body.get('height')} count={img_count}")
            # gen_paramsでcfgを上書き
            gen_params=body.get('gen_params',{})
            if gen_params:
                for k in ('seed_mode','seed_value','steps','cfg','sampler_name','scheduler'):
                    if k in gen_params: cfg[k]=gen_params[k]
            lora_slots=body.get('lora_slots',[])
            workflow_file=body.get('workflow_file','').strip()
            if workflow_file:
                cfg['workflow_json_path'] = os.path.join(_workflows_dir, workflow_file)
                print(f"[ComfyUI] ワークフロー選択: {workflow_file}")
            Handler.cancel_event.clear()
            result={"positive_prompt":"","comfyui_sent":False,"prompt_id":"","error":"","comfyui_error":""}

            try:
                if use_llm:
                    print(f"\n[LLM] 生成開始: {user_input}")
                    raw=call_llm(user_input,cfg)
                    positive=extract_positive_prompt(raw)
                    if Handler.cancel_event.is_set():
                        result["error"]="cancelled"
                        self.send_response(200)
                        self.send_header('Content-Type','application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(result,ensure_ascii=False).encode('utf-8'))
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
                    if positive_flat and prompt_prefix:
                        prefix_set = {t.strip().lower() for t in prompt_prefix if t}
                        deduped = [t for t in positive_flat.split(',') if t.strip().lower() not in prefix_set]
                        positive_flat = ', '.join(t.strip() for t in deduped if t.strip())
                    positive_flat=", ".join(str(t) for t in prompt_prefix)+("", ", "+positive_flat)[bool(positive_flat)]
                if char_direct_tags:
                    direct_str=", ".join(str(t) for t in char_direct_tags if t)
                    # LLM出力にすでに含まれるタグは除去して重複防止
                    if positive_flat:
                        direct_set = {t.strip().lower() for t in char_direct_tags if t}
                        flat_tags = {t.strip().lower() for t in positive_flat.split(',')}
                        deduped_direct = [t for t in char_direct_tags if t and t.strip().lower() not in flat_tags]
                        direct_str = ", ".join(str(t) for t in deduped_direct if t)
                    if direct_str:
                        positive_flat=(positive_flat+", "+direct_str).strip(", ")
                # extra_tags適用前・extra_note_enなしで保存（再生成時の二重防止）
                result["pre_extra_prompt"] = positive_flat
                if extra_tags:
                    extra_str=", ".join(str(t) for t in extra_tags)
                    positive_flat=(positive_flat+", "+extra_str).strip(", ") if positive_flat else extra_str
                # extra_note_enは必ず最後
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
                    # JS側と同じclient_idを使用（progressイベントの受信に必要）
                    shared_cid = body.get('client_id', str(uuid.uuid4()))
                    result["client_id"] = shared_cid
                    for i in range(img_count):
                        if Handler.cancel_event.is_set():
                            break
                        pid, meta = send_to_comfyui(
                            positive_flat, cfg, img_width, img_height, img_fmt, shared_cid,
                            negative_prompt=negative_prompt, lora_slots=lora_slots
                        )
                        with Handler.history_lock:
                            Handler.history_pending[pid] = meta
                        prompt_ids.append(pid)
                        print(f"[ComfyUI] キューに追加 ({i+1}/{img_count}): {pid}")
                        watch_and_postprocess(
                            comfyui_url=comfyui_url,
                            output_dir=output_dir,
                            date_folder=date_folder,
                            prompt_id=pid,
                            client_id=shared_cid,
                            output_format=img_fmt,
                            embed_metadata=embed_metadata,
                            parameters_text=_build_parameters_text(meta) if embed_metadata else "",
                            prompt_json=meta.get("prompt_json", "") if embed_metadata else "",
                            workflow_json=meta.get("workflow_json", "") if embed_metadata else "",
                        )
                        # incrementモード: seed+1して保存
                        if cfg.get('seed_mode') == 'increment':
                            cfg['seed_value'] = int(cfg.get('seed_value', 0)) + 1
                            save_cfg = load_config()
                            save_cfg['seed_value'] = cfg['seed_value']
                            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                                json.dump(save_cfg, f, ensure_ascii=False, indent=2)
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


def check_server(name,url,path="/", cfg=None):
    try:
        requests.get(url+path,timeout=3)
        print(f"  ✓ {name}: {_ct('接続OK', 'Connected', cfg)} ({url})")
    except Exception as e:
        print(f"  ✗ {name}: {_ct('接続失敗', 'Connection failed', cfg)} ({url}) -> {e}")

def main():
    _install_exception_logging()
    cfg=load_config()
    try:
        _ensure_history_db(cfg)
    except Exception as e:
        print(f"[OUTPUT-3] DB init error: {e}")
    # Console block from "[接続確認]" downward should follow OS language.
    _os_lang = detect_os_ui_lang()
    _os_cfg = {"console_lang": _os_lang}
    print("="*55)
    print(f"  Anima Pipeline  v{__version__}")
    print("="*55)
    print(f"\n[{_ct('接続確認', 'Connection Check', _os_cfg)}]")
    check_server("LLM",cfg["llm_url"],"/api/v1/models", _os_cfg)
    check_server("ComfyUI  ",cfg["comfyui_url"],"/system_stats", _os_cfg)
    print()
    print(f"  UI:           http://localhost:{UI_PORT}")
    print(f"  LM Studio:    {cfg['llm_url']}")
    print(f"  {_ct('モデル', 'Model', _os_cfg)}:       {cfg['llm_model']}")
    print(f"  ComfyUI:      {cfg['comfyui_url']}")
    print(f"  {_ct('ワークフロー', 'Workflow', _os_cfg)}: {cfg.get('workflow_json_path', _ct('未設定','Unset', _os_cfg))}")
    print(f"  {_ct('設定ファイル', 'Config File', _os_cfg)}: {CONFIG_FILE}")
    print("="*55)
    print(f"\n{_ct('Ctrl+C で停止', 'Press Ctrl+C to stop', _os_cfg)}\n")
    server=HTTPServer(('0.0.0.0',UI_PORT),Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{_ct('停止しました。', 'Stopped.', _os_cfg)}")

if __name__=='__main__':
    main()
