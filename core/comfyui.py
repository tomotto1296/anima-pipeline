import json
import os
import requests
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FILE_HASH_CACHE = {}
_BASENAME_PATH_CACHE = {}

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
            wf_path = os.path.join(BASE_DIR, wf_path)
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
    params += f", Version: Anima Pipeline {meta.get('pipeline_version', 'unknown')}"

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
    pipeline_version: str = "",
):
    workflow_path = cfg.get("workflow_json_path", "").strip()
    if workflow_path and not os.path.isabs(workflow_path):
        workflow_path = os.path.join(BASE_DIR, workflow_path)
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
        "pipeline_version": pipeline_version or "",
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



