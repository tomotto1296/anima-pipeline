import datetime
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARA_PRESETS_DIR = os.path.join(BASE_DIR, "chara")
PRESETS_BASE_DIR = os.path.join(BASE_DIR, "presets")

PRESET_CATEGORIES = ("chara", "scene", "camera", "quality", "lora", "composite", "negative", "positive")


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
