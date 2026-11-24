import unittest

from index import epit, szavak
from kereso import keres

DOCS = {"a": "alma körte", "b": "Körte, szilva!", "c": "alma alma"}


class TestElfogadas(unittest.TestCase):
    def test_szavak(self) -> None:
        self.assertEqual(szavak("Alma, KÖRTE! 3 db"), ["alma", "körte", "3", "db"])
        self.assertEqual(szavak(""), [])

    def test_epit(self) -> None:
        self.assertEqual(epit(DOCS), {"alma": ["a", "c"], "körte": ["a", "b"], "szilva": ["b"]})

    def test_keres(self) -> None:
        idx = epit(DOCS)
        self.assertEqual(keres(idx, "körte"), ["a", "b"])
        self.assertEqual(keres(idx, "alma körte"), ["a"])
        self.assertEqual(keres(idx, "ALMA"), ["a", "c"])
        self.assertEqual(keres(idx, "barack"), [])
        self.assertEqual(keres(idx, " ,"), [])
