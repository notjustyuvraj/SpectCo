# -*- coding: utf-8 -*-
"""
frontend/main_window.py
-----------------------
PyQt6 Desktop Interface for SpeakEasy V1.
"""

from __future__ import annotations

import sys
from PyQt6.QtCore import Qt, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLabel,
    QPushButton,
    QSlider,
    QCheckBox,
    QProgressBar,
    QFrame,
    QApplication,
    QMessageBox,
)

from config import settings
from backend.pipeline import AudioWorker
from utils.logger import get_logger

log = get_logger(__name__)


class SpeakEasyWindow(QMainWindow):
    """
    Main Application Window.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SpeakEasy V1 — Offline Speech to Roman Hindi/Hinglish")
        self.resize(settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)
        self.setMinimumSize(800, 500)

        self._thread: QThread | None = None
        self._worker: AudioWorker | None = None
        self._is_muted = False

        self._init_ui()
        self._start_pipeline()

    def _init_ui(self) -> None:
        """Construct the user interface components."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                color: #E0E0E0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTextEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
            }
            QPushButton {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            QPushButton:checked {
                background-color: #D32F2F;
            }
            QProgressBar {
                border: 1px solid #333;
                border-radius: 4px;
                background-color: #1A1A1A;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #333;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
        """)

        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header bar
        header_layout = QHBoxLayout()
        title_label = QLabel("SpeakEasy V1")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #4CAF50;")
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("color: #AAAAAA; font-style: italic;")

        header_layout.addWidget(title_label)
        header_layout.addSpacing(16)
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Transcript Display Area
        self.transcript_box = QTextEdit(self)
        self.transcript_box.setReadOnly(True)
        self.transcript_box.setPlaceholderText("Spoken words will appear here in Roman Hindi / Hinglish...")
        main_layout.addWidget(self.transcript_box, stretch=1)

        # Controls & VU Meter Bar
        controls_layout = QHBoxLayout()

        # Mute Button
        self.mute_btn = QPushButton("Mute Mic", self)
        self.mute_btn.setCheckable(True)
        self.mute_btn.clicked.connect(self._toggle_mute)
        controls_layout.addWidget(self.mute_btn)

        # Clear Button
        self.clear_btn = QPushButton("Clear Text", self)
        self.clear_btn.clicked.connect(self._clear_transcript)
        controls_layout.addWidget(self.clear_btn)

        # Copy Button
        self.copy_btn = QPushButton("Copy Text", self)
        self.copy_btn.clicked.connect(self._copy_transcript)
        controls_layout.addWidget(self.copy_btn)

        # Light Noise Control Checkbox
        self.noise_checkbox = QCheckBox("Light Noise Boost", self)
        self.noise_checkbox.toggled.connect(self._toggle_noise_control)
        controls_layout.addWidget(self.noise_checkbox)

        controls_layout.addStretch()

        # VU Meter
        vu_label = QLabel("Mic Level:")
        controls_layout.addWidget(vu_label)

        self.vu_meter = QProgressBar(self)
        self.vu_meter.setRange(0, 100)
        self.vu_meter.setValue(0)
        self.vu_meter.setFixedWidth(120)
        self.vu_meter.setFixedHeight(16)
        self.vu_meter.setTextVisible(False)
        controls_layout.addWidget(self.vu_meter)

        main_layout.addLayout(controls_layout)

    def _start_pipeline(self) -> None:
        """Initialize worker thread and connect Qt signals."""
        self._thread = QThread()
        self._worker = AudioWorker()
        self._worker.moveToThread(self._thread)

        # Signals connection
        self._thread.started.connect(self._worker.run)
        self._worker.transcript.connect(self._append_transcript)
        self._worker.level.connect(self._update_vu_meter)
        self._worker.state.connect(self.status_label.setText)
        self._worker.error.connect(self._handle_error)

        self._thread.start()

    @pyqtSlot(str)
    def _append_transcript(self, text: str) -> None:
        """Append new transcribed text to UI."""
        if not text:
            return
        current = self.transcript_box.toPlainText()
        if current:
            self.transcript_box.setPlainText(current + " " + text)
        else:
            self.transcript_box.setPlainText(text)
        
        # Auto-scroll to bottom
        sb = self.transcript_box.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    @pyqtSlot(float)
    def _update_vu_meter(self, level_val: float) -> None:
        """Update VU meter progress bar (0.0 - 1.0)."""
        val = int(min(1.0, max(0.0, level_val)) * 100)
        self.vu_meter.setValue(val)

    @pyqtSlot(str)
    def _handle_error(self, err_msg: str) -> None:
        """Show error message box."""
        log.error("Pipeline error: %s", err_msg)
        self.status_label.setText(f"Error: {err_msg}")

    def _toggle_mute(self, checked: bool) -> None:
        """Handle Mute button toggle."""
        self._is_muted = checked
        if self._worker:
            self._worker.set_muted(checked)
        if checked:
            self.mute_btn.setText("Unmute Mic")
            self.status_label.setText("Microphone Muted")
            self.vu_meter.setValue(0)
        else:
            self.mute_btn.setText("Mute Mic")
            self.status_label.setText("Listening...")

    def _toggle_noise_control(self, checked: bool) -> None:
        if self._worker:
            self._worker.set_noisy_env(checked)

    def _clear_transcript(self) -> None:
        self.transcript_box.clear()

    def _copy_transcript(self) -> None:
        text = self.transcript_box.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.status_label.setText("Copied to clipboard!")

    def closeEvent(self, event) -> None:
        """Ensure threads shut down cleanly when window is closed."""
        if self._worker:
            self._worker.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait(5000)
        event.accept()
