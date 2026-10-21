"""
Hand painted HUD widgets.

Every widget in this module draws itself - there is not a single stock
``QLabel`` rectangle in the overlay. That is what gives the tracker its
"arcane ledger" look: faceted mana crystals, chamfered rows, gold corner
brackets and region hexes instead of flat grey boxes.

All widgets are diff friendly: they keep their identity across updates and
only repaint themselves with new data, so the overlay never flickers.
"""

import math

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme
from .theme import (
    ARCANE, BLOOD, BLOOD_DIM, EMBER, FAINT, GOLD, GOLD_BRIGHT, GOLD_DIM,
    GOLD_SOFT, GOLD_DEEP, MANA, MANA_DARK, MANA_DEEP, MANA_ELECTRIC,
    MUTED, TEXT, VERDANT, VIOLET, qcolor,
)


class Metrics:
    """Global scale factor shared by every widget."""

    def __init__(self):
        self.scale = 1.0

    def __call__(self, value):
        return int(round(value * self.scale))

    def f(self, value):
        return float(value) * self.scale


METRICS = Metrics()


# --------------------------------------------------------------------------
# Image cache
# --------------------------------------------------------------------------
class ArtCache(QtCore.QObject):
    """Loads and caches card art; notifies listeners when it arrives."""

    art_ready = QtCore.pyqtSignal(str)

    def __init__(self, card_db, parent=None):
        super().__init__(parent)
        self.card_db = card_db
        self._pixmaps = {}
        self._thumbs = {}

    def pixmap(self, code):
        if not code:
            return None
        pm = self._pixmaps.get(code)
        if pm is not None:
            return pm
        path = self.card_db.image_path(code)
        if path:
            import os
            if os.path.exists(path):
                pm = QtGui.QPixmap(path)
                if not pm.isNull():
                    self._pixmaps[code] = pm
                    return pm
        self.card_db.request_image(code, on_ready=self._on_downloaded)
        return None

    def thumb(self, code, size):
        key = (code, size.width(), size.height())
        if key in self._thumbs:
            return self._thumbs[key]
        pm = self.pixmap(code)
        if pm is None:
            return None
        thumb = theme.crop_art(pm, size)
        self._thumbs[key] = thumb
        return thumb

    @QtCore.pyqtSlot(str)
    def _on_downloaded(self, code):
        self._pixmaps.pop(code, None)
        self._thumbs = {k: v for k, v in self._thumbs.items() if k[0] != code}
        self.art_ready.emit(code)


# --------------------------------------------------------------------------
# Panel frame
# --------------------------------------------------------------------------
class HudFrame(QtWidgets.QWidget):
    """Base class of every overlay: paints the arcane panel background."""

    def __init__(self, accent=GOLD, accent_side="left", alpha=1.0, parent=None):
        super().__init__(parent)
        self.accent = accent
        self.accent_side = accent_side
        self.panel_alpha = alpha
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_accent(self, color):
        self.accent = color
        self.update()

    def set_panel_alpha(self, alpha):
        self.panel_alpha = alpha
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        theme.paint_panel(
            painter,
            QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
            accent=self.accent,
            accent_side=self.accent_side,
            alpha=self.panel_alpha,
        )


# --------------------------------------------------------------------------
# Section title
# --------------------------------------------------------------------------
class SectionTitle(QtWidgets.QWidget):
    """Hex glyph + caption + fading gold hairline."""

    def __init__(self, text, color=GOLD, parent=None):
        super().__init__(parent)
        self.text = text
        self.color = color
        self.setFixedHeight(METRICS(20))

    def set_text(self, text):
        if text != self.text:
            self.text = text
            self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        cy = self.height() / 2.0
        r = METRICS(3.8)

        # Delicate gold diamond glyph
        path = theme.hex_path(QtCore.QPointF(r + 2, cy), r, flat=False)
        p.setPen(QtGui.QPen(qcolor(GOLD, 0.75), 1))
        p.setBrush(QtGui.QBrush(qcolor(GOLD, 0.20)))
        p.drawPath(path)

        f = theme.header_font(METRICS(8.5), bold=True)
        p.setFont(f)
        p.setPen(qcolor(GOLD_BRIGHT))
        metrics = QtGui.QFontMetrics(f)
        text_w = metrics.horizontalAdvance(self.text)
        x = r * 2 + METRICS(7)
        p.drawText(QtCore.QPointF(x, cy + metrics.ascent() / 2.0 - 1), self.text)

        line_x = x + text_w + METRICS(8)
        if line_x < self.width() - METRICS(4):
            grad = QtGui.QLinearGradient(line_x, 0, self.width(), 0)
            grad.setColorAt(0.0, qcolor(GOLD, 0.35))
            grad.setColorAt(1.0, qcolor(GOLD, 0.0))
            p.setPen(QtGui.QPen(QtGui.QBrush(grad), 1))
            p.drawLine(QtCore.QPointF(line_x, cy), QtCore.QPointF(self.width() - METRICS(4), cy))


