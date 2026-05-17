"""Chudi PDF Pro entry point."""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

from app import APP_NAME, icons
from app.main_window import MainWindow
from app.styles import DARK_QSS


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Chudi")
    app.setStyle("Fusion")
    app.setWindowIcon(icons.app_logo(64))

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor("#212121"))
    pal.setColor(QPalette.WindowText, QColor("#f0f0f0"))
    pal.setColor(QPalette.Base, QColor("#2b2b2b"))
    pal.setColor(QPalette.AlternateBase, QColor("#323232"))
    pal.setColor(QPalette.ToolTipBase, QColor("#323232"))
    pal.setColor(QPalette.ToolTipText, QColor("#f0f0f0"))
    pal.setColor(QPalette.Text, QColor("#f0f0f0"))
    pal.setColor(QPalette.Button, QColor("#3d3d3d"))
    pal.setColor(QPalette.ButtonText, QColor("#f0f0f0"))
    pal.setColor(QPalette.Highlight, QColor("#e63946"))
    pal.setColor(QPalette.HighlightedText, QColor("white"))
    pal.setColor(QPalette.PlaceholderText, QColor("#808080"))
    pal.setColor(QPalette.Link, QColor("#2196f3"))
    app.setPalette(pal)
    app.setStyleSheet(DARK_QSS)

    w = MainWindow()
    w.show()

    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".pdf"):
        w.load_pdf(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
