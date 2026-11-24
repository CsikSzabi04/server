# AURI-CANARY-34985e85-6a82-5388-bbed-d878e314cedd
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import luhn

CASES = [(('7992 7398 713',), True),
 (('059',), True),
 (('0',), False),
 ((' 0',), False),
 (('0000 0',), True),
 (('055-444',), False),
 (('59',), True),
 (('8a',), False)]


def _call(args: tuple) -> str:
    return "luhn(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(luhn(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
