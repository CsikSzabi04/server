# AURI-CANARY-d1e1403d-cb8c-56fc-a626-50e32b0bb214
import copy
import unittest

from solution import ipv4_ervenyes

CASES = [(('192.168.0.1',), True), (('256.1.1.1',), False)]


def _call(args: tuple) -> str:
    return "ipv4_ervenyes(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(ipv4_ervenyes(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
