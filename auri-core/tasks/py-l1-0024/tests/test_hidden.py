# AURI-CANARY-80fc3a0f-27a3-57eb-82b9-3490214d8931
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import primek

CASES = [((1,), []), ((2,), [2]), ((-5,), []), ((30,), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])]


def _call(args: tuple) -> str:
    return "primek(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(primek(*copy.deepcopy(args)), want, msg=_call(args))

    def test_sok(self) -> None:
        self.assertEqual(len(primek(10000)), 1229, msg='len(primek(10000))')


if __name__ == "__main__":
    unittest.main()
