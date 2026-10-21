"""
Main application entry point.

Starts a small local HTTP API (used by the optional browser view on a second
monitor) and the native PyQt6 HUD that lives on top of the game.
"""

import os
import sys
import threading
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from flask import Flask, jsonify, render_template

from card_db import CardDatabase
from tracker_engine import LoRClient

app = Flask(__name__, template_folder="templates")

card_db = CardDatabase("ru_ru")
lor_client = LoRClient(card_db)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def get_state():
    data = lor_client.update()
    if not data:
        return jsonify({"status": "offline"})
    if data.get("status") == "in_game":
        from advisor_engine import compute_counters, compute_threats
        advisor = compute_threats(data, card_db)
        data["threats"] = advisor["threats"]
        data["advisor"] = advisor
        data["counters"] = compute_counters(data, card_db)
    return jsonify(data)


def start_flask():
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


def main():
    print("=" * 52)
    print("   Legends of Runeterra - Deck Tracker HUD")
    print("=" * 52)
    print("1. Локальный API: http://127.0.0.1:5000")

    server_thread = threading.Thread(target=start_flask, daemon=True)
    server_thread.start()
    time.sleep(0.4)

    print("2. Запуск HUD оверлеев...")
    import pyqt_overlay
    pyqt_overlay.main()


if __name__ == "__main__":
    main()
