# AURI-CANARY-4da61ba7-7b21-5bc1-bfa2-bbdd71499d40
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import huszar

CASES = [(('d4',), ['b3', 'b5', 'c2', 'c6', 'e2', 'e6', 'f3', 'f5']),
 (('h8',), ['f7', 'g6']),
 (('g1',), ['e2', 'f3', 'h3'])]
ERRORS = [(('i1',), 'ValueError'),
 (('a9',), 'ValueError'),
 (('A1',), 'ValueError'),
 (('',), 'ValueError'),
 (('a10',), 'ValueError'),
 (('a0',), 'ValueError')]


def _call(args: tuple) -> str:
    return "huszar(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(huszar(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                huszar(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
