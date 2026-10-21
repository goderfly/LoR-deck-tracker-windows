"""
Compact combat & mana advisor.

A slim strip pinned to the top centre of the screen. It answers the only
question that matters while the opponent is thinking: *what can they cast at
me right now* - computed from unit mana plus the spell-mana bank.
"""

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme
from .theme import (
    ARCANE, BLOOD, EMBER, FAINT, GOLD, GOLD_BRIGHT, GOLD_DIM, GOLD_SOFT,
    MANA, MANA_DEEP, MANA_ELECTRIC, MUTED, TEXT, VERDANT, VIOLET, qcolor,
)
from .panels import OverlayWindow
from .widgets import METRICS


class AdvisorBar(OverlayWindow):
    """Always visible readout: turn, opponent mana, immediate threats."""

    HEIGHT = 48

    def __init__(self, preview=None):
        width = METRICS(620)
        height = METRICS(self.HEIGHT)
        screen = QtGui.QGuiApplication.primaryScreen().geometry()
        super().__init__("Советник", width, height,
                         (screen.width() - width) // 2, 16, accent=GOLD)
        self.preview = preview
        self.state = None
        self.threat_pills = []  # [(rect, card_code)]
        self.hovered_code = None
        self.setMouseTracking(True)
        self.setFixedHeight(height)

    # ------------------------------------------------------------------
    def update_state(self, state):
        self.state = state
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        hovered = None
        for rect, code in self.threat_pills:
            if rect.contains(pos):
                hovered = (rect, code)
                break

        if hovered:
            rect, code = hovered
            if code != self.hovered_code:
                self.hovered_code = code
                if self.preview:
                    global_pt = self.mapToGlobal(QtCore.QPoint(int(rect.left()), int(rect.bottom())))
                    self.preview.show_card(code, near_rect=QtCore.QRect(global_pt.x(), global_pt.y(), int(rect.width()), int(rect.height())))
        else:
            if self.hovered_code is not None:
                self.hovered_code = None
                if self.preview:
                    self.preview.hide_preview()

    def leaveEvent(self, e):
        self.hovered_code = None
        if self.preview:
            self.preview.hide_preview()

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        theme.paint_panel(p, rect, accent=GOLD, accent_side="none", alpha=0.96)

        self.threat_pills = []

        state = self.state or {}
        if state.get("status") != "in_game":
            p.setFont(theme.header_font(METRICS(9.5), bold=True))
            p.setPen(qcolor(GOLD_BRIGHT))
            p.drawText(rect.adjusted(METRICS(14), 0, 0, 0),
                       QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                       "⚔ СОВЕТНИК БОЯ · ОЖИДАНИЕ НАЧАЛА МАТЧА")
            return

        turn = state.get("turn", {}) or {}
        phase = turn.get("phase", "ours")
        advisor = state.get("advisor", {}) or {}
        unit_mana = advisor.get("unitMana", turn.get("theirMaxMana", 0))
        spell_mana = advisor.get("spellMana", 0)
        effective = advisor.get("effectiveMana", unit_mana + spell_mana)

        x = METRICS(12)
        cy = self.height() / 2.0

        # --- turn badge -------------------------------------------------
        phase_txt = "ВАША АТАКА" if phase == "ours" else ("АТАКА ВРАГА" if phase == "theirs" else "МУЛЛИГАН")
        turn_num = turn.get("ourTurn", 1)
        phase_col = MANA if phase == "ours" else GOLD

        turn_badge = QtCore.QRectF(x, cy - METRICS(11), METRICS(110), METRICS(22))
        p.setPen(QtGui.QPen(qcolor(phase_col, 0.8), 1))
        p.setBrush(QtGui.QBrush(qcolor(phase_col, 0.18)))
        p.drawRoundedRect(turn_badge, METRICS(4), METRICS(4))
        p.setFont(theme.header_font(METRICS(8.5), bold=True))
        p.setPen(qcolor(GOLD_BRIGHT if phase == "theirs" else MANA_ELECTRIC))
        p.drawText(turn_badge, QtCore.Qt.AlignmentFlag.AlignCenter, f"{phase_txt} · Х{turn_num}")
        x += METRICS(118)

        # Divider
        p.setPen(QtGui.QPen(qcolor(GOLD_DIM, 0.4), 1))
        p.drawLine(QtCore.QPointF(x, METRICS(8)), QtCore.QPointF(x, self.height() - METRICS(8)))
        x += METRICS(10)

        # --- Opponent Mana formula: Unit + Spell = Effective ------------
        p.setFont(theme.header_font(METRICS(8), bold=True))
        p.setPen(qcolor(MUTED))
        p.drawText(QtCore.QRectF(x, 0, METRICS(70), self.height()),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                   "МАНА ВРАГА:")
        x += METRICS(72)

        # Mana pill: [4 + 2 заклинаний = 6]
        mana_rect = QtCore.QRectF(x, cy - METRICS(10), METRICS(96), METRICS(20))
        p.setPen(QtGui.QPen(qcolor(MANA, 0.7), 1))
        p.setBrush(QtGui.QBrush(qcolor("#081A2A", 0.85)))
        p.drawRoundedRect(mana_rect, METRICS(4), METRICS(4))

        p.setFont(theme.number_font(METRICS(8.5), bold=True))
        p.setPen(qcolor(MANA_ELECTRIC))
        mana_str = f"💎 {unit_mana} + ✦ {spell_mana} = {effective}"
        p.drawText(mana_rect, QtCore.Qt.AlignmentFlag.AlignCenter, mana_str)
        x += METRICS(104)

        # Divider
        p.setPen(QtGui.QPen(qcolor(GOLD_DIM, 0.4), 1))
        p.drawLine(QtCore.QPointF(x, METRICS(8)), QtCore.QPointF(x, self.height() - METRICS(8)))
        x += METRICS(10)

        # --- Immediate Threats (Playable Now) ---------------------------
        threats = [t for t in (state.get("threats", []) or []) if t.get("canNow")]

        p.setFont(theme.header_font(METRICS(8), bold=True))
        p.setPen(qcolor(MUTED))
        p.drawText(QtCore.QRectF(x, 0, METRICS(65), self.height()),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                   "УГРОЗЫ:")
        x += METRICS(68)

        if not threats:
            p.setFont(theme.body_font(METRICS(8)))
            p.setPen(qcolor(VERDANT, 0.9))
            p.drawText(QtCore.QRectF(x, 0, self.width() - x - METRICS(8), self.height()),
                       QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                       f"✓ Безопасно: нет быстрых заклинаний под их {effective} маны")
            return

        chip_font = theme.card_name_font(METRICS(8.5), bold=True)
        for threat in threats[:4]:
            label = f"{threat['name']} ({threat['cost']})"
            fm = QtGui.QFontMetrics(chip_font)
            w = fm.horizontalAdvance(label) + METRICS(14)
            if x + w > self.width() - METRICS(8):
                break
            pill = QtCore.QRectF(x, cy - METRICS(10), w, METRICS(20))
            self.threat_pills.append((pill.toRect(), threat.get("code")))

            # Color by threat category
            cat = threat.get("cat", "BURST")
            t_col = EMBER if cat in ("LETHAL", "SWEEP") else (VIOLET if cat == "COUNTER" else GOLD)

            p.setPen(QtGui.QPen(qcolor(t_col, 0.85), 1))
            p.setBrush(QtGui.QBrush(qcolor(t_col, 0.20)))
            p.drawRoundedRect(pill, METRICS(4), METRICS(4))
            p.setFont(chip_font)
            p.setPen(qcolor(GOLD_BRIGHT if cat in ("LETHAL", "SWEEP") else TEXT))
            p.drawText(pill, QtCore.Qt.AlignmentFlag.AlignCenter, label)
            x += w + METRICS(5)
