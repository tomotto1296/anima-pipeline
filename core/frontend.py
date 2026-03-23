from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parent.parent
_INDEX_HTML_PATH = _BASE_DIR / "frontend" / "index.html"
_HTML_CACHE = None


def load_html_template() -> str:
    global _HTML_CACHE
    if _HTML_CACHE is None:
        _HTML_CACHE = _INDEX_HTML_PATH.read_text(encoding="utf-8")
    return _HTML_CACHE
