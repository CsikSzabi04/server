# AURI-CANARY-71492f46-9258-5953-a3f9-6a2f0bf69eca
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import ismetel

CASES = [(('x', 1, ','), 'x'), (('', 3, '|'), '||'), (('hó', 2, ''), 'hóhó'), (('a', -2, '-'), '')]


def _call(args: tuple) -> str:
    return "ismetel(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(ismetel(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
