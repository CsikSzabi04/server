# AURI-CANARY-b00ce746-c1c2-5b8d-b531-b0f57ca01a76
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import nagybetus_szavak

CASES = [(('',), []), (('Árvíz és Öböl',), ['Árvíz', 'Öböl']), (('1Alma Bé',), ['Bé']), (('ALMA körte',), ['ALMA'])]


def _call(args: tuple) -> str:
    return "nagybetus_szavak(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(nagybetus_szavak(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
