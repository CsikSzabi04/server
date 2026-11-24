# AURI-CANARY-20851c4a-471b-5642-9337-a7da693f8327
import copy
import unittest

from solution import atlag

CASES = [(([1, 2, 3, 4],), 2.5), (([],), None)]


def _call(args: tuple) -> str:
    return "atlag(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(atlag(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
