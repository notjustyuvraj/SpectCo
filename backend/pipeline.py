# -*- coding: utf-8 -*-
"""
backend/pipeline.py
-------------------
AudioWorker — Qt bridge between the audio/ASR backend and the UI thread.

Threading model:
    sounddevice OS thread
        → _chunk_queue  (bounded 200 slots ≈ ~60 s audio — prevents RAM runaway)
    Audio accumulation loop  [QThread, this object]
        → Dual-layer VAD gate (RMS energy + voiced-fraction check)
        → _asr_queue  (maxsize=1 — ensures only ONE pending buffer at a time)
    ASR thread  [daemon Python thread]
        → faster-whisper transcription
        → Qt signals → UI

Why maxsize=1 on _asr_queue?
    We want the LATEST audio, not a backlog. If ASR is still running when a
    new buffer is ready, we discard the old buffer (it's already stale) rather
    than queuing work that will arrive seconds late to the UI.

Why dual-layer VAD?
    1. Per-chunk RMS in the callback loop (cheap, avoids polluting the accumulator)
    2. Buffer-level voiced-fraction check before push to ASR (saves a full
       Whisper inference call for mostly-silent windows)
"""

from __future__ import annotations

import queue
import threading
import time

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from config import settings
from backend.asr.engine import ASREngine
from backend.audio.capture import AudioCapture
from backend.audio.processor import AudioProcessor
from utils.logger import get_logger

log = get_logger(__name__)

# Chunk queue capacity: 200 × 300 ms = 60 s max backlog. Prevents unbounded RAM.
_CHUNK_QUEUE_MAX = 200


