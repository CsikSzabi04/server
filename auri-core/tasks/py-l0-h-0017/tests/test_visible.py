# AURI-CANARY-ab924bfe-5fe4-5881-bb0a-f549e485be9a
import copy
import unittest

from solution import van_ismetlodes

CASES = [(([1, 2, 1],), True), (([1, 2, 3],), False)]


def _call(args: tuple) -> str:
    return "van_ismetlodes(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(van_ismetlodes(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
