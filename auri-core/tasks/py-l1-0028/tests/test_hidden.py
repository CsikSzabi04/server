# AURI-CANARY-d579e180-1824-53ed-857d-fe7a0dff7851
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import zarojelek

CASES = [(('',), True),
 (('a(b)c',), True),
 (('(',), False),
 ((')(',), False),
 (('([)]',), False),
 (('{[()()]}',), True),
 (('((x)',), False)]


def _call(args: tuple) -> str:
    return "zarojelek(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(zarojelek(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
