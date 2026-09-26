# -*- coding: utf-8 -*-
"""
backend/asr/engine.py
---------------------
Offline Speech-to-Text using faster-whisper (CTranslate2).

Design decisions:
  - task="transcribe"     — never translate, always preserve spoken words
  - language=None         — auto-detect enables correct Hindi/English/Hinglish handling
  - beam_size=5           — beam search substantially reduces WER vs greedy
  - no_speech_threshold   — Whisper's internal VAD skips silent segments early
  - condition_on_previous_text=False — prevents hallucination/repetition loops
  - without_timestamps=True — saves ~10% CPU (no timestamp decoding)
"""

from __future__ import annotations

import numpy as np
from config import settings
from backend.transliteration.romanizer import transliterate_text
from utils.logger import get_logger

log = get_logger(__name__)

# Realistic exemplar sentences showing Hinglish + English target output (NOT meta-instructions).
# Giving real sentences guides Whisper's LM toward emitting Romanized Hindi / English directly.
_INITIAL_PROMPT = (
    "Mera naam Yuvraj hai. Main kal office nahi aunga. "
    "Sir, I need two days to complete this project meeting."
)

_HALLUCINATION_PHRASES = {
    "hinglish only",
    "write hindi words in english",
    "write hindi words in english letters",
    "hinglish hindi and hinglish only",
    "subtitles by",
    "thank you for watching",
    "thanks for watching",
    "subscribe to my channel",
    "please like and subscribe",
    "all is well. thank you very much. bye",
    "learn of the peace",
    "see you in a second",
}


def _is_hallucination_or_repetition(text: str) -> bool:
    """Return True if text is a known hallucination phrase or repetitive sequence."""
    clean = text.strip().lower().rstrip(".!?,")
    if clean in _HALLUCINATION_PHRASES:
        return True

    words = clean.split()
    if len(words) >= 4:
        # If >60% of words are identical to the first word (e.g. "aap aap aap aap...")
        first = words[0]
        if words.count(first) / len(words) > 0.6:
            return True

    return False


class ASREngine:
    """
    Offline Speech-to-Text engine using faster-whisper (CTranslate2).
    """

    def __init__(
        self,
        model_size:   str       = settings.ASR_MODEL,
        language:     str | None = settings.ASR_LANGUAGE,
        compute_type: str       = settings.COMPUTE_TYPE,
        cpu_threads:  int       = settings.CPU_THREADS,
        output_mode:  str       = settings.OUTPUT_MODE,
    ) -> None:
        self._language    = language
        self._output_mode = output_mode
        self._model       = None

        log.info("Loading faster-whisper '%s' [%s, threads=%d]...",
                 model_size, compute_type, cpu_threads)
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                model_size,
                device="cpu",
                compute_type=compute_type,
                cpu_threads=cpu_threads,
                # num_workers=1: single decode worker — lower peak RAM,
                # enough throughput for our single-buffer async pipeline.
                num_workers=1,
            )
            log.info("ASR engine ready.")
        except ImportError:
            log.error("faster-whisper not installed. Run: pip install faster-whisper")
        except Exception:
            log.exception("Failed to load ASR model.")

    @property
    def ready(self) -> bool:
        return self._model is not None

    def transcribe(self, audio: np.ndarray) -> str | None:
        """
        Transcribe a 16 kHz mono float32 buffer.

        Returns the formatted text, or None if audio was silent / too short.
        """
        if self._model is None:
            return None

        # --- Sanitise ---------------------------------------------------------
        audio = np.asarray(audio, dtype=np.float32)
        audio = np.nan_to_num(audio, nan=0.0, posinf=1.0, neginf=-1.0)
        audio = np.clip(audio, -1.0, 1.0)

        if audio.size < 1600:          # < 100 ms — skip unconditionally
            return None

        # --- RMS gate (fast path, avoids calling CTranslate2 on silence) -----
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < settings.VAD_RMS_THRESHOLD:
            return None

        # --- Peak normalise to 0.95 ------------------------------------------
        peak = float(np.max(np.abs(audio)))
        if peak < 1e-4:
            return None
        audio = audio * (0.95 / peak)

        # --- Whisper inference -----------------------------------------------
        try:
            segments, info = self._model.transcribe(
                audio,
                language=self._language,          # None = auto-detect
                task="transcribe",                # NEVER translate
                beam_size=settings.BEAM_SIZE,     # 5 = best WER on CPU
                initial_prompt=_INITIAL_PROMPT,
                vad_filter=True,                  # Whisper built-in VAD
                vad_parameters={
                    "threshold": 0.5,             # Silero VAD sensitivity
                    "min_silence_duration_ms": 400,
                    "speech_pad_ms": 200,          # pad around speech edges
                },
                no_speech_threshold=settings.NO_SPEECH_THRESHOLD,
                compression_ratio_threshold=2.4,  # Filter repetitive loops
                log_prob_threshold=-1.0,          # Filter low confidence output
                hallucination_silence_threshold=0.5, # Filter silence hallucinations
                temperature=0.0,                  # deterministic output
                condition_on_previous_text=False, # prevents repetition loops
                without_timestamps=True,          # saves ~10% CPU
            )

            # Consume generator and filter by no-speech probability
            parts: list[str] = []
            for seg in segments:
                # Skip segments Whisper itself thinks are not speech
                if hasattr(seg, "no_speech_prob") and seg.no_speech_prob > settings.NO_SPEECH_THRESHOLD:
                    continue
                text = seg.text.strip()
                if text and not _is_hallucination_or_repetition(text):
                    parts.append(text)

            if not parts:
                return None

            raw = " ".join(parts)
            if _is_hallucination_or_repetition(raw):
                return None

            return transliterate_text(raw, mode=self._output_mode)

        except Exception:
            log.exception("ASR transcription error.")
            return None
