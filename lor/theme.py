"""
Visual language of the overlay - "Hextech Runeterra Luxury".

The look is inspired directly by the official Legends of Runeterra and League of Legends
client UI (Piltover Hextech gold filigree, deep obsidian slate, radiant cyan mana crystals,
and clean, high-legibility Cyrillic gaming typography).

Everything is expressed in relative units so the global ``scale`` setting can
resize the whole interface cleanly.
"""

import math

from PyQt6 import QtCore, QtGui

# --------------------------------------------------------------------------
# Palette (Official League / LoR Hextech aesthetic)
# --------------------------------------------------------------------------
VOID = "#04070D"
PANEL_TOP = "#0F1826"
PANEL_MID = "#0A111D"
PANEL_BOT = "#070C15"
PANEL_EDGE = "#1C293D"

# Hextech Ornate Gold
GOLD_BRIGHT = "#F0E6D2"     # Warm Ivory / Light Gold (League Champion font color)
GOLD = "#C8AA6E"            # The canonical League of Legends / LoR Gold
GOLD_DIM = "#785A28"        # Antique Piltover Bronze
GOLD_SOFT = "#DFD1B3"       # Soft gold for subtitle text
GOLD_DEEP = "#463714"       # Deep shadow gold

# Hextech Mana Cyan
MANA = "#00F0FF"            # Radiant Hextech cyan
MANA_ELECTRIC = "#80F7FF"   # Bright cyan highlight
MANA_DEEP = "#007A9E"       # Deep mana core
MANA_DARK = "#041B29"       # Shadow cyan

# Arcane & Status Colors
ARCANE = "#9E7BFF"          # Arcane purple
ARCANE_DIM = "#45327A"
ARCANE_GLOW = "#B99EFF"

# Tactical & Warning Colors (Subtle & readable, never garish)
EMBER = "#E5A93C"           # Warm tactical amber (replaces neon red for normal warnings)
BLOOD = "#D93848"           # Subtle deep crimson (reserved ONLY for lethal threats)
BLOOD_DIM = "#4A1820"
VERDANT = "#4ADE80"         # Emerald green for safe / all copies out
VIOLET = "#B875FF"          # Spell counters

# Textures & Text
TEXT = "#F1F5F9"            # Crisp high-contrast card name text
MUTED = "#8FA3BC"           # Secondary metadata text
FAINT = "#4B5E78"           # Subtle disabled text

REGION_COLORS = {
    "Demacia": "#EAE0B2",
    "Noxus": "#E65249",
    "Ionia": "#52AEE5",
    "Freljord": "#A5D2F5",
    "ShadowIsles": "#56DFC5",
    "PiltoverZaun": "#E8B83D",
    "Targon": "#BA93F2",
    "Shurima": "#EAA04D",
    "Bilgewater": "#4FC9A8",
    "BandleCity": "#BA96EB",
    "Runeterra": "#C8AA6E",
    "SpiritBlossom": "#F2A4D3",
    "ElderDragon": "#D4C085",
}


def region_color(ref):
    if not ref:
        return GOLD
    return REGION_COLORS.get(ref, GOLD)


def qcolor(value, alpha=None):
    c = QtGui.QColor(value)
    if alpha is not None:
        c.setAlpha(int(alpha * 255) if alpha <= 1 else int(alpha))
    return c


# --------------------------------------------------------------------------
# Fonts (Dedicated Cyrillic gaming typography hierarchy)
# --------------------------------------------------------------------------
def header_font(size=10, bold=True):
    """Refined gaming font for window headers and section titles."""
    f = QtGui.QFont()
    f.setFamilies([
        "Segoe UI Variable Display", "Segoe UI Semibold", "Segoe UI",
        "Constantia", "Trebuchet MS", "Arial"
    ])
    f.setPointSize(int(size) if isinstance(size, int) else int(round(size)))
    f.setBold(bold)
    try:
        f.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, 0.4)
    except Exception:
        pass
    return f


