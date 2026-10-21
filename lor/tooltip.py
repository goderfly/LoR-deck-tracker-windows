"""
Hextech Styled Tooltip Popup.

Renders tactile tooltips matching the Hextech Runeterra aesthetic:
chamfered borders, antique gold trim, radiant cyan title, dark obsidian fill,
and always stays on top above the topmost overlay windows.
"""

from PyQt6 import QtCore, QtGui, QtWidgets
from . import theme, win32ext
from .theme import GOLD, GOLD_BRIGHT, GOLD_DIM, MANA, MUTED, TEXT, qcolor
from .widgets import METRICS


class HextechTooltip(QtWidgets.QWidget):
    """Floating tactical tooltip with Runeterra styling and topmost z-ordering."""

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = HextechTooltip()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.WindowType.ToolTip
            | QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.title_text = ""
        self.body_text = ""
        self.accent_color = GOLD

        self.hide_timer = QtCore.QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_tip(self, title, body, global_pos, accent=GOLD, duration_ms=0):
        """Display tooltip near global_pos with given title and description."""
        self.title_text = title
        self.body_text = body
        self.accent_color = accent

        # Measure dimensions
        padding_h = METRICS(14)
        padding_v = METRICS(10)
        title_font = theme.header_font(METRICS(9), bold=True)
        body_font = theme.body_font(METRICS(8.5), bold=False)

        fm_title = QtGui.QFontMetrics(title_font)
        fm_body = QtGui.QFontMetrics(body_font)

        max_text_w = METRICS(300)
        title_w = fm_title.horizontalAdvance(title) if title else 0

        # Calculate bounding rect for wrapped body
        body_rect = fm_body.boundingRect(
            QtCore.QRect(0, 0, max_text_w, 2000),
            int(QtCore.Qt.TextFlag.TextWordWrap),
            body
        )

        w = max(title_w, body_rect.width()) + padding_h * 2
        w = max(w, METRICS(160))
        h = padding_v * 2 + (fm_title.height() + METRICS(4) if title else 0) + body_rect.height()

        self.setFixedSize(int(w), int(h))

        # Position next to cursor / target, ensuring it remains on screen
        screen = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        x = global_pos.x() + METRICS(16)
        y = global_pos.y() + METRICS(16)

        if x + w > screen.right() - 8:
            x = global_pos.x() - w - METRICS(8)
        if y + h > screen.bottom() - 8:
            y = global_pos.y() - h - METRICS(8)

        x = max(screen.left() + 8, min(x, screen.right() - w - 8))
        y = max(screen.top() + 8, min(y, screen.bottom() - h - 8))

        self.move(int(x), int(y))
        self.show()
        self.raise_()
        win32ext.keep_topmost(self)

        if duration_ms > 0:
            self.hide_timer.start(duration_ms)
        else:
            self.hide_timer.stop()

    def hide_tip(self):
        self.hide_timer.stop()
        self.hide()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        rect = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # 1. Background panel
        path = theme.chamfered_path(rect, 6.0)

        # Subtle dark obsidian gradient
        grad = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, qcolor("#0F1826", 0.98))
        grad.setColorAt(1.0, qcolor("#070B13", 0.99))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QBrush(grad))
        p.drawPath(path)

        # Outer border in Hextech Gold / accent
        pen_edge = QtGui.QPen(qcolor(self.accent_color, 0.85), 1.2)
        p.setPen(pen_edge)
        p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # Inner fine hairline
        inner_path = theme.chamfered_path(rect.adjusted(2, 2, -2, -2), 4.5)
        p.setPen(QtGui.QPen(qcolor(GOLD_DIM, 0.35), 1.0))
        p.drawPath(inner_path)

        # Corner gold rivets
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QBrush(qcolor(GOLD_BRIGHT, 0.95)))
        dot_r = 1.0
        for cx, cy in [(rect.left() + 4, rect.top() + 4),
                       (rect.right() - 4, rect.top() + 4),
                       (rect.left() + 4, rect.bottom() - 4),
                       (rect.right() - 4, rect.bottom() - 4)]:
            p.drawEllipse(QtCore.QPointF(cx, cy), dot_r, dot_r)

        # 2. Text Content
        pad_x = METRICS(12)
        cur_y = METRICS(10)

        if self.title_text:
            p.setFont(theme.header_font(METRICS(9), bold=True))
            p.setPen(qcolor(self.accent_color))
            title_rect = QtCore.QRectF(pad_x, cur_y, self.width() - pad_x * 2, METRICS(16))
            p.drawText(title_rect, QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, self.title_text)
            cur_y += METRICS(18)

            # Hairline divider under title
            p.setPen(QtGui.QPen(qcolor(GOLD_DIM, 0.5), 1))
            p.drawLine(QtCore.QPointF(pad_x, cur_y - 2), QtCore.QPointF(self.width() - pad_x, cur_y - 2))
            cur_y += METRICS(4)

        if self.body_text:
            p.setFont(theme.body_font(METRICS(8.5), bold=False))
            p.setPen(qcolor(TEXT))
            body_rect = QtCore.QRectF(pad_x, cur_y, self.width() - pad_x * 2, self.height() - cur_y - METRICS(8))
            p.drawText(body_rect, int(QtCore.Qt.TextFlag.TextWordWrap), self.body_text)
