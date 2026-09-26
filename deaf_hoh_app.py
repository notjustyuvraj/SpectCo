# -*- coding: utf-8 -*-
"""
deaf_hoh_app.py
---------------
Backwards compatibility entry point launching SpeakEasy V1.
"""

import sys
from PyQt6.QtWidgets import QApplication
from frontend.main_window import SpeakEasyWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = SpeakEasyWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()