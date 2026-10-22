"""
The three overlay modules of the tracker.

* ``PlayerPanel``   - left edge: the cards you still hold, topdeck odds, the
                     mana curve and the deck specific counters.
* ``OpponentPanel`` - right edge: what the opponent revealed, how many cards
                     they keep (and how long they kept them) and the mana
                     aware threat board.
* ``AdvisorBar``    - top centre: a compact always visible readout of the
                     opponent's mana and the spells they can actually cast.

None of them uses tabs: everything a player needs during a turn is visible
at the same time, exactly like Hearthstone Deck Tracker.
"""

import os

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme, win32ext
from .tooltip import HextechTooltip
from .theme import (
    ARCANE, BLOOD, BLOOD_DIM, EMBER, FAINT, GOLD, GOLD_BRIGHT, GOLD_DIM,
    GOLD_SOFT, GOLD_DEEP, MANA, MANA_DARK, MANA_DEEP, MANA_ELECTRIC,
    MUTED, PANEL_EDGE, PANEL_MID, PANEL_TOP, TEXT, VERDANT, VIOLET, qcolor,
)
from .widgets import (
    ArtCache, CardBar, HudFrame, InfoRow, ManaCurve, METRICS, SectionTitle,
    ThreatRow,
)


# ==========================================================================
# Small painted controls
# ==========================================================================
class IconButton(QtWidgets.QWidget):
    """A tiny hand drawn icon button (lock / sliders / cross / mouse)."""

    def __init__(self, kind, tooltip="", color=GOLD, on_click=None, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.color = color
        self.hovered = False
        self.active = False
        self.on_click = on_click
        self.tooltip_text = tooltip
        self.setFixedSize(METRICS(20), METRICS(20))
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

    def enterEvent(self, e):
        self.hovered = True
        self.update()
        if self.tooltip_text:
            pos = self.mapToGlobal(QtCore.QPoint(self.width(), self.height()))
            HextechTooltip.instance().show_tip(self.tooltip_text, "", pos, accent=GOLD)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.hovered = False
        self.update()
        HextechTooltip.instance().hide_tip()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if self.on_click:
            self.on_click()
        super().mousePressEvent(e)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(self.rect())
        col = qcolor(self.color, 0.95 if (self.active or self.hovered) else 0.6)
        if self.hovered:
            p.setPen(QtGui.QPen(qcolor(self.color, 0.5), 1))
            p.setBrush(QtGui.QBrush(qcolor(self.color, 0.16)))
            p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)

        pen = QtGui.QPen(col)
        pen.setWidthF(1.4)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        cx, cy = rect.center().x(), rect.center().y()
        s = rect.width()

        if self.kind == "lock":
            closed = self.active
            body = QtCore.QRectF(cx - s * 0.26, cy - s * 0.02, s * 0.52, s * 0.34)
            p.drawRoundedRect(body, 2, 2)
            shackle = QtGui.QPainterPath()
            if closed:
                shackle.moveTo(cx - s * 0.18, cy - s * 0.02)
                shackle.arcTo(QtCore.QRectF(cx - s * 0.18, cy - s * 0.34, s * 0.36, s * 0.36),
                              0, 180)
            else:
                shackle.moveTo(cx + s * 0.02, cy - s * 0.02)
                shackle.arcTo(QtCore.QRectF(cx - s * 0.10, cy - s * 0.34, s * 0.36, s * 0.36),
                              90, 180)
            p.drawPath(shackle)
        elif self.kind == "sliders":
            for i, y in enumerate((cy - s * 0.22, cy, cy + s * 0.22)):
                p.drawLine(QtCore.QPointF(cx - s * 0.28, y), QtCore.QPointF(cx + s * 0.28, y))
            for i, (x, y) in enumerate(((cx - s * 0.10, cy - s * 0.22),
                                       (cx + s * 0.14, cy),
                                       (cx - s * 0.18, cy + s * 0.22))):
                p.setBrush(QtGui.QBrush(col))
                p.drawEllipse(QtCore.QPointF(x, y), s * 0.075, s * 0.075)
        elif self.kind == "close":
            p.drawLine(QtCore.QPointF(cx - s * 0.20, cy - s * 0.20),
                       QtCore.QPointF(cx + s * 0.20, cy + s * 0.20))
            p.drawLine(QtCore.QPointF(cx + s * 0.20, cy - s * 0.20),
                       QtCore.QPointF(cx - s * 0.20, cy + s * 0.20))
        elif self.kind == "mouse":
            p.drawRoundedRect(QtCore.QRectF(cx - s * 0.22, cy - s * 0.30, s * 0.44, s * 0.60), 5, 5)
            p.drawLine(QtCore.QPointF(cx, cy - s * 0.28), QtCore.QPointF(cx, cy - s * 0.06))
        elif self.kind == "card":
            p.drawRoundedRect(QtCore.QRectF(cx - s * 0.24, cy - s * 0.30, s * 0.48, s * 0.60), 3, 3)
            p.drawEllipse(QtCore.QPointF(cx, cy), s * 0.09, s * 0.09)


