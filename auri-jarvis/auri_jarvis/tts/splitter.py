"""Streaming sentence splitter: raw LLM deltas in → speakable sentences out.

Speaks each sentence as soon as it is complete (low latency), but never cuts at
abbreviations ("pl.", "stb.", "e.g."), decimals ("3.14"), file names ("node.js"),
Hungarian ordinals/dates ("2004. január", "5. fejezet"). Fenced code blocks are not
read aloud — one short spoken placeholder replaces them.
"""

from __future__ import annotations

import re

ABBREVIATIONS = {
    # Hungarian
    "pl",
    "stb",
    "dr",
    "kb",
    "ill",
    "ún",
    "vö",
    "ld",
    "sz",
    "tel",
    "db",
    "ford",
    "max",
    "min",
    "jan",
    "febr",
    "márc",
    "ápr",
    "jún",
    "júl",
    "aug",
    "szept",
    "okt",
    "nov",
    "dec",
    "id",
    "u",
    # English
    "mr",
    "mrs",
    "ms",
    "e.g",
    "i.e",
    "etc",
    "vs",
    "st",
    "no",
    "fig",
    "approx",
}
CODE_PLACEHOLDER = {"hu": "A kódot kiírtam a képernyőre.", "en": "I put the code on the screen."}
_CLOSERS = "\"'”’)]»"


class SentenceSplitter:
    def __init__(self, max_chars: int = 220, lang: str = "hu") -> None:
        self.max_chars = max_chars
        self.lang = lang
        self._buf = ""
        self._in_code = False
        self._said_code = False

    def feed(self, delta: str) -> list[str]:
        self._buf += delta
        out: list[str] = []
        while True:
            if self._consume_code(out):
                continue
            if self._in_code:  # inside an unfinished code block: wait for the closing fence
                break
            cut = self._find_cut(self._buf, final=False)
            if cut is None:
                break
            sentence, self._buf = self._buf[:cut].strip(), self._buf[cut:]
            if sentence:
                out.append(sentence)
        return out

    def flush(self) -> list[str]:
        out: list[str] = []
        if self._in_code:  # unterminated code block: drop it
            self._buf, self._in_code = "", False
            self._placeholder(out)
        while self._buf.strip():
            if self._consume_code(out):
                continue
            if self._in_code:  # code block never closed: don't read it aloud
                self._buf, self._in_code = "", False
                self._placeholder(out)
                break
            cut = self._find_cut(self._buf, final=True) or len(self._buf)
            sentence, self._buf = self._buf[:cut].strip(), self._buf[cut:]
            if sentence:
                out.append(sentence)
        self._buf = ""
        return out

    # ── code fences ────────────────────────────────────────────────────────
    def _consume_code(self, out: list[str]) -> bool:
        if not self._in_code:
            i = self._buf.find("```")
            if i < 0:
                return False
            before = self._buf[:i].strip()
            if before:
                out.append(before)
            self._buf, self._in_code = self._buf[i + 3 :], True
            return True
        j = self._buf.find("```")
        if j < 0:
            # keep only a tail that might be the start of the closing fence
            self._buf = self._buf[-2:]
            return False
        self._buf, self._in_code = self._buf[j + 3 :], False
        self._placeholder(out)
        return True

    def _placeholder(self, out: list[str]) -> None:
        if not self._said_code:
            out.append(CODE_PLACEHOLDER.get(self.lang, CODE_PLACEHOLDER["en"]))
            self._said_code = True

    # ── sentence boundaries ───────────────────────────────────────────────
    def _find_cut(self, s: str, *, final: bool) -> int | None:
        for i, ch in enumerate(s):
            if ch == "\n":
                if s[:i].strip():
                    return i + 1
                continue
            if ch not in ".!?…":
                continue
            j = i + 1
            while j < len(s) and (s[j] in ".!?…" or s[j] in _CLOSERS):
                j += 1
            if j >= len(s):  # need to see what follows (".js", "?!", a closing quote…)
                if final:
                    return j
                return None
            if not s[j].isspace():
                continue  # "node.js", "3.14", "e.g."
            if ch == "." and not self._period_ends(s, i, j, final):
                continue
            return j
        if len(s) > self.max_chars:  # very long clause: cut at a comma / space
            k = max(s.rfind(", ", 0, self.max_chars), s.rfind("; ", 0, self.max_chars))
            if k < 40:
                k = s.rfind(" ", 0, self.max_chars)
            return k + 1 if k > 0 else self.max_chars
        return None

    @staticmethod
    def _period_ends(s: str, i: int, j: int, final: bool) -> bool:
        m = re.search(r"([\w.]+)$", s[:i])
        word = m.group(1) if m else ""
        if word.lower().rstrip(".") in ABBREVIATIONS:
            return False
        k = j
        while k < len(s) and s[k].isspace():
            k += 1
        if k >= len(s):
            return final  # can't tell yet — wait for the next word
        nxt = s[k]
        if word.isdigit() and (nxt.islower() or nxt.isdigit()):
            return False  # "2004. január", "5. fejezet"
        if len(word) == 1 and word.isalpha() and word.isupper():
            return False  # initials: "J. R. R. Tolkien"
        return not nxt.islower()
