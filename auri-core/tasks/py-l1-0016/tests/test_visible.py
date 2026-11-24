# AURI-CANARY-f88066e7-2679-52b2-b839-ca66b8c50f80
import copy
import unittest

from solution import snake_camel

CASES = [(('parse_forint_value',), 'parseForintValue')]


def _call(args: tuple) -> str:
    return "snake_camel(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(snake_camel(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
