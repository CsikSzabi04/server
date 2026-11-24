# AURI-CANARY-3e2c44de-20ea-59f3-a3d9-5055539751a5
import copy
import unittest

from solution import szo_minta

CASES = [(('abba', 'kutya macska macska kutya'), True), (('abba', 'kutya macska macska hal'), False)]


def _call(args: tuple) -> str:
    return "szo_minta(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szo_minta(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
