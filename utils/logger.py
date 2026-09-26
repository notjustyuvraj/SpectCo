# -*- coding: utf-8 -*-
"""
utils/logger.py
---------------
Centralised logging for SpeakEasy V1.

Usage:
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Whisper model loaded.")
    log.error("Microphone failed: %s", exc)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Log file lives next to the package root.
_LOG_PATH = Path(__file__).parent.parent / "speakeasy.log"

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return

    root = logging.getLogger("speakeasy")
    root.setLevel(logging.DEBUG)

    # -------------------------------------------------------------------------
    # Console handler — INFO and above, human-readable.
    # -------------------------------------------------------------------------
    # Ensure stdout handles UTF-8 on Windows without throwing UnicodeEncodeError
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter(
            fmt="[%(levelname)s] %(name)s: %(message)s",
        )
    )
    root.addHandler(console)

    # -------------------------------------------------------------------------
    # File handler — DEBUG and above, with timestamps.
    # Rotates at 2 MB, keeps 3 backups so the log stays small.
    # -------------------------------------------------------------------------
    file_handler = RotatingFileHandler(
        _LOG_PATH,
        maxBytes=2 * 1024 * 1024,   # 2 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the 'speakeasy' root.

    Pass __name__ as the argument so log lines show the module.
    """
    _configure()
    # Strip leading package paths for cleaner names.
    short = name.replace("speakeasy.", "")
    return logging.getLogger(f"speakeasy.{short}")
