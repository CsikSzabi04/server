"""HTML → PageDoc with the standard library only (03/02 §3).

Drops script/style/nav/footer/aside/form/…, HIDDEN content (hidden, aria-hidden, display:none,
visibility:hidden — the favourite hiding place of prompt injections), comments and zero-width
characters; prefers <main>/<article>/role=main; keeps headings as section paths, <pre>/<code> blocks
with their language, lists and tables. Injection patterns (visible or hidden) → `suspicious`.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

from ..lang import detect_lang
from .text import norm_quote
from .trust import page_kind
from .types import PageDoc, Section

MAX_SECTION = 1500
MAX_TEXT = 40_000
_DROP = {"script", "style", "nav", "footer", "aside", "form", "noscript", "template", "svg", "iframe", "button",
         "select", "textarea", "object", "canvas", "dialog", "menu"}
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track",
         "wbr"}
_BLOCK = {"p", "div", "li", "tr", "br", "section", "dt", "dd", "blockquote", "h4", "h5", "h6", "table", "ul", "ol",
          "figure", "figcaption", "hr", "summary", "details"}
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?:px)?\s*(?:;|$)", re.I)
_LANG_CLASS = re.compile(r"(?:language|lang|highlight|brush)[-:_ ]?([a-z0-9+#]+)", re.I)
_ZW = re.compile("[​‌‍⁠﻿­]")
INJECTION = re.compile(
    r"ignore\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above)\s+instructions|disregard\s+(?:all\s+)?(?:previous|prior)"
    r"|you\s+are\s+now\b|system\s+prompt|new\s+instructions\s*:|<\s*/?\s*(?:system|szerep|web_adat)\b"
    r"|hagyd\s+figyelmen\s+kívül\s+(?:az\s+)?(?:eddigi\s+|korábbi\s+)?utasítás|mostantól\s+te\s+vagy"
    r"|reveal\s+(?:your|the)\s+(?:system|hidden)\s+prompt|act\s+as\s+(?:an?\s+)?(?:unrestricted|jailbroken)",
    re.I,
)


class _Extractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.stack: list[tuple[str, bool, bool]] = []  # (tag, starts_skip, starts_main)
        self.skip = 0
        self.hidden_text: list[str] = []
        self._skip_hidden = False
        self.in_main = 0
        self.main_seen = False
        self.title = ""
        self._in_title = False
        self.lang_attr = ""
        self.noindex = False
        # two parallel outputs: the whole body and the main region
        self.out = {"all": _Builder(), "main": _Builder()}
        self.links: list[tuple[str, str]] = []
        self._a: tuple[str, list[str]] | None = None
        self._pre = 0
        self._pre_lang = ""
        self._pre_buf: list[str] = []
        self._heading: tuple[int, list[str]] | None = None

    # ── helpers ─────────────────────────────────────────────────────────
    def _emit(self, fn: str, *args: object) -> None:
        targets = [self.out["all"]] + ([self.out["main"]] if self.in_main else [])
        for b in targets:
            getattr(b, fn)(*args)

    @staticmethod
    def _hidden(attrs: dict[str, str | None]) -> bool:
        if "hidden" in attrs or (attrs.get("aria-hidden") or "").lower() == "true":
            return True
        if _HIDDEN_STYLE.search(attrs.get("style") or ""):
            return True
        cls = (attrs.get("class") or "").lower()
        return any(c in cls.split() for c in ("sr-only", "visually-hidden", "d-none", "hidden"))

    # ── parser callbacks ────────────────────────────────────────────────
    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {k.lower(): v for k, v in attrs_list}
        if tag == "html" and attrs.get("lang"):
            self.lang_attr = (attrs.get("lang") or "")[:2].lower()
        if tag == "meta":
            name = (attrs.get("name") or "").lower()
            content = (attrs.get("content") or "").lower()
            if name in ("robots", "googlebot") and ("noindex" in content or "noai" in content):
                self.noindex = True
            return
        if tag == "title":
            self._in_title = True
        if tag in _VOID:
            if tag == "br" and not self.skip:
                self._emit("newline")
            return
        starts_skip = not self.skip and (tag in _DROP or tag == "head" or self._hidden(attrs))
        starts_main = (tag in ("main", "article") or (attrs.get("role") or "") == "main") and not self.skip
        self.stack.append((tag, starts_skip, starts_main))
        if starts_skip:
            self.skip += 1
            self._skip_hidden = tag not in _DROP and tag != "head"
            if self._skip_hidden:
                self.hidden_text.append("")  # collect hidden text: injection detection only
            return
        if self.skip:
            return
        if starts_main:
            self.in_main += 1
            self.main_seen = True
        if tag in ("h1", "h2", "h3"):
            self._heading = (int(tag[1]), [])
        elif tag == "pre":
            self._pre += 1
            self._pre_buf = []
            self._pre_lang = _code_lang(attrs.get("class") or "")
        elif tag == "code" and self._pre:
            self._pre_lang = self._pre_lang or _code_lang(attrs.get("class") or "")
        elif tag == "a" and attrs.get("href"):
            self._a = (urljoin(self.base, attrs.get("href") or ""), [])
        elif tag == "li":
            self._emit("newline")
            self._emit("text", "- ")
        elif tag in ("td", "th"):
            self._emit("text", " | ")
        elif tag in _BLOCK:
            self._emit("newline")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in _VOID:
            return
        if not any(t == tag for t, _, _ in self.stack):
            return  # stray end tag
        while self.stack:
            t, starts_skip, starts_main = self.stack.pop()
            if starts_skip:
                self.skip -= 1
            elif not self.skip:
                self._close(t, starts_main)
            if t == tag:
                break

    def _close(self, tag: str, starts_main: bool) -> None:
        if starts_main:
            self.in_main -= 1
        if tag in ("h1", "h2", "h3") and self._heading:
            level, buf = self._heading
            self._heading = None
            self._emit("heading", level, " ".join("".join(buf).split()))
        elif tag == "pre" and self._pre:
            self._pre -= 1
            if not self._pre:
                code = "".join(self._pre_buf).strip("\n")
                if code.strip():
                    self._emit("code", self._pre_lang or "text", code)
        elif tag == "a" and self._a:
            href, buf = self._a
            self._a = None
            text = " ".join("".join(buf).split())
            if href.startswith(("http://", "https://")) and len(self.links) < 300:
                self.links.append((href, text[:120]))
        elif tag in _BLOCK:
            self._emit("newline")

    def handle_data(self, data: str) -> None:
        data = _ZW.sub("", data)
        if self._in_title and not self.title:
            self.title = " ".join(data.split())[:200]
        if self.skip:
            if self._skip_hidden:
                self.hidden_text[-1] += data
            return
        if self._pre:
            self._pre_buf.append(data)
            return
        if self._heading:
            self._heading[1].append(data)
            return
        if self._a:
            self._a[1].append(data)
        self._emit("text", data)


class _Builder:
    """Collects sections: heading path + text + code blocks."""

    def __init__(self) -> None:
        self.sections: list[Section] = []
        self.path: tuple[str, ...] = ()
        self.buf: list[str] = []
        self.blocks: list[tuple[str, str]] = []

    def text(self, s: str) -> None:
        self.buf.append(s)

    def newline(self) -> None:
        self.buf.append("\n")

    def code(self, lang: str, code: str) -> None:
        self.buf.append("\n")
        self.blocks.append((lang, code))

    def heading(self, level: int, text: str) -> None:
        self.flush()
        if text:
            self.path = (*self.path[: level - 1], text)
            self.buf.append(text + "\n")

    def flush(self) -> None:
        raw = "".join(self.buf)
        lines = [" ".join(ln.split()) for ln in raw.split("\n")]
        text = "\n".join(ln for ln in lines if ln and ln not in ("-", "|"))
        if text or self.blocks:
            for chunk in _chunks(text, MAX_SECTION) or [""]:
                self.sections.append(Section(self.path, chunk, self.blocks))
                self.blocks = []
        self.buf = []


def _chunks(text: str, n: int) -> list[str]:
    if len(text) <= n:
        return [text] if text else []
    out, cur = [], ""
    for para in text.split("\n"):
        while len(para) > n:  # one huge paragraph
            if cur:
                out.append(cur)
                cur = ""
            out.append(para[:n])
            para = para[n:]
        if len(cur) + len(para) + 1 > n and cur:
            out.append(cur)
            cur = para
        else:
            cur = f"{cur}\n{para}" if cur else para
    if cur:
        out.append(cur)
    return out


def _code_lang(cls: str) -> str:
    m = _LANG_CLASS.search(cls)
    if m:
        return m.group(1).lower()
    parts = [c for c in cls.lower().split() if c not in ("hljs", "highlight", "code", "notranslate", "sourcecode")]
    return parts[0] if len(parts) == 1 and parts[0].isalpha() and len(parts[0]) <= 12 else ""


def _cap(sections: list[Section], limit: int) -> list[Section]:
    out, used = [], 0
    for s in sections:
        size = len(s.text) + sum(len(c) for _, c in s.code)
        if used + size > limit:
            break
        out.append(s)
        used += size
    return out


def html_to_page(html: str, *, url: str, final_url: str | None = None, fetched_at: str = "",
                 content_type: str = "text/html") -> PageDoc:
    final = final_url or url
    if "html" not in content_type and "xml" not in content_type:
        text = _ZW.sub("", html)[:MAX_TEXT]
        sections = [Section((), c) for c in _chunks("\n".join(" ".join(ln.split()) for ln in text.splitlines()),
                                                     MAX_SECTION)]
        title, lang_attr, noindex, links, hidden = "", "", False, [], []
    else:
        p = _Extractor(final)
        p.feed(html)
        p.close()
        for b in p.out.values():
            b.flush()
        main = p.out["main"].sections
        main_len = sum(len(s.text) for s in main)
        sections = main if p.main_seen and main_len >= 200 else p.out["all"].sections
        sections = _cap(sections, MAX_TEXT)
        title, lang_attr, noindex, links, hidden = p.title, p.lang_attr, p.noindex, p.links, p.hidden_text
    body = "\n".join(s.text for s in sections)
    suspicious = bool(INJECTION.search(norm_quote(body))) or any(INJECTION.search(h) for h in hidden)
    # the real tag (tr, es, …) is kept: detect_lang knows only hu/en/de and reads Spanish á/é/í/ó/ú as
    # Hungarian, so a re-guess let foreign pages through the answer-language filter (P2 r01, 2026-11-24)
    lang = lang_attr if len(lang_attr) == 2 and lang_attr.isalpha() else detect_lang(body[:2000])
    return PageDoc(
        url=url, final_url=final, title=title, lang=lang, fetched_at=fetched_at,
        content_hash="sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest(),
        kind=page_kind(final), sections=sections, links=links, suspicious=suspicious, noindex=noindex,
    )
