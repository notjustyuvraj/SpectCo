# -*- coding: utf-8 -*-
"""
frontend/app.py
---------------
SpeakEasyApp — the main application window.

Responsibilities
----------------
* Build the UI from widgets.
* Create the QThread + AudioWorker pipeline.
* Connect pipeline signals to UI update slots.
* Handle application lifecycle (start, close).

The app intentionally knows nothing about sounddevice, Whisper, or
numpy.  All of that lives in the backend package.
"""

from __future__ import annotations

import time

from PyQt6.QtCore import QThread, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

import config
from backend.pipeline import AudioWorker
from frontend.widgets import SettingsSidebar, TranscriptPanel, VUMeter
from frontend.styles import (
    APP_STYLE,
    C_ACCENT,
    C_TEXT_DIM,
    C_CYAN,
    C_ACCENT_DARK,
    badge_style,
    MIC_LIVE_STYLE,
    MIC_MUTED_STYLE,
)
from utils.logger import get_logger

log = get_logger(__name__)


class SpeakEasyApp(QMainWindow):
    """
    Main application window.

    Layout
    ------
    [Header: title | badges | clear button          ]
    [Sidebar | Splitter: left panel | right panel   ]
    [Bottom bar: VU meter | ASR status | word count ]
    [Status bar                                     ]
    """

    def __init__(self) -> None:
        super().__init__()

        self._word_count = 0
        self._session_start = time.time()

        self.setWindowTitle("SpeakEasy — Hindi/Hinglish Speech-to-Text")
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

        self._setup_palette()
        self._build_ui()
        self._start_pipeline()

        # Update session stats every second — lightweight, just string formatting.
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(1000)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_palette(self) -> None:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window,     QColor("#0a0a14"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#e8e8f0"))
        self.setPalette(palette)
        self.setStyleSheet(APP_STYLE)

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("MAIN")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 6)
        root.setSpacing(6)

        root.addWidget(self._build_header())

        middle = QHBoxLayout()
        middle.setSpacing(8)

        self._sidebar = SettingsSidebar()
        middle.addWidget(self._sidebar)
        middle.addWidget(self._build_panels(), 1)

        root.addLayout(middle, 1)
        root.addWidget(self._build_bottom_bar())

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Starting microphone and ASR model…")

        self._wire_sidebar()

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet("""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #0d0d2e, stop:0.5 #1a0a3d, stop:1 #0d1a2e
            );
            border-radius: 8px;
            border: 1px solid #1e1e3f;
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 0, 14, 0)

        title = QLabel("SpeakEasy  |  Roman Hinglish Offline ASR")
        title.setStyleSheet(f"color:{C_ACCENT}; font-size:15px; font-weight:bold;")
        layout.addWidget(title)
        layout.addStretch()

        # Static "OFFLINE" badge.
        offline_badge = QLabel("OFFLINE")
        offline_badge.setStyleSheet(badge_style("#003f1a", "#22c55e"))
        layout.addWidget(offline_badge)
        layout.addSpacing(8)

        # Dynamic mic status badge.
        self._mic_badge = QLabel("MIC STARTING")
        self._mic_badge.setStyleSheet(badge_style("#3f3200", "#facc15"))
        layout.addWidget(self._mic_badge)
        layout.addSpacing(8)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(30)
        clear_btn.clicked.connect(self._clear_transcript)
        layout.addWidget(clear_btn)

        return header

    def _build_panels(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)

        self._left_panel = TranscriptPanel(
            "LEFT EYE  /  PRIMARY DISPLAY", C_ACCENT_DARK
        )
        self._right_panel = TranscriptPanel(
            "RIGHT EYE  /  SECONDARY DISPLAY", C_CYAN
        )

        splitter.addWidget(self._left_panel)
        splitter.addWidget(self._right_panel)
        splitter.setSizes([500, 500])
        return splitter

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(34)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        mic_label = QLabel("Mic Level:")
        mic_label.setStyleSheet(f"color:{C_TEXT_DIM}; font-size:10px;")
        layout.addWidget(mic_label)

        self._vu_meter = VUMeter()
        self._vu_meter.setMinimumWidth(160)
        layout.addWidget(self._vu_meter)

        layout.addStretch()

        self._asr_status = QLabel("ASR: Starting…")
        self._asr_status.setStyleSheet(
            f"color:#38bdf8; font-size:10px; font-family:monospace;"
        )
        layout.addWidget(self._asr_status)

        layout.addStretch()

        self._stats_label = QLabel("Words: 0  |  Session: 0:00")
        self._stats_label.setStyleSheet(
            f"color:{C_TEXT_DIM}; font-size:10px;"
        )
        layout.addWidget(self._stats_label)

        return bar

    def _wire_sidebar(self) -> None:
        self._sidebar.font_changed.connect(self._on_font_changed)
        self._sidebar.opacity_changed.connect(self._on_opacity_changed)
        self._sidebar.noisy_changed.connect(self._on_noisy_changed)
        self._sidebar.mute_changed.connect(self._on_mute_changed)

    # ------------------------------------------------------------------
    # Pipeline startup
    # ------------------------------------------------------------------

    def _start_pipeline(self) -> None:
        self._worker = AudioWorker()
        self._thread = QThread()

        # Move the worker to the thread so its run() executes there.
        self._worker.moveToThread(self._thread)

        # Connect lifecycle.
        self._thread.started.connect(self._worker.run)

        # Connect backend → UI signals.
        self._worker.transcript.connect(self._on_transcript)
        self._worker.level.connect(self._vu_meter.set_level)
        self._worker.state.connect(self._on_state)
        self._worker.error.connect(self._on_error)

        self._thread.start()
        log.info("Pipeline thread started.")

    # ------------------------------------------------------------------
    # Sidebar slot handlers
    # ------------------------------------------------------------------

    @pyqtSlot(bool)
    def _on_mute_changed(self, muted: bool) -> None:
        # Forward to the worker via a queued connection (crosses thread boundary).
        self._worker.set_muted(muted)

        self._mic_badge.setText("MIC MUTED" if muted else "MIC LIVE")
        self._mic_badge.setStyleSheet(
            MIC_MUTED_STYLE if muted else MIC_LIVE_STYLE
        )

    @pyqtSlot(bool)
    def _on_noisy_changed(self, noisy: bool) -> None:
        self._worker.set_noisy_env(noisy)
        self.statusBar().showMessage(
            f"Light noise control {'enabled' if noisy else 'disabled'}.", 3000
        )

    @pyqtSlot(int)
    def _on_font_changed(self, size: int) -> None:
        self._left_panel.set_font_size(size)
        self._right_panel.set_font_size(size)

    @pyqtSlot(float)
    def _on_opacity_changed(self, opacity: float) -> None:
        self._left_panel.set_opacity(opacity)
        self._right_panel.set_opacity(opacity)

    # ------------------------------------------------------------------
    # Pipeline signal handlers
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def _on_transcript(self, text: str) -> None:
        self._left_panel.append_text(text)
        self._right_panel.append_text(text)
        self._word_count += len(text.split())

        self._asr_status.setText("ASR: ✓ Text received")
        self._asr_status.setStyleSheet(
            "color:#22c55e; font-size:10px; font-family:monospace;"
        )
        # Reset status label after 2 s.
        QTimer.singleShot(2000, self._reset_asr_label)

    @pyqtSlot(str)
    def _on_state(self, message: str) -> None:
        self.statusBar().showMessage(message)

        if "Transcribing" in message:
            self._asr_status.setText("ASR: Transcribing…")
            self._asr_status.setStyleSheet(
                "color:#facc15; font-size:10px; font-family:monospace;"
            )
        elif "Listening" in message:
            self._asr_status.setText("ASR: Listening…")
            self._asr_status.setStyleSheet(
                f"color:{C_TEXT_DIM}; font-size:10px; font-family:monospace;"
            )

    @pyqtSlot(str)
    def _on_error(self, message: str) -> None:
        log.error("Pipeline error: %s", message)
        self.statusBar().showMessage(message, 6000)
        self._asr_status.setText("ASR: Error")
        self._asr_status.setStyleSheet(
            "color:#ef4444; font-size:10px; font-family:monospace;"
        )

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _clear_transcript(self) -> None:
        self._left_panel.clear()
        self._right_panel.clear()
        self._word_count = 0

    def _reset_asr_label(self) -> None:
        self._asr_status.setText("ASR: Listening…")
        self._asr_status.setStyleSheet(
            f"color:{C_TEXT_DIM}; font-size:10px; font-family:monospace;"
        )

    def _update_stats(self) -> None:
        elapsed = int(time.time() - self._session_start)
        m, s = divmod(elapsed, 60)
        self._stats_label.setText(
            f"Words: {self._word_count}  |  Session: {m}:{s:02d}"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        """
        Cleanly shut down the pipeline before the window closes.

        We wait up to 10 s for the ASR thread to finish its current
        inference (the prototype only waited 2 s, causing a hard kill
        mid-inference that could corrupt model state).
        """
        log.info("Closing application…")

        self._worker.stop()

        if self._thread.isRunning():
            self._thread.quit()
            finished = self._thread.wait(10_000)   # 10 second grace period
            if not finished:
                log.warning("Worker thread did not stop in time — forcing.")
                self._thread.terminate()

        log.info("Application closed.")
        event.accept()
