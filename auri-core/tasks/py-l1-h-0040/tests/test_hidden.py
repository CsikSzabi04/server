# AURI-CANARY-9ea9c482-407f-5ea8-bc8d-ae0f87bd4a84
# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import builtins
import copy
import unittest

from solution import hex_szin

CASES = [(('#000000',), [0, 0, 0]),
 (('#FFFFFF',), [255, 255, 255]),
 (('#1a2B3c',), [26, 43, 60]),
 (('#abc',), [170, 187, 204])]
ERRORS = [(('ff8800',), 'ValueError'),
 (('#ff880',), 'ValueError'),
 (('#ggg',), 'ValueError'),
 (('',), 'ValueError'),
 (('#ff88001',), 'ValueError'),
 (('#ff8800\n',), 'ValueError')]


def _call(args: tuple) -> str:
    return "hex_szin(" + ", ".join(map(repr, args)) + ")"


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        for args, want in CASES:
            with self.subTest(call=_call(args)):
                self.assertEqual(hex_szin(*copy.deepcopy(args)), want, msg=_call(args))

    def test_hibak(self) -> None:
        for args, exc in ERRORS:
            with self.subTest(call=_call(args)), self.assertRaises(getattr(builtins, exc), msg=_call(args)):
                hex_szin(*copy.deepcopy(args))


if __name__ == "__main__":
    unittest.main()
