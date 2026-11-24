# AURI-CANARY-db01f964-d922-5a99-88a6-2ec4fb05c377
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import levenshtein

CASES = [(('', 'abc'), 3),
 (('abc', ''), 3),
 (('alma', 'alma'), 0),
 (('flaw', 'lawn'), 2),
 (('ház', 'háziasszony'), 8),
 (('körte', 'körtefa'), 2)]


def _call(args: tuple) -> str:
    return "levenshtein(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(levenshtein(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
