# AURI-CANARY-6d139bcb-7db7-57c9-ab7d-93fdba493bea
import copy
import unittest

from solution import isbn10_ervenyes

CASES = [(('0-306-40615-2',), True), (('0-306-40615-3',), False)]


def _call(args: tuple) -> str:
    return "isbn10_ervenyes(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(isbn10_ervenyes(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
