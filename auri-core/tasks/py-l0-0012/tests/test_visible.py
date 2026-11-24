# AURI-CANARY-84848832-e492-5dd5-9ad3-803e15c171df
import copy
import unittest

from solution import szorzotabla

CASES = [((2,), [[1, 2], [2, 4]])]


def _call(args: tuple) -> str:
    return "szorzotabla(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szorzotabla(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
