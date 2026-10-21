"""
Tactical advisor: threat catalogue, spell-mana engine and deck counters.

The engine is completely data driven - every threat is derived from the live
DataDragon database instead of a hand written list, and the curated table only
adds severity/annotation for the cards that really decide games.

Three pillars
-------------
``build_catalog``      scans every published card and keeps the Fast/Burst
                       spells, tagging them with a tactical category.
``compute_threats``    intersects the catalogue with the regions the opponent
                       actually revealed and ranks them against the mana the
                       opponent will have on their next turn (unit mana plus
                       the spell-mana bank).
``compute_counters``   surfaces the deck specific mechanics a pro player
                       actually tracks: poison puffcaps, flashbomb traps,
                       Hallowed / Slain scaling and champion level ups.
"""

import re

# --------------------------------------------------------------------------
# Curated severity table (card codes are language independent).
# --------------------------------------------------------------------------
THREAT_TEMPLATES = {
    # --- board wipes / finisher answers ---------------------------------
    "01SI001": ("LETHAL", 100, "Мгновенно уничтожает любого бойца. Ответ на вашу ульту."),
    "01SI015": ("LETHAL", 99, "Убивает ВСЕХ бойцов на столе. Не держите руку на доске."),
    "01DE007": ("LETHAL", 95, "Бьёт всех сражающихся врагов одновременно."),
    "01FR020": ("SWEEP", 90, "2 урона всем бойцам на столе."),
    "01FR042": ("SWEEP", 88, "Замораживает двух врагов на взрывной скорости."),
    "01FR014": ("SWEEP", 82, "2 урона всему живому в начале следующего раунда."),
    # --- counters --------------------------------------------------------
    "04SH059": ("COUNTER", 92, "Отменяет любое заклинание врага на стеке."),
    "01IO049": ("COUNTER", 90, "Отменяет быстрое/медленное заклинание или навык."),
    "03IO020": ("COUNTER", 78, "Отменяет заклинание стоимостью до 3 маны."),
    # --- burst / fight winning ------------------------------------------
    "01DE026": ("BURST", 80, "Союзник и враг бьют друг друга. Снимает ваши баффы."),
    "01PZ039": ("BURST", 78, "Сбрасывает карту и наносит 3 урона любой цели."),
    "02NX003": ("BURST", 74, "3 урона любой цели, жертвуя союзника."),
    "01IO012": ("BURST", 72, "Быстрый бафф на взрывной скорости."),
    "04FR010": ("BURST", 70, "Может создать заморозку или ярость Севера."),
    "04SH109": ("BURST", 68, "-4 атаки и снятие ключевых слов на взрывной."),
    "03MT085": ("BURST", 66, "Снимает все баффы и текст карты на этот раунд."),
    "03DE014": ("BURST", 62, "+1/+2 и блок неуловимых, взрывная скорость."),
    "04SH069": ("BURST", 60, "+2 союзнику и Уязвимость вашему бойцу."),
    "02DE001": ("BURST", 70, "Два союзника бьют одного выбранного врага."),
    # --- removal ---------------------------------------------------------
    "01NX004": ("BURST", 64, "Уничтожает бойца с силой атаки 3 или меньше."),
    "01SI049": ("BURST", 60, "Жертвует бойца, берёт 2 карты и даёт Уязвимость."),
    "01SI040": ("BURN", 58, "1 урон и призывает паука 1/1."),
    "04BW010": ("BURST", 58, "5 урона бойцу, стоит 4 при Грабеже."),
    # --- damage ----------------------------------------------------------
    "02BW045": ("BURN", 52, "По 1 урона трём случайным целям врага."),
    "01PZ052": ("BURN", 40, "2 урона любой цели."),
    "01NX002": ("BURN", 56, "4 урона напрямую по Нексусу."),
    "03MT023": ("BURN", 50, "6 урона, накладывает немоту при Рассвете."),
    "03PZ011": ("BURST", 44, "3 урона или разрушает место силы."),
    "05BC209": ("CONTROL", 46, "Характеристики любого бойца становятся 1/6."),
    "02BW020": ("BURN", 30, "0 маны: 1 урон по Нексусу, активирует Грабёж."),
    "01IO002": ("CONTROL", 48, "Возвращает вашего раскачанного бойца в руку."),
    "05BC166": ("BURN", 30, "1 урон и берёт карту."),
    "02FR007": ("BURST", 42, "+3/+4 союзнику до конца раунда."),
    "03MT019": ("CONTROL", 42, "Щит от магии и +1/+1 на взрывной скорости."),
    "03MT035": ("BURST", 40, "+1/+1 и добирает карту при Активации Ночи."),
}

