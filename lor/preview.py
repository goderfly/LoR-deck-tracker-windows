"""
HDT style card preview popup.

Hovering a card row opens a floating, fully framed preview of the card with
its localised Russian text, keywords (SpellShield, Overwhelm, Elusive ...) and
the champion level-up condition.
"""

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme, win32ext
from .theme import (
    GOLD, GOLD_BRIGHT, GOLD_DIM, GOLD_SOFT, MANA, MANA_DARK, MANA_ELECTRIC,
    MUTED, TEXT, qcolor,
)
from .widgets import METRICS


class CardPreview(QtWidgets.QWidget):
    """Frameless popup that renders the full card artwork plus metadata."""

    def __init__(self, card_db, art_cache, parent=None):
        super().__init__(parent)
        self.card_db = card_db
        self.art_cache = art_cache
        self.code = ""
        self.card = {}

        self.setWindowFlags(
            QtCore.Qt.WindowType.ToolTip
            | QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(METRICS(520), METRICS(400))

    # ------------------------------------------------------------------
    def show_card(self, code, extra=None, near_rect=None):
        card = self.card_db.get_card(code) if code else None
        if not card:
            self.hide()
            return
        self.code = code
        self.card = card
        self.extra = extra or {}
        self.update()
        if near_rect is not None:
            self._place(near_rect)
        self.show()
        self.raise_()
        win32ext.keep_topmost(self)

    def hide_preview(self):
        self.hide()

    def _place(self, near_rect):
        screen = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        if isinstance(near_rect, QtCore.QPoint):
            # Convert single point to small anchor rect
            near_rect = QtCore.QRect(near_rect.x(), near_rect.y(), 10, 10)
        elif not hasattr(near_rect, "right"):
            near_rect = QtCore.QRect(100, 100, 10, 10)

        x = near_rect.right() + 12
        if x + self.width() > screen.right():
            x = near_rect.left() - self.width() - 12
        x = max(screen.left() + 4, min(x, screen.right() - self.width() - 4))
        y = near_rect.top() - 10
        y = max(screen.top() + 4, min(y, screen.bottom() - self.height() - 4))
        self.move(int(x), int(y))

    # ------------------------------------------------------------------
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)

        card = self.card
        outer = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        theme.paint_panel(p, outer, accent=GOLD, accent_side="none", alpha=0.97)

        art_rect = QtCore.QRectF(10, 10, 244, 366)
        p.setPen(QtGui.QPen(qcolor(GOLD_DIM, 0.9), 1))
        p.setBrush(QtGui.QBrush(qcolor("#05080F", 0.9)))
        p.drawRoundedRect(art_rect, 8, 8)

        pixmap = self.art_cache.pixmap(self.code)
        if pixmap is not None and not pixmap.isNull():
            p.save()
            clip = QtGui.QPainterPath()
            clip.addRoundedRect(art_rect.adjusted(1, 1, -1, -1), 7, 7)
            p.setClipPath(clip)
            scaled = pixmap.scaled(
                art_rect.size().toSize(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
            x = art_rect.left() + (art_rect.width() - scaled.width()) / 2
            y = art_rect.top() + (art_rect.height() - scaled.height()) / 2
            p.drawPixmap(QtCore.QPointF(x, y), scaled)
            p.restore()
        else:
            p.setFont(theme.body_font(9))
            p.setPen(qcolor(MUTED))
            p.drawText(art_rect, QtCore.Qt.AlignmentFlag.AlignCenter, "Загрузка арта…")

        # ---------------- info column -----------------------------------
        x = art_rect.right() + 14
        width = self.width() - x - 12
        y = 14

        is_champ = card.get("isChampion", False)
        name = card.get("name", self.code)

        p.setFont(theme.card_name_font(12, bold=True))
        p.setPen(qcolor(GOLD_SOFT if is_champ else TEXT))
        fm = QtGui.QFontMetrics(p.font())
        p.drawText(QtCore.QRectF(x, y, width, 20),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                   fm.elidedText(("★ " if is_champ else "") + name,
                                 QtCore.Qt.TextElideMode.ElideRight, int(width)))
        y += 21

        # type + speed
        speed = card.get("spellSpeed", "")
        ctype = card.get("type", "")
        meta = " ".join([s for s in (speed, ctype) if s])
        p.setFont(theme.body_font(8.5))
        p.setPen(qcolor(MUTED))
        p.drawText(QtCore.QRectF(x, y, width, 15), QtCore.Qt.AlignmentFlag.AlignLeft, meta)
        y += 17

        # stats
        if card.get("type") in ("Unit", "Боец") or is_champ:
            stat_w = METRICS(48)
            stat_h = METRICS(20)

            # Attack badge
            att_rect = QtCore.QRectF(x, y, stat_w, stat_h)
            p.setPen(QtGui.QPen(qcolor("#F5C14B", 0.6), 1))
            p.setBrush(QtGui.QBrush(qcolor("#2B210A", 0.7)))
            p.drawRoundedRect(att_rect, 3, 3)
            p.setFont(theme.display_font(10, bold=True))
            p.setPen(qcolor("#FFEAA7"))
            p.drawText(att_rect, QtCore.Qt.AlignmentFlag.AlignCenter, f"⚔ {card.get('attack', 0)}")

            # Health badge
            hp_rect = QtCore.QRectF(x + stat_w + 6, y, stat_w, stat_h)
            p.setPen(QtGui.QPen(qcolor("#FF6B7A", 0.6), 1))
            p.setBrush(QtGui.QBrush(qcolor("#2E0B10", 0.7)))
            p.drawRoundedRect(hp_rect, 3, 3)
            p.setPen(qcolor("#FFCCD2"))
            p.drawText(hp_rect, QtCore.Qt.AlignmentFlag.AlignCenter, f"❤ {card.get('health', 0)}")

            y += 26
        elif card.get("cost") is not None:
            # Spell mana badge
            cost_rect = QtCore.QRectF(x, y, METRICS(56), METRICS(18))
            p.setPen(QtGui.QPen(qcolor(MANA, 0.7), 1))
            p.setBrush(QtGui.QBrush(qcolor(MANA_DARK, 0.7)))
            p.drawRoundedRect(cost_rect, 3, 3)
            p.setFont(theme.display_font(8.5, bold=True))
            p.setPen(qcolor(MANA_ELECTRIC))
            p.drawText(cost_rect, QtCore.Qt.AlignmentFlag.AlignCenter, f"МАНА: {card.get('cost', 0)}")
            y += 24

        # regions
        refs = card.get("regionRefs") or []
        rx = x
        for ref in refs[:4]:
            r = 9
            theme.paint_region_badge(p, QtCore.QPointF(rx + r, y + r), r, ref)
            rx += r * 2 + 3
        if refs:
            y += 22

        # keywords
        kws = card.get("keywords") or []
        kws = [k for k in kws if k]
        if kws:
            p.setFont(theme.body_font(8, bold=True))
            p.setPen(qcolor(MANA))
            p.drawText(QtCore.QRectF(x, y, width, 14), QtCore.Qt.AlignmentFlag.AlignLeft,
                       " · ".join(kws))
            y += 16

        # description
        desc = card.get("description", "") or ""
        f = theme.body_font(8.5)
        p.setFont(f)
        p.setPen(qcolor("#C3D2E4"))
        fm = QtGui.QFontMetrics(f)
        text_rect = QtCore.QRectF(x, y, width, max(40, self.height() - y - 96))
        p.drawText(text_rect, int(QtCore.Qt.TextFlag.TextWordWrap), desc)

        # level up condition
        lvl = card.get("levelupDescription", "") or ""
        if lvl:
            box_h = min(70, self.height() - y - 12)
            box = QtCore.QRectF(x, self.height() - box_h - 12, width, box_h)
            p.setPen(QtGui.QPen(qcolor(GOLD, 0.45), 1))
            p.setBrush(QtGui.QBrush(qcolor(GOLD, 0.08)))
            p.drawRoundedRect(box, 5, 5)
            p.setFont(theme.display_font(7.5))
            p.setPen(qcolor(GOLD))
            p.drawText(QtCore.QRectF(box.left() + 6, box.top() + 3, box.width() - 12, 13),
                       QtCore.Qt.AlignmentFlag.AlignLeft, "ПОВЫШЕНИЕ УРОВНЯ")
            p.setFont(theme.body_font(8))
            p.setPen(qcolor("#D9E4F2"))
            p.drawText(box.adjusted(6, 17, -6, -4), int(QtCore.Qt.TextFlag.TextWordWrap), lvl)

        # deck counter
        extra = getattr(self, "extra", {}) or {}
        if extra.get("remaining") is not None:
            p.setFont(theme.mono_font(8.5, bold=True))
            p.setPen(qcolor(GOLD_SOFT))
            p.drawText(QtCore.QRectF(art_rect.left(), self.height() - 20, 244, 16),
                       QtCore.Qt.AlignmentFlag.AlignLeft,
                       f"В КОЛДЕ: {extra.get('remaining')}/{extra.get('initial', '?')}")