class ToggleChip(QtWidgets.QWidget):
    """Small clickable pill used for filters and toggles."""

    def __init__(self, text, on_click=None, color=GOLD, parent=None):
        super().__init__(parent)
        self.text = text
        self.on_click = on_click
        self.color = color
        self.active = False
        self.hovered = False
        self.setFixedHeight(METRICS(18))
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

    def set_active(self, value):
        if self.active != value:
            self.active = value
            self.update()

    def enterEvent(self, e):
        self.hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.hovered = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if self.on_click:
            self.on_click()
        super().mousePressEvent(e)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        fm = QtGui.QFontMetrics(theme.body_font(METRICS(8), bold=True))
        w = fm.horizontalAdvance(self.text) + METRICS(14)
        self.setFixedWidth(w)
        rect = QtCore.QRectF(0, 0, w, self.height())
        if self.active:
            p.setPen(QtGui.QPen(qcolor(self.color, 0.8), 1))
            p.setBrush(QtGui.QBrush(qcolor(self.color, 0.22)))
        else:
            p.setPen(QtGui.QPen(qcolor(FAINT, 0.6), 1))
            p.setBrush(QtGui.QBrush(qcolor("#0C1422", 0.55)))
        p.drawRoundedRect(rect, METRICS(4), METRICS(4))
        p.setFont(theme.body_font(METRICS(8), bold=True))
        p.setPen(qcolor(self.color if self.active else MUTED))
        p.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, self.text)


# ==========================================================================
# Overlay window base
# ==========================================================================
class OverlayWindow(QtWidgets.QWidget):
    """Frameless, translucent, draggable and lockable overlay window."""

    def __init__(self, title, width, height, x, y, accent=GOLD, show_in_taskbar=False):
        super().__init__()
        self.setWindowTitle(title)
        self.accent = accent
        self.drag_position = None
        self.is_locked = False
        self.on_position_changed = None

        if show_in_taskbar:
            flags = (QtCore.Qt.WindowType.FramelessWindowHint |
                     QtCore.Qt.WindowType.WindowStaysOnTopHint |
                     QtCore.Qt.WindowType.Window)
        else:
            flags = (QtCore.Qt.WindowType.FramelessWindowHint |
                     QtCore.Qt.WindowType.WindowStaysOnTopHint |
                     QtCore.Qt.WindowType.Tool)
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setGeometry(x, y, width, height)

        self.body = QtWidgets.QWidget(self)
        self.body.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.body.setMouseTracking(True)

        win32ext.set_no_activate(self, True)
        if show_in_taskbar:
            win32ext.show_in_taskbar(self)
        else:
            win32ext.hide_from_taskbar(self)
        win32ext.keep_topmost(self)

    # -- dragging --------------------------------------------------------
    def mousePressEvent(self, event):
        if not self.is_locked and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if (not self.is_locked and
                event.buttons() == QtCore.Qt.MouseButton.LeftButton and
                self.drag_position is not None):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        if self.on_position_changed:
            self.on_position_changed(self.pos().x(), self.pos().y())
        super().mouseReleaseEvent(event)

    def set_locked(self, locked):
        self.is_locked = locked

    def ensure_topmost(self):
        win32ext.keep_topmost(self)


