"""
DataDragon card database for Legends of Runeterra.

Key features
------------
* Multi-language: ru_ru (default) and en_us, each with its own on-disk cache.
* Auto-discovers every published set (not a hardcoded "set1..set5" list) by
  reading Riot's ``globals`` manifest, so brand new cards always resolve to a
  localised name instead of a raw ``06DE048`` id.
* Localised keywords, spell speeds, rarities and region icons.
* Background card-art downloader with an on-disk cache (thread safe).
* Graceful offline operation: if Riot's CDN is unreachable the cached database
  is used and the tracker keeps working.

All public methods are safe to call from the Qt UI thread; network activity
always happens on worker threads.
"""

import os
import json
import logging
import threading
import requests
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("CardDB")

import sys

if getattr(sys, "frozen", False):
    BUNDLE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    EXE_DIR = BUNDLE_DIR

BUNDLE_DATA_DIR = os.path.join(BUNDLE_DIR, "data")
USER_DATA_DIR = os.path.join(EXE_DIR, "data")
os.makedirs(USER_DATA_DIR, exist_ok=True)

DATA_DIR = USER_DATA_DIR
ICONS_DIR = os.path.join(DATA_DIR, "icons")
REGIONS_DIR = os.path.join(ICONS_DIR, "regions")
CARD_IMAGES_DIR = os.path.join(DATA_DIR, "card_images")

LANGUAGES = ("ru_ru", "en_us")
DEFAULT_LANGUAGE = "ru_ru"

DD_HOST = "https://dd.b.pvp.net"
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

# Candidate dataset names. The first nine are the classic releases, the rest
# are probed opportunistically so future sets light up automatically.
SET_CANDIDATES = [
    "set1", "set2", "set3", "set4", "set5",
    "set6", "set6cde", "set7", "set7b", "set8", "set9",
    "set10", "set10a", "set10b", "set10c", "set11", "set11a",
    "set12", "set12a", "set13", "setevent",
]


def _cache_path(language):
    aliases = [language]
    if "_" in language:
        aliases.append(language.split("_")[0])
    elif language == "ru":
        aliases.append("ru_ru")
    for lang in aliases:
        for folder in (DATA_DIR, BUNDLE_DATA_DIR):
            p = os.path.join(folder, f"cards_cache_{lang}.json")
            if os.path.exists(p):
                return p
    return os.path.join(DATA_DIR, f"cards_cache_{language}.json")


def _globals_path(language):
    aliases = [language]
    if "_" in language:
        aliases.append(language.split("_")[0])
    elif language == "ru":
        aliases.append("ru_ru")
    for lang in aliases:
        for folder in (DATA_DIR, BUNDLE_DATA_DIR):
            p = os.path.join(folder, f"globals_{lang}.json")
            if os.path.exists(p):
                return p
    return os.path.join(DATA_DIR, f"globals_{language}.json")


