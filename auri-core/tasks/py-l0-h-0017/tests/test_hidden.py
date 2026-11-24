# AURI-CANARY-ab924bfe-5fe4-5881-bb0a-f549e485be9a
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import van_ismetlodes

CASES = [(([],), False), (([0, 0],), True), (([-1, 1],), False), (([5, 4, 3, 2, 1, 5],), True)]


def _call(args: tuple) -> str:
    return "van_ismetlodes(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(van_ismetlodes(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
