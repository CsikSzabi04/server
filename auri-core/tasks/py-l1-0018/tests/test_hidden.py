# AURI-CANARY-bae43364-2374-5789-891e-859f0311637c
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import idotartam_mp

CASES = [(('2h',), 7200),
 (('1h 1m 1s',), 3661),
 (('90m',), 5400),
 (('0s',), 0),
 (('10m 5s',), 605),
 (('1h 5s',), 3605)]
ERRORS = [(('',), 'ValueError'),
 (('1x',), 'ValueError'),
 (('30m 1h',), 'ValueError'),
 (('h',), 'ValueError'),
 (('1h 1h',), 'ValueError'),
 (('1h30m',), 'ValueError')]


def _call(args: tuple) -> str:
    return "idotartam_mp(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(idotartam_mp(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                idotartam_mp(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
