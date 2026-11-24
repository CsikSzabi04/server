# AURI-CANARY-7029c79e-5c99-5446-9c30-d345adc67520
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import palindrom

CASES = [(('',), True),
 (('Géza, kék az ég!',), True),
 (('Ab1ba',), True),
 (('ége',), False),
 (('12321',), True),
 (('12 3',), False),
 (('!!!',), True)]


def _call(args: tuple) -> str:
    return "palindrom(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(palindrom(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
