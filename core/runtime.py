import sys
import requests


def check_server(name, url, path='/', cfg=None, ct=None):
    try:
        requests.get(url + path, timeout=3)
        ok = ct('\u63a5\u7d9aOK', 'Connected', cfg) if ct else 'Connected'
        print(f"  ✓ {name}: {ok} ({url})")
    except Exception as e:
        ng = ct('\u63a5\u7d9a\u5931\u6557', 'Connection failed', cfg) if ct else 'Connection failed'
        print(f"  ✗ {name}: {ng} ({url}) -> {e}")


def print_startup_banner(cfg, *, version, ui_port, config_file, ct=None, os_cfg=None):
    tr = ct if callable(ct) else (lambda ja, en, _cfg=None: en)
    lang_cfg = os_cfg or {}
    print('=' * 55)
    print(f'  Anima Pipeline  v{version}')
    print('=' * 55)
    print(f"\n[{tr('\u63a5\u7d9a\u78ba\u8a8d', 'Connection Check', lang_cfg)}]")
    check_server('LLM', cfg['llm_url'], '/api/v1/models', lang_cfg, tr)
    check_server('ComfyUI  ', cfg['comfyui_url'], '/system_stats', lang_cfg, tr)
    print()
    print(f'  UI:           http://localhost:{ui_port}')
    print(f"  LM Studio:    {cfg['llm_url']}")
    print(f"  {tr('\u30e2\u30c7\u30eb', 'Model', lang_cfg)}:       {cfg['llm_model']}")
    print(f"  ComfyUI:      {cfg['comfyui_url']}")
    print(f"  {tr('\u30ef\u30fc\u30af\u30d5\u30ed\u30fc', 'Workflow', lang_cfg)}: {cfg.get('workflow_json_path', tr('\u672a\u8a2d\u5b9a','Unset', lang_cfg))}")
    print(f"  {tr('\u8a2d\u5b9a\u30d5\u30a1\u30a4\u30eb', 'Config File', lang_cfg)}: {config_file}")
    print('=' * 55)
    print(f"\n{tr('Ctrl+C \u3067\u505c\u6b62', 'Press Ctrl+C to stop', lang_cfg)}\n")


def configure_console_utf8():
    # Avoid mojibake in launcher/captured consoles.
    for stream_name in ('stdout', 'stderr'):
        st = getattr(sys, stream_name, None)
        if st and hasattr(st, 'reconfigure'):
            try:
                st.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass


def init_runtime_context(load_config_fn, ensure_history_db_fn, detect_os_ui_lang_fn):
    cfg = load_config_fn()
    try:
        ensure_history_db_fn(cfg)
    except Exception as e:
        print(f"[OUTPUT-3] DB init error: {e}")
    os_cfg = {'console_lang': detect_os_ui_lang_fn()}
    return cfg, os_cfg


def run_server_forever(server_cls, handler_cls, host, port, *, ct=None, os_cfg=None):
    tr = ct if callable(ct) else (lambda ja, en, _cfg=None: en)
    lang_cfg = os_cfg or {}
    server = server_cls((host, port), handler_cls)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{tr('\u505c\u6b62\u3057\u307e\u3057\u305f\u3002', 'Stopped.', lang_cfg)}")
