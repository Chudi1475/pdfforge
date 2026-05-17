"""Dark theme stylesheet for the app."""

DARK_QSS = """
* { font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
QMainWindow, QDialog { background: #1e1e1e; color: #e0e0e0; }
QWidget { background: #1e1e1e; color: #e0e0e0; }
QMenuBar { background: #252526; color: #d4d4d4; border-bottom: 1px solid #333; }
QMenuBar::item { padding: 6px 12px; background: transparent; }
QMenuBar::item:selected { background: #094771; }
QMenu { background: #252526; color: #d4d4d4; border: 1px solid #3c3c3c; }
QMenu::item { padding: 6px 24px; }
QMenu::item:selected { background: #094771; }
QMenu::separator { height: 1px; background: #3c3c3c; margin: 4px 0; }
QToolBar { background: #2d2d30; border: none; spacing: 4px; padding: 4px; }
QToolBar QToolButton {
    background: transparent; color: #d4d4d4; border: 1px solid transparent;
    padding: 5px 10px; border-radius: 4px; font-weight: 500;
}
QToolBar QToolButton:hover { background: #3e3e42; border: 1px solid #555; }
QToolBar QToolButton:checked { background: #094771; border: 1px solid #0a84ff; }
QToolBar QToolButton:pressed { background: #1a5a91; }
QToolBar::separator { background: #3c3c3c; width: 1px; margin: 4px 6px; }
QStatusBar { background: #007acc; color: white; }
QStatusBar::item { border: none; }
QDockWidget { color: #d4d4d4; }
QDockWidget::title { background: #2d2d30; padding: 6px; text-align: left; border-bottom: 1px solid #333; }
QListWidget { background: #252526; color: #d4d4d4; border: none; outline: 0; padding: 4px; }
QListWidget::item { background: transparent; padding: 4px; margin: 2px; border-radius: 4px; border: 2px solid transparent; }
QListWidget::item:selected { background: #094771; border: 2px solid #0a84ff; }
QListWidget::item:hover { background: #2a2d2e; }
QScrollBar:vertical { background: #1e1e1e; width: 14px; margin: 0; }
QScrollBar::handle:vertical { background: #424242; min-height: 30px; border-radius: 4px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #4e4e4e; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #1e1e1e; height: 14px; margin: 0; }
QScrollBar::handle:horizontal { background: #424242; min-width: 30px; border-radius: 4px; margin: 2px; }
QScrollBar::handle:horizontal:hover { background: #4e4e4e; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QPushButton {
    background: #0e639c; color: white; border: none; padding: 7px 16px;
    border-radius: 4px; font-weight: 500;
}
QPushButton:hover { background: #1177bb; }
QPushButton:pressed { background: #094771; }
QPushButton:disabled { background: #3c3c3c; color: #888; }
QPushButton#secondary { background: #3c3c3c; color: #d4d4d4; }
QPushButton#secondary:hover { background: #4e4e4e; }
QPushButton#danger { background: #b51d2a; }
QPushButton#danger:hover { background: #d62a39; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #3c3c3c; color: #e0e0e0; border: 1px solid #555;
    padding: 5px; border-radius: 4px; selection-background-color: #094771;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #0a84ff; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background: #2d2d30; color: #d4d4d4; selection-background-color: #094771; border: 1px solid #555; }
QCheckBox { color: #d4d4d4; spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; background: #3c3c3c; border: 1px solid #555; border-radius: 3px; }
QCheckBox::indicator:checked { background: #0a84ff; border: 1px solid #0a84ff; }
QLabel { color: #d4d4d4; }
QGroupBox { color: #d4d4d4; border: 1px solid #3c3c3c; border-radius: 4px; margin-top: 10px; padding-top: 10px; font-weight: 500; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
QTabWidget::pane { border: 1px solid #3c3c3c; background: #1e1e1e; }
QTabBar::tab { background: #2d2d30; color: #d4d4d4; padding: 8px 16px; border: 1px solid #3c3c3c; }
QTabBar::tab:selected { background: #1e1e1e; border-bottom: 2px solid #0a84ff; }
QSlider::groove:horizontal { background: #3c3c3c; height: 4px; border-radius: 2px; }
QSlider::handle:horizontal { background: #0a84ff; width: 14px; margin: -5px 0; border-radius: 7px; }
QProgressBar { background: #3c3c3c; border: none; border-radius: 4px; text-align: center; color: white; }
QProgressBar::chunk { background: #0a84ff; border-radius: 4px; }
"""
