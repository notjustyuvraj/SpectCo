# -*- coding: utf-8 -*-
"""
backend/audio/capture.py
------------------------
Thread-safe microphone capture using sounddevice.
"""

from __future__ import annotations

import queue
import numpy as np
import sounddevice as sd
from config import settings
from utils.logger import get_logger

log = get_logger(__name__)


class AudioCapture:
    """
    Manages sounddevice.InputStream to record audio from microphone.
    """

    def __init__(self, chunk_queue: queue.Queue[np.ndarray]) -> None:
        self._queue = chunk_queue
        self._stream: sd.InputStream | None = None
        self._muted = False
        self._input_device_id: int | None = None

    def set_input_device(self, device_id: int | None) -> None:
        """Set specific microphone device ID."""
        self._input_device_id = device_id

    def set_muted(self, muted: bool) -> None:
        """Mute/unmute microphone callback."""
        self._muted = muted

    def has_input_device(self) -> bool:
        """Check if at least one input audio device exists."""
        try:
            devices = sd.query_devices()
            return any(d.get("max_input_channels", 0) > 0 for d in devices)
        except Exception:
            return False

    def get_input_device_name(self) -> str:
        """Return human-readable name of current input device."""
        try:
            if self._input_device_id is not None:
                dev = sd.query_devices(self._input_device_id)
                return dev.get("name", "Unknown")
            dev = sd.query_devices(kind="input")
            return dev.get("name", "Default Microphone")
        except Exception:
            return "Default Microphone"

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Callback invoked by sounddevice on dedicated OS thread."""
        if status:
            log.warning("Audio capture status flags: %s", status)

        if self._muted:
            return

        chunk = indata[:, 0].copy()
        try:
            self._queue.put_nowait(chunk)
        except queue.Full:
            pass

    def start(self) -> None:
        """Start input stream."""
        if self._stream is not None:
            self.stop()

        self._stream = sd.InputStream(
            samplerate=settings.SAMPLE_RATE,
            blocksize=settings.BLOCK_SIZE,
            channels=1,
            dtype="float32",
            device=self._input_device_id,
            callback=self._audio_callback,
        )
        self._stream.start()
        log.info("Audio capture stream started.")

    def stop(self) -> None:
        """Stop and close input stream."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                log.exception("Error closing sounddevice stream.")
            finally:
                self._stream = None
            log.info("Audio capture stream stopped.")
