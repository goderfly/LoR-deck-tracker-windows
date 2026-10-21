"""
Application coordinator.

Owns the card database, the game client poller and the three HUD modules and
keeps them in sync. The whole loop is designed around a single rule: the UI
is only ever *updated*, never rebuilt, so nothing flickers while a ranked
match is running.
"""

import json
import os
import sys
import threading

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme, win32ext
from .advisor import AdvisorBar
from .advisor_engine import build_catalog, compute_counters, compute_threats
from .card_db import CardDatabase
from .panels import OpponentPanel, PlayerPanel
from .preview import CardPreview
from .settings import SettingsDialog
from .theme import qcolor
from .tracker_engine import LoRClient
from .widgets import ArtCache, METRICS

if getattr(sys, "frozen", False):
    EXE_DIR = os.path.dirname(sys.executable)
    DATA_DIR = os.path.join(EXE_DIR, "data")
    BUNDLE_DIR = getattr(sys, "_MEIPASS", EXE_DIR)
    BUNDLE_DATA_DIR = os.path.join(BUNDLE_DIR, "data")
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    BUNDLE_DATA_DIR = DATA_DIR

SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

POLL_MS = 300

DEFAULT_SETTINGS = {
    "scale": 1.0,
    "opacity": 0.92,
    "language": "ru_ru",
    "player_overlay_visible": True,
    "opponent_overlay_visible": True,
    "advisor_overlay_visible": True,
    "tooltips_enabled": True,
    "click_through": False,
    "locked": False,
    "always_visible": False,
    "opp_spell_mana": 0,
    "player_pos": None,
    "opponent_pos": None,
    "advisor_pos": None,
    "settings_pos": None,
}


def load_settings():
    target = SETTINGS_FILE
    if not os.path.exists(target) and os.path.exists(os.path.join(BUNDLE_DATA_DIR, "settings.json")):
        target = os.path.join(BUNDLE_DATA_DIR, "settings.json")
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            result = DEFAULT_SETTINGS.copy()
            result.update(data)
            return result
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


