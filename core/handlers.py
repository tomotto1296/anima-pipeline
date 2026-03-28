from http.server import BaseHTTPRequestHandler


def build_handler(context: dict):
    # Inject main-module symbols so moved handler can keep existing references.
    for k, v in (context or {}).items():
        globals()[k] = v

    class Handler(BaseHTTPRequestHandler):
        cancel_event = __import__('threading').Event()
        lm_session = None
        history_pending = {}
        history_saved_paths = set()
        history_lock = threading.Lock()
        def log_message(self,fmt,*args):pass

        def _send_bytes(self, data: bytes, mime: str, cache_control: str | None = None, extra_headers: dict | None = None):
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            if cache_control:
                self.send_header('Cache-Control', cache_control)
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, payload, code: int = 200):
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _serve_file(self, file_path: str, mime: str | None = None, cache_control: str | None = None) -> bool:
            if not os.path.isfile(file_path):
                self.send_response(404)
                self.end_headers()
                return False
            with open(file_path, 'rb') as f:
                data = f.read()
            if not mime:
                import mimetypes
                mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            self._send_bytes(data, mime, cache_control=cache_control)
            return True

        def _serve_static_from_root(self, req_path: str, prefix: str, root_dir: str, cache_control: str = 'public, max-age=3600') -> bool:
            rel = req_path[len(prefix):]
            if not rel:
                self.send_response(404)
                self.end_headers()
                return False
            root_real = os.path.realpath(root_dir)
            target = os.path.realpath(os.path.normpath(os.path.join(root_real, rel)))
            if not (target == root_real or target.startswith(root_real + os.sep)):
                self.send_response(403)
                self.end_headers()
                return False
            return self._serve_file(target, cache_control=cache_control)

        def _qs_int(self, qs: dict, key: str, default: int, min_value: int | None = None, max_value: int | None = None) -> int:
            try:
                value = int((qs.get(key, [str(default)])[0] or str(default)))
            except Exception:
                value = default
            if min_value is not None:
                value = max(min_value, value)
            if max_value is not None:
                value = min(max_value, value)
            return value

        def _parse_request_path_qs(self) -> tuple[str, dict]:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            req_path = parsed.path
            req_qs = parse_qs(parsed.query, keep_blank_values=True)
            return req_path, req_qs
        def _lora_favorites_path(self) -> str:
            return _sf('lora_favorites.json')
        def _load_lora_favorites(self) -> list[str]:
            fp = self._lora_favorites_path()
            if not os.path.exists(fp):
                return []
            try:
                with open(fp, 'r', encoding='utf-8-sig') as f:
                    raw = json.load(f)
            except Exception:
                return []
            if not isinstance(raw, list):
                return []
            out = []
            seen = set()
            for name in raw:
                n = str(name or '').strip()
                if not n or n in seen:
                    continue
                seen.add(n)
                out.append(n)
            return out
        def _save_lora_favorites(self, favorites: list[str]):
            fp = self._lora_favorites_path()
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, 'w', encoding='utf-8') as f:
                json.dump(favorites if isinstance(favorites, list) else [], f, ensure_ascii=False, indent=2)
        def _resolve_workflow_path_for_diagnostics(self, cfg: dict) -> str:
            wf_file = str(cfg.get('workflow_file', '') or '').strip()
            if wf_file:
                cand = os.path.normpath(os.path.join(_workflows_dir, wf_file))
                if os.path.isfile(cand):
                    return cand
            wf_path = str(cfg.get('workflow_json_path', '') or '').strip()
            if not wf_path:
                return ''
            if not os.path.isabs(wf_path):
                # Keep compatibility with both "workflows/foo.json" and "foo.json" styles.
                cand_base = os.path.normpath(os.path.join(_base_dir, wf_path))
                if os.path.isfile(cand_base):
                    return cand_base
                cand_workflows = os.path.normpath(os.path.join(_workflows_dir, wf_path))
                if os.path.isfile(cand_workflows):
                    return cand_workflows
                wf_path = cand_base
            return os.path.normpath(wf_path)
        def _collect_workflow_node_info(self, workflow_obj) -> tuple[set[str], int]:
            ids = set()
            lora_count = 0
            def add_node(node_id, node_type):
                nonlocal lora_count
                if node_id is None:
                    return
                ids.add(str(node_id))
                if str(node_type or '').lower() == 'loraloader':
                    lora_count += 1
            if isinstance(workflow_obj, dict):
                if isinstance(workflow_obj.get('nodes'), list):
                    for node in workflow_obj.get('nodes', []):
                        if not isinstance(node, dict):
                            continue
                        add_node(node.get('id'), node.get('type'))
                elif isinstance(workflow_obj.get('prompt'), dict):
                    for nid, node in workflow_obj.get('prompt', {}).items():
                        if not isinstance(node, dict):
                            continue
                        add_node(nid, node.get('class_type') or node.get('type'))
                else:
                    for nid, node in workflow_obj.items():
                        if not isinstance(node, dict):
                            continue
                        add_node(nid, node.get('class_type') or node.get('type'))
            return ids, lora_count
        def _build_diagnostics_results(self, cfg: dict) -> list[dict]:
            import urllib.request as _ureq

            results = []

            def add_result(key, label, level, message, hint=''):
                item = {
                    'key': key,
                    'label': label,
                    'label_en': label,
                    'level': level,
                    'message': message,
                    'message_en': message,
                }
                if hint:
                    item['hint'] = hint
                    item['hint_en'] = hint
                results.append(item)

            comfy = str(cfg.get('comfyui_url', 'http://127.0.0.1:8188') or '').rstrip('/')
            try:
                with _ureq.urlopen(comfy + '/system_stats', timeout=5) as r:
                    stats = json.loads(r.read())
                pyver = str(stats.get('system', {}).get('python_version', '?'))
                add_result('comfyui', 'ComfyUI Connection', 'ok', f'Connected (Python {pyver})')
            except Exception as e:
                add_result('comfyui', 'ComfyUI Connection', 'error', f'Connection failed: {e}', 'Check that ComfyUI is running and URL is correct')

            llm_platform = str(cfg.get('llm_platform', '') or '').strip()
            llm_url = str(cfg.get('llm_url', '') or '').strip().rstrip('/')
            llm_token = str(cfg.get('llm_token', '') or '').strip()
            llm_default_url = str(DEFAULT_CONFIG.get('llm_url', 'http://localhost:1234') or '').strip().rstrip('/')
            llm_unset = (not llm_platform) and (not llm_token) and (not llm_url or llm_url == llm_default_url)

            if llm_unset:
                add_result('llm', 'LLM Connection', 'skip', 'Skipped (not configured)')
            elif not llm_url:
                add_result('llm', 'LLM Connection', 'error', 'LLM URL is not configured', 'Set the LLM URL in settings')
            else:
                try:
                    if llm_platform == 'gemini':
                        test_url = llm_url + '/models'
                    else:
                        base = llm_url.removesuffix('/v1')
                        test_url = base + '/v1/models'
                    headers = {'Content-Type': 'application/json'}
                    if llm_token:
                        headers['Authorization'] = f'Bearer {llm_token}'
                    req = _ureq.Request(test_url, headers=headers)
                    with _ureq.urlopen(req, timeout=5) as r:
                        r.read()
                    disp = llm_platform or 'Custom'
                    add_result('llm', 'LLM Connection', 'ok', f'Connected ({disp})')
                except Exception as e:
                    add_result('llm', 'LLM Connection', 'error', f'Connection failed: {e}', 'Check LLM URL, token, and model settings')

            workflow_path = self._resolve_workflow_path_for_diagnostics(cfg)
            workflow_obj = None
            workflow_ok = False
            if not workflow_path:
                add_result('workflow', 'Workflow JSON', 'error', 'Path is not configured', 'Check workflow JSON path in settings')
            elif not os.path.isfile(workflow_path):
                add_result('workflow', 'Workflow JSON', 'error', f'Not found: {workflow_path}', 'Check that the file path is correct')
            else:
                try:
                    with open(workflow_path, 'r', encoding='utf-8') as f:
                        workflow_obj = json.load(f)
                    workflow_ok = True
                    add_result('workflow', 'Workflow JSON', 'ok', 'Loaded successfully')
                except Exception as e:
                    add_result('workflow', 'Workflow JSON', 'error', f'Failed to parse: {e}', 'Check JSON format and file contents')

            node_ids, lora_nodes = self._collect_workflow_node_info(workflow_obj if workflow_ok else {})

            def check_node(cfg_key: str, key: str, label: str):
                raw_id = str(cfg.get(cfg_key, '') or '').strip()
                if not raw_id:
                    add_result(key, label, 'error', 'Not configured', 'Set the Node ID in settings')
                    return
                if not workflow_ok:
                    add_result(key, label, 'error', f'Cannot verify (configured: {raw_id})', 'Fix workflow JSON error first')
                    return
                if raw_id in node_ids:
                    add_result(key, label, 'ok', f'Found ({raw_id})')
                else:
                    add_result(key, label, 'error', f'Not found ({raw_id})', 'Make setting value match the workflow node ID')

            check_node('positive_node_id', 'pos_node', 'Positive Node ID')
            check_node('negative_node_id', 'neg_node', 'Negative Node ID')
            check_node('ksampler_node_id', 'ksampler', 'KSampler Node ID')

            expected_lora_slots = 4
            if not workflow_ok:
                add_result('lora_nodes', 'LoRA Nodes', 'error', 'Cannot verify', 'Fix workflow JSON error first')
            elif lora_nodes >= expected_lora_slots:
                add_result('lora_nodes', 'LoRA Nodes', 'ok', f'OK (LoraLoader: {lora_nodes})')
            elif lora_nodes > 0:
                add_result('lora_nodes', 'LoRA Nodes', 'warning', f'Potential shortage (LoraLoader: {lora_nodes}, recommended: {expected_lora_slots})', 'Use a LoRA x4-compatible workflow')
            else:
                add_result('lora_nodes', 'LoRA Nodes', 'warning', 'LoraLoader not found', 'Use a LoRA-capable workflow or adjust settings')

            output_format = str(cfg.get('output_format', 'png') or 'png').lower()
            output_dir = str(cfg.get('comfyui_output_dir', '') or '').strip()
            if output_format != 'webp':
                add_result('output_dir', 'Output Directory', 'skip', 'Not required in PNG mode')
            elif not output_dir:
                add_result('output_dir', 'Output Directory', 'warning', 'Not configured', 'Set ComfyUI output folder when using WebP conversion')
            elif not os.path.isdir(output_dir):
                add_result('output_dir', 'Output Directory', 'warning', f'Directory does not exist: {output_dir}', 'Check that the directory path is correct')
            else:
                add_result('output_dir', 'Output Directory', 'ok', 'Configured')

            return results

        def _handle_get_early_routes(self, req_path: str, req_qs: dict, unquote_fn) -> bool:
            if req_path.startswith('/presets/'):
                parts = [p for p in req_path.split('/') if p]
                payload = {"status": "error", "error": "Unknown preset category"}
                code = 200
                try:
                    if len(parts) == 2:
                        category = parts[1]
                        payload = {"presets": list_presets(category), "status": "ok"}
                    elif len(parts) == 3:
                        category = parts[1]
                        name = unquote_fn(parts[2])
                        payload = load_preset(category, name)
                    else:
                        code = 400
                        payload = {"status": "error", "error": "Invalid presets endpoint"}
                except FileNotFoundError:
                    payload = {"status": "error", "error": "Preset not found"}
                except ValueError as e:
                    payload = {"status": "error", "error": str(e)}
                except json.JSONDecodeError:
                    payload = {"status": "error", "error": "Preset file is corrupted"}
                except Exception as e:
                    payload = {"status": "error", "error": str(e)}
                self._send_json(payload, code=code)
                return True

            if req_path == '/chara_list':
                try:
                    payload = {"presets": list_presets("chara"), "status": "ok"}
                except Exception as e:
                    payload = {"presets": [], "status": "error", "error": str(e)}
                self._send_json(payload)
                return True

            if req_path == '/chara_load':
                name = str(req_qs.get("name", [""])[0] or "").strip()
                try:
                    payload = load_preset("chara", name)
                except FileNotFoundError:
                    payload = {"status": "error", "error": "Preset not found"}
                except Exception as e:
                    payload = {"status": "error", "error": str(e)}
                self._send_json(payload)
                return True

            if req_path == '/manifest.json':
                manifest_candidates = [
                    os.path.join(_base_dir, 'manifest.json'),
                    os.path.join(_base_dir, 'docs', 'manifest.json'),
                ]
                manifest_fp = next((fp for fp in manifest_candidates if os.path.isfile(fp)), None)
                if not manifest_fp:
                    self.send_response(404)
                    self.end_headers()
                    return True
                self._serve_file(manifest_fp, mime='application/manifest+json', cache_control='public, max-age=3600')
                return True

            if req_path in ('/favicon.ico', '/favicon-light.ico', '/favicon-dark.ico'):
                if req_path == '/favicon-dark.ico':
                    icon_fp = os.path.join(_base_dir, 'assets', 'icons', 'favicon-dark.ico')
                else:
                    icon_fp = os.path.join(_base_dir, 'assets', 'icons', 'favicon-light.ico')
                self._serve_file(icon_fp, mime='image/x-icon', cache_control='public, max-age=3600')
                return True

            if req_path.startswith('/assets/'):
                self._serve_static_from_root(req_path, '/assets/', os.path.join(_base_dir, 'assets'))
                return True

            if req_path.startswith('/frontend/'):
                self._serve_static_from_root(req_path, '/frontend/', os.path.join(_base_dir, 'frontend'))
                return True

            return False

        def _handle_get_poll_status(self, req_qs: dict, unquote_fn):
            import urllib.request as _ureq
            ids_raw = req_qs.get('ids', [''])[0]
            ids = unquote_fn(ids_raw).split(',')
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
                        outputs = hist[pid].get('outputs', {})
                        for nid, out in outputs.items():
                            imgs = out.get('images', [])
                            if imgs:
                                output_dir = cfg.get('comfyui_output_dir','').strip()
                                if not output_dir:
                                    wf_path = cfg.get('workflow_json_path','')
                                    if wf_path and not os.path.isabs(wf_path):
                                        wf_path = os.path.join(_base_dir, wf_path)
                                    wf_path = wf_path.replace(os.sep,'/')
                                    parts = wf_path.split('/')
                                    for i,pn in enumerate(parts):
                                        if pn.lower()=='comfyui':
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
            except Exception:
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
            self._send_json({'completed':completed,'total':len(ids),'queue':queue_info,'image_paths':image_paths})

        def _handle_get_info_routes(self, req_path: str, req_qs: dict) -> bool:
            if self.path=='/':
                self.send_response(200)
                self.send_header('Content-Type','text/html; charset=utf-8')
                self.end_headers()
                ui_opts = load_ui_options()
                os_lang = detect_os_ui_lang()
                injected = HTML.replace(
                    '<script>',
                    '<script>\nconst __OPT__ = ' + json.dumps(ui_opts, ensure_ascii=False) + ';\nconst __APP_VERSION__ = ' + json.dumps(__version__) + ';\nconst __OS_LANG__ = ' + json.dumps(os_lang) + ';\n',
                    1  # ???<script>????
                )
                self.wfile.write(injected.encode('utf-8'))
                return True

            if req_path == '/config':
                self._send_json(load_config())
                return True

            if self.path=='/logs_info':
                cfg = load_config()
                info = {
                    'log_dir': _resolve_log_dir(cfg),
                    'log_file': get_log_file_path(),
                    'log_level': cfg.get('log_level', 'normal'),
                    'log_retention_days': int(cfg.get('log_retention_days', 30) or 30),
                }
                self._send_json(info)
                return True

            if self.path=='/logs_zip':
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
                return True

            if req_path.startswith('/test_connection'):
                import urllib.request as _ureq
                target = req_qs.get('target',[''])[0]
                cfg = load_config()
                result = {'ok': False, 'message': '????????'}
                if target == 'comfyui':
                    comfy = cfg.get('comfyui_url','http://127.0.0.1:8188').rstrip('/')
                    try:
                        with _ureq.urlopen(comfy+'/system_stats', timeout=5) as r:
                            stats = json.loads(r.read())
                        python_ver = stats.get('system',{}).get('python_version','?')
                        result = {'ok': True, 'message': f'ComfyUI ??OK (Python {python_ver})'}
                    except Exception as e:
                        result = {'ok': False, 'message': f'ComfyUI ????: {e}'}
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
                self._send_json(result)
                return True

            return False

        def _handle_get_history_routes(self, req_path: str, req_qs: dict) -> bool:
            if req_path.startswith('/history_list'):
                qs = req_qs
                page = self._qs_int(qs, 'page', 1, min_value=1)
                per_page = self._qs_int(qs, 'per_page', 20, min_value=1, max_value=100)
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
                self._send_json(payload)
                return True

            if req_path.startswith('/history_detail'):
                qs = req_qs
                history_id = self._qs_int(qs, 'id', 0, min_value=0)
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
                self._send_json(payload)
                return True

            return False

        def _handle_get_image_route(self, req_qs: dict) -> bool:
            img_path = req_qs.get('path', [''])[0].strip().replace('/', os.sep)
            if not img_path:
                self.send_response(404)
                self.end_headers()
                return True

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
                return True

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
                    if size1 > 0 and size1 == size2 and len(buf) == size1:
                        data = buf
                        break
                except Exception:
                    pass
                _time.sleep(0.06)
            if not data:
                self.send_response(503)
                self.end_headers()
                return True
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.end_headers()
            self.wfile.write(data)
            return True

        def _handle_chara_thumb_route(self, req_qs: dict, unquote_fn) -> bool:
            fn = unquote_fn(req_qs.get('file', [''])[0]).strip()
            if (not fn) or (os.path.basename(fn) != fn) or (not fn.endswith('.json')):
                self.send_response(404)
                self.end_headers()
                return True
            thumb_path = os.path.join(CHARA_PRESETS_DIR, os.path.splitext(fn)[0] + '.webp')
            if not os.path.exists(thumb_path):
                self.send_response(404)
                self.end_headers()
                return True
            with open(thumb_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'image/webp')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return True

        def _handle_get_poll_route(self, req_path: str, req_qs: dict, unquote_fn) -> bool:
            if req_path != '/poll_status':
                return False
            self._handle_get_poll_status(req_qs, unquote_fn)
            return True
        def _handle_get_session_route(self, req_path: str) -> bool:
            if req_path != '/session':
                return False
            sf = _sf('anima_session_last.json')
            data = {}
            if os.path.exists(sf):
                with open(sf, encoding='utf-8') as f:
                    data = json.load(f)
            self._send_json(data)
            return True

        def _extract_named_session_name(self, req_path: str) -> str:
            from urllib.parse import unquote
            prefix = '/sessions/'
            if not req_path.startswith(prefix):
                return ''
            raw_name = req_path[len(prefix):]
            if (not raw_name) or ('/' in raw_name):
                return ''
            return unquote(raw_name)

        def _handle_get_named_sessions_route(self, req_path: str) -> bool:
            if req_path == '/sessions':
                try:
                    self._send_json({'status': 'ok', 'sessions': list_named_sessions()})
                except Exception as e:
                    self._send_json({'status': 'error', 'error': str(e), 'sessions': []}, code=500)
                return True

            name = self._extract_named_session_name(req_path)
            if not name:
                return False

            try:
                self._send_json(load_named_session(name))
            except FileNotFoundError:
                self._send_json({'status': 'error', 'error': 'Session not found'}, code=404)
            except json.JSONDecodeError:
                self._send_json({'status': 'error', 'error': 'Session file is corrupted'}, code=500)
            except ValueError as e:
                self._send_json({'status': 'error', 'error': str(e)}, code=400)
            except Exception as e:
                self._send_json({'status': 'error', 'error': str(e)}, code=500)
            return True

        def _handle_get_chara_presets_route(self, req_path: str) -> bool:
            if req_path != '/chara_presets':
                return False
            presets = []
            if os.path.exists(CHARA_PRESETS_DIR):
                for fn in sorted(os.listdir(CHARA_PRESETS_DIR)):
                    if fn.endswith('.json'):
                        try:
                            with open(os.path.join(CHARA_PRESETS_DIR, fn), 'r', encoding='utf-8-sig') as f:
                                p = json.load(f)
                            p['_filename'] = fn
                            thumb_fn = os.path.splitext(fn)[0] + '.webp'
                            thumb_path = os.path.join(CHARA_PRESETS_DIR, thumb_fn)
                            if os.path.exists(thumb_path):
                                p['_thumb_path'] = thumb_path.replace('\\', '/')
                            presets.append(p)
                        except Exception:
                            pass
            self._send_json(presets)
            return True
        def _handle_get_generate_preset_route(self, req_path: str, req_qs: dict) -> bool:
            if req_path != '/generate_preset':
                return False

            chara_name = req_qs.get('name',[''])[0].strip()
            chara_name_en = req_qs.get('name_en',[''])[0].strip()
            chara_series = req_qs.get('series',[''])[0].strip()
            chara_series_en = req_qs.get('series_en',[''])[0].strip()
            if not chara_name:
                self._send_json({'error':'キャラ名が必要です'}, code=400)
                return True

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

            def _fallback_ascii_tag(text: str) -> str:
                import re as _re_tag
                s = str(text or '').strip().lower().replace('\u3000', ' ').replace('\u30fb', ' ')
                s = _re_tag.sub(r'\s+', '_', s)
                s = _re_tag.sub(r'[^a-z0-9_()]+', '_', s)
                s = _re_tag.sub(r'_+', '_', s).strip('_')
                return s

            def _lookup_danbooru_tag(text: str) -> str:
                q = str(text or '').strip()
                if not q:
                    return ''
                from urllib.parse import quote
                candidates = [q, q.replace(' ', '_')]
                for cand in candidates:
                    try:
                        url = 'https://danbooru.donmai.us/tags.json?search[name_matches]='+quote(cand)+'*&search[order]=count&limit=10'
                        req = _ureq.Request(url, headers={'User-Agent':'anima-pipeline/1.0'})
                        with _ureq.urlopen(req, timeout=8) as r:
                            arr = json.loads(r.read())
                        if isinstance(arr, list) and arr:
                            best = max(arr, key=lambda x: int((x or {}).get('post_count', 0) or 0))
                            nm = str((best or {}).get('name', '') or '').strip()
                            if _is_plausible_tag(nm):
                                return nm
                    except Exception:
                        pass
                return ''

            def _is_plausible_tag(tag: str) -> bool:
                s = str(tag or '').strip().lower()
                if not s:
                    return False
                if len(s) > 48:
                    return False
                if s.count('_') > 5:
                    return False
                banned_exact = {
                    'no_think', 'nothink', 'think', 'json', 'output', 'tag', 'english', 'japanese',
                }
                if s in banned_exact:
                    return False
                banned_fragments = (
                    'the_user', 'wants', 'convert', 'danbooru', 'style', 'series_name', 'character_name',
                    'one_tag', 'lower_snake_case', 'code_fence', 'explanation',
                )
                if any(f in s for f in banned_fragments):
                    return False
                # Must include ASCII letters; avoid Japanese string fallback.
                if not re.search(r'[a-z]', s):
                    return False
                return True


            def _infer_en_tag_with_llm(text: str, kind: str) -> str:
                src = str(text or '').strip()
                if not src:
                    return ''
                try:
                    import re as _re_llm
                    q = (
                        f'Convert Japanese {kind} name to one Danbooru-style English tag.\n'
                        'Return only one tag in lower_snake_case. No code fences, no explanation.\n'
                        f'Input: {src}'
                    )
                    raw = str(call_llm(q, cfg) or '').strip()
                    raw = _re_llm.sub(r'```[a-z]*|```', '', raw).strip()
                    candidates = []
                    for line in raw.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        for chunk in line.split(','):
                            c = chunk.strip().lower().replace(' ', '_').strip("`\"'./")
                            c = _re_llm.sub(r'[^a-z0-9_()]+', '', c)
                            if c:
                                candidates.append(c)
                    for out in candidates:
                        if _is_plausible_tag(out) and any(ch.isalpha() for ch in out):
                            return out
                except Exception:
                    pass
                return ''


            inferred_name_en = (
                chara_name_en
                or _lookup_danbooru_tag(chara_name)
                or _infer_en_tag_with_llm(chara_name, 'character')
                or _fallback_ascii_tag(chara_name)
            )
            inferred_series_en = (
                chara_series_en
                or _lookup_danbooru_tag(chara_series)
                or _infer_en_tag_with_llm(chara_series, 'series')
                or _fallback_ascii_tag(chara_series)
            )
            def _normalize_en_name_series(name_tag: str, series_tag: str) -> tuple[str, str]:
                n = str(name_tag or '').strip().lower()
                s = str(series_tag or '').strip().lower()

                # series aliases sometimes come as fate_(series)
                ms = re.match(r'^([a-z0-9_]+)_\(series\)$', s)
                if ms:
                    s = ms.group(1)

                # character tags can come as name_(series); split for UI fields
                mn = re.match(r'^([a-z0-9_]+)_\(([^()]+)\)$', n)
                if mn:
                    n_base = mn.group(1)
                    n_series = mn.group(2)
                    n = n_base
                    if not s and _is_plausible_tag(n_series):
                        s = n_series

                if not _is_plausible_tag(n):
                    n = ''
                if s and not _is_plausible_tag(s):
                    s = ''
                return n, s

            inferred_name_en, inferred_series_en = _normalize_en_name_series(inferred_name_en, inferred_series_en)
            _tpl = load_preset_gen_prompt()
            preset_prompt = _tpl.replace('{chara_name}', chara_name).replace('{chara_series}', chara_series or 'unknown').replace('{wiki_text}', wiki_text or 'Not found. Use your training knowledge.')
            try:
                result_json = ''
                for attempt in range(2):
                    try:
                        result_json = call_llm(preset_prompt, cfg)
                    except Exception as e:
                        # Retry once when model returns no content-like response.
                        emsg = str(e or '')
                        if attempt == 0 and ('finish_reason' in emsg or 'content' in emsg.lower()):
                            print('[preset_gen] empty/invalid LLM response; retrying once (1/1)')
                            continue
                        raise
                    if str(result_json or '').strip():
                        break
                    if attempt == 0:
                        print('[preset_gen] empty LLM response; retrying once (1/1)')
                if not str(result_json or '').strip():
                    raise ValueError('LLM returned empty content for preset generation')
                import re as _re
                result_json = _re.sub(r'`[a-z]*','',result_json).strip().strip('').strip()
                preset_data = json.loads(result_json)
                preset_display_name = chara_name
                if chara_name and inferred_name_en and chara_name.lower() != inferred_name_en.lower():
                    preset_display_name = f'{chara_name}（{inferred_name_en}）'
                elif inferred_name_en and not chara_name:
                    preset_display_name = inferred_name_en

                preset = {
                    'name': preset_display_name,
                    'data': {
                        'name': chara_name,
                        'name_en': inferred_name_en,
                        'series': chara_series,
                        'series_en': inferred_series_en,
                        'gender': preset_data.get('gender','female'),
                        'age': preset_data.get('age','adult'),
                        'original': False,
                        'hairstyle': preset_data.get('hairstyle',''),
                        'hairstyle_lm': '',
                        'haircolor': preset_data.get('haircolor',''),
                        'eyes': preset_data.get('eyes',''),
                        'skin': preset_data.get('skin',''),
                        'bust': preset_data.get('bust',''),
                        'outfit': '',
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
                safe_name = preset_display_name.replace('/','_').replace('\\','_')[:30]
                filename = '{:03d}_{}'.format(n, safe_name)
                with open(os.path.join(CHARA_PRESETS_DIR, filename),'w',encoding='utf-8') as f:
                    json.dump(preset, f, ensure_ascii=False, indent=2)
                preset['_filename'] = filename
                print('[プリセット生成] 保存: '+filename)
                self._send_json({'ok':True,'preset':preset})
            except Exception as e:
                print('[プリセット生成] エラー: '+str(e))
                self._send_json({'error':str(e)}, code=500)
            return True

        def do_GET(self):
            from urllib.parse import unquote
            req_path, req_qs = self._parse_request_path_qs()

            if self._handle_get_early_routes(req_path, req_qs, unquote):
                return

            if self._handle_get_info_routes(req_path, req_qs):
                return

            if req_path == '/poll_status':
                self._handle_get_poll_status(req_qs, unquote)
                return

            if self._handle_get_session_route(req_path):
                return

            if self._handle_get_named_sessions_route(req_path):
                return

            if self._handle_get_history_routes(req_path, req_qs):
                return

            if self._handle_get_generate_preset_route(req_path, req_qs):
                return

            if self._handle_get_chara_presets_route(req_path):
                return

            if self._handle_get_misc_routes(req_path, req_qs, unquote):
                return

            if self._handle_get_terminal_image_routes(req_path, req_qs, unquote):
                return

            self.send_response(404)
            self.end_headers()

        def _handle_get_misc_routes(self, req_path: str, req_qs: dict, unquote_fn) -> bool:
            if req_path == '/diagnostics':
                cfg = load_config()
                results = self._build_diagnostics_results(cfg)
                errors = sum(1 for r in results if r.get('level') == 'error')
                warnings = sum(1 for r in results if r.get('level') == 'warning')
                status = 'ok' if errors == 0 else 'error'
                self._send_json({
                    'status': status,
                    'results': results,
                    'summary': {'errors': errors, 'warnings': warnings},
                })
                return True

            if req_path == '/lora_list':
                import urllib.request as _ureq
                cfg2 = load_config()
                comfy = cfg2.get('comfyui_url','http://127.0.0.1:8188').rstrip('/')
                loras = []
                try:
                    with _ureq.urlopen(comfy+'/object_info/LoraLoader', timeout=5) as r:
                        info = json.loads(r.read())
                    lora_name_field = info.get('LoraLoader',{}).get('input',{}).get('required',{}).get('lora_name')
                    print(f'[lora_list] lora_name_field type={type(lora_name_field)} len={len(lora_name_field) if lora_name_field else 0}')
                    if isinstance(lora_name_field, list) and len(lora_name_field) > 0:
                        first = lora_name_field[0]
                        if isinstance(first, list):
                            loras = first
                        else:
                            loras = lora_name_field
                    print(f'[lora_list] got {len(loras)} loras')
                except Exception as e:
                    print(f'[lora_list] error: {e}')
                self._send_json({'loras': loras})
                return True

            if req_path == '/lora_favorites':
                self._send_json({'status': 'ok', 'favorites': self._load_lora_favorites()})
                return True

            if req_path == '/workflows':
                files = []
                try:
                    for f in sorted(os.listdir(_workflows_dir)):
                        if f.lower().endswith('.json'):
                            files.append(f)
                except Exception:
                    pass
                self._send_json({'files': files})
                return True

            if req_path == '/version':
                self._send_json({'version': __version__})
                return True

            if req_path == '/extra_tags':
                self._send_json({"tags":load_extra_tags()})
                return True

            if req_path == '/style_tags':
                self._send_json({"tags":load_style_tags()})
                return True

            if req_path == '/neg_extra_tags':
                import os as _os
                _is_default = not _os.path.exists(NEG_EXTRA_TAGS_FILE)
                self._send_json({"tags":load_neg_extra_tags(),"is_default":_is_default})
                return True

            if req_path == '/neg_style_tags':
                self._send_json({"tags":load_neg_style_tags()})
                return True

            if req_path == '/lora_thumbnail':
                lora_name = unquote_fn(req_qs.get('name', [''])[0])
                cfg2 = load_config()
                lora_path = lora_name.replace('\\', '/').replace('\\\\', '/')
                if '/' in lora_path:
                    subfolder, fname = lora_path.rsplit('/', 1)
                else:
                    subfolder, fname = '', lora_path
                base = fname.rsplit('.', 1)[0] if '.' in fname else fname

                lora_roots = []
                comfyui_output = cfg2.get('comfyui_output_dir', '')
                if comfyui_output:
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
                        for ext in ['jpg', 'jpeg', 'png', 'webp']:
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
                return True

            if req_path == '/open_folder':
                url_or_path = unquote_fn(req_qs.get('path',[''])[0].strip())
                folder_path = ''
                if '/view?' in url_or_path or url_or_path.startswith('http'):
                    cfg2 = load_config()
                    output_dir = cfg2.get('comfyui_output_dir','').strip()
                    if not output_dir:
                        wf_path = cfg2.get('workflow_json_path','')
                        if wf_path and not os.path.isabs(wf_path):
                            wf_path = os.path.join(_base_dir, wf_path)
                        parts = wf_path.replace(os.sep,'/').split('/')
                        for i, p in enumerate(parts):
                            if p.lower() == 'comfyui':
                                output_dir = os.path.normpath('/'.join(parts[:i+1]) + '/output')
                                break
                    try:
                        from urllib.parse import parse_qs, urlparse
                        vqs = parse_qs(urlparse(url_or_path).query)
                        subfolder = unquote_fn(vqs.get('subfolder',[''])[0])
                        folder_path = os.path.normpath(os.path.join(output_dir, subfolder)) if subfolder else os.path.normpath(output_dir)
                    except Exception:
                        folder_path = os.path.normpath(output_dir) if output_dir else ''
                else:
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
                self._send_json(result)
                return True

            return False

        def _handle_get_terminal_image_routes(self, req_path: str, req_qs: dict, unquote_fn) -> bool:
            if req_path == '/get_image':
                self._handle_get_image_route(req_qs)
                return True

            if req_path == '/chara_thumb':
                self._handle_chara_thumb_route(req_qs, unquote_fn)
                return True

            return False

        def _handle_post_preset_routes(self, req_path: str, body: dict, unquote_fn) -> bool:
            if req_path.startswith('/presets/'):
                parts = [p for p in req_path.split('/') if p]
                payload = {"status": "error", "error": "Invalid presets endpoint"}
                code = 200
                try:
                    if len(parts) != 3:
                        code = 400
                        raise ValueError("Invalid presets endpoint")
                    category = parts[1]
                    name = unquote_fn(parts[2])
                    data = body.get("data", {})
                    payload = save_preset(category, name, data)
                except ValueError as e:
                    payload = {"status": "error", "error": str(e)}
                except Exception as e:
                    payload = {"status": "error", "error": str(e)}
                self._send_json(payload, code=code)
                return True

            if req_path == '/chara_save':
                name = str(body.get("name", "") or "").strip()
                data = body.get("data", {})
                try:
                    payload = save_preset("chara", name, data)
                except Exception as e:
                    payload = {"status": "error", "error": str(e)}
                self._send_json(payload)
                return True

            if req_path == '/chara_delete':
                name = str(body.get("name", "") or "").strip()
                try:
                    payload = delete_preset("chara", name)
                except Exception as e:
                    payload = {"status": "error", "error": str(e)}
                self._send_json(payload)
                return True

            return False
        def do_POST(self):
            length=int(self.headers.get('Content-Length',0))
            body=json.loads(self.rfile.read(length))
            from urllib.parse import unquote
            req_path, req_qs = self._parse_request_path_qs()
    
            if self._handle_post_preset_routes(req_path, body, unquote):
                return

            if self._handle_post_common_routes(req_path, body):
                return

            if req_path == '/regen':
                self._handle_post_regen(body)
                return

            if self._handle_post_terminal_routes(req_path, req_qs, body, unquote):
                return

            self.send_response(404)
            self.end_headers()





        def _handle_post_common_routes(self, req_path: str, body: dict) -> bool:
            if req_path == '/config':
                self._handle_post_config(body)
                return True

            if req_path == '/session':
                self._handle_post_session(body)
                return True

            if self._handle_post_named_sessions_route(req_path, body):
                return True

            if req_path == '/history_update':
                self._handle_post_history_update(body)
                return True

            if req_path == '/history_delete':
                self._handle_post_history_delete(body)
                return True

            if req_path == '/chara_presets':
                self._handle_post_chara_presets(body)
                return True

            if req_path == '/chara_preset_thumb':
                self._handle_post_chara_preset_thumb(body)
                return True

            if req_path == '/lora_favorites':
                self._handle_post_lora_favorites(body)
                return True

            if req_path in ('/extra_tags', '/style_tags', '/neg_extra_tags', '/neg_style_tags'):
                self._handle_post_save_tags(req_path, body)
                return True

            return False
        def _handle_post_regen(self, body):
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
                        negative_prompt=regen_negative, lora_slots=regen_lora_slots, pipeline_version=__version__
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
                self._send_json(result)
            except Exception as e:
                self._send_json({'error': str(e)}, code=500)
            return

        def _handle_post_terminal_routes(self, req_path: str, req_qs: dict, body: dict, unquote_fn) -> bool:
            if req_path == '/get_image':
                self._handle_get_image_route(req_qs)
                return True

            if req_path == '/chara_thumb':
                self._handle_chara_thumb_route(req_qs, unquote_fn)
                return True

            if req_path == '/cancel':
                self._handle_post_cancel()
                return True

            if req_path == '/generate':
                self._handle_post_generate(body)
                return True

            return False
        def _handle_post_named_sessions_route(self, req_path: str, body: dict) -> bool:
            name = self._extract_named_session_name(req_path)
            if not name:
                return False

            overwrite = bool(body.get('overwrite', False))
            data = body.get('data', body)
            if not isinstance(data, dict):
                data = {}
            try:
                result = save_named_session(name, data, overwrite=overwrite)
                self._send_json(result)
            except FileExistsError:
                self._send_json({'status': 'error', 'error': 'Session already exists. Overwrite?'}, code=409)
            except ValueError as e:
                self._send_json({'status': 'error', 'error': str(e)}, code=400)
            except Exception as e:
                self._send_json({'status': 'error', 'error': str(e)}, code=500)
            return True
        def _handle_post_config(self, body):
            save_config(body)
            self._send_json({'ok': True})

        def _handle_post_session(self, body):
            sf = _sf('anima_session_last.json')
            with open(sf, 'w', encoding='utf-8') as f:
                json.dump(body, f, ensure_ascii=False, indent=2)
            self._send_json({'ok': True})
        def _handle_post_history_update(self, body):
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
            self._send_json(payload)

        def _handle_post_history_delete(self, body):
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
            self._send_json(payload)

        def _handle_post_chara_presets(self, body):
            # body: {action:'save'|'delete', preset:{name,data}, filename?}
            action = body.get('action', 'save')
            os.makedirs(CHARA_PRESETS_DIR, exist_ok=True)
            result = {'ok': True}
            try:
                if action == 'save':
                    preset = body.get('preset', {})
                    existing = sorted([f for f in os.listdir(CHARA_PRESETS_DIR) if f.endswith('.json')])
                    n = len(existing) + 1
                    safe_name = str(preset.get('name', 'preset')).replace('/', '_').replace('\\', '_')[:30]
                    filename = f'{n:03d}_{safe_name}.json'
                    if body.get('filename'):
                        filename = str(body['filename'])
                    filepath = os.path.join(CHARA_PRESETS_DIR, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(preset, f, ensure_ascii=False, indent=2)
                    result['filename'] = filename
                    print(f'[プリセット] 保存: {filename}')
                elif action == 'delete':
                    filename = str(body.get('filename', ''))
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
            self._send_json(result)

        def _handle_post_chara_preset_thumb(self, body):
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

                image_path = _resolve_image_path_with_webp_fallback(image_path)
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
            self._send_json(result)
        def _handle_post_lora_favorites(self, body):
            try:
                incoming = body if isinstance(body, dict) else {}
                favorites = []
                seen = set()
                for name in incoming.get('favorites', []) if isinstance(incoming.get('favorites', []), list) else []:
                    n = str(name or '').strip()
                    if not n or n in seen:
                        continue
                    seen.add(n)
                    favorites.append(n)
                self._save_lora_favorites(favorites)
                self._send_json({"status": "ok", "favorites": favorites})
            except Exception as e:
                self._send_json({"status": "error", "error": str(e)}, code=500)
        def _handle_post_generate(self, body):
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
                        self._send_json(result)
                        return
                    print(f"[LLM] 完了: {positive}")
                    result["positive_prompt"]=positive
                    positive_flat=positive.replace("\\n"," ").replace("\n"," ")
                else:
                    print("[LLM] スキップ")
                    result["positive_prompt"]=""
                    positive_flat=""
                if prompt_prefix:
                    if positive_flat and prompt_prefix:
                        prefix_set = {t.strip().lower() for t in prompt_prefix if t}
                        deduped = [t for t in positive_flat.split(',') if t.strip().lower() not in prefix_set]
                        positive_flat = ', '.join(t.strip() for t in deduped if t.strip())
                    positive_flat=", ".join(str(t) for t in prompt_prefix)+("", ", "+positive_flat)[bool(positive_flat)]
                if char_direct_tags:
                    direct_str=", ".join(str(t) for t in char_direct_tags if t)
                    if positive_flat:
                        direct_set = {t.strip().lower() for t in char_direct_tags if t}
                        flat_tags = {t.strip().lower() for t in positive_flat.split(',')}
                        deduped_direct = [t for t in char_direct_tags if t and t.strip().lower() not in flat_tags]
                        direct_str = ", ".join(str(t) for t in deduped_direct if t)
                    if direct_str:
                        positive_flat=(positive_flat+", "+direct_str).strip(", ")
                result["pre_extra_prompt"] = positive_flat
                if extra_tags:
                    extra_str=", ".join(str(t) for t in extra_tags)
                    positive_flat=(positive_flat+", "+extra_str).strip(", ") if positive_flat else extra_str
                if extra_note_en:
                    positive_flat=positive_flat.rstrip(". ").rstrip(",")+", "+extra_note_en
                result["final_prompt"]=positive_flat
                result["negative_prompt"]=negative_prompt

                try:
                    print("[ComfyUI] 送信中...")
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
                            output_dir = os.path.normpath(os.path.join(os.path.dirname(wf_path), "..", "..", "output"))
                    comfyui_url = cfg.get('comfyui_url','http://127.0.0.1:8188')
                    prompt_ids = []
                    shared_cid = body.get('client_id', str(uuid.uuid4()))
                    result["client_id"] = shared_cid
                    for i in range(img_count):
                        if Handler.cancel_event.is_set():
                            break
                        pid, meta = send_to_comfyui(
                            positive_flat, cfg, img_width, img_height, img_fmt, shared_cid,
                            negative_prompt=negative_prompt, lora_slots=lora_slots, pipeline_version=__version__
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
                        if cfg.get('seed_mode') == 'increment':
                            cfg['seed_value'] = int(cfg.get('seed_value', 0)) + 1
                            save_cfg = load_config()
                            save_cfg['seed_value'] = cfg['seed_value']
                            save_config(save_cfg)
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
            self._send_json(result)

        def _handle_post_cancel(self):
            cfg = load_config()
            comfyui_url = cfg.get('comfyui_url', 'http://127.0.0.1:8188')
            cancel_warn = ''
            try:
                import urllib.request as _ur
                req = _ur.Request(comfyui_url.rstrip('/') + '/interrupt', data=b'', method='POST')
                _ur.urlopen(req, timeout=1.5)
                req2 = _ur.Request(
                    comfyui_url.rstrip('/') + '/queue',
                    data=json.dumps({'clear': True}).encode(),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                _ur.urlopen(req2, timeout=1.5)
            except Exception as e:
                cancel_warn = str(e)

            Handler.cancel_event.set()
            if Handler.lm_session:
                try:
                    Handler.lm_session.close()
                except Exception:
                    pass

            print('[ComfyUI] 生成中止')
            payload = {'ok': True}
            if cancel_warn:
                payload['warn'] = cancel_warn
            self._send_json(payload)
        def _handle_post_save_tags(self, req_path: str, body: dict):
            tags = body.get("tags", [])
            if req_path == '/extra_tags':
                save_extra_tags(tags)
            elif req_path == '/style_tags':
                save_style_tags(tags)
            elif req_path == '/neg_extra_tags':
                save_neg_extra_tags(tags)
            elif req_path == '/neg_style_tags':
                save_neg_style_tags(tags)
            self._send_json({'ok': True})
        def do_DELETE(self):
            from urllib.parse import unquote
            req_path, _ = self._parse_request_path_qs()

            if self._handle_delete_named_session_routes(req_path):
                return

            if self._handle_delete_preset_routes(req_path, unquote):
                return

            self.send_response(404)
            self.end_headers()

        def _handle_delete_named_session_routes(self, req_path: str) -> bool:
            name = self._extract_named_session_name(req_path)
            if not name:
                return False
            try:
                payload = delete_named_session(name)
                self._send_json(payload)
            except FileNotFoundError:
                self._send_json({'status': 'error', 'error': 'Session not found'}, code=404)
            except ValueError as e:
                self._send_json({'status': 'error', 'error': str(e)}, code=400)
            except Exception as e:
                self._send_json({'status': 'error', 'error': str(e)}, code=500)
            return True
        def _handle_delete_preset_routes(self, req_path: str, unquote_fn) -> bool:
            if req_path.startswith('/presets/'):
                parts = [p for p in req_path.split('/') if p]
                payload = {"status": "error", "error": "Invalid presets endpoint"}
                code = 200
                try:
                    if len(parts) != 3:
                        code = 400
                        raise ValueError("Invalid presets endpoint")
                    category = parts[1]
                    name = unquote_fn(parts[2])
                    payload = delete_preset(category, name)
                except FileNotFoundError:
                    payload = {"status": "error", "error": "Preset not found"}
                except ValueError as e:
                    payload = {"status": "error", "error": str(e)}
                except Exception as e:
                    payload = {"status": "error", "error": str(e)}
                self._send_json(payload, code=code)
                return True

            return False

    return Handler
