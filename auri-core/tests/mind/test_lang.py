"""NK11: the one shared detector. Cases = web/tests/brain-answers.test.ts + the lang.ts comments."""

import pytest

from auri_core.lang import answer_lang, detect_lang

CASES = [
    ("ki vagy?", "hu"),  # accent-free Hungarian (the autolearn detector said 'en')
    ("a Föld", "hu"),  # ö + a tied Hungarian vote
    ("nem", "hu"),
    ("what is gravity", "en"),
    ("who are you", "en"),
    ("Mi a fotoszintézis?", "hu"),  # Hungarian-unique accent
    ("Was ist das?", "de"),
    ("Straße", "de"),
    ("a", "en"),  # lone article: tie → English
    ("grün", "de"),  # ö/ü with no other signal
    ("12345 ?!", "unknown"),
    ("", "unknown"),
    ("hogyan kell ezt megcsinalni", "hu"),
    ("Hello, how are you?", "en"),
]


@pytest.mark.parametrize(("text", "want"), CASES)
def test_detect_lang(text, want):
    assert detect_lang(text) == want


def test_answer_lang():
    assert answer_lang("ki vagy?") == "hu" and answer_lang("Was ist das?") == "en"
    assert answer_lang("ki vagy?", "en") == "en"
