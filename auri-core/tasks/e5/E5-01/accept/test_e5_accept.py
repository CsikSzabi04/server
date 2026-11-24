import unittest

from formaz import szoveg
from lista import hozzaad, osszesen, torol


class TestElfogadas(unittest.TestCase):
    def test_hozzaad_osszesen(self) -> None:
        lst: dict[str, int] = {}
        hozzaad(lst, "tej", 2)
        hozzaad(lst, "kenyér", 1)
        hozzaad(lst, "tej", 3)
        self.assertEqual(lst, {"tej": 5, "kenyér": 1})
        self.assertEqual(osszesen(lst), 6)

    def test_hibak(self) -> None:
        lst = {"tej": 1}
        with self.assertRaises(ValueError):
            hozzaad(lst, "alma", 0)
        with self.assertRaises(KeyError):
            torol(lst, "alma")
        torol(lst, "tej")
        self.assertEqual(lst, {})

    def test_szoveg(self) -> None:
        self.assertEqual(szoveg({"tej": 2, "alma": 3}), "alma: 3\ntej: 2")
        self.assertEqual(szoveg({}), "")
