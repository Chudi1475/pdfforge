"""PDFForge entry point."""
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.styles import DARK_QSS


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PDFForge")
    app.setOrganizationName("PDFForge")
    app.setStyle("Fusion")

    # palette (covers areas not styled by QSS)
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(30, 30, 30))
    pal.setColor(QPalette.WindowText, QColor(224, 224, 224))
    pal.setColor(QPalette.Base, QColor(37, 37, 38))
    pal.setColor(QPalette.AlternateBase, QColor(45, 45, 48))
    pal.setColor(QPalette.ToolTipBase, QColor(45, 45, 48))
    pal.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
    pal.setColor(QPalette.Text, QColor(224, 224, 224))
    pal.setColor(QPalette.Button, QColor(60, 60, 60))
    pal.setColor(QPalette.ButtonText, QColor(224, 224, 224))
    pal.setColor(QPalette.Highlight, QColor(9, 71, 113))
    pal.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    pal.setColor(QPalette.PlaceholderText, QColor(140, 140, 140))
    app.setPalette(pal)
    app.setStyleSheet(DARK_QSS)

    w = MainWindow()
    w.show()

    # open file passed on the cli
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".pdf"):
        w.load_pdf(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
