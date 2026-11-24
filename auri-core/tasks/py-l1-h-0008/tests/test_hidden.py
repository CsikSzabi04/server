# AURI-CANARY-40b5b27d-88e0-5865-b1ce-7e94cda62213
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import spiral

CASES = [(([[1, 2, 3], [4, 5, 6], [7, 8, 9]],), [1, 2, 3, 6, 9, 8, 7, 4, 5]),
 (([[1, 2], [3, 4], [5, 6]],), [1, 2, 4, 6, 5, 3]),
 (([[1], [2], [3]],), [1, 2, 3]),
 (([[1, 2, 3]],), [1, 2, 3]),
 (([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]],), [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7])]


def _call(args: tuple) -> str:
    return "spiral(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(spiral(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
