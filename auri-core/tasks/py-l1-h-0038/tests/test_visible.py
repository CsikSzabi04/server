# AURI-CANARY-b441ad6a-a775-5482-8e0f-43e87d017ee1
import copy
import unittest

from solution import tobbi_szorzata

CASES = [(([1, 2, 3, 4],), [24, 12, 8, 6]), (([],), [])]


def _call(args: tuple) -> str:
    return "tobbi_szorzata(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(tobbi_szorzata(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