# --------------------------------------------------------------------------
# Card row (the HDT style "card bar")
# --------------------------------------------------------------------------
class CardBar(QtWidgets.QWidget):
    """[crystal] [art] [name / meta] [topdeck %] [xN]

    The widget is reused for the lifetime of a card code - only the data is
    refreshed, so the list never rebuilds and never flickers.
    """

    HEIGHT = 40

    def __init__(self, art_cache, on_hover=None, parent=None):
        super().__init__(parent)
        self.art_cache = art_cache
        self.on_hover = on_hover
        self.card = {}
        self.code = ""
        self.hovered = False
        self.setMouseTracking(True)
        self.setFixedHeight(METRICS(self.HEIGHT))

    # -- data ------------------------------------------------------------
    def set_card(self, card):
        self.card = card or {}
        self.code = self.card.get("code", "")
        self.update()

    # -- interaction -----------------------------------------------------
    def enterEvent(self, event):
        self.hovered = True
        self.update()
        if self.on_hover:
            self.on_hover(self.code, self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.update()
        if self.on_hover:
            self.on_hover(None, self)
        super().leaveEvent(event)

    # -- painting --------------------------------------------------------
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)

        card = self.card
        remaining = card.get("remaining", 0)
        alive = remaining > 0
        is_champ = card.get("isChampion", False)
        regions = card.get("regionRefs") or card.get("regions") or []
        accent = theme.region_color(regions[0]) if regions else GOLD

        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radius = METRICS(5)

        # 1. Base dark obsidian tile
        bg_color = qcolor("#0A111D" if alive else "#060A12")
        if not alive:
            border_color = qcolor(FAINT, 0.20)
        elif is_champ:
            border_color = qcolor(GOLD, 0.75)
        elif self.hovered:
            border_color = qcolor(MANA, 0.85)
        else:
            border_color = qcolor("#1B2738", 0.75)

        p.setPen(QtGui.QPen(border_color, 1.2 if (self.hovered or is_champ) else 1.0))
        p.setBrush(QtGui.QBrush(bg_color))
        p.drawRoundedRect(rect, radius, radius)

        # 2. Panoramic cropped card art (HDT / LoR Guardian style)
        if alive:
            art_w = rect.width() * 0.65
            art_rect = QtCore.QRectF(rect.right() - art_w, rect.top() + 1, art_w, rect.height() - 2)
            thumb = self.art_cache.thumb(self.code, art_rect.size().toSize())
            if thumb is not None and not thumb.isNull():
                p.save()
                clip = QtGui.QPainterPath()
                clip.addRoundedRect(rect, radius, radius)
                p.setClipPath(clip)

                # Draw illustration
                p.drawPixmap(art_rect.toRect(), thumb)

                # Horizontal gradient overlay: 100% solid on left, transparent on right
                grad = QtGui.QLinearGradient(art_rect.left(), 0, art_rect.right(), 0)
                grad.setColorAt(0.0, qcolor("#0A111D", 1.0))
                grad.setColorAt(0.32, qcolor("#0A111D", 0.95))
                grad.setColorAt(0.65, qcolor("#0A111D", 0.40))
                grad.setColorAt(1.0, qcolor("#0A111D", 0.05))
                p.setPen(QtCore.Qt.PenStyle.NoPen)
                p.setBrush(QtGui.QBrush(grad))
                p.drawRect(art_rect)
                p.restore()

        # Hover cyan accent indicator on left edge
        if self.hovered and alive:
            bar = QtCore.QRectF(rect.left() + 1.5, rect.top() + 4, 2.5, rect.height() - 8)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QBrush(qcolor(MANA, 0.95)))
            p.drawRoundedRect(bar, 1, 1)

        left = METRICS(6)
        cy = self.height() / 2.0

        # 3. Faceted cyan mana crystal
        gem_r = METRICS(9.5)
        theme.paint_mana_crystal(
            p, QtCore.QPointF(left + gem_r + 1, cy), gem_r,
            card.get("cost", 0), alpha=1.0 if alive else 0.40,
        )
        left += gem_r * 2 + METRICS(8)

        # 4. Count badge (right edge)
        badge_w = METRICS(28)
        badge = QtCore.QRectF(self.width() - badge_w - METRICS(5),
                              cy - METRICS(9), badge_w, METRICS(18))
        if alive:
            if is_champ:
                p.setPen(QtGui.QPen(qcolor(GOLD_BRIGHT, 0.85), 1))
                p.setBrush(QtGui.QBrush(qcolor(GOLD_DIM, 0.45)))
            else:
                p.setPen(QtGui.QPen(qcolor(GOLD, 0.65), 1))
                p.setBrush(QtGui.QBrush(qcolor("#101A2C", 0.80)))
        else:
            p.setPen(QtGui.QPen(qcolor(FAINT, 0.4), 1))
            p.setBrush(QtGui.QBrush(qcolor("#080D16", 0.50)))
        p.drawRoundedRect(badge, METRICS(3.5), METRICS(3.5))
        p.setFont(theme.number_font(METRICS(8.5), bold=True))
        p.setPen(qcolor(GOLD_BRIGHT if (alive and is_champ) else (GOLD_SOFT if alive else FAINT)))
        count_str = "★" if (is_champ and remaining == 1) else f"x{remaining}"
        p.drawText(badge, QtCore.Qt.AlignmentFlag.AlignCenter, count_str)

        # 5. Topdeck probability
        prob = card.get("prob", 0.0)
        prob_w = METRICS(36)
        if alive and prob > 0:
            prob_rect = QtCore.QRectF(badge.left() - prob_w - METRICS(6),
                                       cy + METRICS(3), prob_w, METRICS(3))
            grad = QtGui.QLinearGradient(prob_rect.left(), 0, prob_rect.right(), 0)
            grad.setColorAt(0.0, qcolor(MANA, 0.85))
            grad.setColorAt(1.0, qcolor(ARCANE, 0.85))
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QBrush(grad))
            fill = QtCore.QRectF(prob_rect)
            fill.setWidth(max(METRICS(2), prob_rect.width() * min(1.0, prob / 100.0)))
            p.drawRoundedRect(fill, METRICS(1.5), METRICS(1.5))

            p.setFont(theme.number_font(METRICS(7.5), bold=True))
            p.setPen(qcolor(MANA_ELECTRIC, 0.95))
            p.drawText(QtCore.QRectF(prob_rect.left(), cy - METRICS(11),
                                     prob_rect.width(), METRICS(12)),
                        QtCore.Qt.AlignmentFlag.AlignRight, f"{prob:.0f}%")

        # 6. Card name & type/speed
        text_right = (badge.left() - prob_w - METRICS(10)) if (alive and prob > 0) else (badge.left() - METRICS(8))
        avail = max(METRICS(40), text_right - left)

        name = card.get("name", self.code)
        if is_champ:
            name = f"★ {name}"
        speed = card.get("spellSpeed", "")
        speed_ref = (card.get("spellSpeedRef") or "").lower()
        speed_tag = ""
        speed_color = MUTED
        if speed:
            if "burst" in speed_ref or "взрыв" in speed.lower():
                speed_tag = "ВЗРЫВ"
                speed_color = MANA
            elif "fast" in speed_ref or "быстр" in speed.lower():
                speed_tag = "БЫСТР"
                speed_color = EMBER
            else:
                speed_tag = "МЕДЛ"
                speed_color = VIOLET

        name_font = theme.card_name_font(METRICS(10.0), bold=True)
        name_color = qcolor(GOLD_BRIGHT if is_champ else "#FFFFFF", 1.0 if alive else 0.40)
        p.setFont(name_font)
        fm = QtGui.QFontMetrics(name_font)
        shown = fm.elidedText(name, QtCore.Qt.TextElideMode.ElideRight, int(avail))

        # Text drop shadow for high contrast over art
        p.setPen(qcolor("#000000", 0.95 if alive else 0.4))
        p.drawText(QtCore.QRectF(left + 1, cy - METRICS(12) + 1, avail, METRICS(14)),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                   shown)
        p.setPen(name_color)
        p.drawText(QtCore.QRectF(left, cy - METRICS(12), avail, METRICS(14)),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                   shown)

        # Meta line: speed / region
        meta_font = theme.body_font(METRICS(7.5), bold=bool(speed_tag))
        p.setFont(meta_font)
        meta_parts = []
        if speed_tag:
            meta_parts.append(speed_tag)
        if regions:
            meta_parts.append(str(regions[0]))
        ctype = card.get("type", "")
        if ctype and ctype not in ("Unit", "Spell", "Боец", "Заклинание"):
            meta_parts.append(ctype)
        meta = " · ".join(meta_parts)
        if meta:
            p.setPen(qcolor(speed_color if speed_tag else MUTED, 0.90 if alive else 0.35))
            p.drawText(QtCore.QRectF(left, cy + METRICS(1), avail, METRICS(12)),
                       QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                       meta)