# ==========================================================================
# Player deck panel
# ==========================================================================
class PlayerPanel(OverlayWindow):
    """Left edge HUD: everything that is still in your deck."""

    def __init__(self, card_db, art_cache, preview, on_open_settings, on_lock_toggle, on_close=None):
        width = METRICS(322)
        height = METRICS(660)
        super().__init__("LoR Deck Tracker", width, height, 18, 70, accent=GOLD, show_in_taskbar=True)
        self.card_db = card_db
        self.art_cache = art_cache
        self.preview = preview
        self.on_open_settings = on_open_settings
        self.on_lock_toggle = on_lock_toggle
        self.on_close = on_close

        self.tiles = {}
        self.last_signature = None
        self.show_only_remaining = True
        self.cost_filter = None
        self.state = None

        self._build()
        win32ext.set_no_activate(self, True)

    # -- construction ----------------------------------------------------
    def _build(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = HudFrame(accent=GOLD, accent_side="none")
        self.frame = frame
        outer.addWidget(frame)

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(METRICS(11), METRICS(9), METRICS(11), METRICS(9))
        layout.setSpacing(METRICS(6))

        # ---- header --------------------------------------------------
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(METRICS(4))

        title = QtWidgets.QLabel("ВАША КОЛОДА")
        title.setFont(theme.header_font(METRICS(11), bold=True))
        title.setStyleSheet(f"color: {GOLD}; background: transparent; border: none;")
        header.addWidget(title)

        self.title_player = QtWidgets.QLabel("")
        self.title_player.setFont(theme.body_font(METRICS(8.5)))
        self.title_player.setStyleSheet(f"color: {MUTED}; background: transparent; border: none;")
        header.addWidget(self.title_player)
        header.addStretch()

        self.lock_btn = IconButton("lock", "Закрепить положение", GOLD,
                                   on_click=self._toggle_lock)
        header.addWidget(self.lock_btn)
        self.settings_btn = IconButton("sliders", "Настройки", GOLD,
                                       on_click=self.on_open_settings)
        header.addWidget(self.settings_btn)
        self.close_btn = IconButton("close", "Скрыть оверлей", GOLD, on_click=self._handle_close)
        header.addWidget(self.close_btn)
        layout.addLayout(header)

        # ---- status strip --------------------------------------------
        self.status = InfoRow()
        layout.addWidget(self.status)

        self.turn_strip = InfoRow()
        layout.addWidget(self.turn_strip)

        # ---- filter row ----------------------------------------------
        filter_row = QtWidgets.QHBoxLayout()
        filter_row.setSpacing(METRICS(4))
        self.only_remaining_chip = ToggleChip("ТОЛЬКО ОСТАВШИЕСЯ", on_click=self._toggle_only_remaining)
        self.only_remaining_chip.set_active(True)
        filter_row.addWidget(self.only_remaining_chip)
        filter_row.addStretch()
        self.count_lbl = QtWidgets.QLabel("")
        self.count_lbl.setFont(theme.mono_font(METRICS(8.5)))
        self.count_lbl.setStyleSheet(f"color: {GOLD_SOFT}; background: transparent; border: none;")
        filter_row.addWidget(self.count_lbl)
        layout.addLayout(filter_row)

        # ---- card list -----------------------------------------------
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: rgba(4, 7, 13, 0.40);
                width: {METRICS(5)}px;
                border: none;
                margin-left: 2px;
                margin-right: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {GOLD_DIM};
                border-radius: 2px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {GOLD};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self.content = QtWidgets.QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.list_layout = QtWidgets.QVBoxLayout(self.content)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(METRICS(3))
        self.list_layout.addStretch()
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, stretch=1)

        # ---- mana curve ----------------------------------------------
        curve_title = SectionTitle("КРИВАЯ МАНЫ", GOLD)
        layout.addWidget(curve_title)
        self.curve = ManaCurve()
        layout.addWidget(self.curve)

        # ---- counters -------------------------------------------------
        self.counter_title = SectionTitle("СЧЁТЧИКИ", GOLD)
        layout.addWidget(self.counter_title)
        self.counter_layout = QtWidgets.QHBoxLayout()
        self.counter_layout.setSpacing(METRICS(4))
        self.counter_wrap = QtWidgets.QWidget()
        self.counter_wrap.setStyleSheet("background: transparent;")
        self.counter_wrap.setLayout(self.counter_layout)
        self.counter_layout.addStretch()
        layout.addWidget(self.counter_wrap)

        self.empty_lbl = QtWidgets.QLabel("Ожидание матча…")
        self.empty_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setFont(theme.body_font(METRICS(9)))
        self.empty_lbl.setStyleSheet(f"color: {MUTED}; background: transparent; border: none;")
        layout.addWidget(self.empty_lbl, 1)

    # -- helpers ---------------------------------------------------------
    def _handle_close(self):
        self.hide()
        if self.on_close:
            self.on_close()

    def _toggle_lock(self):
        self.on_lock_toggle(not self.is_locked)

    def _toggle_only_remaining(self):
        self.show_only_remaining = not self.show_only_remaining
        self.only_remaining_chip.set_active(self.show_only_remaining)
        self.last_signature = None
        if self.state:
            self.update_state(self.state)

    def _on_hover(self, code, widget):
        if not code:
            self.preview.hide_preview()
            return
        extra = {}
        if self.state:
            for card in self.state.get("myDeck", []):
                if card.get("code") == code:
                    extra = {"remaining": card.get("remaining"), "initial": card.get("initial")}
                    break
        self.preview.show_card(code, extra=extra,
                               near_rect=QtCore.QRect(widget.mapToGlobal(QtCore.QPoint(0, 0)), widget.size()))

    # -- state -----------------------------------------------------------
    def update_state(self, state):
        self.state = state
        if not state or state.get("status") != "in_game":
            self._render_idle(state)
            return

        self.empty_lbl.setVisible(False)
        self.scroll.setVisible(True)
        self.title_player.setText(state.get("playerName", ""))

        total = state.get("totalRemaining", 0)
        initial = state.get("totalInitial", 0)
        self.status.set_row("КАРТ В КОЛОДЕ", f"{total} / {initial}", GOLD_SOFT)

        turn = state.get("turn", {}) or {}
        phase = turn.get("phase", "ours")
        phase_txt = {"ours": "ВАШ ХОД", "theirs": "ХОД ПРОТИВНИКА",
                     "mulligan": "МУЛЛИГАН"}.get(phase, "")
        self.turn_strip.set_row(
            f"{phase_txt} · ХОД {turn.get('ourTurn', 1)}",
            f"МАКС МАНА ВРАГА: {turn.get('theirMaxMana', 0)}",
            MANA if phase == "ours" else EMBER,
        )

        deck = state.get("myDeck", []) or []
        visible = []
        for card in deck:
            if self.show_only_remaining and card.get("remaining", 0) <= 0:
                continue
            visible.append(card)

        self.count_lbl.setText(f"{len(visible)} карт")
        self._sync_tiles(visible)

        # mana curve
        buckets = {}
        for card in deck:
            cost = card.get("cost", 0)
            key = cost if cost <= 7 else 8
            buckets[key] = buckets.get(key, 0) + card.get("remaining", 0)
        curve = [(k, buckets.get(k, 0)) for k in range(0, 9)]
        self.curve.set_curve(curve)

        self._render_counters(state)

    def _render_idle(self, state):
        self.empty_lbl.setVisible(True)
        self.scroll.setVisible(False)
        self.title_player.setText("")
        status = (state or {}).get("status", "offline")
        if status == "offline":
            self.empty_lbl.setText("LoR не запущен")
            self.status.set_row("СОСТОЯНИЕ", "НЕТ СВЯЗИ", FAINT)
        else:
            self.empty_lbl.setText("Ожидание матча…")
            self.status.set_row("СОСТОЯНИЕ", "В МЕНЮ", MUTED)
        self.turn_strip.set_row("", "")
        self.count_lbl.setText("")
        self.curve.set_curve([])
        self._clear_tiles()
        self._clear_counters()

    def _clear_tiles(self):
        for tile in self.tiles.values():
            self.list_layout.removeWidget(tile)
            tile.setParent(None)
            tile.deleteLater()
        self.tiles.clear()
        self.last_signature = None

    def _sync_tiles(self, cards):
        codes = [c["code"] for c in cards]
        signature = tuple((c["code"], c["remaining"], c["prob"]) for c in cards)
        if signature == self.last_signature:
            return
        self.last_signature = signature

        for code in list(self.tiles.keys()):
            if code not in codes:
                tile = self.tiles.pop(code)
                self.list_layout.removeWidget(tile)
                tile.setParent(None)
                tile.deleteLater()

        for idx, card in enumerate(cards):
            code = card["code"]
            tile = self.tiles.get(code)
            if tile is None:
                tile = CardBar(self.art_cache, on_hover=self._on_hover)
                self.tiles[code] = tile
                self.list_layout.insertWidget(idx, tile)
            tile.set_card(card)

    def _clear_counters(self):
        while self.counter_layout.count():
            item = self.counter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _render_counters(self, state):
        counters = state.get("counters", {}) or {}
        self._clear_counters()

        chips = []

        puff = counters.get("puffcap", {}) or {}
        if isinstance(puff, dict):
            if puff.get("theirs"):
                names = ", ".join(p["name"] if isinstance(p, dict) else str(p) for p in puff["theirs"][:2])
                chips.append((VERDANT, f"ГРИБЫ ×{puff.get('theirPuffcaps', 0)}", names))
            if puff.get("ours"):
                chips.append((MANA, "ГРИБЫ В КОЛОДЕ", f"{len(puff['ours'])} карт"))
        elif counters.get("puffcaps"):
            chips.append((VERDANT, f"ГРИБЫ ×{counters['puffcaps']}", f"~{counters.get('puffcap_avg_dmg', 0)} ур./дров"))

        flash = counters.get("flashbomb", {}) or {}
        if isinstance(flash, dict):
            if flash.get("theirs"):
                chips.append((EMBER, f"ФЛЕШБОМБЫ ~{flash.get('expectedInTop8', 0)}",
                              "в топ-8 вашей колоды"))
        elif counters.get("flashbombs"):
            chips.append((EMBER, f"ФЛЕШБОМБЫ ×{counters['flashbombs']}", "ловушки в колоде"))

        hallowed = counters.get("hallowed", []) or []
        if hallowed:
            if isinstance(hallowed, list):
                names = ", ".join(h["name"] if isinstance(h, dict) else str(h) for h in hallowed[:2])
                chips.append((GOLD, "СВЯТОСТЬ", names or str(len(hallowed))))
            else:
                chips.append((GOLD, f"СВЯТОСТЬ +{hallowed}", "атака первого союзника"))

        if counters.get("slain"):
            chips.append((BLOOD, "СРАЖЕНО", str(counters["slain"])))

        spell = counters.get("spellMana", []) or []
        if spell:
            chips.append((VIOLET, "МАНА ЗАКЛИНАНИЙ",
                          ", ".join(s["name"] for s in spell[:2])))

        champs = counters.get("champions", []) or []
        for champ in champs[:2]:
            chips.append((ARCANE, f"{champ['name']} УР.{champ['level']}",
                          f"x{champ['count']}"))

        for color, title, sub in chips:
            chip = _CounterChip(color, title, sub)
            self.counter_layout.addWidget(chip)
        self.counter_layout.addStretch()
        self.counter_title.setVisible(bool(chips))


