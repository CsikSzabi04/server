# AURI-CANARY-b441ad6a-a775-5482-8e0f-43e87d017ee1
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import tobbi_szorzata

CASES = [(([5],), [1]),
 (([2, 0, 3],), [0, 6, 0]),
 (([0, 0, 2],), [0, 0, 0]),
 (([-1, 2, -3],), [-6, 3, -2]),
 (([1, 1],), [1, 1])]


def _call(args: tuple) -> str:
    return "tobbi_szorzata(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(tobbi_szorzata(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
