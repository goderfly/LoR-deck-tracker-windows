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

        # Smooth fade-in animation
        self._opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QtCore.QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_anim.setDuration(130)
        self._fade_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

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

        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def hide_preview(self):
        self._fade_anim.stop()
        self._opacity_effect.setOpacity(0.0)
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
            medallion_r = METRICS(11)
            cy_m = y + medallion_r

            # Attack Medallion (Solar Gold Gem with metallic rim)
            cx_att = x + medallion_r
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            # Outer gold rim
            p.setBrush(QtGui.QBrush(qcolor("#D4AF37")))
            p.drawEllipse(QtCore.QPointF(cx_att, cy_m), medallion_r, medallion_r)
            # Inner amber jewel
            att_grad = QtGui.QRadialGradient(QtCore.QPointF(cx_att, cy_m), medallion_r * 0.85)
            att_grad.setColorAt(0.0, qcolor("#FFE28A"))
            att_grad.setColorAt(0.7, qcolor("#D48806"))
            att_grad.setColorAt(1.0, qcolor("#522802"))
            p.setBrush(QtGui.QBrush(att_grad))
            p.drawEllipse(QtCore.QPointF(cx_att, cy_m), medallion_r * 0.85, medallion_r * 0.85)
            # Stat text
            p.setFont(theme.display_font(10, bold=True))
            p.setPen(qcolor("#FFF8DB"))
            p.drawText(QtCore.QRectF(cx_att - medallion_r, cy_m - medallion_r, medallion_r * 2, medallion_r * 2),
                       QtCore.Qt.AlignmentFlag.AlignCenter, str(card.get('attack', 0)))

            # Health Medallion (Ruby Heart Shield with metallic rim)
            cx_hp = cx_att + medallion_r * 2 + METRICS(10)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            # Outer dark crimson rim
            p.setBrush(QtGui.QBrush(qcolor("#B82E3E")))
            p.drawEllipse(QtCore.QPointF(cx_hp, cy_m), medallion_r, medallion_r)
            # Inner ruby jewel
            hp_grad = QtGui.QRadialGradient(QtCore.QPointF(cx_hp, cy_m), medallion_r * 0.85)
            hp_grad.setColorAt(0.0, qcolor("#FF808F"))
            hp_grad.setColorAt(0.7, qcolor("#D92538"))
            hp_grad.setColorAt(1.0, qcolor("#4D0810"))
            p.setBrush(QtGui.QBrush(hp_grad))
            p.drawEllipse(QtCore.QPointF(cx_hp, cy_m), medallion_r * 0.85, medallion_r * 0.85)
            # Stat text
            p.setPen(qcolor("#FFF0F2"))
            p.drawText(QtCore.QRectF(cx_hp - medallion_r, cy_m - medallion_r, medallion_r * 2, medallion_r * 2),
                       QtCore.Qt.AlignmentFlag.AlignCenter, str(card.get('health', 0)))

            y += int(medallion_r * 2 + METRICS(8))
        elif card.get("cost") is not None:
            # Spell mana crystal badge
            cost_r = METRICS(9.5)
            theme.paint_mana_crystal(p, QtCore.QPointF(x + cost_r + 2, y + cost_r), cost_r, card.get("cost", 0))
            y += int(cost_r * 2 + METRICS(6))

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