# Cards that attach poison puffcaps (Bandle City / Set 1 Pilt).
PUFFCAP_ATTACH = {
    "01PZ008": 5,     # Teemo (level 1)
    "01PZ008T2": 10,  # Teemo (level 2 - doubles the puffcaps)
    "01PZ008T1": 5,   # Teemo's Mushroom Cloud
    "01PZ010": 5,     # Mushroom Cloud
    "05BC070": 3,     # Ava Achiever
    "05BC100": 3,     # Puffcap Pup
    "05BC164": 3,     # Poison Dart
    "05BC221": 3,     # Puffcap Ring
    "05BC223": 3,     # Entrapment
}

# Cards that drop flashbomb traps into the opponent's deck.
FLASHBOMB_SOURCES = {
    "07PZ017": 1,   # Flashbomb Peddler - one trap per spell played
    "05PZ006": 1,   # Caitlyn
}
FLASHBOMB_TRAP = "05PZ008"

# Cards that grant spell mana (banked mana usable for any spell).
SPELL_MANA_SOURCES = {
    "01PZ019": 2,   # Eager Apprentice - refill 2 spell mana
    "05PZ025": 1,   # Forge Chief - 1 spell mana per attack
    "05BC102": 1,   # Wizened Wizard - 1 spell mana at round start
}

CATEGORY_LABELS = {
    "LETHAL": "УБИЙСТВО",
    "SWEEP": "ЗАЧИСТКА",
    "COUNTER": "ОТМЕНА",
    "BURST": "БУРСТ",
    "BURN": "УРОН",
    "CONTROL": "КОНТРОЛЬ",
    "DRAW": "ДРО",
}

CATEGORY_ORDER = ["LETHAL", "SWEEP", "COUNTER", "BURST", "BURN", "CONTROL", "DRAW"]

_RU_HINTS = {
    "LETHAL": ("уничтож", "убива", "убьёт", "смерть"),
    "SWEEP": ("всем бойцам", "всех бойцов", "всему живому"),
    "COUNTER": ("отмен", "отмени", "запрет"),
    "BURN": ("урон", "нексус"),
    "DRAW": ("возьмите", "добер", "карт"),
}
_EN_HINTS = {
    "LETHAL": ("kill", "destroy"),
    "SWEEP": ("all units", "all enemies"),
    "COUNTER": ("cancel", "counter"),
    "BURN": ("damage", "nexus"),
    "DRAW": ("draw a card", "draw "),
}


def _detect_category(name, description, keywords):
    text = f"{name} {description}".lower()
    for cat, needles in _RU_HINTS.items():
        if any(n in text for n in needles):
            return cat
    for cat, needles in _EN_HINTS.items():
        if any(n in text for n in needles):
            return cat
    if "SpellShield" in (keywords or []):
        return "CONTROL"
    return "BURST"


