# AURI-CANARY-6d139bcb-7db7-57c9-ab7d-93fdba493bea
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import isbn10_ervenyes

CASES = [(('0306406152',), True),
 (('0-8044-2957-X',), True),
 (('0-8044-2957-x',), False),
 (('X-8044-2957-0',), False),
 (('030640615',), False),
 (('03064061522',), False),
 (('',), False),
 (('0 306 40615 2',), False)]


def _call(args: tuple) -> str:
    return "isbn10_ervenyes(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(isbn10_ervenyes(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
