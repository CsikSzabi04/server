# AURI-CANARY-484c85b0-ba99-5cf0-95b4-abbfde8b3f07
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import anagramma

CASES = [(('', ''), True),
 (('a b', 'ba'), True),
 (('aab', 'abb'), False),
 (('Árvíz', 'zívrá'), True),
 (('ab', 'ab '), True),
 (('alma', 'lama'), True)]


def _call(args: tuple) -> str:
    return "anagramma(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(anagramma(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