class OverlayManager(QtCore.QObject):
    """Glue between the game client, the card database and the HUD."""

    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        METRICS.scale = float(self.settings.get("scale", 1.0))

        self.card_db = CardDatabase(self.settings.get("language", "ru_ru"))
        self.art_cache = ArtCache(self.card_db)
        self.catalog = build_catalog(self.card_db)

        self.lor_client = LoRClient(self.card_db)

        self.preview = CardPreview(self.card_db, self.art_cache)
        self.preview.hide()

        self.player_panel = None
        self.opponent_panel = None
        self.advisor_bar = None
        self.settings_dialog = None
        self._build_panels()

        self.last_state = {"status": "offline"}
        self._last_catalog_lang = self.card_db.language

        self.tray_icon = None
        self.tray_status_action = None
        self.tray_always_vis_act = None
        self._setup_tray()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(POLL_MS)

        self.apply_settings(self.settings)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build_panels(self):
        screen = QtGui.QGuiApplication.primaryScreen().geometry()

        self.player_panel = PlayerPanel(
            self.card_db, self.art_cache, self.preview,
            on_open_settings=self.open_settings,
            on_lock_toggle=self._toggle_lock,
            on_close=self._close_player_panel,
        )
        self.player_panel.on_position_changed = lambda x, y: self.save_pos("player_pos", x, y)

        self.opponent_panel = OpponentPanel(
            self.card_db, self.art_cache, self.preview,
            on_open_settings=self.open_settings,
            on_lock_toggle=self._toggle_lock,
            on_close=self._close_opponent_panel,
        )
        self.opponent_panel.on_position_changed = lambda x, y: self.save_pos("opponent_pos", x, y)

        self.advisor_bar = AdvisorBar(preview=self.preview)
        self.advisor_bar.on_position_changed = lambda x, y: self.save_pos("advisor_pos", x, y)

        self._restore_positions()

    def _restore_positions(self):
        screen = QtGui.QGuiApplication.primaryScreen().geometry()
        if self.settings.get("player_pos"):
            self.player_panel.move(*self.settings["player_pos"])
        else:
            self.player_panel.move(METRICS(18), METRICS(70))
        if self.settings.get("opponent_pos"):
            self.opponent_panel.move(*self.settings["opponent_pos"])
        else:
            w = self.opponent_panel.width()
            self.opponent_panel.move(screen.width() - w - METRICS(18), METRICS(70))
        if self.settings.get("advisor_pos"):
            self.advisor_bar.move(*self.settings["advisor_pos"])
        else:
            w = self.advisor_bar.width()
            self.advisor_bar.move((screen.width() - w) // 2, METRICS(16))

    # ------------------------------------------------------------------
    # System Tray
    # ------------------------------------------------------------------
    def _setup_tray(self):
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return

        icon_path = os.path.join(DATA_DIR, "icons", "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(BUNDLE_DATA_DIR, "icons", "app_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(BUNDLE_DATA_DIR, "icons", "app_icon.png")

        qicon = QtGui.QIcon(icon_path) if os.path.exists(icon_path) else QtGui.QIcon()
        self.tray_icon = QtWidgets.QSystemTrayIcon(qicon, self)
        self.tray_icon.setToolTip("LoR Deck Tracker: Ожидание Legends of Runeterra...")

        menu = QtWidgets.QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme.PANEL_TOP};
                color: {theme.TEXT};
                border: 1px solid {theme.GOLD_DIM};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px 6px 12px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: {theme.PANEL_EDGE};
                color: {theme.GOLD_SOFT};
            }}
            QMenu::separator {{
                height: 1px;
                background: {theme.PANEL_EDGE};
                margin: 4px 6px;
            }}
        """)

        title_action = menu.addAction("LoR Deck Tracker v1.0.0")
        title_action.setEnabled(False)
        font = title_action.font()
        font.setBold(True)
        title_action.setFont(font)

        self.tray_status_action = menu.addAction("Статус: Ожидание LoR...")
        self.tray_status_action.setEnabled(False)

        menu.addSeparator()

        settings_act = menu.addAction("Настройки...")
        settings_act.triggered.connect(self.open_settings)

        self.tray_always_vis_act = menu.addAction("Всегда показывать оверлеи (тест)")
        self.tray_always_vis_act.setCheckable(True)
        self.tray_always_vis_act.setChecked(bool(self.settings.get("always_visible", False)))
        self.tray_always_vis_act.toggled.connect(self._toggle_always_visible)

        reset_pos_act = menu.addAction("Сбросить позиции окон")
        reset_pos_act.triggered.connect(self.reset_positions)

        menu.addSeparator()

        quit_act = menu.addAction("Выход")
        quit_act.triggered.connect(QtWidgets.QApplication.quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

        if self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(
                "Legends of Runeterra Deck Tracker",
                "Трекер запущен. Оверлей появится автоматически при входе в матч.",
                QtWidgets.QSystemTrayIcon.MessageIcon.Information,
                3000
            )

    def _on_tray_activated(self, reason):
        if reason in (QtWidgets.QSystemTrayIcon.ActivationReason.Trigger,
                      QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_settings()

    def _toggle_always_visible(self, checked):
        self.settings["always_visible"] = checked
        save_settings(self.settings)
        self.apply_settings(self.settings)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    def save_pos(self, key, x, y):
        self.settings[key] = [x, y]
        save_settings(self.settings)

    def open_settings(self):
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(
                self.settings,
                on_apply=self.apply_settings,
                on_reset_positions=self.reset_positions,
                on_refresh_db=self.refresh_cards,
                on_close=self.close_settings,
            )
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        win32ext.set_no_activate(self.settings_dialog, False)

    def close_settings(self):
        if self.settings_dialog:
            self.settings_dialog.hide()

    def apply_settings(self, settings):
        self.settings = settings
        save_settings(settings)

        new_scale = float(settings.get("scale", 1.0))
        if abs(new_scale - METRICS.scale) > 0.001:
            self._rebuild_for_scale(new_scale)

        opacity = float(settings.get("opacity", 0.92))
        for panel in (self.player_panel, self.opponent_panel, self.advisor_bar):
            if panel:
                panel.setWindowOpacity(opacity)

        locked = bool(settings.get("locked", False))
        for panel in (self.player_panel, self.opponent_panel):
            if panel:
                panel.set_locked(locked)
                panel.lock_btn.active = locked

        click_through = bool(settings.get("click_through", False))
        for panel in (self.player_panel, self.opponent_panel, self.advisor_bar):
            if panel:
                win32ext.set_click_through(panel, click_through)
        if click_through:
            self.preview.hide()

        language = settings.get("language", "ru_ru")
        if language != self.card_db.language:
            self._switch_language(language)

        if self.tray_always_vis_act:
            self.tray_always_vis_act.blockSignals(True)
            self.tray_always_vis_act.setChecked(bool(settings.get("always_visible", False)))
            self.tray_always_vis_act.blockSignals(False)

        self._apply_visibility()

    def _apply_visibility(self):
        in_game = (self.last_state or {}).get("status") == "in_game"
        always = bool(self.settings.get("always_visible", False))
        show = in_game or always

        if self.settings.get("player_overlay_visible", True) and show:
            self.player_panel.show()
        else:
            self.player_panel.hide()

        if self.settings.get("opponent_overlay_visible", True) and show:
            self.opponent_panel.show()
        else:
            self.opponent_panel.hide()

        if self.settings.get("advisor_overlay_visible", True) and show:
            self.advisor_bar.show()
        else:
            self.advisor_bar.hide()

    def _rebuild_for_scale(self, scale):
        METRICS.scale = scale
        positions = {
            "player": (self.player_panel.pos().x(), self.player_panel.pos().y()),
            "opponent": (self.opponent_panel.pos().x(), self.opponent_panel.pos().y()),
            "advisor": (self.advisor_bar.pos().x(), self.advisor_bar.pos().y()),
        }
        visibilities = (
            self.player_panel.isVisible(),
            self.opponent_panel.isVisible(),
            self.advisor_bar.isVisible(),
        )
        self.player_panel.hide()
        self.opponent_panel.hide()
        self.advisor_bar.hide()
        self.preview.hide()
        self._build_panels()
        self.player_panel.move(*positions["player"])
        self.opponent_panel.move(*positions["opponent"])
        self.advisor_bar.move(*positions["advisor"])
        self.player_panel.setVisible(visibilities[0])
        self.opponent_panel.setVisible(visibilities[1])
        self.advisor_bar.setVisible(visibilities[2])
        self.apply_settings(self.settings)

    def _switch_language(self, language):
        self.card_db.set_language(language)
        self.catalog = build_catalog(self.card_db)
        self._last_catalog_lang = language
        # force a full refresh of the visible data
        self.last_state = {"status": "offline"}
        self.player_panel.last_signature = None
        self.opponent_panel.threat_signature = None
        self.opponent_panel.played_signature = None

    def refresh_cards(self):
        def worker():
            self.card_db.fetch_all(self.card_db.language)
            QtCore.QMetaObject.invokeMethod(
                self, "_after_refresh", QtCore.Qt.ConnectionType.QueuedConnection)

        threading.Thread(target=worker, daemon=True).start()

    @QtCore.pyqtSlot()
    def _after_refresh(self):
        self.catalog = build_catalog(self.card_db)
        self.last_state = {"status": "offline"}

    def reset_positions(self):
        screen = QtGui.QGuiApplication.primaryScreen().geometry()
        self.player_panel.move(METRICS(18), METRICS(70))
        w = self.opponent_panel.width()
        self.opponent_panel.move(screen.width() - w - METRICS(18), METRICS(70))
        aw = self.advisor_bar.width()
        self.advisor_bar.move((screen.width() - aw) // 2, METRICS(16))
        self.save_pos("player_pos", self.player_panel.pos().x(), self.player_panel.pos().y())
        self.save_pos("opponent_pos", self.opponent_panel.pos().x(), self.opponent_panel.pos().y())
        self.save_pos("advisor_pos", self.advisor_bar.pos().x(), self.advisor_bar.pos().y())

    def _close_player_panel(self):
        self.settings["player_overlay_visible"] = False
        save_settings(self.settings)
        self._apply_visibility()

    def _close_opponent_panel(self):
        self.settings["opponent_overlay_visible"] = False
        save_settings(self.settings)
        self._apply_visibility()

    def _toggle_lock(self, locked):
        self.settings["locked"] = locked
        self.apply_settings(self.settings)

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------
    def poll(self):
        state = self.lor_client.update()
        if not state:
            state = {"status": "offline"}

        if state.get("status") == "in_game":
            advisor = compute_threats(
                state, self.card_db, self.catalog,
                extra_spell_mana=int(self.settings.get("opp_spell_mana", 0)),
            )
            state["threats"] = advisor["threats"]
            state["advisor"] = advisor
            state["counters"] = compute_counters(state, self.card_db)
        else:
            state.setdefault("threats", [])
            state.setdefault("counters", {})

        self.last_state = state
        self.player_panel.update_state(state)
        self.opponent_panel.update_state(state)
        self.advisor_bar.update_state(state)
        self._apply_visibility()

        if self.tray_icon and self.tray_status_action:
            if state.get("status") == "in_game":
                pname = state.get("playerName", "Игрок")
                oname = state.get("opponentName", "Враг")
                self.tray_status_action.setText(f"В игре: {pname} vs {oname}")
                self.tray_icon.setToolTip(f"LoR Deck Tracker: В бою ({pname} vs {oname})")
            elif state.get("status") == "menu":
                self.tray_status_action.setText("Статус: В меню игры")
                self.tray_icon.setToolTip("LoR Deck Tracker: В меню игры")
            else:
                self.tray_status_action.setText("Статус: Ожидание LoR...")
                self.tray_icon.setToolTip("LoR Deck Tracker: Ожидание запуска игры...")

        self.player_panel.ensure_topmost()
        self.opponent_panel.ensure_topmost()
        self.advisor_bar.ensure_topmost()

        # Keep popups and tooltips topmost above panels if visible
        if self.preview and self.preview.isVisible():
            win32ext.keep_topmost(self.preview)
        from .tooltip import HextechTooltip
        tooltip = HextechTooltip.instance()
        if tooltip and tooltip.isVisible():
            win32ext.keep_topmost(tooltip)
