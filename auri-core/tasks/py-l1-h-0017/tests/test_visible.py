# AURI-CANARY-4ec8c631-2174-5e1a-a568-dd387eda0eb3
import copy
import unittest

from solution import kozos_elotag

CASES = [((['virág', 'virágzik', 'virgonc'],), 'vir'), (([],), '')]


def _call(args: tuple) -> str:
    return "kozos_elotag(" + ", ".join(map(repr, args)) + ")"


class TestVisible(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(kozos_elotag(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
