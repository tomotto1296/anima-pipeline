import builtins
import datetime
import json
import locale
import os
import re
import sys
import threading
import traceback

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_DIR = os.path.join(BASE_DIR, 'settings')
os.makedirs(SETTINGS_DIR, exist_ok=True)


def _sf(name: str) -> str:
    return os.path.join(SETTINGS_DIR, name)


CONFIG_FILE = _sf('pipeline_config.json')
EXTRA_TAGS_FILE = _sf('extra_tags.json')
STYLE_TAGS_FILE = _sf('style_tags.json')
NEG_EXTRA_TAGS_FILE = _sf('extra_tags_negative.json')
NEG_STYLE_TAGS_FILE = _sf('style_tags_negative.json')
UI_OPTIONS_FILE = _sf('ui_options.json')
DEFAULT_LOGS_DIR = os.path.join(BASE_DIR, 'logs')

_ORIG_PRINT = builtins.print
_LOG_LOCK = threading.Lock()
_LOG_FP = None
_LOG_FH = None
_LOG_LEVEL = 'normal'  # normal / debug
_LOG_DIR = DEFAULT_LOGS_DIR


def _mask_sensitive(text: str) -> str:
    s = str(text or '')
    s = re.sub(r'(?i)\b(token|api[_ -]?key|authorization)\b(\s*[:=]\s*)([^\s,;]+)', r'\1\2***', s)
    s = re.sub(r'(?i)\bBearer\s+[A-Za-z0-9._\-+/=]+', 'Bearer ***', s)
    return s


def _resolve_log_dir(cfg: dict | None = None) -> str:
    c = cfg or {}
    raw = str(c.get('log_dir', 'logs') or 'logs').strip()
    if not raw:
        raw = 'logs'
    if os.path.isabs(raw):
        return os.path.normpath(raw)
    return os.path.normpath(os.path.join(BASE_DIR, raw))


def _cleanup_old_logs(log_dir: str, retention_days: int):
    if retention_days <= 0:
        return
    cutoff = datetime.datetime.now() - datetime.timedelta(days=retention_days)
    try:
        for fn in os.listdir(log_dir):
            if not fn.lower().endswith('.log'):
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
    if level == 'DEBUG' and _LOG_LEVEL != 'debug':
        return
    if not _LOG_FH:
        return
    line = _mask_sensitive(message).replace('\r', '')
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with _LOG_LOCK:
        try:
            _LOG_FH.write(f'[{ts}] [{level}] {line}\n')
            _LOG_FH.flush()
        except Exception:
            pass


def _apply_log_config(cfg: dict):
    global _LOG_FP, _LOG_FH, _LOG_LEVEL, _LOG_DIR
    _LOG_LEVEL = 'debug' if str(cfg.get('log_level', 'normal')).lower() == 'debug' else 'normal'
    _LOG_DIR = _resolve_log_dir(cfg)
    os.makedirs(_LOG_DIR, exist_ok=True)
    try:
        retention = int(cfg.get('log_retention_days', 30))
    except Exception:
        retention = 30
    if retention < 0:
        retention = 0
    _cleanup_old_logs(_LOG_DIR, retention)
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    fp = os.path.join(_LOG_DIR, f'anima_{today}.log')
    if _LOG_FP != fp or _LOG_FH is None:
        try:
            if _LOG_FH:
                _LOG_FH.close()
        except Exception:
            pass
        _LOG_FP = fp
        _LOG_FH = open(_LOG_FP, 'a', encoding='utf-8')


def get_log_file_path() -> str:
    return _LOG_FP or ''


def _patched_print(*args, **kwargs):
    try:
        _ORIG_PRINT(*args, **kwargs)
    except Exception:
        pass
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\n')
    try:
        msg = sep.join(str(a) for a in args) + ('' if end == '\n' else str(end))
    except Exception:
        msg = ' '.join(str(a) for a in args)
    _log_write('INFO', msg.rstrip('\n'))


builtins.print = _patched_print


def _install_exception_logging():
    def _hook(exc_type, exc, tb):
        _log_write('ERROR', ''.join(traceback.format_exception(exc_type, exc, tb)))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook
    try:
        def _thread_hook(args):
            _log_write('ERROR', ''.join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))

        threading.excepthook = _thread_hook
    except Exception:
        pass


