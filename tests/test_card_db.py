"""
Unit tests for CardDatabase and tactical advisor catalog.
"""

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from lor.card_db import CardDatabase
from lor.advisor_engine import build_catalog


class TestCardDatabase(unittest.TestCase):
    def setUp(self):
        self.db = CardDatabase("ru_ru", autoload=True)

    def test_database_loads_russian_cards(self):
        self.assertGreater(len(self.db.cards), 1000, "Should have over 1000 Russian cards cached")
        # Check a classic Demacia card
        # Garen = 01DE012
        card = self.db.get_card("01DE012")
        self.assertIsNotNone(card, "Garen (01DE012) must exist")
        self.assertEqual(card.get("name"), "Гарен", "Garen should be localized to Гарен")
        self.assertEqual(card.get("cost"), 5)

    def test_region_icons_exist(self):
        regions = ["Demacia", "Noxus", "Ionia", "Freljord", "ShadowIsles", "Bilgewater", "Shurima", "Targon", "BandleCity", "Runeterra"]
        for reg in regions:
            icon = self.db.get_region_icon(reg)
            self.assertIsNotNone(icon, f"Icon for {reg} should resolve")
            self.assertTrue(os.path.exists(icon), f"Icon file for {reg} must exist on disk: {icon}")

    def test_threat_catalog(self):
        catalog = build_catalog(self.db)
        self.assertGreater(len(catalog), 50, "Threat catalog should have combat tricks and answers")


if __name__ == "__main__":
    unittest.main()
