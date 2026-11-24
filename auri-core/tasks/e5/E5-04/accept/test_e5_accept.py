import unittest

from naplo import beolvas
from statisztika import napi

SOROK = ["2026-11-21 4.5", "2026-11-21 -1", "rossz sor", "2026-11-22 10", "2026-11-22 abc", "", "26-11-22 3", "2026-11-22"]


class TestElfogadas(unittest.TestCase):
    def test_beolvas(self) -> None:
        self.assertEqual(beolvas(SOROK), [("2026-11-21", 4.5), ("2026-11-21", -1.0), ("2026-11-22", 10.0)])
        self.assertEqual(beolvas([]), [])

    def test_napi(self) -> None:
        m = [("2026-11-21", 4.5), ("2026-11-21", -1.0), ("2026-11-22", 10.0)]
        self.assertEqual(napi(m), {"2026-11-21": (-1.0, 4.5, 1.75), "2026-11-22": (10.0, 10.0, 10.0)})
