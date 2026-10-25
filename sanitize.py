"""Code-layer defense — clean a vendor document BEFORE the model sees it.

Removes the things a person would never see but a naive text extractor reads at full size:
- HTML: <script>/<style>, HTML comments, and elements hidden by inline CSS
  (display:none, visibility:hidden, opacity:0, font-size:0).
- PDF: text drawn in a sub-5-point font or positioned off the page.
- Email: prefer the plain-text body (CSS tricks live in the HTML part).
- Any format: zero-width characters used to obfuscate injected text.

`read_document_clean(path)` is the defended counterpart of `tools.read_document_text`.
"""

from __future__ import annotations

import re
from email import message_from_string
from email.policy import default as default_policy
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from pypdf import PdfReader

ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
MIN_PT = 5.0  # drop PDF text smaller than this (0.8pt micro-text is an attack)

def _is_hiding_css(props: str) -> bool:
    """True if a block of CSS properties would hide text from a human on a white page."""
    p = (props or "").lower()
    if re.search(r"display\s*:\s*none", p):
        return True
    if re.search(r"visibility\s*:\s*hidden", p):
        return True
    if re.search(r"opacity\s*:\s*0(?!\.)", p):
        return True
    if re.search(r"font-size\s*:\s*0(px|pt|em|rem|%)?\b", p):
        return True
    # off-screen positioning (position:absolute/fixed pushed off the page, or text-indent)
    if re.search(r"position\s*:\s*(absolute|fixed)", p) and re.search(r"(left|top)\s*:\s*-\s*\d", p):
        return True
    if re.search(r"text-indent\s*:\s*-\s*\d", p):
        return True
    if re.search(r"clip\s*:\s*rect\(\s*0", p):
        return True
    # white / transparent text (the shop's quotes are on white backgrounds)
    if re.search(r"color\s*:\s*(#fff(fff)?\b|white\b|transparent\b)", p):
        return True
    return False


_HIDDEN_RE = _is_hiding_css  # kept for callers that pass a style string


def strip_zero_width(s: str) -> str:
    return (s or "").translate(ZERO_WIDTH)


def _hiding_selectors(soup: BeautifulSoup) -> list[str]:
    """Selectors in <style> rules whose properties hide text (class/id/tag based)."""
    selectors: list[str] = []
    for style in soup.find_all("style"):
        css = style.get_text()
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            if _is_hiding_css(m.group(2)):
                for sel in m.group(1).split(","):
                    sel = sel.strip()
                    if sel:
                        selectors.append(sel)
    return selectors


def sanitize_html(raw: str) -> str:
    """Return only the visible text of an HTML document.

    Removes elements hidden by inline style, by a <style> rule (class/id/tag), by the hidden
    attribute, plus scripts, styles, and HTML comments."""
    soup = BeautifulSoup(raw, "html.parser")
    # 1. Elements hidden via a <style> rule (read rules first, then act).
    for sel in _hiding_selectors(soup):
        try:
            for el in soup.select(sel):
                el.decompose()
        except Exception:
            pass
    # 2. Strip scripts, styles, and comments.
    for tag in soup(["script", "style"]):
        tag.decompose()
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()
    # 3. Elements hidden via an inline style= attribute, or the hidden attribute.
    for tag in soup.find_all(style=lambda v: bool(v) and _is_hiding_css(v)):
        tag.decompose()
    for tag in soup.find_all(hidden=True):
        tag.decompose()
    return strip_zero_width(soup.get_text(separator="\n")).strip()


def sanitize_pdf(path: Path) -> str:
    """Keep only PDF text in a readable font size and on the visible page."""
    reader = PdfReader(str(path))
    kept: list[str] = []
    for page in reader.pages:
        try:
            height = float(page.mediabox.height)
            width = float(page.mediabox.width)
        except Exception:
            height, width = 792.0, 612.0

        def visitor(text, cm, tm, font_dict, font_size, _k=kept, _h=height, _w=width):
            if not text or not text.strip():
                return
            scale = abs(tm[3]) if tm and tm[3] else 1.0
            eff = abs((font_size or 0)) * (scale or 1.0)
            x = (tm[4] if tm else 0) + (cm[4] if cm else 0)
            y = (tm[5] if tm else 0) + (cm[5] if cm else 0)
            on_page = (-2 <= y <= _h + 2) and (-2 <= x <= _w + 2)
            if eff >= MIN_PT and on_page:
                _k.append(text)

        page.extract_text(visitor_text=visitor)
    return strip_zero_width("".join(kept)).strip()


def sanitize_eml(raw: str) -> str:
    """Prefer the plain-text body; fall back to sanitized HTML. CSS hiding lives in HTML."""
    msg = message_from_string(raw, policy=default_policy)
    header = f"From: {msg.get('From', '')}\nSubject: {msg.get('Subject', '')}\n"

    plain = None
    html = None
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/plain" and plain is None:
            plain = part.get_content()
        elif ctype == "text/html" and html is None:
            html = part.get_content()
    if plain is not None:
        body = strip_zero_width(plain)
    elif html is not None:
        body = sanitize_html(html)
    else:
        body = strip_zero_width(msg.get_body().get_content() if msg.get_body() else "")
    return (header + "\n" + body).strip()


def read_document_clean(doc_path: str) -> str:
    path = Path(doc_path)
    suffix = path.suffix.lower()
    if suffix in (".html", ".htm"):
        return sanitize_html(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".pdf":
        return sanitize_pdf(path)
    if suffix == ".eml":
        return sanitize_eml(path.read_text(encoding="utf-8", errors="replace"))
    return strip_zero_width(path.read_text(encoding="utf-8", errors="replace")).strip()
