import unittest

from solution import top_words


class TestVisible(unittest.TestCase):
    def test_alap(self) -> None:
        self.assertEqual(top_words("alma körte alma", 1), [("alma", 2)], msg='top_words("alma körte alma", 1)')

    def test_egyenloseg(self) -> None:
        self.assertEqual(top_words("b a b a c", 2), [("a", 2), ("b", 2)], msg='top_words("b a b a c", 2)')

    def test_ures(self) -> None:
        self.assertEqual(top_words("", 3), [], msg='top_words("", 3)')


if __name__ == "__main__":
    unittest.main()
