"""
Settings window.

Exposes everything a player may want to tune: global scale, transparency,
language, which overlay is visible, click-through, position locking and the
manual spell-mana bank of the opponent (the API cannot read it directly).
"""

from PyQt6 import QtCore, QtGui, QtWidgets

from . import theme
from .theme import (
    GOLD, GOLD_BRIGHT, GOLD_DIM, GOLD_SOFT, MANA, MANA_DEEP, MANA_DARK,
    MUTED, PANEL_EDGE, PANEL_TOP, TEXT, qcolor,
)
from .panels import IconButton, OverlayWindow
from .widgets import HudFrame, METRICS

STYLE = """
QWidget {
    background: transparent;
    color: %(text)s;
    font-family: 'Segoe UI', Tahoma, sans-serif;
    font-size: 12px;
}
QLabel {
    background: transparent;
    border: none;
}
QCheckBox {
    background: transparent;
    spacing: 8px;
    padding: 3px 0;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid %(gold_dim)s;
    background: #0A1220;
}
QCheckBox::indicator:hover {
    border-color: %(gold)s;
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 %(gold_bright)s, stop:1 %(gold)s);
    border: 1px solid %(gold_bright)s;
}
QComboBox {
    background: #0E1728;
    border: 1px solid %(gold_dim)s;
    border-radius: 4px;
    padding: 5px 10px;
    color: %(gold_soft)s;
    font-weight: 600;
    min-width: 130px;
}
QComboBox:hover {
    border-color: %(gold)s;
}
QComboBox QAbstractItemView {
    background: #0A111E;
    border: 1px solid %(gold_dim)s;
    selection-background-color: #1A2B44;
    color: %(text)s;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #0E1728;
    border: 1px solid #1C2D47;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #007A9E, stop:1 #00F0FF);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 %(gold_bright)s, stop:1 %(gold)s);
    border: 2px solid #3B2A0D;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #121F33, stop:1 #0A1220);
    border: 1px solid %(gold_dim)s;
    border-radius: 4px;
    color: %(gold_soft)s;
    padding: 7px 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1C2E4A, stop:1 #101B2E);
    border-color: %(gold_bright)s;
    color: #FFFFFF;
}
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0087AC, stop:1 #005670);
    border: 1px solid #00F0FF;
    color: white;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00A6D4, stop:1 #006C8C);
    border-color: #7BF6FF;
}
""" % {
    "text": TEXT,
    "gold": GOLD,
    "gold_bright": GOLD_BRIGHT,
    "gold_dim": GOLD_DIM,
    "gold_soft": GOLD_SOFT,
    "muted": MUTED,
}


