"""
Unit tests for PyQt6 Overlay rendering pipeline with realistic game state.
"""

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PyQt6 import QtWidgets, QtCore
from lor.card_db import CardDatabase
from lor.widgets import ArtCache
from lor.preview import CardPreview
from lor.panels import PlayerPanel, OpponentPanel
from lor.advisor import AdvisorBar
from lor.advisor_engine import get_threats_for_regions


class TestOverlayRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance()
        if cls.app is None:
            cls.app = QtWidgets.QApplication([])
        cls.db = CardDatabase("ru_ru", autoload=True)
        cls.art = ArtCache(cls.db)

    def setUp(self):
        self.preview = CardPreview(self.db, self.art)
        self.player_panel = PlayerPanel(
            self.db, self.art, self.preview,
            on_open_settings=lambda: None,
            on_lock_toggle=lambda locked: None,
        )
        self.opp_panel = OpponentPanel(
            self.db, self.art, self.preview,
            on_open_settings=lambda: None,
            on_lock_toggle=lambda locked: None,
        )
        self.advisor_bar = AdvisorBar(self.preview)

    def tearDown(self):
        self.preview.close()
        self.player_panel.close()
        self.opp_panel.close()
        self.advisor_bar.close()

    def test_full_mock_game_render(self):
        threats = get_threats_for_regions(["ShadowIsles", "Freljord"], card_db=self.db)

        mock_data = {
            "status": "in_game",
            "playerName": "goderfly",
            "opponentName": "SI_Control",
            "totalRemaining": 33,
            "totalInitial": 40,
            "myDeck": [
                {"code": "06DE048", "name": "Барсук-преградитель", "cost": 3, "type": "Unit", "supertype": "", "spellSpeed": "", "regions": ["Demacia"], "remaining": 3, "initial": 3, "prob": 9.1},
                {"code": "01DE012", "name": "Гарен", "cost": 5, "type": "Unit", "supertype": "Champion", "spellSpeed": "", "regions": ["Demacia"], "remaining": 2, "initial": 3, "prob": 6.1},
                {"code": "01DE020", "name": "Один на один", "cost": 2, "type": "Spell", "supertype": "", "spellSpeed": "Быстрое", "regions": ["Demacia"], "remaining": 1, "initial": 3, "prob": 3.0},
                {"code": "04SH073", "name": "Рек'Сай", "cost": 3, "type": "Unit", "supertype": "Champion", "spellSpeed": "", "regions": ["Shurima"], "remaining": 0, "initial": 3, "prob": 0.0},
            ],
            "myGraveyard": [
                {"code": "04SH073", "name": "Рек'Сай", "cost": 3, "count": 3}
            ],
            "myHand": [{"code": "01DE012", "name": "Гарен", "cost": 5}],
            "myBoard": [],
            "opponentBoard": [{"code": "01FR039", "name": "Юркий поро", "cost": 1}],
            "opponentPlayed": [{"code": "01FR039", "name": "Юркий поро", "cost": 1, "count": 2}],
            "opponentHandCount": 4,
            "opponentMulliganKept": 2,
            "opponentRegions": ["ShadowIsles", "Freljord"],
            "opponentUnitMana": 3,
            "opponentSpellMana": 3,
            "hasAttackToken": True,
            "threats": threats,
            "counters": {"puffcaps": 5, "puffcap_avg_dmg": 0.65, "hallowed": 2},
        }

        # Render player deck panel
        self.player_panel.update_state(mock_data)
        self.assertGreater(len(self.player_panel.tiles), 0, "Player panel should create card tiles")
        self.assertIn("06DE048", self.player_panel.tiles)

        # Render opponent panel
        self.opp_panel.update_state(mock_data)
        self.assertGreater(len(self.opp_panel.played_rows), 0, "Opponent panel should render played cards")
        self.assertEqual(self.opp_panel.hand_strip.count, 4)
        self.assertEqual(self.opp_panel.hand_strip.mulligan, 2)

        # Render tactical advisor bar
        self.advisor_bar.update_state(mock_data)
        self.assertEqual(self.advisor_bar.state.get("status"), "in_game")

        # Tooltip preview
        self.preview.show_card("06DE048", near_rect=QtCore.QRect(100, 100, 200, 30))
        self.assertTrue(self.preview.isVisible())
        self.assertEqual(self.preview.card.get("name"), "Барсук-преградитель")


if __name__ == "__main__":
    unittest.main()
