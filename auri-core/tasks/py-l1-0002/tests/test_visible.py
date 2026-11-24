import unittest

from solution import monogram


class TestVisible(unittest.TestCase):
    def test_alap(self) -> None:
        self.assertEqual(monogram("Teszt Elek"), "T. E.", msg='monogram("Teszt Elek")')

    def test_ketjegyu(self) -> None:
        self.assertEqual(monogram("Csizmadia Zsófia"), "Cs. Zs.", msg='monogram("Csizmadia Zsófia")')

    def test_ures(self) -> None:
        self.assertEqual(monogram(""), "", msg='monogram("")')


if __name__ == "__main__":
    unittest.main()
