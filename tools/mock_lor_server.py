"""
Mock game server for local testing when LoR client is not actively in a match.
Emulates http://127.0.0.1:21337/ endpoints with realistic match progression:
- Turn 1: Initial draw (4 cards in hand)
- Turn 2: Play unit, opponent plays unit
- Turn 3: Combat phase, spells on stack
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

MOCK_DECK = {
    "DeckCode": "CEBAIAIEDMPTINQGAECBAGRHFMYTQAQBAEBTEBIBAMBA6HJGGUAQCAIEGQ",
    "CardsInDeck": {
        "01PZ008": 3, # Teemo
        "01PZ052": 3, # Mystic Shot
        "05BC164": 3, # Poison Dart
        "01PZ025": 3, # Puffcap Peddler
        "05PZ010": 3, # Advanced Intel
        "01PZ039": 2, # Ezreal
        "01PZ027": 3, # Thermogenic Beam
        "02PZ008": 2  # Gotcha!
    }
}

class MockLoRHandler(BaseHTTPRequestHandler):
    start_time = time.time()

    def log_message(self, format, *args):
        pass # Suppress noisy logs

    def do_GET(self):
        elapsed = int(time.time() - self.start_time)

        if self.path == "/static-decklist":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(MOCK_DECK).encode("utf-8"))
            return

        elif self.path == "/game-result":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"GameID": 1, "LocalPlayerWon": True}).encode("utf-8"))
            return

        elif self.path == "/positional-rectangles":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            # Dynamic game state based on elapsed time:
            # 0-3s: In Hand only
            # 4-10s: Opponent plays Shadow Isles unit (Sinister Poro / Elise)
            # >10s: Player plays Teemo to board
            rects = [
                {"CardID": 100, "CardCode": "face", "TopLeftX": 83, "TopLeftY": 481, "Width": 117, "Height": 117, "LocalPlayer": True},
                {"CardID": 101, "CardCode": "face", "TopLeftX": 83, "TopLeftY": 716, "Width": 117, "Height": 117, "LocalPlayer": False},
                {"CardID": 201, "CardCode": "05BC164", "TopLeftX": 440, "TopLeftY": 80, "Width": 175, "Height": 245, "LocalPlayer": True},
                {"CardID": 202, "CardCode": "01PZ052", "TopLeftX": 607, "TopLeftY": 85, "Width": 176, "Height": 246, "LocalPlayer": True},
                {"CardID": 203, "CardCode": "01PZ025", "TopLeftX": 775, "TopLeftY": 85, "Width": 177, "Height": 247, "LocalPlayer": True},
                {"CardID": 204, "CardCode": "05PZ010", "TopLeftX": 944, "TopLeftY": 81, "Width": 178, "Height": 248, "LocalPlayer": True},
            ]

            # Opponent plays Shadow Isles card
            rects.append({"CardID": 301, "CardCode": "01SI037", "TopLeftX": 800, "TopLeftY": 980, "Width": 127, "Height": 160, "LocalPlayer": False})

            # Player Teemo in hand or on board
            if elapsed > 5:
                # Teemo on board (TopLeftY > 250)
                rects.append({"CardID": 200, "CardCode": "01PZ008", "TopLeftX": 600, "TopLeftY": 400, "Width": 176, "Height": 246, "LocalPlayer": True})
            else:
                # Teemo in hand (TopLeftY < 250)
                rects.append({"CardID": 200, "CardCode": "01PZ008", "TopLeftX": 270, "TopLeftY": 80, "Width": 176, "Height": 246, "LocalPlayer": True})

            response = {
                "PlayerName": "BorisPlayer",
                "OpponentName": "SI_Control_Master",
                "GameState": "InProgress",
                "Screen": {"ScreenWidth": 1920, "ScreenHeight": 1080},
                "Rectangles": rects
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

        else:
            self.send_response(404)
            self.end_headers()

def run_mock_server(port=21337):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, MockLoRHandler)
    print(f"Mock LoR Game Client API running on http://127.0.0.1:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_mock_server()
