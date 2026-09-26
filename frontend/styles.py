# -*- coding: utf-8 -*-
"""
frontend/styles.py
------------------
All Qt StyleSheet (QSS) strings for SpeakEasy V1.

Keeping styles here means designers can tweak colours / sizes without
touching any logic code.
"""

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

C_BG          = "#0a0a14"
C_BG_CARD     = "#0d0d1a"
C_BG_ELEM     = "#1a1a2e"
C_BG_ELEM2    = "#1e1e2e"
C_BORDER      = "#2d2d3d"
C_ACCENT      = "#a78bfa"   # purple — primary accent
C_ACCENT_DARK = "#7c3aed"
C_CYAN        = "#06b6d4"
C_GREEN       = "#22c55e"
C_RED         = "#ef4444"
C_YELLOW      = "#facc15"
C_TEXT        = "#e8e8f0"
C_TEXT_DIM    = "#64748b"
C_TEXT_MID    = "#94a3b8"

FONT_STACK = "'Noto Sans Devanagari', 'Nirmala UI', 'Mangal', sans-serif"

# ---------------------------------------------------------------------------
# Application-level stylesheet
# ---------------------------------------------------------------------------

APP_STYLE = f"""
QMainWindow,
QWidget#MAIN {{
    background: {C_BG};
}}

QStatusBar {{
    background: {C_BG_CARD};
    color: {C_TEXT_DIM};
    font-size: 10px;
}}

QSplitter::handle {{
    background: {C_BG_ELEM2};
    width: 2px;
}}
"""

# ---------------------------------------------------------------------------
# Sidebar stylesheet
# ---------------------------------------------------------------------------

SIDEBAR_STYLE = f"""
QWidget {{
    background: transparent;
}}

QGroupBox {{
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    margin-top: 6px;
    padding-top: 4px;
    color: {C_ACCENT};
    font-size: 11px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 6px;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {C_BORDER};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    background: {C_ACCENT};
    border-radius: 7px;
    margin: -5px 0;
}}

QSlider::sub-page:horizontal {{
    background: {C_ACCENT_DARK};
    border-radius: 2px;
}}

QSpinBox {{
    background: {C_BG_ELEM};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 2px 6px;
}}

QProgressBar {{
    background: {C_BG_ELEM};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    color: {C_TEXT};
}}

QProgressBar::chunk {{
    background: {C_ACCENT_DARK};
    border-radius: 6px;
}}

QPushButton {{
    background: {C_BG_ELEM2};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 6px;
    font-size: 11px;
}}

QPushButton:hover {{
    background: {C_BORDER};
    border-color: {C_ACCENT_DARK};
}}

QPushButton:pressed {{
    background: {C_ACCENT_DARK};
}}

QCheckBox {{
    color: {C_TEXT};
    font-size: 11px;
}}
"""


# ---------------------------------------------------------------------------
# Badge helper
# ---------------------------------------------------------------------------

def badge_style(bg: str, fg: str) -> str:
    return (
        f"background:{bg};"
        f"color:{fg};"
        f"border:1px solid {fg};"
        "border-radius:4px;"
        "padding:2px 8px;"
        "font-size:10px;"
        "font-weight:bold;"
    )


MIC_LIVE_STYLE  = badge_style("#003f1a", C_GREEN)
MIC_MUTED_STYLE = badge_style("#3f0000", C_RED)

# ---------------------------------------------------------------------------
# Mute button
# ---------------------------------------------------------------------------

def mute_button_style(muted: bool) -> str:
    color = C_RED if muted else C_GREEN
    bg    = "#3f0000" if muted else "#003f1a"
    return (
        f"QPushButton {{"
        f"background:{bg};"
        f"color:{color};"
        f"border:1px solid {color};"
        "border-radius:6px;"
        "padding:8px;"
        "font-size:12px;"
        "font-weight:bold;"
        "}"
    )


# ---------------------------------------------------------------------------
# Transcript panel
# ---------------------------------------------------------------------------

def panel_style(border_color: str, opacity: float, font_size: int) -> str:
    alpha = int(opacity * 255)
    return f"""
    #PANEL {{
        background: rgba(15, 15, 25, {alpha});
        border: 1px solid {border_color};
        border-radius: 10px;
    }}
    #HEADER {{
        color: {border_color};
        font-size: 11px;
        font-weight: bold;
        font-family: {FONT_STACK};
        padding: 2px;
    }}
    #TEXT {{
        background: transparent;
        color: {C_TEXT};
        font-size: {font_size}px;
        font-family: {FONT_STACK};
        border: none;
    }}
    """
