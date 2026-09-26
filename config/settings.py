# -*- coding: utf-8 -*-
"""
config/settings.py
------------------
Centralized configuration for SpeakEasy V1.

Tuning guide (quick reference):
  ASR_MODEL      : "tiny" (fastest, lowest accuracy) → "small" → "medium" (slowest, best)
  ACCUM_SECS     : Larger = fewer ASR calls, more latency. 5.5s is the sweet spot for small/CPU.
  BEAM_SIZE      : 1 = greedy (faster, more errors). 5 = beam search (best WER, ~30% more CPU).
  VAD_THRESHOLD  : 0.0–1.0 — higher = only send audio when speech is clearly present.
  CPU_THREADS    : CTranslate2 threads. 4 is ideal for 12-core machines (leaves OS/UI headroom).
"""

import os

# ---------------------------------------------------------------------------
# Audio capture
# ---------------------------------------------------------------------------
SAMPLE_RATE: int = 16_000        # Whisper requires 16 kHz mono
BLOCK_SIZE:  int = 4_800         # ~300 ms per sounddevice callback chunk

# ---------------------------------------------------------------------------
# Accumulation & VAD gate (pre-ASR)
# ---------------------------------------------------------------------------
# How many seconds of audio to collect before sending to ASR.
# Must be large enough that ASR finishes before the next buffer arrives.
# For "small" on CPU: inference ≈ 3-4 s for a 5.5 s buffer. Safe margin.
ACCUM_SECS: float = 5.5

# RMS energy threshold below which a completed buffer is NOT sent to ASR.
# This is the primary CPU saver — don't call Whisper during silence.
# Typical mic noise floor: 0.001–0.003. Speech: 0.01+.
VAD_RMS_THRESHOLD: float = 0.008

# Minimum fraction of "voiced" chunks needed in an accumulated buffer
# before sending to ASR. A chunk is "voiced" if its RMS > VAD_RMS_THRESHOLD.
# 0.10 = at least 10% of chunks must be speech (prevents sending mostly-silent buffers).
VAD_VOICED_FRACTION: float = 0.10

# ---------------------------------------------------------------------------
# ASR model
# ---------------------------------------------------------------------------
ASR_MODEL:    str      = "small"  # Multilingual model — do NOT use small.en
ASR_LANGUAGE: str | None = None   # None = auto-detect (best for Hindi/English/Hinglish mix)
COMPUTE_TYPE: str      = "int8"   # int8 = fastest CPU quantisation with minimal WER loss
CPU_THREADS:  int      = 4        # CTranslate2 beam threads (4 optimal for 12-core CPU)

# Beam size — critical WER vs CPU tradeoff:
#   1 = greedy decode, fastest, ~15-20% higher WER on Hinglish
#   5 = beam search, ~30% more CPU, significantly lower WER  ← recommended
BEAM_SIZE: int = 5

# No-speech probability threshold. If Whisper's internal VAD assigns a
# higher no-speech probability than this, the segment is silently dropped.
NO_SPEECH_THRESHOLD: float = 0.6

# ---------------------------------------------------------------------------
# Output mode
# ---------------------------------------------------------------------------
OUTPUT_MODE: str = "roman"   # "roman" = Devanagari→Roman, "raw" = unchanged

# ---------------------------------------------------------------------------
# UI defaults
# ---------------------------------------------------------------------------
DEFAULT_FONT_SIZE: int   = 14
DEFAULT_OPACITY:   float = 0.70
WINDOW_WIDTH:      int   = 1100
WINDOW_HEIGHT:     int   = 700
