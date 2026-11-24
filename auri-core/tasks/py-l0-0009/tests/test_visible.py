# AURI-CANARY-b00ce746-c1c2-5b8d-b531-b0f57ca01a76
import copy
import unittest

from solution import nagybetus_szavak

CASES = [(('Teszt Elek alma',), ['Teszt', 'Elek'])]


def _call(args: tuple) -> str:
    return "nagybetus_szavak(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(nagybetus_szavak(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
