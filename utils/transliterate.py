# -*- coding: utf-8 -*-
"""
utils/transliterate.py
----------------------
Wrapper utility linking to backend.transliteration.romanizer.
"""

from __future__ import annotations

from backend.transliteration.romanizer import transliterate_text


def format_transcript(text: str, mode: str = "roman") -> str:
    """
    Format raw ASR output for display by delegating to romanizer.

    Parameters
    ----------
    text : str
        Raw text from Whisper.
    mode : str
        "roman" — convert Devanagari to Roman Hinglish (default).
        "raw"   — return text unchanged.
    """
    return transliterate_text(text, mode=mode)