def card_name_font(size=10, bold=True):
    """
    High-legibility typography for Russian card names.
    CRITICAL: Zero extra letter spacing ensures natural, beautiful Cyrillic kerning!
    """
    f = QtGui.QFont()
    f.setFamilies([
        "Segoe UI Variable Text", "Segoe UI", "Calibri", "Helvetica Neue", "Arial"
    ])
    f.setPointSize(int(size) if isinstance(size, int) else int(round(size)))
    f.setBold(bold)
    f.setWeight(QtGui.QFont.Weight.DemiBold if bold else QtGui.QFont.Weight.Normal)
    try:
        f.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, 0.0)
    except Exception:
        pass
    return f


def number_font(size=9, bold=True):
    """Geometric font for mana costs, counts (x3, x2), and topdeck percentages."""
    f = QtGui.QFont()
    f.setFamilies([
        "Segoe UI Variable Small", "Segoe UI Semibold", "Segoe UI", "Arial"
    ])
    f.setPointSize(int(size) if isinstance(size, int) else int(round(size)))
    f.setBold(bold)
    return f


def body_font(size=9, bold=False):
    """Clean readable sans for descriptions, tooltips, and tactical advice."""
    f = QtGui.QFont()
    f.setFamilies(["Segoe UI", "Calibri", "Arial"])
    f.setPointSize(int(size) if isinstance(size, int) else int(round(size)))
    f.setBold(bold)
    return f


def mono_font(size=8.5, bold=True):
    f = QtGui.QFont()
    f.setFamilies(["Cascadia Code", "Consolas", "Courier New"])
    f.setPointSize(int(size) if isinstance(size, int) else int(round(size)))
    f.setBold(bold)
    return f


# Backwards compatibility alias
def display_font(size=11, bold=True):
    return header_font(size, bold)


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def chamfered_path(rect, cut=10.0):
    """A rectangle with cut corners - the signature silhouette of a Runeterra panel."""
    p = QtGui.QPainterPath()
    x0, y0 = rect.left(), rect.top()
    x1, y1 = rect.right(), rect.bottom()
    c = min(cut, (x1 - x0) / 3.0, (y1 - y0) / 3.0)
    p.moveTo(x0 + c, y0)
    p.lineTo(x1 - c, y0)
    p.lineTo(x1, y0 + c)
    p.lineTo(x1, y1 - c)
    p.lineTo(x1 - c, y1)
    p.lineTo(x0 + c, y1)
    p.lineTo(x0, y1 - c)
    p.lineTo(x0, y0 + c)
    p.closeSubpath()
    return p


def hex_path(center, radius, flat=True):
    """Regular hexagon, used for section diamonds and region badges."""
    pts = []
    for i in range(6):
        ang = (60.0 * i + (0 if flat else 30)) * math.pi / 180.0
        pts.append(QtCore.QPointF(
            center.x() + radius * math.cos(ang),
            center.y() + radius * math.sin(ang),
        ))
    p = QtGui.QPainterPath()
    p.addPolygon(QtGui.QPolygonF(pts))
    p.closeSubpath()
    return p


def crystal_path(center, radius):
    """Faceted mana crystal: a vertically stretched hexagon."""
    w = radius * 0.82
    h = radius * 1.12
    pts = [
        QtCore.QPointF(center.x(), center.y() - h),
        QtCore.QPointF(center.x() + w, center.y() - h * 0.34),
        QtCore.QPointF(center.x() + w * 0.72, center.y() + h * 0.72),
        QtCore.QPointF(center.x(), center.y() + h),
        QtCore.QPointF(center.x() - w * 0.72, center.y() + h * 0.72),
        QtCore.QPointF(center.x() - w, center.y() - h * 0.34),
    ]
    p = QtGui.QPainterPath()
    p.addPolygon(QtGui.QPolygonF(pts))
    p.closeSubpath()
    return p


