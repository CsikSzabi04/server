# AURI-CANARY-c5e0444b-461a-55fb-84d8-80fa89ead877
import copy
import unittest

from solution import pascal_sor

CASES = [((0,), [1]), ((4,), [1, 4, 6, 4, 1])]


def _call(args: tuple) -> str:
    return "pascal_sor(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(pascal_sor(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