class _CounterChip(QtWidgets.QWidget):
    """Counter tile: coloured title + small subtitle."""

    def __init__(self, color, title, sub, parent=None):
        super().__init__(parent)
        self.color = color
        self.title = title
        self.sub = sub
        self.setFixedHeight(METRICS(34))
        self.setMinimumWidth(METRICS(104))
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                           QtWidgets.QSizePolicy.Policy.Fixed)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QtGui.QPen(qcolor(self.color, 0.45), 1))
        p.setBrush(QtGui.QBrush(qcolor(self.color, 0.10)))
        p.drawRoundedRect(rect, METRICS(5), METRICS(5))
        p.setFont(theme.body_font(METRICS(7.5), bold=True))
        p.setPen(qcolor(self.color))
        p.drawText(QtCore.QRectF(rect.left() + 5, rect.top() + 2, rect.width() - 10, 12),
                   QtCore.Qt.AlignmentFlag.AlignLeft, self.title)
        p.setFont(theme.body_font(METRICS(6.5)))
        p.setPen(qcolor(MUTED))
        fm = QtGui.QFontMetrics(p.font())
        p.drawText(QtCore.QRectF(rect.left() + 5, rect.top() + 14, rect.width() - 10, 12),
                   QtCore.Qt.AlignmentFlag.AlignLeft,
                   fm.elidedText(self.sub, QtCore.Qt.TextElideMode.ElideRight,
                                 int(rect.width() - 10)))


