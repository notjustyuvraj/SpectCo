# -*- coding: utf-8 -*-
"""
frontend/widgets.py
-------------------
Reusable Qt widgets for SpeakEasy V1.

Widgets
-------
VUMeter          — animated mic level bar
TranscriptPanel  — scrollable transcript display
SettingsSidebar  — mute, noise control, font size, opacity
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import config
from frontend.styles import (
    SIDEBAR_STYLE,
    mute_button_style,
    panel_style,
    C_ACCENT,
    C_TEXT_DIM,
    C_TEXT_MID,
    C_TEXT,
)


# =============================================================================
# VU Meter
# =============================================================================

class VUMeter(QWidget):
    """Horizontal gradient bar showing mic input level."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(12)
        self._level = 0.0

    def set_level(self, value: float) -> None:
        self._level = max(0.0, min(1.0, value))
        self.update()   # schedules a repaint — does NOT block

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Background track.
        painter.setBrush(QColor(20, 20, 30))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 4, 4)

        filled = int(w * self._level)
        if filled <= 0:
            painter.end()
            return

        # Green → yellow → red gradient.
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor("#00e676"))
        grad.setColorAt(0.6, QColor("#ffeb3b"))
        grad.setColorAt(1.0, QColor("#f44336"))

        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(0, 0, filled, h, 4, 4)
        painter.end()


# =============================================================================
# Transcript Panel
# =============================================================================

class TranscriptPanel(QFrame):
    """
    Scrollable, read-only text area for displaying transcripts.

    Parameters
    ----------
    title       : label shown above the text area
    border_color: accent colour for the frame border and header text
    """

    def __init__(
        self,
        title: str,
        border_color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PANEL")

        self._border_color = border_color
        self._opacity   = config.DEFAULT_OPACITY
        self._font_size = config.DEFAULT_FONT_SIZE

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header = QLabel(title)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setObjectName("HEADER")
        layout.addWidget(header)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setObjectName("TEXT")
        self._text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self._text_edit)

        self._apply_style()

    # ------------------------------------------------------------------

    def append_text(self, text: str) -> None:
        """Append a transcript line and scroll to the bottom."""
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(f"{text}\n")
        self._text_edit.setTextCursor(cursor)
        self._text_edit.ensureCursorVisible()

    def clear(self) -> None:
        self._text_edit.clear()

    def set_font_size(self, size: int) -> None:
        self._font_size = max(8, min(24, size))
        self._apply_style()

    def set_opacity(self, value: float) -> None:
        self._opacity = max(0.0, min(0.8, value))
        self._apply_style()

    # ------------------------------------------------------------------

    def _apply_style(self) -> None:
        self.setStyleSheet(
            panel_style(self._border_color, self._opacity, self._font_size)
        )


# =============================================================================
# Settings Sidebar
# =============================================================================

class SettingsSidebar(QWidget):
    """
    Left-hand control panel.

    Signals
    -------
    font_changed(int)     — new font size in points
    opacity_changed(float)— new panel opacity 0.0 – 0.8
    noisy_changed(bool)   — noise control toggled
    mute_changed(bool)    — mute toggled
    """

    font_changed    = pyqtSignal(int)
    opacity_changed = pyqtSignal(float)
    noisy_changed   = pyqtSignal(bool)
    mute_changed    = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(SIDEBAR_STYLE)
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Section heading
        heading = QLabel("Controls")
        heading.setStyleSheet(
            f"color:{C_ACCENT}; font-size:13px; font-weight:bold;"
        )
        layout.addWidget(heading)

        # ---- Mic mute toggle ------------------------------------------
        self._mute_btn = QPushButton("Mic: LIVE")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setStyleSheet(mute_button_style(False))
        self._mute_btn.toggled.connect(self._on_mute_toggled)
        layout.addWidget(self._mute_btn)

        layout.addWidget(self._hline())

        # ---- Noise control --------------------------------------------
        noise_group  = QGroupBox("Noise & Environment")
        noise_layout = QVBoxLayout(noise_group)

        self._noisy_cb = QCheckBox("Light Noise Control")
        self._noisy_cb.setToolTip(
            "Gently boosts very quiet signals when the environment is noisy."
        )
        self._noisy_cb.toggled.connect(self.noisy_changed.emit)
        noise_layout.addWidget(self._noisy_cb)

        self._noise_label = QLabel("Ambient: —")
        self._noise_label.setStyleSheet(f"color:{C_TEXT_MID}; font-size:10px;")
        noise_layout.addWidget(self._noise_label)

        layout.addWidget(noise_group)

        layout.addWidget(self._hline())

        # ---- Display settings ----------------------------------------
        display_group  = QGroupBox("Display")
        display_layout = QVBoxLayout(display_group)

        font_label = QLabel("Font Size (8–24 pt):")
        font_label.setStyleSheet(f"color:{C_TEXT}; font-size:10px;")
        display_layout.addWidget(font_label)

        self._font_spin = QSpinBox()
        self._font_spin.setRange(8, 24)
        self._font_spin.setValue(config.DEFAULT_FONT_SIZE)
        self._font_spin.setSuffix(" pt")
        self._font_spin.valueChanged.connect(self.font_changed.emit)
        display_layout.addWidget(self._font_spin)

        self._opacity_label = QLabel(
            f"Opacity: {int(config.DEFAULT_OPACITY * 100)}%"
        )
        self._opacity_label.setStyleSheet(f"color:{C_TEXT}; font-size:10px;")
        display_layout.addWidget(self._opacity_label)

        opacity_slider = QSlider(Qt.Orientation.Horizontal)
        opacity_slider.setRange(0, 80)
        opacity_slider.setValue(int(config.DEFAULT_OPACITY * 100))
        opacity_slider.valueChanged.connect(self._on_opacity_changed)
        display_layout.addWidget(opacity_slider)

        layout.addWidget(display_group)
        layout.addStretch()

    # ------------------------------------------------------------------

    def set_noise_label(self, text: str) -> None:
        self._noise_label.setText(text)

    # ------------------------------------------------------------------

    def _on_mute_toggled(self, checked: bool) -> None:
        self._mute_btn.setText("Mic: MUTED" if checked else "Mic: LIVE")
        self._mute_btn.setStyleSheet(mute_button_style(checked))
        self.mute_changed.emit(checked)

    def _on_opacity_changed(self, value: int) -> None:
        self._opacity_label.setText(f"Opacity: {value}%")
        self.opacity_changed.emit(value / 100.0)

    @staticmethod
    def _hline() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color:#2d2d3d;")
        return line
