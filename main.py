# -*- coding: utf-8 -*-
"""
main.py
-------
Main entry point for SpeakEasy V1 desktop application.
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
