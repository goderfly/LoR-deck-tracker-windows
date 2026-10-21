"""
LoR Deck Tracker - Native HUD Package for Legends of Runeterra.
"""

from .advisor_engine import build_catalog, compute_counters, compute_threats
from .card_db import CardDatabase
from .manager import OverlayManager
from .panels import OpponentPanel, PlayerPanel
from .preview import CardPreview
from .settings import SettingsDialog
from .tracker_engine import LoRClient

__version__ = "1.0.0"
__author__ = "LoR Deck Tracker Community"

__all__ = [
    "CardDatabase",
    "LoRClient",
    "OverlayManager",
    "PlayerPanel",
    "OpponentPanel",
    "CardPreview",
    "SettingsDialog",
    "build_catalog",
    "compute_counters",
    "compute_threats",
]
