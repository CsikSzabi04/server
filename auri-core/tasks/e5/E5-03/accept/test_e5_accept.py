import unittest

from ar import brutto
from kosar import vegosszeg
from nyugta import nyugta

T = [(100, 27, 2), (50, 27, 1)]


class TestElfogadas(unittest.TestCase):
    def test_brutto(self) -> None:
        self.assertEqual([brutto(100, 27), brutto(50, 27), brutto(10, 5), brutto(0, 27), brutto(2, 27)], [127, 64, 11, 0, 3])
        for args in ((-1, 27), (1, -5)):
            with self.assertRaises(ValueError):
                brutto(*args)

    def test_vegosszeg(self) -> None:
        self.assertEqual(vegosszeg(T), 318)
        self.assertEqual(vegosszeg([]), 0)

    def test_nyugta(self) -> None:
        self.assertEqual(nyugta(T), ["2 x 127 Ft = 254 Ft", "1 x 64 Ft = 64 Ft", "ÖSSZESEN: 318 Ft"])
        self.assertEqual(nyugta([]), ["ÖSSZESEN: 0 Ft"])
