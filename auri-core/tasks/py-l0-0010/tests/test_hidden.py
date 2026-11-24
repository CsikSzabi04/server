# AURI-CANARY-20851c4a-471b-5642-9337-a7da693f8327
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import atlag

CASES = [(([5],), 5.0), (([1, 2],), 1.5), (([1, 1, 2],), 1.33), (([-1.5, 1.5],), 0.0)]


def _call(args: tuple) -> str:
    return "atlag(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(atlag(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
