"""
Legends of Runeterra client poller and state tracker.

Design notes
------------
The in-game overlay must never flicker or collapse, therefore this module is
built around three rules:

1. **Classify by rendering size, not by screen position.** The LoR client
   renders hand cards large (~176x247), board units small (~127x160) and
   cards on the stack horizontally (~274x158). Screen coordinates are game
   world coordinates and are unusable for classification.
2. **Never trust a single poll.** A half-second long ``InProgress`` payload
   with an empty rectangle list is a normal animation artefact. The tracker
   keeps the last coherent snapshot alive for a couple of seconds instead of
   blanking the UI.
3. **Track by persistent ``CardID``.** The same card keeps its id for the
   whole match, so a card that leaves the hand and hits the board (or dies)
   is still accounted for and never "returns to the deck".
"""

import time
import logging
import requests

logger = logging.getLogger("LoRClient")

LOR_API_BASE = "http://127.0.0.1:21337"

# Rendering thresholds (client pixels).
HAND_MIN_HEIGHT = 200       # hand fan / card preview
STACK_MIN_WIDTH = 180       # horizontal rendering = spell on the stack
BOARD_MAX_HEIGHT = 200

MULLIGAN_CARDS = 4
MAX_MANA = 10


class LoRClient:
    """Polls the local LoR game client and produces a UI-ready snapshot."""

    def __init__(self, card_db):
        self.card_db = card_db
        self.session = requests.Session()

        # --- match identity -------------------------------------------
        self.in_game = False
        self.game_state = "Menus"
        self.player_name = ""
        self.opponent_name = ""
        self.screen_width = 1920
        self.screen_height = 1080

        # --- our deck --------------------------------------------------
        self.initial_deck = {}          # {card_code: count}
        self.deck_code = ""
        self.drawn_card_ids = set()     # every CardID we ever owned
        self.drawn_codes_by_id = {}     # {card_id: card_code}
        self.hand_ids = set()
        self.board_ids = set()

        # --- opponent ---------------------------------------------------
        self.opp_card_ids = set()
        self.opp_codes_by_id = {}       # {card_id: card_code}
        self.opp_revealed = {}          # {card_code: {count, turn, on_board}}
        self.opp_regions = set()
        self.opp_board_ids = set()

        # --- zones ------------------------------------------------------
        self.my_hand = []
        self.my_board = []
        self.opp_board = []
        self.spell_stack = []

        # --- turn model -------------------------------------------------
        self.phase = "ours"             # ours | theirs | mulligan
        self.our_turn = 1
        self.last_our_draw_count = 0

        # --- stability --------------------------------------------------
        self.last_valid_payload = None
        self.last_in_game_time = 0
        self.last_nonempty_time = 0
        self.consecutive_offline_ticks = 0
        self.deck_locked = False

    # ------------------------------------------------------------------
    # Low level HTTP
    # ------------------------------------------------------------------
    def _get(self, path, timeout=0.8):
        try:
            resp = self.session.get(f"{LOR_API_BASE}{path}", timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def get_positional_rectangles(self):
        return self._get("/positional-rectangles")

    def get_static_decklist(self):
        data = self._get("/static-decklist")
        if data and data.get("CardsInDeck"):
            return data
        return None

    def get_game_result(self):
        return self._get("/game-result")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def reset_match(self):
        self.in_game = False
        self.game_state = "Menus"
        self.player_name = ""
        self.opponent_name = ""
        self.initial_deck = {}
        self.deck_code = ""
        self.drawn_card_ids = set()
        self.drawn_codes_by_id = {}
        self.hand_ids = set()
        self.board_ids = set()
        self.opp_card_ids = set()
        self.opp_codes_by_id = {}
        self.opp_revealed = {}
        self.opp_regions = set()
        self.opp_board_ids = set()
        self.my_hand = []
        self.my_board = []
        self.opp_board = []
        self.spell_stack = []
        self.phase = "ours"
        self.our_turn = 1
        self.last_our_draw_count = 0
        self.last_valid_payload = None
        self.last_in_game_time = 0
        self.last_nonempty_time = 0
        self.consecutive_offline_ticks = 0

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    @staticmethod
    def classify_rectangle(rect):
        """Return one of 'hand' / 'board' / 'stack' for a rectangle."""
        width = rect.get("Width", 0) or 0
        height = rect.get("Height", 0) or 0
        if height >= HAND_MIN_HEIGHT and width <= 240:
            return "hand"
        if width > height and width >= STACK_MIN_WIDTH:
            return "stack"
        return "board"

    def classify_rectangles(self, rectangles, screen_w=1920, screen_h=1080):
        """Split the client rectangles into hand / board / stack buckets."""
        my_hand, my_board, opp_board, spell_stack = [], [], [], []

        for r in rectangles or []:
            card_code = r.get("CardCode")
            if not card_code or card_code == "face":
                continue

            card_id = r.get("CardID")
            local = bool(r.get("LocalPlayer", False))
            zone = self.classify_rectangle(r)
            info = self.card_db.get_card(card_code)

            item = {
                "cardId": card_id,
                "cardCode": card_code,
                "info": info,
                "x": r.get("TopLeftX", 0),
                "y": r.get("TopLeftY", 0),
                "w": r.get("Width", 0),
                "h": r.get("Height", 0),
                "local": local,
                "zone": zone,
            }

            if local:
                if card_id is not None and card_id not in self.drawn_card_ids:
                    self.drawn_card_ids.add(card_id)
                    self.drawn_codes_by_id[card_id] = card_code
                if zone == "hand":
                    self.hand_ids.add(card_id)
                    my_hand.append(item)
                else:
                    self.board_ids.add(card_id)
                    my_board.append(item)
            else:
                if card_id is not None and card_id not in self.opp_card_ids:
                    self.opp_card_ids.add(card_id)
                    self.opp_codes_by_id[card_id] = card_code
                    self._register_opponent_card(card_code, info)
                if zone == "stack":
                    spell_stack.append(item)
                else:
                    self.opp_board_ids.add(card_id)
                    opp_board.append(item)

        return my_hand, my_board, opp_board, spell_stack

    def _register_opponent_card(self, card_code, info):
        entry = self.opp_revealed.get(card_code)
        if entry is None:
            entry = {"count": 0, "turn": self.our_turn + 1, "firstSeen": time.time()}
            self.opp_revealed[card_code] = entry
        entry["count"] += 1
        if info:
            for ref in (info.get("regionRefs") or []):
                self.opp_regions.add(ref)
            for name in (info.get("regions") or []):
                self.opp_regions.add(name)

    # ------------------------------------------------------------------
    # Turn model
    # ------------------------------------------------------------------
    def _update_turn_model(self):
        drawn = len(self.drawn_card_ids)
        if drawn < MULLIGAN_CARDS:
            self.phase = "mulligan"
            self.our_turn = 1
            return
        if drawn != self.last_our_draw_count:
            # We just drew -> it is our turn.
            self.last_our_draw_count = drawn
            self.phase = "ours"
        self.our_turn = max(1, 2 * (drawn - MULLIGAN_CARDS) + 1)

    def _mark_opponent_turn(self):
        """A freshly revealed opponent card means the opponent is acting."""
        if self.phase != "mulligan":
            self.phase = "theirs"

    def turn_info(self):
        our_turn = self.our_turn
        their_turn = our_turn + 1
        if self.phase == "theirs":
            their_drawn = MULLIGAN_CARDS + their_turn // 2
        else:
            their_drawn = MULLIGAN_CARDS + (their_turn - 1) // 2
        their_drawn = max(MULLIGAN_CARDS, their_drawn)
        revealed_total = sum(v["count"] for v in self.opp_revealed.values())
        # In LoR, hand size cannot exceed 10 cards.
        opp_hand = min(10, max(0, their_drawn - revealed_total))
        return {
            "phase": self.phase,
            "ourTurn": our_turn,
            "theirTurn": their_turn,
            "ourMaxMana": min(our_turn, MAX_MANA),
            "theirMaxMana": min(their_turn, MAX_MANA),
            "ourCardsDrawn": len(self.drawn_card_ids),
            "theirCardsDrawn": their_drawn,
            "oppHandSize": opp_hand,
            "oppRevealedCount": revealed_total,
        }

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------
    def update(self):
        now = time.time()
        rect_data = self.get_positional_rectangles()

        if not rect_data:
            self.consecutive_offline_ticks += 1
            if self.in_game and (now - self.last_in_game_time) < 3.0 and self.last_valid_payload:
                return self.last_valid_payload
            if self.consecutive_offline_ticks > 3 and self.in_game:
                self.reset_match()
            return {"status": "offline"}

        self.consecutive_offline_ticks = 0
        state = rect_data.get("GameState")

        if state != "InProgress":
            if self.in_game and (now - self.last_in_game_time) < 3.0 and self.last_valid_payload:
                return self.last_valid_payload
            if self.in_game:
                self.reset_match()
            return {"status": "menus"}

        self.last_in_game_time = now

        if not self.in_game:
            self.in_game = True
            logger.info("New match started")
            self.player_name = rect_data.get("PlayerName", "Игрок")
            self.opponent_name = rect_data.get("OpponentName", "Оппонент")

        if not self.initial_deck:
            deck_data = self.get_static_decklist()
            if deck_data and deck_data.get("CardsInDeck"):
                self.deck_code = deck_data.get("DeckCode", "")
                self.initial_deck = deck_data.get("CardsInDeck", {})
                logger.info("Loaded decklist (%s unique cards)", len(self.initial_deck))

        screen = rect_data.get("Screen", {}) or {}
        self.screen_width = screen.get("ScreenWidth", 1920)
        self.screen_height = screen.get("ScreenHeight", 1080)

        rectangles = rect_data.get("Rectangles", []) or []
        playable = [r for r in rectangles if r.get("CardCode") and r.get("CardCode") != "face"]

        if not playable and self.in_game and (now - self.last_nonempty_time) < 2.5:
            # Transient animation frame - keep the previous snapshot alive.
            if self.last_valid_payload:
                return self.last_valid_payload
        if playable:
            self.last_nonempty_time = now

        previous_opp_ids = set(self.opp_card_ids)
        my_hand, my_board, opp_board, spell_stack = self.classify_rectangles(
            rectangles, self.screen_width, self.screen_height
        )

        if set(self.opp_card_ids) != previous_opp_ids:
            self._mark_opponent_turn()

        self.my_hand = my_hand
        self.my_board = my_board
        self.opp_board = opp_board
        self.spell_stack = spell_stack
        self._update_turn_model()

        payload = self.get_tracker_payload()
        self.last_valid_payload = payload
        return payload

    # ------------------------------------------------------------------
    # Payload assembly
    # ------------------------------------------------------------------
    def _card_brief(self, item):
        info = item.get("info") or {}
        return {
            "cardId": item.get("cardId"),
            "code": item.get("cardCode"),
            "name": info.get("name", item.get("cardCode")),
            "cost": info.get("cost", 0),
            "type": info.get("type", "Unit"),
            "supertype": info.get("supertype", ""),
            "spellSpeed": info.get("spellSpeed", ""),
            "spellSpeedRef": info.get("spellSpeedRef", ""),
            "regions": info.get("regions", []),
            "regionRefs": info.get("regionRefs", []),
            "attack": info.get("attack", 0),
            "health": info.get("health", 0),
            "cardImg": info.get("cardImg", ""),
        }

    def get_tracker_payload(self):
        """Build the complete snapshot consumed by the overlays."""
        drawn_counts = {}
        for card_id, code in self.drawn_codes_by_id.items():
            drawn_counts[code] = drawn_counts.get(code, 0) + 1

        remaining_deck = []
        total_remaining = 0

        for code, initial_count in self.initial_deck.items():
            drawn = drawn_counts.get(code, 0)
            rem = max(0, initial_count - drawn)
            total_remaining += rem
            info = self.card_db.get_card(code)
            remaining_deck.append({
                "code": code,
                "name": info.get("name", code),
                "cost": info.get("cost", 0),
                "type": info.get("type", "Unit"),
                "supertype": info.get("supertype", ""),
                "spellSpeed": info.get("spellSpeed", ""),
                "spellSpeedRef": info.get("spellSpeedRef", ""),
                "regions": info.get("regions", []),
                "regionRefs": info.get("regionRefs", []),
                "attack": info.get("attack", 0),
                "health": info.get("health", 0),
                "description": info.get("description", ""),
                "keywords": info.get("keywords", []),
                "keywordRefs": info.get("keywordRefs", []),
                "isChampion": info.get("isChampion", False),
                "cardImg": info.get("cardImg", ""),
                "initial": initial_count,
                "drawn": drawn,
                "remaining": rem,
                "prob": 0.0,
            })

        if total_remaining > 0:
            for item in remaining_deck:
                item["prob"] = round((item["remaining"] / total_remaining) * 100, 1)

        # Sort by cost, champions first inside the same cost bracket.
        remaining_deck.sort(key=lambda x: (x["cost"], not x["isChampion"], x["name"]))

        # --- our graveyard (played / destroyed) -------------------------
        active_ids = {c["cardId"] for c in self.my_hand + self.my_board}
        grave_counts = {}
        for card_id, code in self.drawn_codes_by_id.items():
            if card_id not in active_ids:
                grave_counts[code] = grave_counts.get(code, 0) + 1

        my_graveyard = []
        for code, count in grave_counts.items():
            info = self.card_db.get_card(code)
            my_graveyard.append({
                "code": code,
                "name": info.get("name", code),
                "cost": info.get("cost", 0),
                "type": info.get("type", "Unit"),
                "count": count,
                "cardImg": info.get("cardImg", ""),
            })
        my_graveyard.sort(key=lambda x: (x["cost"], x["name"]))

        # --- opponent revealed cards ------------------------------------
        opponent_cards = []
        for code, entry in self.opp_revealed.items():
            info = self.card_db.get_card(code)
            opponent_cards.append({
                "code": code,
                "name": info.get("name", code),
                "cost": info.get("cost", 0),
                "type": info.get("type", "Unit"),
                "supertype": info.get("supertype", ""),
                "spellSpeed": info.get("spellSpeed", ""),
                "spellSpeedRef": info.get("spellSpeedRef", ""),
                "regions": info.get("regions", []),
                "regionRefs": info.get("regionRefs", []),
                "cardImg": info.get("cardImg", ""),
                "count": entry["count"],
                "turn": entry.get("turn", 0),
                "onBoard": code in {c["cardCode"] for c in self.opp_board},
                # In a 40 card deck a card is played at most 3 times.
                "estLeft": max(0, 3 - entry["count"]),
            })
        opponent_cards.sort(key=lambda x: (x["cost"], x["name"]))

        turn = self.turn_info()

        payload = {
            "status": "in_game",
            "playerName": self.player_name,
            "opponentName": self.opponent_name,
            "deckCode": self.deck_code,
            "totalRemaining": total_remaining,
            "totalInitial": sum(self.initial_deck.values()),
            "turn": turn,
            # legacy aliases
            "myDeck": remaining_deck,
            "myGraveyard": my_graveyard,
            "myHand": [self._card_brief(c) for c in self.my_hand],
            "myBoard": [self._card_brief(c) for c in self.my_board],
            "opponentBoard": [self._card_brief(c) for c in self.opp_board],
            "opponentCards": opponent_cards,
            "opponentRegions": sorted(self.opp_regions),
            # richer aliases
            "deck": remaining_deck,
            "oppRevealed": opponent_cards,
            "spellStack": [self._card_brief(c) for c in self.spell_stack],
        }
        return payload


if __name__ == "__main__":  # pragma: no cover - manual smoke test
    import json
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    from card_db import CardDatabase
    db = CardDatabase("ru_ru")
    client = LoRClient(db)
    data = client.update()
    print(json.dumps if False else "")
    print("status:", data.get("status"))
    print("turn:", data.get("turn"))
    for card in data.get("myDeck", [])[:10]:
        print(f"  [{card['cost']}m] {card['name']} {card['remaining']}/{card['initial']} ({card['prob']}%)")
    print("opponent revealed:", [(c["name"], c["count"], c["turn"]) for c in data.get("opponentCards", [])])