class AudioWorker(QObject):
    """
    QObject that runs inside a QThread.

    The main thread moves this object to a QThread and connects signals to
    UI slots. All heavy work runs here and in _asr_loop().
    """

    transcript = pyqtSignal(str)    # Roman-Hinglish transcribed text
    level      = pyqtSignal(float)  # VU meter 0.0–1.0
    state      = pyqtSignal(str)    # Status string
    error      = pyqtSignal(str)    # Error string

    def __init__(self) -> None:
        super().__init__()

        # Bounded chunk queue — drops oldest chunks if accumulation loop lags.
        self._chunk_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=_CHUNK_QUEUE_MAX)

        # Single-slot ASR queue — only ONE pending buffer at a time.
        # If ASR is busy when a new buffer arrives, the old one is replaced.
        self._asr_queue: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=1)

        self._processor   = AudioProcessor()
        self._capture     = AudioCapture(chunk_queue=self._chunk_queue)
        self._engine: ASREngine | None = None

        # Accumulation buffer (only touched by audio loop thread)
        self._accum: list[np.ndarray] = []
        self._accum_samples: int      = 0
        self._voiced_chunks: int      = 0     # chunks above VAD threshold
        self._total_chunks:  int      = 0     # total chunks in this buffer

        self._target_samples: int = int(settings.ACCUM_SECS * settings.SAMPLE_RATE)

        self._running = False
        self._asr_thread: threading.Thread | None = None

        # VU level throttle — emit at most ~10 times/sec (every 2 polls @ 20 ms)
        self._level_poll_counter = 0
        self._last_level: float  = 0.0

    # ------------------------------------------------------------------
    # Qt slots — called from main thread
    # ------------------------------------------------------------------

    @pyqtSlot(bool)
    def set_muted(self, muted: bool) -> None:
        self._capture.set_muted(muted)
        if muted:
            self._flush_chunk_queue()
            self._reset_accum()

    @pyqtSlot(bool)
    def set_noisy_env(self, noisy: bool) -> None:
        self._processor.noisy_env = noisy

    # ------------------------------------------------------------------
    # Main entry point (called by QThread.started)
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._running = True
        self.state.emit("Loading ASR model…")

        self._engine = ASREngine()
        if not self._engine.ready:
            self.error.emit(
                "ASR model failed to load. "
                "Install: pip install faster-whisper"
            )

        # Start the dedicated ASR thread
        self._asr_thread = threading.Thread(
            target=self._asr_loop,
            name="ASRThread",
            daemon=True,
        )
        self._asr_thread.start()

        # Start microphone
        if not self._capture.has_input_device():
            self.state.emit("No microphone detected.")
            self.error.emit("No audio input device found. Connect a microphone.")
        else:
            try:
                self._capture.start()
                name = self._capture.get_input_device_name()
                self.state.emit(f"Listening… ({name})")
                log.info("Capture started: %s", name)
            except Exception as exc:
                self.error.emit(f"Microphone error: {exc}")
                self.state.emit("Microphone failed.")

        # Audio accumulation loop
        while self._running:
            self._drain_and_accumulate()
            time.sleep(0.02)   # 20 ms poll

        # Shutdown
        self._capture.stop()
        try:
            self._asr_queue.put_nowait(None)   # sentinel
        except queue.Full:
            pass
        if self._asr_thread:
            self._asr_thread.join(timeout=10)

        log.info("AudioWorker stopped cleanly.")

    # ------------------------------------------------------------------
    # Internal — audio accumulation (runs in QThread)
    # ------------------------------------------------------------------

    def _drain_and_accumulate(self) -> None:
        """
        Pull all available chunks from the capture queue, run through the
        audio processor, track voice activity, and accumulate.

        When enough audio is collected AND the voiced-fraction gate passes,
        push to the ASR queue (replacing any pending stale buffer).
        """
        new_level: float | None = None

        while True:
            try:
                raw = self._chunk_queue.get_nowait()
            except queue.Empty:
                break

            clean = self._processor.process(raw)
            if clean.size == 0:
                continue

            # Track RMS for VU meter (accumulate max over the poll period)
            rms = AudioProcessor.rms(clean)
            candidate = min(1.0, rms * 15.0)
            if new_level is None or candidate > new_level:
                new_level = candidate

            # Voice activity tracking per chunk
            is_voiced = rms >= settings.VAD_RMS_THRESHOLD
            self._accum.append(clean)
            self._accum_samples += len(clean)
            self._total_chunks  += 1
            if is_voiced:
                self._voiced_chunks += 1

        # Throttle VU level signal: emit every 2nd poll (~10 fps)
        self._level_poll_counter += 1
        if self._level_poll_counter >= 2:
            self._level_poll_counter = 0
            emit_level = new_level if new_level is not None else 0.0
            if abs(emit_level - self._last_level) > 0.01:  # only if changed
                self.level.emit(emit_level)
                self._last_level = emit_level

        # Check if we have enough audio to send to ASR
        if self._accum_samples < self._target_samples:
            return

        # --- Buffer-level VAD gate -------------------------------------------
        voiced_fraction = (
            self._voiced_chunks / self._total_chunks
            if self._total_chunks > 0 else 0.0
        )

        if voiced_fraction < settings.VAD_VOICED_FRACTION:
            # Mostly silence — discard this buffer and start fresh.
            log.debug(
                "VAD gate: %.0f%% voiced < %.0f%% threshold — skipping ASR.",
                voiced_fraction * 100,
                settings.VAD_VOICED_FRACTION * 100,
            )
            self._reset_accum()
            return

        # Build the audio array and push to ASR
        audio = np.concatenate(self._accum).astype(np.float32)
        self._reset_accum()

        # Replace any stale pending buffer rather than queuing behind it.
        # This ensures ASR always works on the most recent speech window.
        try:
            # Drain any old pending item first
            try:
                self._asr_queue.get_nowait()
            except queue.Empty:
                pass
            self._asr_queue.put_nowait(audio)
        except queue.Full:
            log.warning("ASR queue unexpectedly full — chunk dropped.")

    def _reset_accum(self) -> None:
        self._accum.clear()
        self._accum_samples = 0
        self._voiced_chunks = 0
        self._total_chunks  = 0

    def _flush_chunk_queue(self) -> None:
        while True:
            try:
                self._chunk_queue.get_nowait()
            except queue.Empty:
                break

    # ------------------------------------------------------------------
    # Internal — ASR thread (daemon Python thread)
    # ------------------------------------------------------------------

    def _asr_loop(self) -> None:
        log.info("ASR thread started.")
        while True:
            audio = self._asr_queue.get()   # blocking wait
            if audio is None:               # sentinel → exit
                break

            self.state.emit("Transcribing…")
            try:
                text = self._engine.transcribe(audio) if self._engine else None
            except Exception:
                log.exception("Unexpected ASR loop error.")
                text = None

            if text:
                log.info("Transcript: %s", text)
                self.transcript.emit(text)

            self.state.emit("Listening…")

        log.info("ASR thread stopped.")

    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Signal the worker to stop (called from main thread)."""
        self._running = False
