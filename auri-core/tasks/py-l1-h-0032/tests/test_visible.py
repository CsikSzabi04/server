# AURI-CANARY-8f305171-cdb0-548f-b497-5a934452c79e
import copy
import unittest

from solution import csucsok

CASES = [(([1, 3, 2],), [1]), (([],), [])]


def _call(args: tuple) -> str:
    return "csucsok(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(csucsok(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
