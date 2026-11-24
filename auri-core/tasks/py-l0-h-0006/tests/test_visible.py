# AURI-CANARY-04c83581-2c74-5fa3-a124-9bf5cad4f319
import copy
import unittest

from solution import kezdobetuk

CASES = [(('magyar tudományos akadémia',), 'MTA'), (('',), '')]


def _call(args: tuple) -> str:
    return "kezdobetuk(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(kezdobetuk(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
