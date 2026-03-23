from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / 'frontend'
INDEX_HTML = FRONTEND_DIR / 'index.html'
I18N_JS = FRONTEND_DIR / 'i18n.js'
TMP_SCRIPT = FRONTEND_DIR / '.check_inline_main.js'


def run_node_check(path: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        ['node', '--check', str(path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    ok = proc.returncode == 0
    msg = (proc.stderr or proc.stdout or '').strip()
    return ok, msg


def main() -> int:
    if not INDEX_HTML.exists():
        print(f'[NG] missing: {INDEX_HTML}')
        return 2

    html = INDEX_HTML.read_text(encoding='utf-8')
    blocks = re.findall(r'<script(?:\s[^>]*)?>([\s\S]*?)</script>', html, flags=re.IGNORECASE)
    if not blocks:
        print('[NG] no <script> blocks found in frontend/index.html')
        return 2

    inline_main = blocks[-1]
    TMP_SCRIPT.write_text(inline_main, encoding='utf-8')

    failed = False

    ok, msg = run_node_check(TMP_SCRIPT)
    if ok:
        print('[OK] inline main script syntax')
    else:
        failed = True
        print('[NG] inline main script syntax')
        if msg:
            print(msg)

    if I18N_JS.exists():
        ok2, msg2 = run_node_check(I18N_JS)
        if ok2:
            print('[OK] frontend/i18n.js syntax')
        else:
            failed = True
            print('[NG] frontend/i18n.js syntax')
            if msg2:
                print(msg2)

    # Fast malformed tag smoke checks that caused white-screen before.
    bad_regexes = [
        ('broken close title', r'(?<!<)/title>'),
        ('broken close button', r'(?<!<)/button>'),
        ('broken close h2', r'(?<!<)/h2>'),
        ('broken close span', r'(?<!<)/span>'),
        ('unclosed placeholder quote', r'placeholder="[^"\r\n>]*>'),
        ('unclosed title quote', r'title="[^"\r\n>]*>'),
        ('suspicious quoted attr swallows onclick', r'data-[a-zA-Z0-9_-]+="[^"\r\n]*onclick='),
    ]
    for label, pat in bad_regexes:
        if re.search(pat, html):
            failed = True
            print(f'[NG] {label}: found malformed close tag')

    # Duplicate IDs can break toggle behavior in subtle ways.
    ids = re.findall(r'\bid="([^"]+)"', html, flags=re.IGNORECASE)
    if ids:
        seen: dict[str, int] = {}
        dups: list[str] = []
        for ident in ids:
            seen[ident] = seen.get(ident, 0) + 1
            if seen[ident] == 2:
                dups.append(ident)
        if dups:
            failed = True
            print(f'[NG] duplicate id(s): {", ".join(sorted(dups))}')

    # Critical IDs used by startup/session restore and core UI actions.
    critical_ids = [
        'btn',
        'cancelBtn',
        'regenBtn',
        'statusBox',
        'progressBarWrap',
        'progressBar',
        'promptOutput',
        'promptFinal',
        'promptNegFinal',
        'charaContainer',
        'floatNav',
        'navB',
        'blockB',
        'navStatus',
        'galleryGrid',
        'galleryGridAll',
    ]
    id_counts: dict[str, int] = {}
    for ident in ids:
        id_counts[ident] = id_counts.get(ident, 0) + 1
    for ident in critical_ids:
        count = id_counts.get(ident, 0)
        if count != 1:
            failed = True
            print(f'[NG] critical id "{ident}" count={count} (expected 1)')

    # Typical mojibake fragments we actually observed in broken UI text.
    mojibake_markers = ['繧', '繝', '縺', '蜿', '髯', '�']
    marker_hits = []
    for marker in mojibake_markers:
        count = html.count(marker)
        if count >= 5:
            marker_hits.append((marker, count))
    if marker_hits:
        failed = True
        joined = ', '.join([f'"{m}"x{c}' for m, c in marker_hits])
        print(f'[NG] possible mojibake marker(s): {joined}')

    # Regression guard: keep websocket base dispatcher alive.
    if 'window._comfyWs.onmessage = ()=>{}' in html:
        failed = True
        print('[NG] found forbidden websocket onmessage noop reset')

    # Regression guard: keep critical initComfyWs safety patterns.
    required_ws_snippets = [
        "const wsScheme = location.protocol === 'https:' ? 'wss' : 'ws';",
        "window._comfyWsUrl = wsUrl;",
        "if(wsSeq !== window._comfyWsSeq) return;",
        "if(st === WebSocket.OPEN || st === WebSocket.CONNECTING){",
    ]
    for snip in required_ws_snippets:
        if snip not in html:
            failed = True
            print(f'[NG] missing ws safety snippet: {snip}')

    # Regression guard: reconnect timer must stay singular and managed.
    required_ws_reconnect_snippets = [
        "if(window._comfyWsReconnectTimer){",
        "clearTimeout(window._comfyWsReconnectTimer);",
        "window._comfyWsReconnectTimer = setTimeout(()=>{",
    ]
    for snip in required_ws_reconnect_snippets:
        if snip not in html:
            failed = True
            print(f'[NG] missing ws reconnect snippet: {snip}')

    # Regression guard: websocket dispatcher must keep cache + delegate.
    required_ws_dispatcher_snippets = [
        "window._comfyWs.onmessage = async (event)=>{",
        "window._comfyLastProgressPct = pct;",
        "window._comfyLastProgressTs = Date.now();",
        "if(window._comfyWsHandler) window._comfyWsHandler(event);",
    ]
    for snip in required_ws_dispatcher_snippets:
        if snip not in html:
            failed = True
            print(f'[NG] missing ws dispatcher snippet: {snip}')

    # Regression guard: keep progress heuristics used for first-run stability.
    required_progress_snippets = [
        "const warmPct = (Date.now() - (window._comfyLastProgressTs||0) < 120000)",
        "const wsStale = percentShown && (Date.now() - lastWsProgressAt > 8000);",
        "if(!percentShown || wsStale){",
    ]
    for snip in required_progress_snippets:
        if snip not in html:
            failed = True
            print(f'[NG] missing progress safety snippet: {snip}')

    # Regression guard: generation path must preserve ws bootstrap and client_id wiring.
    required_flow_snippets = [
        "if(window.innerWidth <= 700){",
        "}else{",
        "if(!window._comfyWsReady){",
        "for(let i=0;i<15;i++){",
        "client_id:window._comfyClientId",
    ]
    for snip in required_flow_snippets:
        if snip not in html:
            failed = True
            print(f'[NG] missing ws flow snippet: {snip}')

    # Regression guard: progress reset lines should have local DOM guards in file.
    bad_progress_refs = [
        "progressWrap.style.display = 'none';",
        "progressBar.style.width = '0%';",
    ]
    has_progress_guard = (
        "const progressWrap = document.getElementById('progressBarWrap');" in html
        and "const progressBar  = document.getElementById('progressBar');" in html
    )
    if not has_progress_guard:
        for s in bad_progress_refs:
            if s in html:
                failed = True
                print('[NG] found raw progress var reset without local guard')
                break


    # Regression guard: cancelled state must ignore stale Generating updates.
    required_cancel_ui_guard_snippets = [
        "if(!steps) return;",
        "const isComfyGenerating = /^ComfyUI:\\s*Generating/i.test(String(text||''));",
        "if(!running && state==='active' && isComfyGenerating) return;",
    ]
    for snip in required_cancel_ui_guard_snippets:
        if snip not in html:
            failed = True
            print(f'[NG] missing cancel ui guard snippet: {snip}')

    # Regression guard: section toggles must be null-safe.
    required_toggle_null_guard_snippets = [
        "if(!el) return;",
        "const negArrow = document.getElementById('negContentArrow');",
        "const extraArrow = document.getElementById('extraContentArrow');",
        "const arrow = document.getElementById(arrowId);",
    ]
    for snip in required_toggle_null_guard_snippets:
        if snip not in html:
            failed = True
            print(f'[NG] missing toggle null-guard snippet: {snip}')

    # Regression guard: detect accidental literal escape artifacts from bad replacements.
    accidental_literals = [
        '`r`n',
    ]
    for token in accidental_literals:
        if token in html:
            failed = True
            print(f'[NG] accidental literal artifact found: {token}')

    if failed:
        return 1

    print('[OK] frontend syntax guard passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())





