# AURI-CANARY-bd78a898-6b0a-5917-979a-d2da55b741ba
import copy
import unittest

from solution import leghosszabb_novekvo

CASES = [(([1, 2, 3, 1, 2],), 3), (([],), 0)]


def _call(args: tuple) -> str:
    return "leghosszabb_novekvo(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(leghosszabb_novekvo(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