# ==========================================================================
# Opponent panel
# ==========================================================================
class HandStrip(QtWidgets.QWidget):
    """Row of Hextech card back tiles tracking opponent hand age & origin (HDT style)."""

    HEIGHT = 44

    def __init__(self, parent=None):
        super().__init__(parent)
        self.count = 0
        self.mulligan = 0
        self.hovered_idx = None
        self.setMouseTracking(True)
        self.setFixedHeight(METRICS(self.HEIGHT))

    def set_hand(self, count, mulligan):
        if (count, mulligan) != (self.count, self.mulligan):
            self.count, self.mulligan = count, mulligan
            self.update()

    def mouseMoveEvent(self, e):
        card_w = METRICS(24)
        gap = METRICS(3)
        step = card_w + gap
        x = e.position().x() - METRICS(4)
        if x < 0:
            idx = None
        else:
            idx = int(x // step)
            if idx >= self.count:
                idx = None
        if idx != self.hovered_idx:
            self.hovered_idx = idx
            self.update()
            if idx is not None:
                card_w = METRICS(24)
                gap = METRICS(3)
                step = card_w + gap
                tile_local_x = METRICS(4) + idx * step
                tile_local_y = self.height() // 2
                global_pos = self.mapToGlobal(QtCore.QPoint(int(tile_local_x + card_w), int(tile_local_y)))
                if idx < self.mulligan:
                    HextechTooltip.instance().show_tip(
                        f"Карта #{idx+1} · С МУЛЛИГАНА",
                        "Оппонент держит эту карту со старта матча.\nВнимание: 90% вероятность ключевого ремувала (Deny / Vengeance / Single Combat) или ульты!",
                        global_pos,
                        accent=EMBER
                    )
                else:
                    HextechTooltip.instance().show_tip(
                        f"Карта #{idx+1} · ВЗЯТА ИЗ КОЛОДЫ",
                        "Получена оппонентом в процессе игры из обычной колоды.",
                        global_pos,
                        accent=MANA
                    )
            else:
                HextechTooltip.instance().hide_tip()

    def leaveEvent(self, e):
        self.hovered_idx = None
        self.update()
        HextechTooltip.instance().hide_tip()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        if self.count <= 0:
            return

        card_w = METRICS(24)
        card_h = METRICS(32)
        gap = METRICS(3)
        cy = self.height() / 2.0
        x = METRICS(4)

        max_show = min(self.count, 10)
        for i in range(max_show):
            rect = QtCore.QRectF(x, cy - card_h / 2.0, card_w, card_h)
            is_mull = i < self.mulligan
            is_hover = (i == self.hovered_idx)

            # Card Back Tile with metallic border
            card_path = theme.chamfered_path(rect, 3.5)
            grad = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, qcolor("#121E36"))
            grad.setColorAt(1.0, qcolor("#060B14"))
            p.setPen(QtGui.QPen(qcolor(MANA if is_hover else (GOLD if is_mull else PANEL_EDGE), 1.0 if not is_hover else 1.5)))
            p.setBrush(QtGui.QBrush(grad))
            p.drawPath(card_path)

            # Center runic diamond
            center_pts = [
                QtCore.QPointF(rect.center().x(), rect.center().y() - 4),
                QtCore.QPointF(rect.center().x() + 3.5, rect.center().y()),
                QtCore.QPointF(rect.center().x(), rect.center().y() + 4),
                QtCore.QPointF(rect.center().x() - 3.5, rect.center().y()),
            ]
            poly = QtGui.QPolygonF(center_pts)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QBrush(qcolor(GOLD if is_mull else MANA, 0.7 if not is_hover else 1.0)))
            p.drawPolygon(poly)

            # Top badge (МУЛЛ / ХОД)
            badge_h = METRICS(10)
            badge_rect = QtCore.QRectF(rect.left(), rect.top() - METRICS(3), rect.width(), badge_h)
            b_col = EMBER if is_mull else MANA_DEEP
            p.setPen(QtGui.QPen(qcolor(EMBER if is_mull else MANA, 0.8), 1))
            p.setBrush(QtGui.QBrush(qcolor(b_col, 0.75)))
            p.drawRoundedRect(badge_rect, 2, 2)

            p.setFont(theme.display_font(METRICS(6), bold=True))
            p.setPen(qcolor(GOLD_BRIGHT if is_mull else TEXT))
            b_text = "МУЛЛ" if is_mull else f"Х{i+1}"
            p.drawText(badge_rect, QtCore.Qt.AlignmentFlag.AlignCenter, b_text)

            x += card_w + gap

        if self.count > 10:
            p.setFont(theme.display_font(METRICS(9), bold=True))
            p.setPen(qcolor(GOLD_BRIGHT))
            p.drawText(QtCore.QRectF(x + 2, 0, METRICS(40), self.height()),
                       QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, f"+{self.count - 10}")


