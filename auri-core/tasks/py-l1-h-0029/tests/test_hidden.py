# AURI-CANARY-bbb7e7a4-a514-5a6e-ad63-25d70aae5000
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import copy
import unittest

from solution import szigetek

CASES = [((['#.#', '.#.', '#.#'],), 5),
 ((['###', '#.#', '###'],), 1),
 ((['...', '...'],), 0),
 ((['#'],), 1),
 ((['##..', '#..#', '..##', '#...'],), 3)]


def _call(args: tuple) -> str:
    return "szigetek(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(szigetek(*copy.deepcopy(args)), want, msg=_call(args))


if __name__ == "__main__":
    unittest.main()
