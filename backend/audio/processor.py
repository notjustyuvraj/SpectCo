# -*- coding: utf-8 -*-
"""
backend/audio/processor.py
---------------------------
Sanitization and energy computation for incoming audio arrays.
"""

from __future__ import annotations

import numpy as np


class AudioProcessor:
    """
    Lightweight float32 sanitization and RMS calculation.
    """

    _TARGET_RMS: float = 0.035
    _GAIN_MIN: float = 0.8
    _GAIN_MAX: float = 2.0

    def __init__(self, noisy_env: bool = False) -> None:
        self.noisy_env = noisy_env

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Sanitize and optionally apply soft gain."""
        audio = np.asarray(audio, dtype=np.float32)
        audio = np.nan_to_num(audio)
        audio = np.clip(audio, -1.0, 1.0)

        if audio.size == 0:
            return audio

        if self.noisy_env:
            rms_val = self.rms(audio)
            if rms_val > 1e-4:
                gain = float(
                    np.clip(self._TARGET_RMS / rms_val, self._GAIN_MIN, self._GAIN_MAX)
                )
                audio = np.clip(audio * gain, -1.0, 1.0)

        return audio.astype(np.float32)

    @staticmethod
    def rms(audio: np.ndarray) -> float:
        """Compute root-mean-square energy of audio array."""
        return float(np.sqrt(np.mean(audio ** 2)) + 1e-10)