def build_catalog(card_db):
    """Build the Fast/Burst spell catalogue from the card database."""
    catalog = {}
    for code, card in (card_db.cards or {}).items():
        ctype = card.get("type", "")
        speed = card.get("spellSpeedRef") or ""
        if ctype not in ("Spell", "Заклинание") and not speed:
            continue
        if speed not in ("Fast", "Burst"):
            continue
        if card.get("isToken"):
            continue
        cost = card.get("cost", 0)
        if cost <= 0:
            continue

        cat, sev, note = THREAT_TEMPLATES.get(code, (None, None, None))
        if cat is None:
            cat = _detect_category(
                card.get("name", ""), card.get("description", ""), card.get("keywordRefs", [])
            )
            sev = 20 + max(0, 12 - cost) * 2
            note = ""
        catalog[code] = {
            "code": code,
            "name": card.get("name", code),
            "cost": cost,
            "speed": card.get("spellSpeed", ""),
            "speedRef": speed,
            "cat": cat,
            "sev": sev,
            "note": note,
            "regions": card.get("regionRefs", []) or [],
            "regionNames": card.get("regions", []) or [],
            "cardImg": card.get("cardImg", ""),
            "keywords": card.get("keywords", []) or [],
        }
    return catalog


def _region_overlap(catalog_regions, opp_regions):
    """Case/format insensitive intersection between region ref lists."""
    if not opp_regions:
        return False
    opp = {str(r).lower().replace(" ", "") for r in opp_regions}
    for ref in catalog_regions or []:
        key = str(ref).lower().replace(" ", "")
        if key in opp:
            return True
        for o in opp:
            if key in o or o in key:
                return True
    return False


def compute_threats(state, card_db, catalog=None, extra_spell_mana=0):
    """Return the ranked threat list for the current game state."""
    catalog = catalog if catalog is not None else build_catalog(card_db)
    turn = state.get("turn", {}) or {}
    opp_regions = state.get("opponentRegions", []) or []
    revealed_codes = {c["code"] for c in state.get("opponentCards", []) or []}

    their_turn = turn.get("theirTurn", 2) or 2
    unit_mana = min(their_turn, 10)
    spell_mana = max(0, int(extra_spell_mana))
    effective = unit_mana + spell_mana

    threats = []
    for code, entry in catalog.items():
        if not _region_overlap(entry["regions"], opp_regions):
            continue

        cost = entry["cost"]
        fast = entry["speedRef"] in ("Fast", "Burst")
        can_now = bool(fast and cost <= effective)
        can_next = cost <= effective

        threats.append({
            "code": code,
            "name": entry["name"],
            "cost": cost,
            "speed": entry["speed"],
            "speedRef": entry["speedRef"],
            "cat": entry["cat"],
            "catLabel": CATEGORY_LABELS.get(entry["cat"], entry["cat"]),
            "sev": entry["sev"],
            "note": entry["note"],
            "cardImg": entry["cardImg"],
            "fast": fast,
            "canNow": can_now,
            "canNext": can_next,
            "played": code in revealed_codes,
        })

    threats.sort(key=lambda t: (not t["canNow"], -t["sev"], t["cost"]))
    return {
        "threats": threats,
        "unitMana": unit_mana,
        "spellMana": spell_mana,
        "effectiveMana": effective,
        "theirTurn": their_turn,
        "regions": opp_regions,
    }


def _champion_level(card_db, code):
    """Return the level of a champion card code (1 = base, 2+ = level up)."""
    card = card_db.get_card(code)
    if not card:
        return 1
    if not code.endswith(("T1", "T2", "T3", "T4")):
        return 1
    base = code[:-2]
    index = int(code[-1])
    level = 1
    for i in range(1, index + 1):
        variant = card_db.get_card(f"{base}T{i}")
        if variant and variant.get("type") == "Unit" and not variant.get("isToken"):
            level += 1
        elif variant and variant.get("type") == "Unit":
            level += 1
    return max(1, level)


