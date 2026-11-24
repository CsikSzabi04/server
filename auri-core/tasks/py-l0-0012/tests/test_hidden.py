# AURI-CANARY-84848832-e492-5dd5-9ad3-803e15c171df
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import szorzotabla

CASES = [((0,), []), ((1,), [[1]]), ((3,), [[1, 2, 3], [2, 4, 6], [3, 6, 9]]), ((-1,), [])]


def _call(args: tuple) -> str:
    return "szorzotabla(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szorzotabla(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
