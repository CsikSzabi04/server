# HIDDEN: never shown to the model; checks only behaviour stated in prompt_hu.
import random
import unittest
from collections import Counter

from solution import top_words


class TestHidden(unittest.TestCase):
    def test_kisbetu(self) -> None:
        self.assertEqual(top_words("Alma ALMA alma", 5), [("alma", 3)])

    def test_iras_jelek_es_szamok(self) -> None:
        self.assertEqual(top_words("Szia! Szia, világ.", 5), [("szia", 2), ("világ", 1)])
        self.assertEqual(top_words("ab12ab", 3), [("ab", 2)])

    def test_alapertelmezett_rendezes(self) -> None:
        # code-point order: "z" < "á"
        self.assertEqual(top_words("zebra ábel", 2), [("zebra", 1), ("ábel", 1)])

    def test_k_hatarok(self) -> None:
        self.assertEqual(top_words("egy kettő három", 0), [])
        self.assertEqual(top_words("egy kettő kettő", 10), [("kettő", 2), ("egy", 1)])

    def test_negativ_k(self) -> None:
        with self.assertRaises(ValueError):
            top_words("alma", -1)

    def test_veletlen_szovegek(self) -> None:
        rng = random.Random(20261121)
        vocab = ["alma", "Körte", "szilva", "ŐSZ", "nyár", "tél"]
        seps = [" ", ", ", "!", "\n", "-", "  ", "1"]
        for _ in range(200):
            words = [rng.choice(vocab) for _ in range(rng.randint(0, 30))]
            text = "".join(w + rng.choice(seps) for w in words)
            k = rng.randint(0, 8)
            counts = Counter(w.lower() for w in words)
            want = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
            with self.subTest(text=text, k=k):
                self.assertEqual(top_words(text, k), want)


if __name__ == "__main__":
    unittest.main()
