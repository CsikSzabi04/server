# AURI-CANARY-9b2587ba-e5ff-52ae-b375-b80d86780636
import copy
import unittest

from solution import csere

CASES = [(('AlMa',), 'aLmA'), (('',), '')]


def _call(args: tuple) -> str:
    return "csere(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(csere(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
