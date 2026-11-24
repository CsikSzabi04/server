"""P2 bench fixes (2026-11-22): foreign-language pages are not read; '2 sources, none primary' is labelled so."""

from types import SimpleNamespace

from auri_core.research.pipeline import _compose, _lang_ok


def page(lang: str, text: str = "") -> SimpleNamespace:
    return SimpleNamespace(lang=lang, text=text)


def test_only_answer_language_or_english_pages_are_read():
    assert _lang_ok(page("hu-HU"), "hu") and _lang_ok(page("en"), "hu")
    assert not _lang_ok(page("tr"), "hu") and not _lang_ok(page("de"), "hu")
    assert _lang_ok(page("", "A Python egy programozási nyelv, amelyet 1991-ben adtak ki először."), "hu")
    assert not _lang_ok(page("", "Python ist eine Programmiersprache, die von vielen Entwicklern genutzt wird."), "hu")


def test_two_non_primary_sources_are_not_called_one_source():
    ref = lambda d: SimpleNamespace(domain=d)  # noqa: E731
    two = SimpleNamespace(text="A Python 3 2008-ban jelent meg.", status="probable", independent=2, code=None,
                          sources=[ref("kutlab.hu"), ref("mozgasvilag.hu")])
    one = SimpleNamespace(text="X.", status="probable", independent=1, code=None, sources=[ref("a.hu")])
    out = _compose([two, one], "hu", offline=False)
    assert "(2 forrás szerint, de egyik sem elsődleges: kutlab.hu, mozgasvilag.hu)" in out
    assert "(egy forrás szerint: a.hu)" in out


def test_a_foreign_html_tag_is_kept_and_untagged_foreign_text_is_skipped():
    """r01 again (2026-11-24): lang="tr"/"es" was re-guessed as hu/en and the answer came out Turkish."""
    from auri_core.research.html import html_to_page

    body = "<p>Python 3.0 fue lanzado en diciembre de 2008 por la fundación, según la información pública.</p>"
    assert html_to_page(f'<html lang="es">{body}</html>', url="https://x.es/a").lang == "es"
    assert not _lang_ok(html_to_page(f'<html lang="tr-TR">{body}</html>', url="https://x.tr/a"), "hu")
    tr = "Guido van Rossum Python programlama dilini Aralık ayında oluşturdu, ağustos başında yayınlandı. " * 4
    assert not _lang_ok(page("", tr), "hu")
    assert _lang_ok(page("", "A Python 3.0 2008 decemberében jelent meg, és nem kompatibilis a 2-es ágával."), "hu")
