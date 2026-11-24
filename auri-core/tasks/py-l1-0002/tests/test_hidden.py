# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import unittest

from solution import monogram


class TestHidden(unittest.TestCase):
    def test_esetek(self) -> None:
        cases = [
            ("Minta Máté", "M. M."),
            ("  minta   máté  ", "M. M."),
            ("\tMinta\nMáté ", "M. M."),
            ("szabó ábel", "Sz. Á."),
            ("Nyári Tóth Ödön", "Ny. T. Ö."),
            ("Tyukodi Zsuzsa", "Ty. Zs."),
            ("Gyenge Lyukas", "Gy. Ly."),
            ("CSABA", "Cs."),
            ("a", "A."),
            ("Sz", "Sz."),
        ]
        for nev, want in cases:
            with self.subTest(nev=nev):
                self.assertEqual(monogram(nev), want)

    def test_dzs_elsobbseg(self) -> None:
        self.assertEqual(monogram("Dzsungel Dzurkó"), "Dzs. Dz.")
        self.assertEqual(monogram("DZSUNGEL"), "Dzs.")
        self.assertEqual(monogram("dzurkó"), "Dz.")

    def test_csak_szokoz(self) -> None:
        self.assertEqual(monogram("   "), "")
        self.assertEqual(monogram("\t\n"), "")


if __name__ == "__main__":
    unittest.main()