def load_neg_extra_tags():
    if os.path.exists(NEG_EXTRA_TAGS_FILE):
        try:
            with open(NEG_EXTRA_TAGS_FILE, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except Exception:
            pass
    return [
        'bad anatomy', 'extra fingers', 'missing fingers', 'multiple limbs',
        'poorly drawn hands', 'low quality', 'blurry', 'watermark', 'signature',
        'duplicate', 'cloned face', 'jpeg artifacts', 'sepia',
    ]


def save_neg_extra_tags(tags: list):
    with open(NEG_EXTRA_TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)


def load_neg_style_tags():
    if os.path.exists(NEG_STYLE_TAGS_FILE):
        try:
            with open(NEG_STYLE_TAGS_FILE, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_neg_style_tags(tags: list):
    with open(NEG_STYLE_TAGS_FILE, 'w', encoding='utf-8') as f:
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
            with open(EXTRA_TAGS_FILE, 'r', encoding='utf-8-sig') as f:
                return json.load(f).get('tags', [])
        except Exception:
            pass
    return []


def save_extra_tags(tags: list):
    with open(EXTRA_TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'tags': tags}, f, ensure_ascii=False, indent=2)





def migrate_legacy_settings_files(base_dir: str | None = None):
    src_base = os.path.normpath(base_dir) if base_dir else BASE_DIR
    for fn in [
        'pipeline_config.json',
        'extra_tags.json',
        'extra_tags_negative.json',
        'style_tags.json',
        'style_tags_negative.json',
        'ui_options.json',
        'anima_session_last.json',
        'lmstudio_system_prompt.txt',
        'llm_system_prompt.txt',
    ]:
        old_path = os.path.join(src_base, fn)
        new_path = _sf('llm_system_prompt.txt' if 'system_prompt' in fn else fn)
        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)
            print(f'[settings] moved: {fn} -> settings/')

DEFAULT_CONFIG = {
    'llm_platform': '',
    'llm_url': 'http://localhost:1234',
    'llm_token': '',
    'tool_danbooru_rag': True,
    'tool_danbooru_api': True,
    'tool_duckduckgo': True,
    'llm_model': 'qwen/qwen3.5-9b-uncensored-hauhaucs-aggressive',
    'comfyui_url': 'http://127.0.0.1:8188',
    'workflow_json_path': 'workflows/image_anima_preview.json',
    'workflow_file': '',
    'positive_node_id': '11',
    'negative_node_id': '12',
    'comfyui_output_dir': '',
    'clip_node_id': '45',
    'ksampler_node_id': '19',
    'seed_mode': 'random',
    'seed_value': 0,
    'steps': 30,
    'cfg': 4.0,
    'sampler_name': 'er_sde',
    'scheduler': 'simple',
    'output_format': 'png',
    'embed_metadata': True,
    'console_lang': 'ja',
    'log_dir': 'logs',
    'log_retention_days': 30,
    'log_level': 'normal',
    'history_db_path': 'history/history.db',
    'history_thumb_dir': 'history/thumbs',
    'last_scene_preset': '',
    'last_camera_preset': '',
    'last_quality_preset': '',
    'last_lora_preset': '',
    'last_composite_preset': '',
}


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            cfg = DEFAULT_CONFIG.copy()
            with open(CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
                saved = json.load(f)
            migrated = False
            for old_key, new_key in [('lm_studio_url', 'llm_url'), ('lm_studio_token', 'llm_token'), ('lm_studio_model', 'llm_model')]:
                if old_key in saved and new_key not in saved:
                    saved[new_key] = saved.pop(old_key)
                    migrated = True
            for k in ('output_format', 'embed_metadata'):
                if k not in saved:
                    saved[k] = DEFAULT_CONFIG[k]
                    migrated = True
            for k in ('last_scene_preset', 'last_camera_preset', 'last_quality_preset', 'last_lora_preset', 'last_composite_preset'):
                if k not in saved:
                    saved[k] = DEFAULT_CONFIG[k]
                    migrated = True
            cfg.update(saved)
            if str(cfg.get('output_format', 'png')).lower() not in ('png', 'webp'):
                cfg['output_format'] = 'png'
                migrated = True
            else:
                cfg['output_format'] = str(cfg.get('output_format', 'png')).lower()
            cfg['embed_metadata'] = bool(cfg.get('embed_metadata', True))
            if migrated:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
            _apply_log_config(cfg)
            return cfg
        except Exception as e:
            print(f'[設定] 読み込みエラー: {e}')
    cfg = DEFAULT_CONFIG.copy()
    _apply_log_config(cfg)
    return cfg


def save_config(cfg: dict):
    try:
        base = DEFAULT_CONFIG.copy()
        base.update(cfg or {})
        cfg = base
        try:
            cfg['log_retention_days'] = max(0, int(cfg.get('log_retention_days', 30)))
        except Exception:
            cfg['log_retention_days'] = 30
        cfg['output_format'] = str(cfg.get('output_format', 'png')).lower()
        if cfg['output_format'] not in ('png', 'webp'):
            cfg['output_format'] = 'png'
        cfg['embed_metadata'] = bool(cfg.get('embed_metadata', True))
        cfg['log_level'] = 'debug' if str(cfg.get('log_level', 'normal')).lower() == 'debug' else 'normal'
        cfg['log_dir'] = str(cfg.get('log_dir', 'logs') or 'logs').strip() or 'logs'
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        _apply_log_config(cfg)
        print(f'[設定] 保存: {CONFIG_FILE}')
    except Exception as e:
        print(f'[設定] 保存エラー: {e}')


def _console_lang(cfg: dict | None = None) -> str:
    try:
        c = cfg or load_config()
        lang = str(c.get('console_lang', 'ja')).lower()
        return 'en' if lang == 'en' else 'ja'
    except Exception:
        return 'ja'


def _ct(ja: str, en: str, cfg: dict | None = None) -> str:
    return en if _console_lang(cfg) == 'en' else ja


