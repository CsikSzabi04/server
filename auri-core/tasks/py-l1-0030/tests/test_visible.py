# AURI-CANARY-d9683aef-489e-5c68-98be-c0f3edbba9db
import copy
import unittest

from solution import datum

CASES = [(('2026.11.21.',), (2026, 11, 21)), (('2026. 11. 21.',), (2026, 11, 21))]


def _call(args: tuple) -> str:
    return "datum(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(datum(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
