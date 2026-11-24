# AURI-CANARY-98fac19d-ee36-5ca2-b169-d95cc2c21b50
import copy
import unittest

from solution import leghosszabb_szo

CASES = [(('a kutya ugat',), 'kutya'), (('',), '')]


def _call(args: tuple) -> str:
    return "leghosszabb_szo(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(leghosszabb_szo(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
