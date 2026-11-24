# AURI-CANARY-8a54431f-3a1b-5c4f-a310-b56feb209d18
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import taj_ervenyes

CASES = [(('123 456 788',), True),
 (('987654322',), True),
 (('000000000',), True),
 (('12345678',), False),
 (('1234567888',), False),
 (('12345678a',), False),
 (('123-456-788',), False),
 (('',), False),
 (('123  456 788',), False)]


def _call(args: tuple) -> str:
    return "taj_ervenyes(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(taj_ervenyes(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