# --------------------------------------------------------------------------
# Threat row
# --------------------------------------------------------------------------
CATEGORY_COLORS = {
    "LETHAL": BLOOD,
    "SWEEP": EMBER,
    "COUNTER": VIOLET,
    "BURST": MANA,
    "BURN": "#F2A65A",
    "CONTROL": VERDANT,
    "DRAW": MUTED,
}


class ThreatRow(QtWidgets.QWidget):
    """One line of the threat board: category stripe, cost, name, note."""

    HEIGHT = 34

    def __init__(self, art_cache, on_hover=None, parent=None):
        super().__init__(parent)
        self.art_cache = art_cache
        self.on_hover = on_hover
        self.threat = {}
        self.code = ""
        self.hovered = False
        self.setMouseTracking(True)
        self.setFixedHeight(METRICS(self.HEIGHT))

    def set_threat(self, threat):
        self.threat = threat or {}
        self.code = self.threat.get("code", "")
        self.update()

    def enterEvent(self, event):
        self.hovered = True
        self.update()
        if self.on_hover:
            self.on_hover(self.code, self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered = False
        self.update()
        if self.on_hover:
            self.on_hover(None, self)
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)

        t = self.threat
        if not t:
            return
        cat = t.get("cat", "BURST")
        color = CATEGORY_COLORS.get(cat, MANA)
        now = t.get("canNow", False)
        rect = QtCore.QRectF(self.rect()).adjusted(1, 1, -1, -1)

        # Base tile
        bg_a = 0.35 if now else 0.18
        if self.hovered:
            bg_a += 0.18
        p.setPen(QtGui.QPen(qcolor(color, 0.70 if now else 0.25), 1.2 if (now or self.hovered) else 1.0))
        p.setBrush(QtGui.QBrush(qcolor("#0A121F", bg_a)))
        p.drawRoundedRect(rect, METRICS(5), METRICS(5))

        # Panoramic card art preview on right
        art_w = rect.width() * 0.55
        art_rect = QtCore.QRectF(rect.right() - art_w, rect.top() + 1, art_w, rect.height() - 2)
        thumb = self.art_cache.thumb(self.code, art_rect.size().toSize())
        if thumb is not None and not thumb.isNull():
            p.save()
            clip = QtGui.QPainterPath()
            clip.addRoundedRect(rect, METRICS(5), METRICS(5))
            p.setClipPath(clip)
            p.drawPixmap(art_rect.toRect(), thumb)
            grad = QtGui.QLinearGradient(art_rect.left(), 0, art_rect.right(), 0)
            grad.setColorAt(0.0, qcolor("#0A121F", 1.0))
            grad.setColorAt(0.35, qcolor("#0A121F", 0.90))
            grad.setColorAt(0.70, qcolor("#0A121F", 0.40))
            grad.setColorAt(1.0, qcolor("#0A121F", 0.10))
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QBrush(grad))
            p.drawRect(art_rect)
            p.restore()

        # Category stripe on left
        stripe = QtCore.QRectF(rect.left() + 1.5, rect.top() + 3, 2.5, rect.height() - 6)
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QBrush(qcolor(color, 0.95 if now else 0.55)))
        p.drawRoundedRect(stripe, 1.5, 1.5)

        left = METRICS(8)
        cy = self.height() / 2.0

        # Cost mana crystal
        gem_r = METRICS(8.0)
        theme.paint_mana_crystal(p, QtCore.QPointF(left + gem_r, cy), gem_r,
                                 t.get("cost", 0), alpha=1.0)
        left += gem_r * 2 + METRICS(7)

        # "СЕЙЧАС" (NOW) glowing danger badge on right
        flag_w = METRICS(48)
        if now:
            flag = QtCore.QRectF(self.width() - flag_w - METRICS(5), cy - METRICS(7.5), flag_w, METRICS(15))
            p.setPen(QtGui.QPen(qcolor(EMBER, 0.85), 1))
            p.setBrush(QtGui.QBrush(qcolor(EMBER, 0.22)))
            p.drawRoundedRect(flag, METRICS(3), METRICS(3))
            p.setFont(theme.number_font(METRICS(7.5), bold=True))
            p.setPen(qcolor("#FFF3DC"))
            p.drawText(flag, QtCore.Qt.AlignmentFlag.AlignCenter, "СЕЙЧАС")

        # name
        name = t.get("name", "")
        speed = t.get("speed", "")
        title = f"{speed} {name}" if speed else name
        avail = max(METRICS(40), self.width() - left - flag_w - METRICS(14))
        f = theme.card_name_font(METRICS(9.5), bold=now)
        p.setFont(f)
        p.setPen(qcolor(TEXT if now else "#C6D3E4"))
        fm = QtGui.QFontMetrics(f)
        p.drawText(QtCore.QRectF(left, METRICS(2), avail, METRICS(15)),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                   fm.elidedText(title, QtCore.Qt.TextElideMode.ElideRight, int(avail)))

        note = t.get("note", "")
        if note:
            f2 = theme.body_font(METRICS(7.5))
            p.setFont(f2)
            p.setPen(qcolor(MUTED, 0.9))
            fm2 = QtGui.QFontMetrics(f2)
            p.drawText(QtCore.QRectF(left, METRICS(15), avail, METRICS(13)),
                       QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                       fm2.elidedText(note, QtCore.Qt.TextElideMode.ElideRight, int(avail)))


