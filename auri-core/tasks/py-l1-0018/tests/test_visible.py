# AURI-CANARY-bae43364-2374-5789-891e-859f0311637c
import copy
import unittest

from solution import idotartam_mp

CASES = [(('1h 30m',), 5400), (('45s',), 45)]


def _call(args: tuple) -> str:
    return "idotartam_mp(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(idotartam_mp(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
