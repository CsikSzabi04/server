# AURI-CANARY-24dc8a0e-5dc9-5b07-bcc5-3ca97f3ca1f0
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import transzponal

CASES = [(([],), []), (([[1]],), [[1]]), (([[1, 2]],), [[1], [2]]), (([[1], [2]],), [[1, 2]])]
ERRORS = [(([[1, 2], [3]],), 'ValueError')]


def _call(args: tuple) -> str:
    return "transzponal(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(transzponal(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                transzponal(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