# --------------------------------------------------------------------------
# Painting primitives
# --------------------------------------------------------------------------
def paint_panel(painter, rect, accent=GOLD, accent_side="none", alpha=1.0,
                glow=True, brackets=True, radius_cut=10.0):
    """
    Paint the signature Hextech panel:
    - Deep obsidian navy gradient
    - Dark outer metallic border
    - Delicate inner gold filigree hairline
    - Ornate corner brackets with rivets
    - Zero harsh red lines or glowing red halos
    """
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

    path = chamfered_path(rect.adjusted(1, 1, -1, -1), radius_cut)

    # 1. Subtle, warm antique gold & obsidian aura (never harsh red!)
    if glow:
        aura_col = qcolor(GOLD_DIM, 0.14 * alpha)
        for width in (6, 3):
            pen = QtGui.QPen(aura_col, width)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    # 2. Rich dark obsidian gradient fill
    grad = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
    grad.setColorAt(0.0, qcolor(PANEL_TOP, 0.96 * alpha))
    grad.setColorAt(0.5, qcolor(PANEL_MID, 0.97 * alpha))
    grad.setColorAt(1.0, qcolor(PANEL_BOT, 0.98 * alpha))
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(QtGui.QBrush(grad))
    painter.drawPath(path)

    # 3. Outer metallic edge
    pen_edge = QtGui.QPen(qcolor(PANEL_EDGE, 0.95 * alpha), 1.0)
    painter.setPen(pen_edge)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    painter.drawPath(path)

    # 4. Inner delicate gold filigree trim
    inner_path = chamfered_path(rect.adjusted(2.5, 2.5, -2.5, -2.5), max(3.0, radius_cut - 2.0))
    pen_inner = QtGui.QPen(qcolor(GOLD, 0.32 * alpha), 1.0)
    painter.setPen(pen_inner)
    painter.drawPath(inner_path)

    # 5. Corner brackets with rivets
    if brackets:
        _paint_brackets(painter, rect.adjusted(4, 4, -4, -4), qcolor(GOLD, 0.85 * alpha))


def _paint_brackets(painter, rect, color):
    """Draw ornate Hextech corner brackets with golden rivets matching the app icon."""
    pen = QtGui.QPen(color, 1.2)
    pen.setCapStyle(QtCore.Qt.PenCapStyle.SquareCap)
    painter.setPen(pen)
    length = 12.0
    x0, y0 = rect.left(), rect.top()
    x1, y1 = rect.right(), rect.bottom()

    # Corner L-brackets
    painter.drawLine(QtCore.QPointF(x0, y0), QtCore.QPointF(x0 + length, y0))
    painter.drawLine(QtCore.QPointF(x0, y0), QtCore.QPointF(x0, y0 + length))
    painter.drawLine(QtCore.QPointF(x1, y0), QtCore.QPointF(x1 - length, y0))
    painter.drawLine(QtCore.QPointF(x1, y0), QtCore.QPointF(x1, y0 + length))
    painter.drawLine(QtCore.QPointF(x0, y1), QtCore.QPointF(x0 + length, y1))
    painter.drawLine(QtCore.QPointF(x0, y1), QtCore.QPointF(x0, y1 - length))
    painter.drawLine(QtCore.QPointF(x1, y1), QtCore.QPointF(x1 - length, y1))
    painter.drawLine(QtCore.QPointF(x1, y1), QtCore.QPointF(x1, y1 - length))

    # Corner filigree dots (rivets)
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(QtGui.QBrush(qcolor(GOLD_BRIGHT, 0.95)))
    dot_r = 1.3
    for cx, cy in [(x0 + 4, y0 + 4), (x1 - 4, y0 + 4), (x0 + 4, y1 - 4), (x1 - 4, y1 - 4)]:
        painter.drawEllipse(QtCore.QPointF(cx, cy), dot_r, dot_r)

    # Subtle top center ornament
    mid_x = (x0 + x1) / 2.0
    painter.setBrush(QtGui.QBrush(qcolor(GOLD, 0.7)))
    painter.drawEllipse(QtCore.QPointF(mid_x, y0 + 1), 1.5, 1.5)