class SettingsDialog(OverlayWindow):
    """Frameless settings panel."""

    def __init__(self, settings, on_apply, on_reset_positions, on_refresh_db,
                 on_close=None):
        width = METRICS(378)
        height = METRICS(560)
        screen = QtGui.QGuiApplication.primaryScreen().geometry()
        super().__init__("Настройки", width, height,
                         (screen.width() - width) // 2,
                         (screen.height() - height) // 2, accent=GOLD,
                         show_in_taskbar=True)
        self.settings = settings
        self.on_apply = on_apply
        self.on_reset_positions = on_reset_positions
        self.on_refresh_db = on_refresh_db
        self.on_close = on_close
        self.setStyleSheet(STYLE)
        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = HudFrame(accent=GOLD, accent_side="left")
        outer.addWidget(frame)
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(METRICS(18), METRICS(16), METRICS(18), METRICS(16))
        layout.setSpacing(METRICS(8))

        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("НАСТРОЙКИ")
        title.setFont(theme.display_font(METRICS(12)))
        title.setStyleSheet(f"color: {GOLD}; background: transparent; border: none;")
        header.addWidget(title)
        header.addStretch()
        close_btn = IconButton("close", "Закрыть", GOLD, on_click=self.close_dialog)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # ---- scale -----------------------------------------------------
        self._section(layout, "ОФОРМЛЕНИЕ")
        self.scale_value = QtWidgets.QLabel("")
        layout.addWidget(self._slider_row("Масштаб интерфейса", self.scale_value))
        self.scale_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.scale_slider.setRange(80, 130)
        self.scale_slider.setValue(int(self.settings.get("scale", 1.0) * 100))
        self.scale_slider.valueChanged.connect(self._on_scale)
        layout.addWidget(self.scale_slider)

        self.opacity_value = QtWidgets.QLabel("")
        layout.addWidget(self._slider_row("Прозрачность", self.opacity_value))
        self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(int(self.settings.get("opacity", 0.92) * 100))
        self.opacity_slider.valueChanged.connect(self._on_opacity)
        layout.addWidget(self.opacity_slider)

        # ---- language ---------------------------------------------------
        self._section(layout, "ЯЗЫК")
        lang_row = QtWidgets.QHBoxLayout()
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItem("Русский", "ru_ru")
        self.lang_combo.addItem("English", "en_us")
        idx = self.lang_combo.findData(self.settings.get("language", "ru_ru"))
        self.lang_combo.setCurrentIndex(max(0, idx))
        self.lang_combo.currentIndexChanged.connect(self._on_language)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        layout.addLayout(lang_row)

        # ---- overlays ---------------------------------------------------
        self._section(layout, "ОВЕРЛЕИ")
        self.cb_player = self._checkbox(layout, "Панель моей колоды", "player_overlay_visible")
        self.cb_opponent = self._checkbox(layout, "Панель противника", "opponent_overlay_visible")
        self.cb_advisor = self._checkbox(layout, "Панель советника", "advisor_overlay_visible")
        self.cb_tooltips = self._checkbox(layout, "Превью карт при наведении", "tooltips_enabled")
        self.cb_click_through = self._checkbox(layout, "Клик-сквозь (клики идут в игру)",
                                              "click_through")
        self.cb_locked = self._checkbox(layout, "Заблокировать перемещение", "locked")
        self.cb_always = self._checkbox(layout, "Показывать оверлеи вне матча", "always_visible")

        # ---- opponent spell mana ---------------------------------------
        self._section(layout, "МАНА ЗАКЛИНАНИЙ ПРОТИВНИКА")
        hint = QtWidgets.QLabel("API не отдаёт банк заклинаний - задайте его вручную")
        hint.setStyleSheet(f"color: {MUTED}; font-size: 10px; background: transparent;")
        layout.addWidget(hint)
        mana_row = QtWidgets.QHBoxLayout()
        self.mana_minus = QtWidgets.QPushButton("−")
        self.mana_plus = QtWidgets.QPushButton("+")
        self.mana_value = QtWidgets.QLabel(str(self.settings.get("opp_spell_mana", 0)))
        self.mana_value.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.mana_value.setStyleSheet(
            f"color: {GOLD}; font-size: 18px; font-weight: bold; background: transparent;")
        self.mana_minus.setFixedWidth(METRICS(40))
        self.mana_plus.setFixedWidth(METRICS(40))
        self.mana_minus.clicked.connect(lambda: self._bump_mana(-1))
        self.mana_plus.clicked.connect(lambda: self._bump_mana(1))
        mana_row.addWidget(self.mana_minus)
        mana_row.addWidget(self.mana_value, stretch=1)
        mana_row.addWidget(self.mana_plus)
        layout.addLayout(mana_row)

        layout.addStretch()

        # ---- actions ----------------------------------------------------
        buttons = QtWidgets.QHBoxLayout()
        reset_btn = QtWidgets.QPushButton("Сбросить позиции")
        reset_btn.clicked.connect(self.on_reset_positions)
        buttons.addWidget(reset_btn)
        refresh_btn = QtWidgets.QPushButton("Обновить базу карт")
        refresh_btn.clicked.connect(self.on_refresh_db)
        buttons.addWidget(refresh_btn)
        layout.addLayout(buttons)

        done_btn = QtWidgets.QPushButton("Готово")
        done_btn.setObjectName("primary")
        done_btn.clicked.connect(self.close_dialog)
        layout.addWidget(done_btn)

        self._sync_labels()

    # ------------------------------------------------------------------
    def _section(self, layout, text):
        lbl = QtWidgets.QLabel(text)
        lbl.setFont(theme.display_font(METRICS(9)))
        lbl.setStyleSheet(f"color: #7FC7E8; background: transparent; border: none;")
        layout.addWidget(lbl)

    def _slider_row(self, label, value_label):
        container = QtWidgets.QWidget()
        container.setStyleSheet("background: transparent;")
        row = QtWidgets.QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT}; background: transparent;")
        row.addWidget(lbl)
        row.addStretch()
        value_label.setStyleSheet(f"color: {GOLD}; font-weight: bold; background: transparent;")
        row.addWidget(value_label)
        return container

    def _checkbox(self, layout, text, key):
        cb = QtWidgets.QCheckBox(text)
        cb.setChecked(bool(self.settings.get(key, False)))
        cb.stateChanged.connect(self._emit)
        layout.addWidget(cb)
        return cb

    # ------------------------------------------------------------------
    def _sync_labels(self):
        self.scale_value.setText(f"{self.scale_slider.value()}%")
        self.opacity_value.setText(f"{self.opacity_slider.value()}%")
        self.mana_value.setText(str(self.settings.get("opp_spell_mana", 0)))

    def _on_scale(self, value):
        self.scale_value.setText(f"{value}%")
        self.settings["scale"] = value / 100.0
        self._emit()

    def _on_opacity(self, value):
        self.opacity_value.setText(f"{value}%")
        self.settings["opacity"] = value / 100.0
        self._emit()

    def _on_language(self, _index):
        self.settings["language"] = self.lang_combo.currentData()
        self._emit()

    def _bump_mana(self, delta):
        value = int(self.settings.get("opp_spell_mana", 0)) + delta
        value = max(0, min(10, value))
        self.settings["opp_spell_mana"] = value
        self.mana_value.setText(str(value))
        self._emit()

    def _emit(self, *_args):
        self.settings["player_overlay_visible"] = self.cb_player.isChecked()
        self.settings["opponent_overlay_visible"] = self.cb_opponent.isChecked()
        self.settings["advisor_overlay_visible"] = self.cb_advisor.isChecked()
        self.settings["tooltips_enabled"] = self.cb_tooltips.isChecked()
        self.settings["click_through"] = self.cb_click_through.isChecked()
        self.settings["locked"] = self.cb_locked.isChecked()
        self.settings["always_visible"] = self.cb_always.isChecked()
        self.on_apply(self.settings)

    def close_dialog(self):
        if self.on_close:
            self.on_close()
        else:
            self.hide()
