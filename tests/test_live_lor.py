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

db = CardDatabase('ru_ru')
client = LoRClient(db)
data = client.update()

print("Status:", data.get("status"))
print("Player:", data.get("playerName"), "vs", data.get("opponentName"))
print("Remaining deck cards count:", data.get("totalRemaining"))

print("\nDeck cards:")
for c in data.get("myDeck", []):
    print(f"  - [{c['cost']}m] {c['name']} (осталось: {c['remaining']}/{c['initial']}, шанс: {c['prob']}%)")

print(f"\nHand cards ({len(data.get('myHand', []))}):")
for c in data.get("myHand", []):
    print(f"  - [{c['cost']}m] {c['name']}")

print(f"\nOpponent board cards ({len(data.get('opponentBoard', []))}):")
for c in data.get("opponentBoard", []):
    print(f"  - [{c['cost']}m] {c['name']}")

print("\nOpponent regions:", data.get("opponentRegions", []))
threats = get_threats_for_regions(data.get("opponentRegions", []))
print(f"Identified threats ({len(threats)}):")
for t in threats:
    print(f"  - [{t['speed']}] {t.get('nameRu', t['name'])} ({t['cost']}m): {t['warning']}")
