# AURI-CANARY-f655c0fe-1e8d-5c67-9f7a-ae957f5d4dd9
import copy
import unittest

from solution import camel_snake

CASES = [(('parseForintValue',), 'parse_forint_value')]


def _call(args: tuple) -> str:
    return "camel_snake(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(camel_snake(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