# --------------------------------------------------------------------------
# Mana curve
# --------------------------------------------------------------------------
class ManaCurve(QtWidgets.QWidget):
    """Compact histogram of the remaining deck by mana cost."""

    HEIGHT = 46

    def __init__(self, parent=None):
        super().__init__(parent)
        self.buckets = []
        self.setFixedHeight(METRICS(self.HEIGHT))

    def set_curve(self, buckets):
        self.buckets = buckets or []
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        if not self.buckets:
            return
        n = len(self.buckets)
        gap = METRICS(3)
        w = (self.width() - gap * (n - 1)) / max(1, n)
        peak = max([b[1] for b in self.buckets] + [1])
        base_y = self.height() - METRICS(11)

        for i, (cost, count) in enumerate(self.buckets):
            x = i * (w + gap)
            bar_h = (base_y - METRICS(4)) * (count / peak) if peak else 0
            rect = QtCore.QRectF(x, base_y - bar_h, w, max(bar_h, 1.5))
            grad = QtGui.QLinearGradient(0, rect.top(), 0, rect.bottom())
            grad.setColorAt(0.0, qcolor(MANA, 0.95))
            grad.setColorAt(1.0, qcolor(MANA_DEEP, 0.85))
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QBrush(grad))
            p.drawRoundedRect(rect, METRICS(2), METRICS(2))

            p.setFont(theme.mono_font(METRICS(7)))
            p.setPen(qcolor(MUTED))
            p.drawText(QtCore.QRectF(x, base_y + METRICS(1), w, METRICS(10)),
                       QtCore.Qt.AlignmentFlag.AlignCenter, str(cost))
            if count:
                p.setPen(qcolor(TEXT, 0.85))
                p.drawText(QtCore.QRectF(x, rect.top() - METRICS(9), w, METRICS(9)),
                           QtCore.Qt.AlignmentFlag.AlignCenter, str(count))


# --------------------------------------------------------------------------
# Simple key/value row used by the opponent panel
# --------------------------------------------------------------------------
class InfoRow(QtWidgets.QWidget):
    HEIGHT = 22

    def __init__(self, parent=None):
        super().__init__(parent)
        self.key = ""
        self.value = ""
        self.color = TEXT
        self.setFixedHeight(METRICS(self.HEIGHT))

    def set_row(self, key, value, color=TEXT):
        self.key, self.value, self.color = key, value, color
        self.update()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        f = theme.body_font(METRICS(8.5))
        p.setFont(f)
        p.setPen(qcolor(MUTED))
        p.drawText(QtCore.QRectF(METRICS(6), 0, self.width() * 0.62, self.height()),
                   QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                   self.key)
        p.setFont(theme.mono_font(METRICS(9)))
        p.setPen(qcolor(self.color))
        p.drawText(QtCore.QRectF(self.width() * 0.55, 0, self.width() * 0.43 - METRICS(6), self.height()),
                   QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
                   self.value)
