"""
Mock test runner to verify tracker logic and mock game state data against real user sample.
"""

import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from lor.card_db import CardDatabase
from lor.tracker_engine import LoRClient
from lor.advisor_engine import get_threats_for_regions

def test_simulation():
    db = CardDatabase()
    client = LoRClient(db)

    # Mock user game state from prompt:
    user_sample_rectangles = [
        {"CardID":1619740988,"CardCode":"face","TopLeftX":83,"TopLeftY":481,"Width":117,"Height":117,"LocalPlayer":True},
        {"CardID":1446855479,"CardCode":"face","TopLeftX":83,"TopLeftY":716,"Width":117,"Height":117,"LocalPlayer":False},
        {"CardID":1972509950,"CardCode":"05BC164","TopLeftX":440,"TopLeftY":80,"Width":175,"Height":245,"LocalPlayer":True},
        {"CardID":1468602481,"CardCode":"01PZ008","TopLeftX":607,"TopLeftY":85,"Width":176,"Height":246,"LocalPlayer":True},
        {"CardID":424441374,"CardCode":"05PZ010","TopLeftX":775,"TopLeftY":85,"Width":177,"Height":247,"LocalPlayer":True},
        {"CardID":923134223,"CardCode":"01PZ025","TopLeftX":944,"TopLeftY":81,"Width":178,"Height":248,"LocalPlayer":True},
        {"CardID":1176831411,"CardCode":"01SI037","TopLeftX":800,"TopLeftY":980,"Width":127,"Height":160,"LocalPlayer":False},
        {"CardID":1563442685,"CardCode":"01PZ052","TopLeftX":1115,"TopLeftY":72,"Width":178,"Height":249,"LocalPlayer":True}
    ]

    # Mock static deck
    client.in_game = True
    client.player_name = "goderfly"
    client.opponent_name = "decks_easythresh_name"
    client.initial_deck = {
        "05BC164": 3,
        "01PZ008": 3,
        "05PZ010": 3,
        "01PZ025": 3,
        "01PZ052": 3,
        "01PZ040": 3 # Mystic Shot
    }

    my_hand, my_board, opp_board, spell_stack = client.classify_rectangles(user_sample_rectangles, 1728, 1080)
    client.my_hand = my_hand
    client.my_board = my_board
    client.opp_board = opp_board

    payload = client.get_tracker_payload()
    print("Classified Hand cards:", [c["name"] for c in payload["myHand"]])
    print("Classified Opponent units:", [c["name"] for c in payload["opponentBoard"]])
    print("Detected Opponent regions:", payload["opponentRegions"])
    
    threats = get_threats_for_regions(payload["opponentRegions"])
    print(f"Identified {len(threats)} potential threats for opponent regions:")
    for t in threats:
        print(f"  - [{t['speed']}] {t['name']} ({t['cost']}m): {t['warning']}")

    print("\nTop remaining deck calculations:")
    for item in payload["myDeck"][:5]:
        print(f"  - {item['name']}: {item['remaining']}/{item['initial']} left ({item['prob']}%)")

if __name__ == "__main__":
    test_simulation()
