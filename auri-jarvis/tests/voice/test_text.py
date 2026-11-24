"""Pure-logic tests for the VOICE zone: sentence splitting, TTS text cleaning, lexicon."""
from auri_jarvis.stt.lang import guess_lang
from auri_jarvis.stt.lexicon import Lexicon
from auri_jarvis.tts.splitter import CODE_PLACEHOLDER, SentenceSplitter
from auri_jarvis.tts.textclean import clean_for_tts


def split_stream(text: str, step: int = 3) -> list[str]:
    """Feed `text` in small deltas (like an LLM stream) and collect sentences."""
    sp = SentenceSplitter()
    out: list[str] = []
    for i in range(0, len(text), step):
        out += sp.feed(text[i:i + step])
    return out + sp.flush()


# ── splitter ────────────────────────────────────────────────────────────────
def test_splits_plain_sentences_as_they_complete():
    sp = SentenceSplitter()
    assert sp.feed("Máris, uram. Megnyit") == ["Máris, uram."]
    assert sp.feed("om a Chrome-ot! Kész?") == ["Megnyitom a Chrome-ot!"]
    assert sp.flush() == ["Kész?"]


def test_does_not_cut_abbreviations_decimals_dates_filenames():
    text = ("Pl. a node.js gyors, kb. 3.14-szer. Ma 2026. november 20. van, a 5. fejezetnél tartunk. "
            "Use e.g. Python. Done.")
    assert split_stream(text) == [
        "Pl. a node.js gyors, kb. 3.14-szer.",
        "Ma 2026. november 20. van, a 5. fejezetnél tartunk.",
        "Use e.g. Python.",
        "Done.",
    ]


def test_code_blocks_are_not_read_aloud():
    text = "Íme a kód:\n```python\nprint('hi')\nx = 1.5\n```\nFuttasd le."
    assert split_stream(text, step=4) == ["Íme a kód:", CODE_PLACEHOLDER["hu"], "Futtasd le."]


def test_unclosed_code_block_is_dropped_with_placeholder():
    assert split_stream("Nézd:\n```js\nconst a = 1;") == ["Nézd:", CODE_PLACEHOLDER["hu"]]


def test_very_long_clause_is_cut_at_a_comma():
    long = "Ez egy nagyon hosszú mondat, " * 12  # no sentence end at all
    parts = split_stream(long)
    assert len(parts) >= 2 and all(len(p) <= 220 for p in parts)


# ── text cleaning ──────────────────────────────────────────────────────────
def test_markdown_emoji_urls_removed():
    raw = "## Kész ✅\n- **Megnyitottam** a `Chrome`-ot: https://example.com/x 🙂"
    assert clean_for_tts(raw, "hu") == "Kész Megnyitottam a Chrome-ot: a linket kiírtam a képernyőre"


def test_times_and_symbols_read_naturally_in_hungarian():
    assert clean_for_tts("Most 22:15 van, a CPU 37% & a RAM 61%.", "hu") == \
        "Most 22 óra 15 perc van, a CPU 37 százalék és a RAM 61 százalék."
    assert clean_for_tts("Találkozó 9:00-kor, 10:00-ig.", "hu") == "Találkozó 9 órakor, 10 óráig."
    assert clean_for_tts("Szólj 8:30-ra.", "hu") == "Szólj 8 óra 30 percre."


def test_snake_case_is_not_treated_as_italics():
    assert clean_for_tts("Hívd meg a create_ears függvényt.", "en") == "Hívd meg a create ears függvényt."


# ── language guess ─────────────────────────────────────────────────────────
def test_guess_lang():
    assert guess_lang("Auri, nyisd meg a Chrome-ot.") == "hu"
    assert guess_lang("ki vagy") == "hu"
    assert guess_lang("What is the weather like today?") == "en"
    assert guess_lang("") == "hu"


# ── lexicon ────────────────────────────────────────────────────────────────
LEX = Lexicon(
    replace={"nycs meg": "nyisd meg", "visol studió": "Visual Studio", "vízkód": "VS Code", "hei hauri": "Hey Auri"},
    terms=["Auri", "Visual Studio Code", "VS Code", "Chrome", "Spotify", "YouTube"],
)


def test_lexicon_fixes_measured_parakeet_mishearings():
    fixed = LEX.correct("Auri nycs meg a visol studió kódot")
    assert fixed.startswith("Auri nyisd meg a Visual Studio")
    assert LEX.correct("Hei Hauri, indítsd a vízkódot") == "Hey Auri, indítsd a VS Code-ot"


def test_lexicon_fuzzy_terms_keep_hungarian_suffix():
    assert LEX.correct("nyisd meg a Crome-ot") == "nyisd meg a Chrome-ot"
    assert LEX.correct("indítsd a Spotifájt") == "indítsd a Spotifájt"  # too different → untouched


def test_lexicon_leaves_correct_and_ordinary_words_alone():
    for text in ["Auri, nyisd meg a Chrome-ot.", "kérdezd meg Aurit", "hány óra van?",
                 "Állíts be egy időzítőt huszonöt percre."]:
        assert LEX.correct(text) == text