class CardDatabase:
    """Localised card metadata store backed by Riot's DataDragon."""

    def __init__(self, language=DEFAULT_LANGUAGE, autoload=True):
        self.language = language if language in LANGUAGES else DEFAULT_LANGUAGE
        self.cards = {}
        self.globals = {}
        self.set_names = {}          # nameRef -> localised set name
        self.keyword_names = {}      # nameRef -> localised keyword name
        self.keyword_desc = {}       # nameRef -> localised keyword description
        self.spell_speeds = {}       # nameRef -> localised speed name
        self.rarities = {}           # nameRef -> localised rarity name
        self.region_names = {}       # nameRef -> localised region name
        self.region_icons = {}       # nameRef -> local icon path

        self._image_lock = threading.Lock()
        self._pending_images = set()
        self._lock = threading.RLock()

        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(REGIONS_DIR, exist_ok=True)
        os.makedirs(CARD_IMAGES_DIR, exist_ok=True)

        if autoload:
            self.load()

    # ------------------------------------------------------------------
    # Loading / language handling
    # ------------------------------------------------------------------
    def load(self):
        """Load the cached database for the active language."""
        with self._lock:
            path = _cache_path(self.language)
            self.cards = {}
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        self.cards = json.load(fh)
                    logger.info("Loaded %s cards for %s", len(self.cards), self.language)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("Failed to read %s: %s", path, exc)
                    self.cards = {}

            self.globals = {}
            gpath = _globals_path(self.language)
            if os.path.exists(gpath):
                try:
                    with open(gpath, "r", encoding="utf-8") as fh:
                        self.globals = json.load(fh)
                except Exception:
                    self.globals = {}

            self._index_globals()

        if not self.cards:
            # Nothing cached -> pull it down right away (blocking is fine here,
            # it only happens on a cold start).
            self.fetch_all(self.language)

    def set_language(self, language):
        """Switch the active language. Returns True when the DB changed."""
        if language not in LANGUAGES or language == self.language:
            return False
        self.language = language
        self.load()
        return True

    def available_languages(self):
        return list(LANGUAGES)

    # ------------------------------------------------------------------
    # Globals indexing
    # ------------------------------------------------------------------
    def _index_globals(self):
        g = self.globals or {}
        self.set_names = {
            s.get("nameRef"): s.get("name", "")
            for s in g.get("sets", []) if isinstance(s, dict)
        }
        self.keyword_names = {}
        self.keyword_desc = {}
        for kw in g.get("keywords", []) or []:
            if isinstance(kw, dict) and kw.get("nameRef"):
                self.keyword_names[kw["nameRef"]] = kw.get("name", "")
                self.keyword_desc[kw["nameRef"]] = kw.get("description", "")
        self.spell_speeds = {
            s.get("nameRef"): s.get("name", "")
            for s in g.get("spellSpeeds", []) or [] if isinstance(s, dict)
        }
        self.rarities = {
            r.get("nameRef"): r.get("name", "")
            for r in g.get("rarities", []) or [] if isinstance(r, dict)
        }
        self.region_names = {}
        for r in g.get("regions", []) or []:
            if not isinstance(r, dict):
                continue
            ref = r.get("nameRef")
            if not ref:
                continue
            self.region_names[ref] = r.get("name", "")
            icon = self._region_icon_path(ref)
            if icon:
                self.region_icons[ref] = icon
                if not os.path.exists(icon) and r.get("iconAbsolutePath"):
                    threading.Thread(
                        target=self._download,
                        args=(r["iconAbsolutePath"], icon),
                        daemon=True
                    ).start()

    @staticmethod
    def _region_icon_path(region_ref):
        filename = f"{str(region_ref).lower()}.png"
        p1 = os.path.join(REGIONS_DIR, filename)
        if os.path.exists(p1):
            return p1
        p2 = os.path.join(BUNDLE_DATA_DIR, "icons", "regions", filename)
        if os.path.exists(p2):
            return p2
        return p1

    def get_region_icon(self, region_ref):
        """Return a local path for a region icon (by nameRef or display name)."""
        if not region_ref:
            return None
        ref = self._resolve_region_ref(region_ref)
        if ref and ref in self.region_icons:
            return self.region_icons[ref]
        path = self._region_icon_path(ref or region_ref)
        return path if os.path.exists(path) else None

    def _resolve_region_ref(self, value):
        """Map 'Демасия' / 'demacia' / 'Demacia' -> 'Demacia'."""
        if not value:
            return None
        raw = str(value).strip()
        if raw in self.region_names:
            return raw
        low = raw.lower()
        for ref, name in self.region_names.items():
            if ref.lower() == low or (name and name.lower() == low):
                return ref
        # Fallback: substring match on the localised name
        for ref, name in self.region_names.items():
            if name and low and (low in name.lower() or name.lower() in low):
                return ref
        return None

    def region_display_name(self, region_ref):
        ref = self._resolve_region_ref(region_ref)
        if ref and ref in self.region_names:
            return self.region_names[ref]
        return str(region_ref)

    # ------------------------------------------------------------------
    # Networking
    # ------------------------------------------------------------------
    @staticmethod
    def _download(url, dest):
        try:
            resp = requests.get(url, timeout=15, headers=HTTP_HEADERS)
            if resp.status_code == 200 and resp.content:
                tmp = dest + ".part"
                with open(tmp, "wb") as fh:
                    fh.write(resp.content)
                os.replace(tmp, dest)
                return True
        except Exception as exc:
            logger.debug("Download failed %s: %s", url, exc)
        return False

    def fetch_globals(self, language):
        url = f"{DD_HOST}/latest/core/{language}/data/globals-{language}.json"
        try:
            resp = requests.get(url, timeout=20, headers=HTTP_HEADERS)
            if resp.status_code != 200:
                return {}
            resp.encoding = "utf-8"
            with open(_globals_path(language), "w", encoding="utf-8") as fh:
                json.dump(resp.json(), fh, ensure_ascii=False, indent=1)
            return resp.json()
        except Exception as exc:
            logger.warning("globals fetch failed: %s", exc)
            return {}

    def _discover_sets(self, language):
        """Return the dataset names that actually exist for this language."""
        names = []
        for cand in SET_CANDIDATES:
            url = f"{DD_HOST}/latest/{cand}/{language}/data/{cand}-{language}.json"
            try:
                resp = requests.get(url, timeout=12, headers=HTTP_HEADERS)
                if resp.status_code == 200:
                    names.append(cand)
            except Exception:
                continue
        return names

    def fetch_all(self, language=None, on_progress=None):
        """Download every published set for ``language`` and cache the result."""
        language = language or self.language
        if on_progress:
            on_progress("Обновление базы карт…")

        globals_data = self.fetch_globals(language)
        sets = self._discover_sets(language)
        logger.info("Discovered sets for %s: %s", language, sets)

        merged = {}

        def worker(name):
            url = f"{DD_HOST}/latest/{name}/{language}/data/{name}-{language}.json"
            try:
                resp = requests.get(url, timeout=25, headers=HTTP_HEADERS)
                if resp.status_code != 200:
                    return name, []
                resp.encoding = "utf-8"
                return name, resp.json()
            except Exception as exc:
                logger.warning("set %s failed: %s", name, exc)
                return name, []

        with ThreadPoolExecutor(max_workers=8) as pool:
            for name, cards in pool.map(worker, sets):
                if on_progress:
                    on_progress(f"Загружено: {name} ({len(cards)})")
                for card in cards:
                    code = card.get("cardCode")
                    if not code:
                        continue
                    merged[code] = self._normalise(card, name)

        if merged:
            try:
                with open(_cache_path(language), "w", encoding="utf-8") as fh:
                    json.dump(merged, fh, ensure_ascii=False, indent=1)
            except Exception as exc:
                logger.error("Failed to write cache: %s", exc)

        if language == self.language:
            with self._lock:
                self.cards = merged
                if globals_data:
                    self.globals = globals_data
                self._index_globals()

        logger.info("Fetched %s cards for %s", len(merged), language)
        return merged

    def _normalise(self, card, set_name):
        assets = card.get("assets") or []
        first = assets[0] if assets else {}
        regions = card.get("regions", []) or []
        region_refs = card.get("regionRefs", []) or []
        rarity_ref = card.get("rarityRef", "") or ""
        supertype = card.get("supertype", "") or ""
        code = card.get("cardCode", "")
        return {
            "cardCode": code,
            "name": card.get("name", code),
            "cost": card.get("cost", 0),
            "type": card.get("type", "Unit"),
            "supertype": supertype,
            "spellSpeed": card.get("spellSpeed", "") or "",
            "spellSpeedRef": card.get("spellSpeedRef", "") or "",
            "regions": regions,
            "regionRefs": region_refs,
            "attack": card.get("attack", 0),
            "health": card.get("health", 0),
            "description": card.get("descriptionRaw", "") or "",
            "levelupDescription": card.get("levelupDescriptionRaw", "") or "",
            "keywords": card.get("keywords", []) or [],
            "keywordRefs": card.get("keywordRefs", []) or [],
            "rarity": card.get("rarity", "") or "",
            "rarityRef": rarity_ref,
            "cardImg": first.get("gameAbsolutePath", "") or "",
            "fullImg": first.get("fullAbsolutePath", "") or "",
            "setRef": set_name,
            "isChampion": rarity_ref == "Champion" or supertype.lower() in ("champion", "чемпион"),
            "isToken": code.endswith(("T1", "T2", "T3")) or card.get("type") == "Ability",
        }

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------
    def get_card(self, card_code):
        """Return the metadata record for ``card_code`` (never None)."""
        if not card_code or card_code == "face":
            return None
        card = self.cards.get(card_code)
        if card:
            return card
        return {
            "cardCode": card_code,
            "name": card_code,
            "cost": 0,
            "type": "Unit",
            "supertype": "",
            "spellSpeed": "",
            "spellSpeedRef": "",
            "regions": [],
            "regionRefs": [],
            "attack": 0,
            "health": 0,
            "description": "",
            "levelupDescription": "",
            "keywords": [],
            "keywordRefs": [],
            "rarity": "",
            "rarityRef": "",
            "cardImg": "",
            "fullImg": "",
            "setRef": "",
            "isChampion": False,
            "isToken": False,
        }

    def has_card(self, card_code):
        return card_code in self.cards

    def card_name(self, card_code):
        card = self.cards.get(card_code)
        return card["name"] if card else card_code

    def keyword_label(self, keyword_ref):
        """Localised keyword name (falls back to the raw ref)."""
        if not keyword_ref:
            return ""
        return self.keyword_names.get(keyword_ref, keyword_ref)

    def spell_speed_label(self, speed_ref):
        if not speed_ref:
            return ""
        return self.spell_speeds.get(speed_ref, speed_ref)

    def rarity_label(self, rarity_ref):
        if not rarity_ref:
            return ""
        return self.rarities.get(rarity_ref, rarity_ref)

    def region_refs(self, card_code):
        card = self.cards.get(card_code)
        if not card:
            return []
        return card.get("regionRefs", []) or []

    # ------------------------------------------------------------------
    # Card art
    # ------------------------------------------------------------------
    def image_path(self, card_code):
        """Local path of the cached card art (may not exist yet)."""
        return os.path.join(CARD_IMAGES_DIR, f"{card_code}.png")

    def has_image(self, card_code):
        return os.path.exists(self.image_path(card_code))

    def request_image(self, card_code, on_ready=None):
        """Download the card art in the background (no-op if cached)."""
        card = self.cards.get(card_code)
        if not card:
            return
        url = card.get("cardImg") or card.get("fullImg")
        if not url:
            return
        dest = self.image_path(card_code)
        if os.path.exists(dest):
            return
        with self._image_lock:
            if card_code in self._pending_images:
                return
            self._pending_images.add(card_code)

        def worker():
            ok = self._download(url, dest)
            with self._image_lock:
                self._pending_images.discard(card_code)
            if ok and on_ready:
                try:
                    on_ready(card_code)
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def prefetch_images(self, card_codes):
        for code in card_codes:
            self.request_image(code)

    def region_icon_pixmap_source(self, region_ref):
        return self.get_region_icon(region_ref)


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    db = CardDatabase("ru_ru")
    print("cards:", len(db.cards))
    card = db.get_card("06DE048")
    print("06DE048 ->", card["name"], "| cost", card["cost"], "|", card["type"])
    print("regions:", db.region_names)