class PlayedRow(QtWidgets.QWidget):
    """Revealed opponent card with panoramic art, times played, and remaining deck estimation."""

    HEIGHT = 30

    def __init__(self, art_cache, on_hover=None, parent=None):
        super().__init__(parent)
        self.art_cache = art_cache
        self.on_hover = on_hover
        self.card = {}
        self.code = ""
        self.hovered = False
        self.setMouseTracking(True)
        self.setFixedHeight(METRICS(self.HEIGHT))

    def set_card(self, card):
        self.card = card or {}
        self.code = self.card.get("code", "")
        self.update()

    def enterEvent(self, e):
        self.hovered = True
        self.update()
        if self.on_hover:
            self.on_hover(self.code, self)
        count = self.card.get("count", 1)
        rem = max(0, 3 - count)
        global_pos = self.mapToGlobal(QtCore.QPoint(int(self.width()), int(self.height() // 2)))
        status_txt = f"Сыграно копий: {count} из 3.\nВ колоде противника ориентировочно осталось: ~{rem}."
        if count >= 3:
            status_txt += "\n✓ Угроза нейтрализована: все копии этой карты вышли!"
        HextechTooltip.instance().show_tip(
            self.card.get("name", "Карта"),
            status_txt,
            global_pos,
            accent=VERDANT if count >= 3 else (EMBER if count == 2 else GOLD)
        )
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.hovered = False
        self.update()
        HextechTooltip.instance().hide_tip()
        if self.on_hover:
            self.on_hover(None, self)
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        card = self.card
        if not card:
            return
        regions = card.get("regionRefs") or card.get("regions") or []
        accent = theme.region_color(regions[0]) if regions else GOLD_DIM

        count = card.get("count", 1)
        all_played = count >= 3

        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = METRICS(4.5)

        # Base tile
        bg_col = qcolor("#0B121E" if not all_played else "#081610")
        border_col = qcolor(VERDANT if all_played else (MANA if self.hovered else "#1B2738"), 0.85 if self.hovered else 0.40)
        p.setPen(QtGui.QPen(border_col, 1.2 if self.hovered else 1.0))
        p.setBrush(QtGui.QBrush(bg_col))
        p.drawRoundedRect(rect, radius, radius)

        # Panoramic card art on right with smooth fade
        art_w = rect.width() * 0.58
        art_rect = QtCore.QRectF(rect.right() - art_w, rect.top() + 1, art_w, rect.height() - 2)
        thumb = self.art_cache.thumb(self.code, art_rect.size().toSize())
        if thumb is not None and not thumb.isNull():
            p.save()
            clip = QtGui.QPainterPath()
            clip.addRoundedRect(rect, radius, radius)
            p.setClipPath(clip)
            p.drawPixmap(art_rect.toRect(), thumb)
            grad = QtGui.QLinearGradient(art_rect.left(), 0, art_rect.right(), 0)
            grad.setColorAt(0.0, qcolor(bg_col, 1.0))
            grad.setColorAt(0.35, qcolor(bg_col, 0.90))
            grad.setColorAt(0.70, qcolor(bg_col, 0.40))
            grad.setColorAt(1.0, qcolor(bg_col, 0.05))
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QBrush(grad))
            p.drawRect(art_rect)
            p.restore()

        cy = self.height() / 2.0
        left = METRICS(6)

        # Mana crystal
        gem_r = METRICS(7.5)
        theme.paint_mana_crystal(p, QtCore.QPointF(left + gem_r, cy), gem_r,
                                 card.get("cost", 0))
        left += gem_r * 2 + METRICS(7)

        # Count & safety badge (compact LoR-style)
        badge_w = METRICS(30)
        badge = QtCore.QRectF(self.width() - badge_w - METRICS(6), cy - METRICS(8.5),
                              badge_w, METRICS(17))

        badge_col = VERDANT if all_played else (EMBER if count == 2 else GOLD)
        badge_path = theme.chamfered_path(badge, METRICS(3.5))
        p.setPen(QtGui.QPen(qcolor(badge_col, 0.85), 1.0))
        p.setBrush(QtGui.QBrush(qcolor(badge_col, 0.20)))
        p.drawPath(badge_path)

        p.setFont(theme.number_font(METRICS(8), bold=True))
        p.setPen(qcolor("#D7FFE2" if all_played else (GOLD_BRIGHT if count == 2 else TEXT)))
        if all_played:
            p.drawText(badge, QtCore.Qt.AlignmentFlag.AlignCenter, "x3")
        elif count == 2:
            p.drawText(badge, QtCore.Qt.AlignmentFlag.AlignCenter, "x2")
        else:
            p.drawText(badge, QtCore.Qt.AlignmentFlag.AlignCenter, "x1")

        # Card Name
        avail = badge.left() - left - METRICS(6)
        f = theme.card_name_font(METRICS(9.5), bold=True)
        p.setFont(f)
        fm = QtGui.QFontMetrics(f)
        name = card.get("name", "")
        if card.get("onBoard"):
            name = f"{name} ●"
        shown = fm.elidedText(name, QtCore.Qt.TextElideMode.ElideRight, int(avail))

        # Drop shadow for readability over art
        p.setPen(qcolor("#000000", 0.95))
        p.drawText(QtCore.QRectF(left + 1, 1, avail, self.height()),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, shown)
        p.setPen(qcolor(TEXT))
        p.drawText(QtCore.QRectF(left, 0, avail, self.height()),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, shown)


class OpponentPanel(OverlayWindow):
    """Right edge HUD: opponent intel + mana aware threat board."""

    def __init__(self, card_db, art_cache, preview, on_open_settings=None, on_lock_toggle=None, on_close=None):
        width = METRICS(330)
        height = METRICS(660)
        screen = QtGui.QGuiApplication.primaryScreen().geometry()
        super().__init__("Противник", width, height, screen.width() - width - 18, 70,
                         accent=GOLD)
        self.card_db = card_db
        self.art_cache = art_cache
        self.preview = preview
        self.on_open_settings = on_open_settings
        self.on_lock_toggle = on_lock_toggle
        self.on_close = on_close
        self.state = None
        self.threat_rows = {}
        self.played_rows = {}
        self.threat_signature = None
        self.played_signature = None
        self._build()

    def _handle_close(self):
        self.hide()
        if self.on_close:
            self.on_close()

    def _toggle_lock(self):
        if self.on_lock_toggle:
            self.on_lock_toggle(not self.is_locked)

    def _build(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = HudFrame(accent=GOLD, accent_side="none")
        self.frame = frame
        outer.addWidget(frame)

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(METRICS(11), METRICS(9), METRICS(11), METRICS(9))
        layout.setSpacing(METRICS(6))

        # header
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("ПРОТИВНИК")
        title.setFont(theme.header_font(METRICS(11), bold=True))
        title.setStyleSheet(f"color: {GOLD}; background: transparent; border: none;")
        header.addWidget(title)
        self.opp_player = QtWidgets.QLabel("")
        self.opp_player.setFont(theme.body_font(METRICS(8.5)))
        self.opp_player.setStyleSheet(f"color: {MUTED}; background: transparent; border: none;")
        header.addWidget(self.opp_player)
        header.addStretch()
        self.lock_btn = IconButton("lock", "Закрепить положение", GOLD, on_click=self._toggle_lock)
        header.addWidget(self.lock_btn)
        if self.on_open_settings:
            self.settings_btn = IconButton("sliders", "Настройки", GOLD, on_click=self.on_open_settings)
            header.addWidget(self.settings_btn)
        self.close_btn = IconButton("close", "Скрыть оверлей", GOLD, on_click=self._handle_close)
        header.addWidget(self.close_btn)
        layout.addLayout(header)

        self.status = InfoRow()
        layout.addWidget(self.status)

        # regions
        self.region_row = QtWidgets.QWidget()
        self.region_row.setFixedHeight(METRICS(22))
        self.region_row.setStyleSheet("background: transparent;")
        layout.addWidget(self.region_row)

        # ---- hand -----------------------------------------------------
        layout.addWidget(SectionTitle("РУКА ПРОТИВНИКА", ARCANE))
        self.hand_strip = HandStrip()
        layout.addWidget(self.hand_strip)
        self.hand_info = InfoRow()
        layout.addWidget(self.hand_info)

        # ---- scroll area (played + threats) ---------------------------
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: rgba(4, 7, 13, 0.40);
                width: {METRICS(5)}px;
                border: none;
                margin-left: 2px;
                margin-right: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {GOLD_DIM};
                border-radius: 2px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {GOLD};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        self.content = QtWidgets.QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.list_layout = QtWidgets.QVBoxLayout(self.content)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(METRICS(3))
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, stretch=1)

        # sections inside the scroll area
        self.played_title = SectionTitle("СЫГРАНО / СБРОС", GOLD)
        self.list_layout.addWidget(self.played_title)
        self.played_holder = QtWidgets.QWidget()
        self.played_holder.setStyleSheet("background: transparent;")
        self.played_layout = QtWidgets.QVBoxLayout(self.played_holder)
        self.played_layout.setContentsMargins(0, 0, 0, 0)
        self.played_layout.setSpacing(METRICS(2))
        self.list_layout.addWidget(self.played_holder)

        self.threat_title = SectionTitle("УГРОЗЫ И ОТВЕТЫ", GOLD)
        self.list_layout.addWidget(self.threat_title)
        self.threat_holder = QtWidgets.QWidget()
        self.threat_holder.setStyleSheet("background: transparent;")
        self.threat_layout = QtWidgets.QVBoxLayout(self.threat_holder)
        self.threat_layout.setContentsMargins(0, 0, 0, 0)
        self.threat_layout.setSpacing(METRICS(3))
        self.list_layout.addWidget(self.threat_holder)
        self.list_layout.addStretch()

        self.empty_lbl = QtWidgets.QLabel("Ожидание матча…")
        self.empty_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setFont(theme.body_font(METRICS(9)))
        self.empty_lbl.setStyleSheet(f"color: {MUTED}; background: transparent; border: none;")
        layout.addWidget(self.empty_lbl, 1)

    # -- helpers ---------------------------------------------------------
    def _on_hover(self, code, widget):
        if not code:
            self.preview.hide_preview()
            return
        self.preview.show_card(code, near_rect=QtCore.QRect(widget.mapToGlobal(QtCore.QPoint(0, 0)), widget.size()))

    # -- state -----------------------------------------------------------
    def update_state(self, state):
        self.state = state
        if not state or state.get("status") != "in_game":
            self._render_idle(state)
            return

        self.empty_lbl.setVisible(False)
        self.scroll.setVisible(True)

        # Format opponent name nicely (clean up internal bot deck IDs like decks_badstuns_name)
        opp_name = state.get("opponentName", "") or ""
        if opp_name.startswith("decks_") and opp_name.endswith("_name"):
            core_name = opp_name[len("decks_"):-len("_name")]
            opp_name = f"Бот: {core_name.capitalize()}"
        elif opp_name.startswith("decks_"):
            opp_name = f"Бот: {opp_name[len('decks_'):]}"
        self.opp_player.setText(opp_name)

        turn = state.get("turn", {}) or {}
        self.status.set_row("ХОД ПРОТИВНИКА", f"{turn.get('theirTurn', 2)}", EMBER)

        self._render_regions(state.get("opponentRegions", []) or [])

        # hand inference
        hand = state.get("opponentHandCount", turn.get("oppHandSize", 0))
        their_drawn = turn.get("theirCardsDrawn", 4)
        mulligan = state.get("opponentMulliganKept", max(0, hand - max(0, their_drawn - 4)))
        self.hand_strip.set_hand(hand, mulligan)
        self.hand_info.set_row(
            "НЕИЗВЕСТНЫХ КАРТ В РУКЕ",
            f"~{hand}" + (f"  (~{mulligan} с муллигана)" if mulligan else ""),
            ARCANE,
        )

        cards = state.get("opponentCards") or state.get("opponentPlayed", []) or []
        self._render_played(cards)
        self._render_threats(state.get("threats", []) or [])

    def _render_idle(self, state):
        self.empty_lbl.setVisible(True)
        self.scroll.setVisible(False)
        self.opp_player.setText("")
        status = (state or {}).get("status", "offline")
        self.status.set_row("СОСТОЯНИЕ", "НЕТ СВЯЗИ" if status == "offline" else "В МЕНЮ", MUTED)
        self.hand_strip.set_hand(0, 0)
        self.hand_info.set_row("", "")
        self._clear(self.played_layout, self.played_rows)
        self._clear(self.threat_layout, self.threat_rows)
        self.played_signature = None
        self.threat_signature = None
        self.region_row.update()

    def _clear(self, layout, registry):
        for widget in registry.values():
            layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        registry.clear()

    def _render_regions(self, regions):
        for child in self.region_row.findChildren(QtWidgets.QWidget):
            child.setParent(None)
            child.deleteLater()
        layout = QtWidgets.QHBoxLayout(self.region_row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(METRICS(4))
        lbl = QtWidgets.QLabel("РЕГИОНЫ:")
        lbl.setFont(theme.body_font(METRICS(7.5), bold=True))
        lbl.setStyleSheet(f"color: {MUTED}; background: transparent; border: none;")
        layout.addWidget(lbl)
        for ref in regions:
            badge = _RegionBadge(ref)
            layout.addWidget(badge)
        layout.addStretch()

    def _render_played(self, cards):
        signature = tuple((c["code"], c["count"], c.get("onBoard")) for c in cards)
        if signature == self.played_signature:
            return
        self.played_signature = signature
        self._clear(self.played_layout, self.played_rows)

        if not cards:
            lbl = QtWidgets.QLabel("Противник ещё ничего не показал")
            lbl.setFont(theme.body_font(METRICS(8)))
            lbl.setStyleSheet(f"color: {FAINT}; background: transparent; border: none;")
            self.played_layout.addWidget(lbl)
            return

        for card in cards:
            row = PlayedRow(self.art_cache, on_hover=self._on_hover)
            row.set_card(card)
            self.played_rows[card["code"]] = row
            self.played_layout.addWidget(row)

    def _render_threats(self, threats):
        signature = tuple((t["code"], t.get("canNow")) for t in threats)
        if signature == self.threat_signature:
            return
        self.threat_signature = signature
        self._clear(self.threat_layout, self.threat_rows)

        if not threats:
            lbl = QtWidgets.QLabel("Ожидание открытия регионов врага")
            lbl.setFont(theme.body_font(METRICS(8)))
            lbl.setStyleSheet(f"color: {FAINT}; background: transparent; border: none;")
            self.threat_layout.addWidget(lbl)
            return

        now_threats = [t for t in threats if t.get("canNow")]
        future_threats = [t for t in threats if not t.get("canNow")]

        if now_threats:
            for threat in now_threats:
                row = ThreatRow(self.art_cache, on_hover=self._on_hover)
                row.set_threat(threat)
                self.threat_rows[threat["code"]] = row
                self.threat_layout.addWidget(row)
        else:
            safe_lbl = QtWidgets.QLabel("✓ Безопасно: нет быстрых ответов под их текущую ману")
            safe_lbl.setFont(theme.display_font(METRICS(8), bold=True))
            safe_lbl.setStyleSheet(f"color: {VERDANT}; background: rgba(74,222,128,25); padding: 5px; border-radius: 3px;")
            self.threat_layout.addWidget(safe_lbl)

        # Show next turn upcoming threats if room
        if future_threats:
            future_hdr = QtWidgets.QLabel("ПОТЕНЦИАЛЬНЫЕ УГРОЗЫ (СЛЕД. ХОД):")
            future_hdr.setFont(theme.display_font(METRICS(7.5), bold=True))
            future_hdr.setStyleSheet(f"color: {MUTED}; background: transparent; margin-top: 6px;")
            self.threat_layout.addWidget(future_hdr)
            for threat in future_threats[:6]:
                row = ThreatRow(self.art_cache, on_hover=self._on_hover)
                row.set_threat(threat)
                self.threat_rows[threat["code"]] = row
                self.threat_layout.addWidget(row)


class _RegionBadge(QtWidgets.QWidget):
    """Small hexagonal region marker."""

    def __init__(self, ref, parent=None):
        super().__init__(parent)
        self.ref = ref
        self.setFixedSize(METRICS(22), METRICS(22))

    def enterEvent(self, e):
        pos = self.mapToGlobal(QtCore.QPoint(self.width(), self.height()))
        HextechTooltip.instance().show_tip(f"Регион: {self.ref}", "", pos, accent=GOLD)
        super().enterEvent(e)

    def leaveEvent(self, e):
        HextechTooltip.instance().hide_tip()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        theme.paint_region_badge(p, QtCore.QPointF(self.width() / 2, self.height() / 2),
                                 METRICS(9), self.ref)
