"""Visual design system for Chudi PDF Pro - dark professional theme."""

# brand colors
ACCENT = "#e63946"       # primary brand red
ACCENT_HOVER = "#f24a57"
ACCENT_PRESSED = "#c92a37"
ACCENT_BLUE = "#2196f3"  # secondary action blue
SUCCESS = "#43a047"
WARNING = "#fb8c00"

# surfaces (dark theme)
BG_DEEPEST = "#1a1a1a"   # window chrome
BG_BASE = "#212121"      # main background
BG_RAISED = "#2b2b2b"    # toolbars
BG_SURFACE = "#323232"   # panels
BG_HOVER = "#3d3d3d"
BG_ACTIVE = "#4a4a4a"
BG_CANVAS = "#525252"    # behind PDF pages

# text
FG_PRIMARY = "#f0f0f0"
FG_SECONDARY = "#b8b8b8"
FG_MUTED = "#808080"
FG_DISABLED = "#5a5a5a"

# borders
BORDER = "#404040"
BORDER_SUBTLE = "#2d2d2d"

DARK_QSS = f"""
* {{ font-family: 'Segoe UI', 'Inter', 'Arial', sans-serif; font-size: 13px; color: {FG_PRIMARY}; }}

QMainWindow, QWidget {{ background: {BG_BASE}; color: {FG_PRIMARY}; }}
QDialog {{ background: {BG_SURFACE}; color: {FG_PRIMARY}; }}

/* ---- menu ---- */
QMenuBar {{ background: {BG_DEEPEST}; color: {FG_PRIMARY}; border-bottom: 1px solid {BORDER_SUBTLE}; padding: 2px; }}
QMenuBar::item {{ padding: 5px 12px; background: transparent; border-radius: 3px; }}
QMenuBar::item:selected {{ background: {BG_HOVER}; }}
QMenu {{ background: {BG_SURFACE}; color: {FG_PRIMARY}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 7px 28px 7px 22px; border-radius: 3px; }}
QMenu::item:selected {{ background: {ACCENT}; color: white; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

/* ---- top app bar (custom) ---- */
QFrame#TopBar {{ background: {BG_DEEPEST}; border-bottom: 1px solid {BORDER_SUBTLE}; }}
QLabel#Brand {{ color: {FG_PRIMARY}; font-size: 14px; font-weight: 600; padding: 0 8px; }}
QLabel#BrandAccent {{ color: {ACCENT}; font-size: 16px; font-weight: 700; }}

/* ---- top tab bar (document tabs) ---- */
QTabWidget::pane {{ border: none; background: {BG_BASE}; top: -1px; }}
QTabBar {{ background: {BG_DEEPEST}; qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: {BG_DEEPEST}; color: {FG_SECONDARY}; padding: 9px 16px;
    border-right: 1px solid {BORDER_SUBTLE}; min-width: 140px; max-width: 220px;
}}
QTabBar::tab:hover {{ background: {BG_RAISED}; color: {FG_PRIMARY}; }}
QTabBar::tab:selected {{ background: {BG_BASE}; color: {FG_PRIMARY}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::close-button {{
    image: none; subcontrol-position: right;
    background: transparent; border-radius: 2px;
    width: 14px; height: 14px; margin-right: 4px;
}}
QTabBar::close-button:hover {{ background: {ACCENT}; }}
QTabBar QToolButton {{ background: {BG_DEEPEST}; border: none; padding: 4px; }}
QTabBar QToolButton:hover {{ background: {BG_RAISED}; }}

/* ---- toolbar ---- */
QToolBar {{ background: {BG_RAISED}; border: none; spacing: 2px; padding: 4px 8px; border-bottom: 1px solid {BORDER_SUBTLE}; }}
QToolBar QToolButton {{
    background: transparent; color: {FG_PRIMARY}; border: 1px solid transparent;
    padding: 6px 10px; border-radius: 4px; font-weight: 500; min-width: 28px;
}}
QToolBar QToolButton:hover {{ background: {BG_HOVER}; border: 1px solid {BORDER}; }}
QToolBar QToolButton:checked {{ background: {ACCENT}; color: white; border: 1px solid {ACCENT}; }}
QToolBar QToolButton:pressed {{ background: {ACCENT_PRESSED}; }}
QToolBar QToolButton:disabled {{ color: {FG_DISABLED}; }}
QToolBar::separator {{ background: {BORDER}; width: 1px; margin: 6px 6px; }}

/* ---- left icon rail ---- */
QFrame#NavRail {{ background: {BG_DEEPEST}; border-right: 1px solid {BORDER_SUBTLE}; }}
QToolButton#RailButton {{
    background: transparent; border: none; color: {FG_SECONDARY};
    padding: 12px 8px; border-left: 3px solid transparent;
    text-align: center; font-size: 11px;
}}
QToolButton#RailButton:hover {{ background: {BG_RAISED}; color: {FG_PRIMARY}; }}
QToolButton#RailButton:checked {{
    background: {BG_BASE}; color: {ACCENT}; border-left: 3px solid {ACCENT};
}}

/* ---- side panels ---- */
QFrame#SidePanel {{ background: {BG_SURFACE}; border-right: 1px solid {BORDER_SUBTLE}; }}
QLabel#PanelTitle {{
    color: {FG_PRIMARY}; font-size: 12px; font-weight: 600;
    padding: 10px 12px; background: {BG_RAISED}; border-bottom: 1px solid {BORDER_SUBTLE};
    text-transform: uppercase; letter-spacing: 0.5px;
}}

/* ---- right tools pane ---- */
QFrame#ToolsPane {{ background: {BG_SURFACE}; border-left: 1px solid {BORDER_SUBTLE}; }}
QScrollArea#ToolsScroll {{ background: {BG_SURFACE}; border: none; }}
QScrollArea#ToolsScroll > QWidget > QWidget {{ background: {BG_SURFACE}; }}
QPushButton#ToolCard {{
    background: {BG_RAISED}; color: {FG_PRIMARY}; border: 1px solid {BORDER_SUBTLE};
    text-align: left; padding: 12px 14px; border-radius: 6px;
    font-size: 13px; font-weight: 500;
}}
QPushButton#ToolCard:hover {{ background: {BG_HOVER}; border: 1px solid {ACCENT}; }}
QPushButton#ToolCard:pressed {{ background: {BG_ACTIVE}; }}
QLabel#ToolGroupHeader {{
    color: {FG_SECONDARY}; font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.8px;
    padding: 14px 12px 6px 12px;
}}

/* ---- thumbnails sidebar ---- */
QListWidget {{ background: {BG_SURFACE}; color: {FG_PRIMARY}; border: none; outline: 0; padding: 6px; }}
QListWidget::item {{ background: transparent; padding: 6px; margin: 3px; border-radius: 6px; border: 2px solid transparent; }}
QListWidget::item:selected {{ background: {BG_RAISED}; border: 2px solid {ACCENT}; }}
QListWidget::item:hover {{ background: {BG_HOVER}; }}

/* ---- scrollbars ---- */
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 30px; border-radius: 4px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: {BG_ACTIVE}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; min-width: 30px; border-radius: 4px; margin: 2px; }}
QScrollBar::handle:horizontal:hover {{ background: {BG_ACTIVE}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---- inputs ---- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG_BASE}; color: {FG_PRIMARY}; border: 1px solid {BORDER};
    padding: 6px 8px; border-radius: 4px; selection-background-color: {ACCENT};
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {BG_SURFACE}; color: {FG_PRIMARY}; selection-background-color: {ACCENT};
    border: 1px solid {BORDER}; padding: 4px;
}}

/* ---- buttons ---- */
QPushButton {{
    background: {ACCENT}; color: white; border: none; padding: 8px 18px;
    border-radius: 4px; font-weight: 600; min-width: 76px;
}}
QPushButton:hover {{ background: {ACCENT_HOVER}; }}
QPushButton:pressed {{ background: {ACCENT_PRESSED}; }}
QPushButton:disabled {{ background: {BG_HOVER}; color: {FG_DISABLED}; }}
QPushButton#secondary {{ background: {BG_HOVER}; color: {FG_PRIMARY}; }}
QPushButton#secondary:hover {{ background: {BG_ACTIVE}; }}
QPushButton#flat {{ background: transparent; color: {FG_PRIMARY}; }}
QPushButton#flat:hover {{ background: {BG_HOVER}; }}
QPushButton#danger {{ background: {ACCENT}; }}
QPushButton#danger:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#link {{
    background: transparent; color: {ACCENT_BLUE}; padding: 4px;
    text-decoration: underline; min-width: 0;
}}
QPushButton#link:hover {{ color: {ACCENT}; }}

/* ---- checkbox / radio ---- */
QCheckBox, QRadioButton {{ color: {FG_PRIMARY}; spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; background: {BG_BASE}; border: 1px solid {BORDER};
}}
QCheckBox::indicator {{ border-radius: 3px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}

/* ---- labels / groupbox ---- */
QLabel {{ color: {FG_PRIMARY}; }}
QGroupBox {{
    color: {FG_PRIMARY}; border: 1px solid {BORDER}; border-radius: 6px;
    margin-top: 14px; padding-top: 14px; font-weight: 500;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {FG_SECONDARY}; }}

/* ---- tabs in dialogs ---- */
QTabWidget#DialogTabs::pane {{ border: 1px solid {BORDER}; background: {BG_BASE}; border-radius: 4px; }}
QTabWidget#DialogTabs QTabBar::tab {{
    background: {BG_SURFACE}; color: {FG_SECONDARY}; padding: 8px 18px;
    border: 1px solid {BORDER}; border-bottom: none; min-width: 0;
    border-top-left-radius: 4px; border-top-right-radius: 4px;
}}
QTabWidget#DialogTabs QTabBar::tab:selected {{ background: {BG_BASE}; color: {FG_PRIMARY}; border-bottom: 1px solid {BG_BASE}; }}

/* ---- progress ---- */
QProgressBar {{ background: {BG_BASE}; border: 1px solid {BORDER}; border-radius: 4px; text-align: center; color: {FG_PRIMARY}; height: 18px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}

/* ---- slider ---- */
QSlider::groove:horizontal {{ background: {BG_HOVER}; height: 4px; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}

/* ---- status bar ---- */
QStatusBar {{ background: {BG_DEEPEST}; color: {FG_SECONDARY}; border-top: 1px solid {BORDER_SUBTLE}; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {FG_SECONDARY}; padding: 0 8px; }}

/* ---- dock widgets (hidden — using custom panels instead) ---- */
QDockWidget {{ color: {FG_PRIMARY}; }}
QDockWidget::title {{ background: {BG_RAISED}; padding: 6px; }}

/* ---- splitter ---- */
QSplitter::handle {{ background: {BORDER_SUBTLE}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}

/* ---- home screen ---- */
QFrame#HomeRoot {{ background: {BG_BASE}; }}
QLabel#HomeTitle {{ color: {FG_PRIMARY}; font-size: 32px; font-weight: 300; }}
QLabel#HomeSubtitle {{ color: {FG_SECONDARY}; font-size: 14px; }}
QPushButton#PrimaryCTA {{
    background: {ACCENT}; color: white; border: none; padding: 14px 28px;
    border-radius: 6px; font-size: 14px; font-weight: 600; min-width: 200px;
}}
QPushButton#PrimaryCTA:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#RecentCard {{
    background: {BG_SURFACE}; color: {FG_PRIMARY}; border: 1px solid {BORDER};
    text-align: left; padding: 12px 16px; border-radius: 8px; font-weight: 500;
}}
QPushButton#RecentCard:hover {{ background: {BG_HOVER}; border: 1px solid {ACCENT}; }}
QPushButton#QuickAction {{
    background: {BG_SURFACE}; color: {FG_PRIMARY}; border: 1px solid {BORDER};
    padding: 18px; border-radius: 8px; text-align: center; font-weight: 600;
    min-width: 160px; min-height: 80px;
}}
QPushButton#QuickAction:hover {{ background: {BG_HOVER}; border: 1px solid {ACCENT}; }}
QPushButton#QuickAction:pressed {{ background: {BG_ACTIVE}; }}

/* ---- properties strip (contextual bar) ---- */
QFrame#PropertyStrip {{ background: {BG_RAISED}; border-bottom: 1px solid {BORDER_SUBTLE}; min-height: 36px; }}
QFrame#PropertyStrip QLabel {{ color: {FG_SECONDARY}; padding: 0 4px; }}
QFrame#PropertyStrip QToolButton {{
    background: transparent; color: {FG_PRIMARY}; border: 1px solid transparent;
    padding: 4px 8px; border-radius: 3px;
}}
QFrame#PropertyStrip QToolButton:hover {{ background: {BG_HOVER}; }}
QFrame#PropertyStrip QToolButton:checked {{ background: {ACCENT}; color: white; }}

/* ---- search bar ---- */
QLineEdit#TopSearch {{
    background: {BG_RAISED}; border: 1px solid {BORDER}; padding: 6px 10px 6px 28px;
    border-radius: 4px; min-width: 280px;
}}
QLineEdit#TopSearch:focus {{ background: {BG_BASE}; border: 1px solid {ACCENT}; }}
"""
