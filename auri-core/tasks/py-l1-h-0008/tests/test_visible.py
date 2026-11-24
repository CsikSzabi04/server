# AURI-CANARY-40b5b27d-88e0-5865-b1ce-7e94cda62213
import copy
import unittest

from solution import spiral

CASES = [(([[1, 2], [3, 4]],), [1, 2, 4, 3]), (([],), [])]


def _call(args: tuple) -> str:
    return "spiral(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(spiral(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