def paint_mana_crystal(painter, center, radius, value, accent=MANA, alpha=1.0,
                        text_color="#04121E"):
    """Faceted Hextech cyan mana crystal with glowing aura and centered cost."""
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    path = crystal_path(center, radius)

    # Outer radiant mana halo
    halo = QtGui.QRadialGradient(center, radius * 1.8)
    halo.setColorAt(0.0, qcolor(MANA, 0.35 * alpha))
    halo.setColorAt(0.6, qcolor(MANA_DEEP, 0.12 * alpha))
    halo.setColorAt(1.0, qcolor(MANA, 0.0))
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(QtGui.QBrush(halo))
    painter.drawEllipse(center, radius * 1.8, radius * 1.8)

    # Faceted crystal body
    grad = QtGui.QLinearGradient(center.x(), center.y() - radius, center.x(), center.y() + radius)
    grad.setColorAt(0.0, qcolor("#C5FAFF", alpha))
    grad.setColorAt(0.30, qcolor(MANA, alpha))
    grad.setColorAt(0.85, qcolor(MANA_DEEP, alpha))
    grad.setColorAt(1.0, qcolor(MANA_DARK, alpha))
    painter.setBrush(QtGui.QBrush(grad))
    painter.setPen(QtGui.QPen(qcolor("#E6FBFF", 0.95 * alpha), 1.0))
    painter.drawPath(path)

    # Specular upper facet
    facet = QtGui.QPainterPath()
    facet.addPolygon(QtGui.QPolygonF([
        QtCore.QPointF(center.x() - radius * 0.45, center.y() - radius * 0.65),
        QtCore.QPointF(center.x(), center.y() - radius * 0.95),
        QtCore.QPointF(center.x() + radius * 0.15, center.y() - radius * 0.20),
        QtCore.QPointF(center.x() - radius * 0.35, center.y() + radius * 0.10),
    ]))
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(QtGui.QBrush(qcolor("#FFFFFF", 0.45 * alpha)))
    painter.drawPath(facet)

    # Centered crystal value with drop shadow
    val_str = str(value)
    text_rect = QtCore.QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
    f = number_font(max(7, int(radius * 0.85)), bold=True)
    painter.setFont(f)

    # Shadow
    painter.setPen(qcolor("#020810", 0.85 * alpha))
    painter.drawText(text_rect.translated(0.8, 0.8), QtCore.Qt.AlignmentFlag.AlignCenter, val_str)

    # Number
    painter.setPen(qcolor(text_color, alpha))
    painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignCenter, val_str)


def paint_region_badge(painter, center, radius, ref, alpha=1.0):
    """Hexagonal region badge."""
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    col = region_color(ref)
    path = hex_path(center, radius, flat=False)
    grad = QtGui.QLinearGradient(center.x(), center.y() - radius, center.x(), center.y() + radius)
    grad.setColorAt(0.0, qcolor(col, 0.55 * alpha))
    grad.setColorAt(1.0, qcolor(col, 0.16 * alpha))
    painter.setPen(QtGui.QPen(qcolor(col, 0.85 * alpha), 1.0))
    painter.setBrush(QtGui.QBrush(grad))
    painter.drawPath(path)


def paint_pill(painter, rect, color, text, alpha=1.0, font=None, radius=4.0):
    """Small rounded badge with clean border and background."""
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QtGui.QPen(qcolor(color, 0.65 * alpha), 1.0))
    painter.setBrush(QtGui.QBrush(qcolor(color, 0.18 * alpha)))
    painter.drawRoundedRect(rect, radius, radius)
    painter.setPen(QtGui.QPen(qcolor(color, alpha)))
    painter.setFont(font or body_font(8, bold=True))
    painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, text)


def elide(text, font, width):
    fm = QtGui.QFontMetrics(font)
    return fm.elidedText(text, QtCore.Qt.TextElideMode.ElideRight, int(width))


def crop_art(pixmap, target_size: QtCore.QSize) -> QtGui.QPixmap:
    """Return the illustration band of a card image scaled to ``target_size``."""
    out = QtGui.QPixmap(target_size)
    out.fill(QtCore.Qt.GlobalColor.transparent)
    if pixmap is None or pixmap.isNull():
        return out
    src = pixmap.toImage()
    w, h = src.width(), src.height()
    if w <= 0 or h <= 0:
        return out
    band = QtCore.QRect(int(w * 0.02), int(h * 0.13), int(w * 0.96), int(h * 0.30))
    painter = QtGui.QPainter(out)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
    target = QtCore.QRectF(out.rect())
    src_ratio = band.width() / max(1, band.height())
    dst_ratio = target.width() / max(1.0, target.height())
    if src_ratio > dst_ratio:
        new_w = int(band.height() * dst_ratio)
        band = QtCore.QRect(band.x() + (band.width() - new_w) // 2, band.y(), new_w, band.height())
    else:
        new_h = int(band.width() / dst_ratio)
        band = QtCore.QRect(band.x(), band.y() + (band.height() - new_h) // 2, band.width(), new_h)
    painter.drawImage(target, src, QtCore.QRectF(band))
    painter.end()
    return out
