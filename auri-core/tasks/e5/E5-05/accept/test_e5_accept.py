import unittest

from main import futtat
from szamlalo import szamol
from top import top


class TestElfogadas(unittest.TestCase):
    def test_szamol(self) -> None:
        self.assertEqual(szamol("Alma, alma! Körte. ?"), {"alma": 2, "körte": 1})
        self.assertEqual(szamol(""), {})

    def test_top(self) -> None:
        self.assertEqual(top({"b": 2, "a": 2, "c": 5}, 2), [("c", 5), ("a", 2)])
        self.assertEqual(top({}, 3), [])
        self.assertEqual(top({"a": 1}, 0), [])

    def test_futtat(self) -> None:
        self.assertEqual(futtat("x y x. Y z!", 2), "x: 2\ny: 2")
