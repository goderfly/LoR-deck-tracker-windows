"""
Utility script to fetch and update the Russian card database from Riot DataDragon.
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from lor.card_db import CardDatabase


def main():
    print("[*] Initializing CardDatabase...")
    db = CardDatabase("ru_ru", autoload=False)
    print("[*] Fetching all sets from Riot DataDragon CDN for 'ru_ru'...")
    cards = db.fetch_all("ru_ru")
    print(f"[+] Successfully fetched {len(cards)} cards.")
    globals_data = db.fetch_globals("ru_ru")
    print(f"[+] Fetched globals with {len(globals_data.get('regions', []))} regions.")


if __name__ == "__main__":
    main()
