"""
Backwards-compatibility shim for pyqt_overlay.py.
Delegates directly to main.py.
"""

from main import main
from lor.manager import OverlayManager
from lor.panels import OpponentPanel, PlayerPanel
from lor.preview import CardPreview

LoRCardTooltip = CardPreview
PlayerDeckOverlay = PlayerPanel
OpponentOverlay = OpponentPanel

if __name__ == "__main__":
    main()
