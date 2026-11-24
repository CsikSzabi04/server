import unittest

from solution import parse_forint


class TestVisible(unittest.TestCase):
    def test_alap(self) -> None:
        self.assertEqual(parse_forint("1 234 Ft"), 1234, msg='parse_forint("1 234 Ft")')
        self.assertEqual(parse_forint("12 000 HUF"), 12000, msg='parse_forint("12 000 HUF")')

    def test_negativ(self) -> None:
        self.assertEqual(parse_forint("-500 Ft"), -500, msg='parse_forint("-500 Ft")')

    def test_ervenytelen(self) -> None:
        with self.assertRaises(ValueError, msg='parse_forint("abc")'):
            parse_forint("abc")


if __name__ == "__main__":
    unittest.main()
