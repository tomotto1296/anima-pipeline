import datetime
import json
import os
import sqlite3


_BASE_DIR = ""
_SETTINGS_DIR = ""
_DEFAULT_CONFIG = {
    "history_db_path": "history/history.db",
    "history_thumb_dir": "history/thumbs",
}


def configure_history(base_dir: str, settings_dir: str, default_config: dict | None = None):
    global _BASE_DIR, _SETTINGS_DIR, _DEFAULT_CONFIG
    _BASE_DIR = os.path.normpath(str(base_dir or ""))
    _SETTINGS_DIR = os.path.normpath(str(settings_dir or ""))
    cfg = _DEFAULT_CONFIG.copy()
    if isinstance(default_config, dict):
        cfg.update(default_config)
    _DEFAULT_CONFIG = cfg


def _resolve_history_db_path(cfg: dict) -> str:
    raw = str((cfg or {}).get("history_db_path", _DEFAULT_CONFIG["history_db_path"]) or "").strip()
    if not raw:
        raw = _DEFAULT_CONFIG["history_db_path"]
    if os.path.isabs(raw):
        return os.path.normpath(raw)
    return os.path.normpath(os.path.join(_BASE_DIR, raw))


def _resolve_history_thumb_dir(cfg: dict) -> str:
    raw = str((cfg or {}).get("history_thumb_dir", _DEFAULT_CONFIG["history_thumb_dir"]) or "").strip()
    if not raw:
        raw = _DEFAULT_CONFIG["history_thumb_dir"]
    if os.path.isabs(raw):
        return os.path.normpath(raw)
    return os.path.normpath(os.path.join(_BASE_DIR, raw))


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
    sf = os.path.join(_SETTINGS_DIR, "anima_session_last.json")
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
