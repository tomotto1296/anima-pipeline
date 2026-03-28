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
from http.server import ThreadingHTTPServer

UI_PORT = 7860
_base_dir = os.path.dirname(os.path.abspath(__file__))
_settings_dir = os.path.join(_base_dir, 'settings')
_workflows_dir = os.path.join(_base_dir, 'workflows')
os.makedirs(_settings_dir, exist_ok=True)
os.makedirs(_workflows_dir, exist_ok=True)

__version__ = "1.5.16"


def _sf(name):
    return os.path.join(_settings_dir, name)


from core.config import (
    get_active_config_file,
    DEFAULT_CONFIG,
    EXTRA_TAGS_FILE,
    NEG_EXTRA_TAGS_FILE,
    NEG_STYLE_TAGS_FILE,
    STYLE_TAGS_FILE,
    UI_OPTIONS_FILE,
    _ct,
    _install_exception_logging,
    _resolve_log_dir,
    detect_os_ui_lang,
    get_log_file_path,
    load_config,
    load_extra_tags,
    load_neg_extra_tags,
    load_neg_style_tags,
    load_style_tags,
    load_ui_options,
    save_config,
    save_extra_tags,
    save_neg_extra_tags,
    save_neg_style_tags,
    save_style_tags,
)

from core.presets import (
    CHARA_PRESETS_DIR,
    PRESET_CATEGORIES,
    SESSIONS_DIR,
    default_session_name,
    delete_named_session,
    delete_preset,
    list_named_sessions,
    list_presets,
    load_named_session,
    load_preset,
    sanitize_session_name,
    save_named_session,
    save_preset,
)
_FILE_HASH_CACHE = {}
_BASENAME_PATH_CACHE = {}

from core.history import (
    _ensure_history_db,
    _resolve_history_db_path,
    _resolve_image_path_with_webp_fallback,
    _save_history_record,
)

from core.bootstrap import prepare_bootstrap


from core.llm import (
    load_preset_gen_prompt,
    load_system_prompt,
    make_call_llm,
)

from core.comfyui import (
    _build_parameters_text,
    extract_positive_prompt,
    send_to_comfyui,
    watch_and_postprocess,
)

from core.frontend import load_html_template

HTML = load_html_template()

from core.handlers import build_handler
from core.runtime import configure_console_utf8, init_runtime_context, print_startup_banner, run_server_forever

Handler = None


def _set_lm_session(session):
    h = globals().get("Handler")
    if h is not None:
        setattr(h, "lm_session", session)


call_llm = make_call_llm(_set_lm_session)
Handler = build_handler(globals())


def main():
    prepare_bootstrap(_base_dir, _settings_dir, DEFAULT_CONFIG)
    configure_console_utf8()
    _install_exception_logging()
    # Console block from "[接続確認]" downward should follow OS language.
    cfg, _os_cfg = init_runtime_context(
        load_config,
        _ensure_history_db,
        detect_os_ui_lang,
    )
    print_startup_banner(
        cfg,
        version=__version__,
        ui_port=UI_PORT,
        config_file=get_active_config_file(),
        ct=_ct,
        os_cfg=_os_cfg,
    )
    run_server_forever(
        ThreadingHTTPServer,
        Handler,
        '0.0.0.0',
        UI_PORT,
        ct=_ct,
        os_cfg=_os_cfg,
    )


if __name__ == '__main__':
    main()



























































































