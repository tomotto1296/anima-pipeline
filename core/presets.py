import datetime
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARA_PRESETS_DIR = os.path.join(BASE_DIR, "chara")
PRESETS_BASE_DIR = os.path.join(BASE_DIR, "presets")

PRESET_CATEGORIES = ("chara", "scene", "camera", "quality", "lora", "composite", "negative", "positive")
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
_INVALID_SESSION_FILENAME_RE = re.compile(r'[\\/:*?"<>|]+')


def _preset_dir_for_category(category: str) -> str:
    cat = str(category or "").strip().lower()
    if cat == "chara":
        return CHARA_PRESETS_DIR
    return os.path.join(PRESETS_BASE_DIR, cat)


def _is_valid_preset_category(category: str) -> bool:
    return str(category or "").strip().lower() in PRESET_CATEGORIES


def _sanitize_preset_name(name: str) -> str:
    safe = str(name or "").strip().replace("/", "_").replace("\\", "_")
    safe = safe.strip(".")
    return safe[:80]


def _preset_filepath(category: str, name: str) -> str:
    safe_name = _sanitize_preset_name(name)
    if not safe_name:
        return ""
    return os.path.join(_preset_dir_for_category(category), safe_name + ".json")


def list_presets(category: str) -> list[str]:
    if not _is_valid_preset_category(category):
        raise ValueError("Unknown preset category")
    pdir = _preset_dir_for_category(category)
    if not os.path.exists(pdir):
        return []
    names = []
    for fn in sorted(os.listdir(pdir)):
        if fn.lower().endswith(".json"):
            names.append(os.path.splitext(fn)[0])
    return names


def load_preset(category: str, name: str) -> dict:
    if not _is_valid_preset_category(category):
        raise ValueError("Unknown preset category")
    fpath = _preset_filepath(category, name)
    if not fpath:
        raise ValueError("Invalid preset name")
    if not os.path.exists(fpath):
        raise FileNotFoundError("Preset not found")
    with open(fpath, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "data" in raw:
        return {
            "name": raw.get("name", _sanitize_preset_name(name)),
            "data": raw.get("data", {}),
            "savedAt": raw.get("savedAt", ""),
            "status": "ok",
        }
    return {
        "name": _sanitize_preset_name(name),
        "data": raw if isinstance(raw, dict) else {},
        "savedAt": "",
        "status": "ok",
    }


def save_preset(category: str, name: str, data: dict) -> dict:
    if not _is_valid_preset_category(category):
        raise ValueError("Unknown preset category")
    safe_name = _sanitize_preset_name(name)
    if not safe_name:
        raise ValueError("Invalid preset name")
    pdir = _preset_dir_for_category(category)
    os.makedirs(pdir, exist_ok=True)
    fpath = _preset_filepath(category, safe_name)
    payload = {
        "name": safe_name,
        "data": data if isinstance(data, dict) else {},
        "savedAt": datetime.datetime.now().isoformat(),
    }
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return {"status": "ok", "name": safe_name}


def delete_preset(category: str, name: str) -> dict:
    if not _is_valid_preset_category(category):
        raise ValueError("Unknown preset category")
    fpath = _preset_filepath(category, name)
    if not fpath:
        raise ValueError("Invalid preset name")
    if not os.path.exists(fpath):
        raise FileNotFoundError("Preset not found")
    os.remove(fpath)
    return {"status": "ok"}


def sanitize_session_name(name: str) -> str:
    safe = str(name or "").strip()
    safe = _INVALID_SESSION_FILENAME_RE.sub("_", safe)
    safe = re.sub(r"\s+", " ", safe)
    safe = safe.strip(" .")
    return safe[:80]


def default_session_name(now: datetime.datetime | None = None) -> str:
    dt = now or datetime.datetime.now()
    return dt.strftime("Anima_Pipeline_%Y-%m-%d_%H-%M")


def _session_filepath(name: str) -> tuple[str, str]:
    safe_name = sanitize_session_name(name)
    if not safe_name:
        safe_name = default_session_name()
    return safe_name, os.path.join(SESSIONS_DIR, safe_name + ".json")


def save_named_session(name: str, data: dict, overwrite: bool = False) -> dict:
    safe_name, filepath = _session_filepath(name)
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    if (not overwrite) and os.path.exists(filepath):
        raise FileExistsError("Session already exists")
    payload = data if isinstance(data, dict) else {}
    payload.setdefault("savedAt", datetime.datetime.now().isoformat())
    payload["sessionName"] = safe_name
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return {"status": "ok", "name": safe_name, "filename": os.path.basename(filepath)}


def load_named_session(name: str) -> dict:
    safe_name = sanitize_session_name(name)
    if not safe_name:
        raise ValueError("Invalid session name")
    filepath = os.path.join(SESSIONS_DIR, safe_name + ".json")
    if not os.path.exists(filepath):
        raise FileNotFoundError("Session not found")
    with open(filepath, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data.setdefault("sessionName", safe_name)
    return data if isinstance(data, dict) else {}


def delete_named_session(name: str) -> dict:
    safe_name = sanitize_session_name(name)
    if not safe_name:
        raise ValueError("Invalid session name")
    filepath = os.path.join(SESSIONS_DIR, safe_name + ".json")
    if not os.path.exists(filepath):
        raise FileNotFoundError("Session not found")
    os.remove(filepath)
    return {"status": "ok"}


def list_named_sessions() -> list[dict]:
    if not os.path.isdir(SESSIONS_DIR):
        return []
    items: list[dict] = []
    for fn in os.listdir(SESSIONS_DIR):
        if not fn.lower().endswith(".json"):
            continue
        fp = os.path.join(SESSIONS_DIR, fn)
        if not os.path.isfile(fp):
            continue
        base_name = os.path.splitext(fn)[0]
        saved_at = datetime.datetime.fromtimestamp(os.path.getmtime(fp)).isoformat()
        display_name = base_name
        try:
            with open(fp, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if isinstance(data, dict):
                display_name = str(data.get("sessionName", base_name) or base_name)
                saved_at = str(data.get("savedAt", saved_at) or saved_at)
        except Exception:
            pass
        items.append({"name": display_name, "savedAt": saved_at, "filename": fn})
    items.sort(key=lambda x: str(x.get("savedAt", "")), reverse=True)
    return items
