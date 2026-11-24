# AURI-CANARY-d1e1403d-cb8c-56fc-a626-50e32b0bb214
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import ipv4_ervenyes

CASES = [(('0.0.0.0',), True),
 (('255.255.255.255',), True),
 (('01.2.3.4',), False),
 (('1.2.3',), False),
 (('1.2.3.4.5',), False),
 (('1.2..4',), False),
 (('1.2.3.-4',), False),
 ((' 1.2.3.4',), False),
 (('1.2.3.4a',), False),
 (('1000.1.1.1',), False)]


def _call(args: tuple) -> str:
    return "ipv4_ervenyes(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(ipv4_ervenyes(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
