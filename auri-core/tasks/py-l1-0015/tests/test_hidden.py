# AURI-CANARY-f655c0fe-1e8d-5c67-9f7a-ae957f5d4dd9
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import camel_snake

CASES = [(('',), ''),
 (('alma',), 'alma'),
 (('Alma',), 'alma'),
 (('HTTP',), 'h_t_t_p'),
 (('aB',), 'a_b'),
 (('x1Y',), 'x1_y')]


def _call(args: tuple) -> str:
    return "camel_snake(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(camel_snake(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
