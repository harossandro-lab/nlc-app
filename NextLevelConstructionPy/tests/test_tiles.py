"""Tile list tests (no Qt needed). Same expectations as the Java SmokeCheck menu checks."""
import unittest

from nlc import tiles
from nlc.seed import SECTIONS


class TilesTests(unittest.TestCase):
    def test_order_and_count(self):
        ids = [t[0] for t in tiles.TILES]
        want = ["dashboard"] + [s["id"] for s in SECTIONS] + ["ordered", "received", "audit", "database", "suppliers"]
        self.assertEqual(ids, want)
        self.assertEqual(len(ids), 19)

    def test_abbreviations_match_the_web_circles(self):
        got = [tiles.abbreviate(label) for _, label in tiles.TILES]
        self.assertEqual(got, ["DASH", "SF", "1W", "2W", "3W", "4W", "5W", "6W", "RF", "FB", "SW", "ST", "BAL",
                               "WIN", "ORD", "RCV", "AUD", "DB", "TAX"])

    def test_unknown_label_uses_initials(self):
        self.assertEqual(tiles.abbreviate("My Custom Screen"), "MCS")


if __name__ == "__main__":
    unittest.main()
