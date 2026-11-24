# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import random
import unittest

from solution import parse_forint


class TestHidden(unittest.TestCase):
    def test_ervenyes(self) -> None:
        cases = [
            ("-500 Ft", -500),
            ("1 000 Ft", 1000),
            ("  7 Ft ", 7),
            ("0 Ft", 0),
            ("1234 Ft", 1234),
            ("-12 000 HUF", -12000),
            ("5   HUF", 5),
        ]
        for s, v in cases:
            with self.subTest(s=s):
                self.assertEqual(parse_forint(s), v)

    def test_nem_torheto_szokoz(self) -> None:
        self.assertEqual(parse_forint("1\u00a0234\u00a0567 Ft"), 1234567)

    def test_ervenytelen(self) -> None:
        for s in ["abc", "Ft", "", "   ", "12", "Ft 12"]:
            with self.subTest(s=s), self.assertRaises(ValueError):
                parse_forint(s)

    def test_oda_vissza(self) -> None:
        rng = random.Random(20261121)
        for _ in range(300):
            n = rng.randint(-10**9, 10**9)
            sep = rng.choice([" ", "\u00a0"])
            currency = rng.choice(["Ft", "HUF"])
            s = f"{n:,}".replace(",", sep) + " " + currency
            with self.subTest(s=s):
                self.assertEqual(parse_forint(s), n)


if __name__ == "__main__":
    unittest.main()