def compute_counters(state, card_db):
    """Deck specific counters: puffcaps, flashbombs, Hallowed, Slain, champions."""
    deck = state.get("myDeck", []) or []
    revealed = state.get("opponentCards", []) or []
    hand = state.get("myHand", []) or []
    board = state.get("myBoard", []) or []

    # --- poison puffcaps -------------------------------------------------
    our_puffcap_cards = [
        {"code": c["code"], "name": c["name"], "count": c["remaining"],
         "attach": PUFFCAP_ATTACH.get(c["code"], 0)}
        for c in deck
        if c["code"] in PUFFCAP_ATTACH and c["remaining"] > 0
    ]
    their_puffcap_cards = [
        {"code": c["code"], "name": c["name"], "count": c["count"],
         "attach": PUFFCAP_ATTACH.get(c["code"], 0)}
        for c in revealed
        if c["code"] in PUFFCAP_ATTACH
    ]
    their_puffcaps = sum(p["attach"] * p["count"] for p in their_puffcap_cards)

    # --- flashbomb traps -------------------------------------------------
    our_flash = [c for c in deck if c["code"] in FLASHBOMB_SOURCES and c["remaining"] > 0]
    their_flash = [c for c in revealed if c["code"] in FLASHBOMB_SOURCES]
    flash_traps = sum(FLASHBOMB_SOURCES.get(c["code"], 0) * c["count"] for c in their_flash)
    # traps land in the top 8 cards of the opponent's deck
    expected_traps = flash_traps * (8.0 / 40.0)

    # --- Hallowed / Slain ------------------------------------------------
    hallowed_cards = [
        {"code": c["code"], "name": c["name"], "count": c["remaining"]}
        for c in deck
        if "Hallowed" in (c.get("keywordRefs") or [])
    ]
    slain_bonus = 0
    for c in revealed:
        if c.get("type") == "Unit" and not c.get("onBoard"):
            slain_bonus += c.get("count", 0)

    # --- champions -------------------------------------------------------
    champions = []
    for c in deck:
        if not c.get("isChampion"):
            continue
        code = c["code"]
        seen = None
        for zone in (hand, board):
            for item in zone:
                if item.get("code", "").startswith(code[:6]) and item.get("code") != code:
                    seen = item["code"]
        level = _champion_level(card_db, seen) if seen else 1
        base = card_db.get_card(code)
        champions.append({
            "code": code,
            "name": c["name"],
            "count": c["remaining"],
            "level": level,
            "maxLevel": 3 if code == "04SH047" else 2,
            "condition": base.get("levelupDescription", "") if base else "",
        })

    # --- spell mana sources in our deck ----------------------------------
    spell_mana_cards = [
        {"code": c["code"], "name": c["name"], "count": c["remaining"], "amount": SPELL_MANA_SOURCES.get(c["code"], 0)}
        for c in deck
        if c["code"] in SPELL_MANA_SOURCES and c["remaining"] > 0
    ]

    return {
        "puffcap": {
            "ours": our_puffcap_cards,
            "theirs": their_puffcap_cards,
            "theirPuffcaps": their_puffcaps,
            "expectedDamage": their_puffcaps,
        },
        "flashbomb": {
            "ours": our_flash,
            "theirs": their_flash,
            "traps": flash_traps,
            "expectedInTop8": round(expected_traps, 1),
        },
        "hallowed": hallowed_cards,
        "slain": slain_bonus,
        "champions": champions,
        "spellMana": spell_mana_cards,
    }


# --------------------------------------------------------------------------
# Backwards compatible helper used by the legacy browser UI
# --------------------------------------------------------------------------
def get_threats_for_regions(regions, card_db=None):
    """Legacy API: flat list of threats for the given regions."""
    if card_db is None:
        try:
            from card_db import CardDatabase
            card_db = CardDatabase()
        except Exception:
            return []
    catalog = build_catalog(card_db)
    result = []
    for code, entry in catalog.items():
        if _region_overlap(entry["regions"], regions):
            result.append({
                "name": entry["name"],
                "nameRu": entry["name"],
                "cost": entry["cost"],
                "speed": entry["speed"],
                "type": entry["cat"],
                "warning": entry["note"],
                "code": code,
            })
    result.sort(key=lambda t: t["cost"])
    return result
