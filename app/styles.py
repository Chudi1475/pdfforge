"""Dark theme stylesheet for Chudi PDF Pro."""

# brand palette
ACCENT = "#e63946"
ACCENT_HOVER = "#f14252"
ACCENT_PRESSED = "#c92a37"
ACCENT_BLUE = "#3b82f6"
ACCENT_PURPLE = "#a855f7"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"

# surfaces
BG_DEEPEST = "#171717"
BG_BASE = "#1f1f1f"
BG_RAISED = "#262626"
BG_SURFACE = "#2b2b2b"
BG_HOVER = "#363636"
BG_ACTIVE = "#404040"
BG_CANVAS = "#535353"

# text
FG_PRIMARY = "#f5f5f5"
FG_SECONDARY = "#a3a3a3"
FG_MUTED = "#737373"
FG_DISABLED = "#525252"

BORDER = "#404040"
BORDER_SUBTLE = "#262626"

DARK_QSS = f"""
* {{ font-family: 'Segoe UI', 'Inter', 'Arial', sans-serif; font-size: 13px; color: {FG_PRIMARY}; }}

QMainWindow, QWidget {{ background: {BG_BASE}; color: {FG_PRIMARY}; }}
QDialog {{ background: {BG_SURFACE}; color: {FG_PRIMARY}; }}

/* ============== TOP BAR ============== */
QFrame#TopBar {{ background: {BG_DEEPEST}; border-bottom: 1px solid {BORDER_SUBTLE}; }}
QToolButton#TopBarBtn {{
    background: transparent; border: none; color: {FG_PRIMARY};
    padding: 6px 10px; border-radius: 4px; font-size: 13px;
}}
QToolButton#TopBarBtn:hover {{ background: {BG_HOVER}; }}
QToolButton#TopBarBtn::menu-indicator {{ image: none; }}

QFrame#DocTab {{
    background: {BG_DEEPEST}; border: 1px solid transparent; border-radius: 4px;
    padding: 0; margin: 0 2px;
}}
QFrame#DocTab:hover {{ background: {BG_RAISED}; }}
QFrame#DocTabActive {{
    background: {BG_RAISED}; border: 1px solid {BORDER}; border-radius: 4px;
    margin: 0 2px;
}}
QLabel#DocTabLabel {{ color: {FG_PRIMARY}; padding: 6px 8px 6px 0; font-size: 13px; }}
QLabel#DocTabLabelInactive {{ color: {FG_SECONDARY}; padding: 6px 8px 6px 0; }}
QToolButton#DocTabClose {{
    background: transparent; border: none; padding: 2px;
    color: {FG_SECONDARY}; border-radius: 2px; min-width: 16px; max-width: 16px;
}}
QToolButton#DocTabClose:hover {{ background: {ACCENT}; color: white; }}

QPushButton#CreateBtn {{
    background: transparent; color: {FG_PRIMARY}; border: 1px solid {BORDER};
    padding: 5px 14px; border-radius: 4px; font-weight: 500; min-width: 80px;
}}
QPushButton#CreateBtn:hover {{ background: {BG_HOVER}; }}

QLabel#Brand {{ color: {FG_PRIMARY}; font-size: 14px; font-weight: 600; }}
QLabel#BrandAccent {{ color: {ACCENT}; font-size: 14px; font-weight: 700; }}

/* ============== MODE TABS BAR ============== */
QFrame#ModeBar {{ background: {BG_BASE}; border-bottom: 1px solid {BORDER_SUBTLE}; }}
QToolButton#ModeTab {{
    background: transparent; color: {FG_SECONDARY}; border: none;
    padding: 10px 18px; font-weight: 500; font-size: 14px;
    border-bottom: 2px solid transparent;
}}
QToolButton#ModeTab:hover {{ color: {FG_PRIMARY}; }}
QToolButton#ModeTab:checked {{ color: {FG_PRIMARY}; border-bottom: 2px solid {ACCENT}; }}

QLineEdit#FindBox {{
    background: {BG_RAISED}; border: 1px solid {BORDER}; padding: 6px 10px 6px 32px;
    border-radius: 4px; min-width: 260px; color: {FG_PRIMARY};
}}
QLineEdit#FindBox:focus {{ background: {BG_SURFACE}; border: 1px solid {ACCENT}; }}

QPushButton#ShareBtn {{
    background: {BG_RAISED}; color: {FG_PRIMARY}; border: 1px solid {BORDER};
    padding: 6px 18px; border-radius: 4px; font-weight: 600; min-width: 80px;
}}
QPushButton#ShareBtn:hover {{ background: {BG_HOVER}; }}

QPushButton#AskAiBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT}, stop:0.5 #d946ef, stop:1 #8b5cf6);
    color: white; border: none; padding: 7px 16px;
    border-radius: 18px; font-weight: 600; min-width: 130px;
}}
QPushButton#AskAiBtn:hover {{ opacity: 0.92; }}

QToolButton#TopActionBtn {{
    background: transparent; border: none; color: {FG_PRIMARY};
    padding: 6px; border-radius: 4px;
}}
QToolButton#TopActionBtn:hover {{ background: {BG_HOVER}; }}

/* ============== MODE PANEL (left) ============== */
QFrame#ModePanel {{ background: {BG_BASE}; border-right: 1px solid {BORDER_SUBTLE}; }}
QLabel#ModePanelTitle {{
    color: {FG_PRIMARY}; font-size: 18px; font-weight: 500;
    padding: 14px 18px 8px 18px;
}}
QToolButton#ModePanelClose {{
    background: transparent; border: none; color: {FG_SECONDARY};
    padding: 4px; border-radius: 3px; min-width: 26px;
}}
QToolButton#ModePanelClose:hover {{ background: {BG_HOVER}; color: {FG_PRIMARY}; }}
QToolButton#GearBtn {{
    background: transparent; border: none; color: {FG_SECONDARY};
    padding: 4px; border-radius: 3px; min-width: 26px;
}}
QToolButton#GearBtn:hover {{ background: {BG_HOVER}; color: {FG_PRIMARY}; }}
QLabel#SectionHeader {{
    color: {FG_SECONDARY}; font-size: 11px; font-weight: 700;
    padding: 16px 18px 6px 18px; letter-spacing: 1.2px;
}}
QPushButton#ModeToolBtn {{
    background: transparent; color: {FG_PRIMARY}; border: none;
    text-align: left; padding: 9px 18px; font-size: 13px; font-weight: 400;
}}
QPushButton#ModeToolBtn:hover {{ background: {BG_HOVER}; }}
QPushButton#ModeToolBtn:pressed {{ background: {BG_ACTIVE}; }}
QPushButton#ModeToolBtn[selected="true"] {{ background: {BG_HOVER}; color: {ACCENT}; }}

QToolButton#IconCircle {{
    background: transparent; border: none; color: {FG_PRIMARY};
    padding: 6px; border-radius: 4px; min-width: 32px; min-height: 32px;
}}
QToolButton#IconCircle:hover {{ background: {BG_HOVER}; }}

QPushButton#MoreBtn, QPushButton#ViewLessBtn {{
    background: transparent; color: {ACCENT_BLUE}; border: none;
    text-align: left; padding: 8px 18px; font-weight: 500;
}}
QPushButton#MoreBtn:hover, QPushButton#ViewLessBtn:hover {{
    color: {ACCENT_HOVER}; text-decoration: underline;
}}

/* ============== FLOATING TOOL PALETTE ============== */
QFrame#FloatingPalette {{
    background: {BG_SURFACE}; border: 1px solid {BORDER}; border-radius: 18px;
}}
QToolButton#PaletteBtn {{
    background: transparent; border: none; color: {FG_PRIMARY};
    padding: 6px; border-radius: 4px; min-width: 34px; min-height: 34px;
}}
QToolButton#PaletteBtn:hover {{ background: {BG_HOVER}; }}
QToolButton#PaletteBtn:checked {{ background: {ACCENT_BLUE}; color: white; }}
QFrame#PaletteSep {{ background: {BORDER}; max-height: 1px; min-height: 1px; margin: 4px 6px; }}

/* ============== RIGHT RAIL ============== */
QFrame#RightRail {{ background: {BG_BASE}; border-left: 1px solid {BORDER_SUBTLE}; }}
QToolButton#RailBtn {{
    background: transparent; border: none; color: {FG_PRIMARY};
    padding: 10px 4px; border-right: 3px solid transparent;
    min-height: 40px; max-width: 44px;
}}
QToolButton#RailBtn:hover {{ background: {BG_HOVER}; }}
QToolButton#RailBtn:checked {{ background: {BG_RAISED}; color: {ACCENT}; border-right: 3px solid {ACCENT}; }}

/* ============== PAGE NAV WIDGET (corner) ============== */
QFrame#PageNav {{
    background: {BG_SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
}}
QLineEdit#PageNavInput {{
    background: transparent; border: 1px solid transparent; color: {FG_PRIMARY};
    padding: 2px; min-width: 32px; max-width: 40px; text-align: right;
}}
QLineEdit#PageNavInput:focus {{ border: 1px solid {ACCENT}; }}
QLabel#PageNavLabel {{ color: {FG_SECONDARY}; padding: 0 4px; }}
QToolButton#PageNavBtn {{
    background: transparent; border: none; color: {FG_PRIMARY};
    padding: 4px; border-radius: 3px; min-width: 26px;
}}
QToolButton#PageNavBtn:hover {{ background: {BG_HOVER}; }}

/* ============== CANVAS / SCROLL ============== */
QGraphicsView {{ background: {BG_CANVAS}; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 14px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 30px; border-radius: 4px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: {BG_ACTIVE}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 14px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; min-width: 30px; border-radius: 4px; margin: 2px; }}
QScrollBar::handle:horizontal:hover {{ background: {BG_ACTIVE}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ============== INPUTS ============== */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG_SURFACE}; color: {FG_PRIMARY}; border: 1px solid {BORDER};
    padding: 6px 8px; border-radius: 4px; selection-background-color: {ACCENT_BLUE};
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {BG_SURFACE}; color: {FG_PRIMARY};
    selection-background-color: {ACCENT}; border: 1px solid {BORDER}; padding: 4px;
}}

/* ============== BUTTONS ============== */
QPushButton {{
    background: {ACCENT_BLUE}; color: white; border: none; padding: 8px 18px;
    border-radius: 18px; font-weight: 600; min-width: 76px;
}}
QPushButton:hover {{ background: #2563eb; }}
QPushButton:pressed {{ background: #1d4ed8; }}
QPushButton:disabled {{ background: {BG_HOVER}; color: {FG_DISABLED}; }}
QPushButton#secondary {{
    background: transparent; color: {FG_PRIMARY}; border: 1px solid {BORDER};
}}
QPushButton#secondary:hover {{ background: {BG_HOVER}; }}
QPushButton#flat {{ background: transparent; color: {FG_PRIMARY}; border: none; }}
QPushButton#flat:hover {{ background: {BG_HOVER}; }}
QPushButton#danger {{ background: {ACCENT}; }}
QPushButton#danger:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#link {{ background: transparent; color: {ACCENT_BLUE}; border: none; padding: 4px; text-decoration: underline; min-width: 0; }}
QPushButton#link:hover {{ color: {ACCENT}; }}
QPushButton#PrimaryRound {{
    background: {ACCENT_BLUE}; color: white; border: none; padding: 9px 22px;
    border-radius: 20px; font-weight: 600;
}}
QPushButton#PrimaryRound:hover {{ background: #2563eb; }}

/* ============== MENUS ============== */
QMenu {{ background: {BG_SURFACE}; color: {FG_PRIMARY}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 7px 28px 7px 22px; border-radius: 3px; }}
QMenu::item:selected {{ background: {ACCENT_BLUE}; color: white; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

/* ============== CHECK / RADIO ============== */
QCheckBox, QRadioButton {{ color: {FG_PRIMARY}; spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; background: {BG_SURFACE}; border: 1px solid {BORDER};
}}
QCheckBox::indicator {{ border-radius: 3px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {ACCENT_BLUE}; border: 1px solid {ACCENT_BLUE};
}}

/* ============== GROUPS / TABS ============== */
QGroupBox {{
    color: {FG_PRIMARY}; border: 1px solid {BORDER}; border-radius: 6px;
    margin-top: 14px; padding-top: 14px; font-weight: 500;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {FG_SECONDARY}; }}

QTabWidget::pane {{ border: 1px solid {BORDER}; background: {BG_BASE}; border-radius: 4px; }}
QTabWidget QTabBar::tab {{
    background: {BG_SURFACE}; color: {FG_SECONDARY}; padding: 8px 18px;
    border: 1px solid {BORDER}; border-bottom: none; min-width: 0;
    border-top-left-radius: 4px; border-top-right-radius: 4px;
}}
QTabWidget QTabBar::tab:selected {{ background: {BG_BASE}; color: {FG_PRIMARY}; border-bottom: 1px solid {BG_BASE}; }}

QProgressBar {{ background: {BG_SURFACE}; border: 1px solid {BORDER}; border-radius: 4px; text-align: center; color: {FG_PRIMARY}; height: 18px; }}
QProgressBar::chunk {{ background: {ACCENT_BLUE}; border-radius: 3px; }}

/* ============== STATUS / LISTS ============== */
QStatusBar {{ background: {BG_DEEPEST}; color: {FG_SECONDARY}; border-top: 1px solid {BORDER_SUBTLE}; }}
QStatusBar QLabel {{ color: {FG_SECONDARY}; padding: 0 8px; }}

QListWidget {{ background: {BG_SURFACE}; color: {FG_PRIMARY}; border: none; outline: 0; padding: 6px; }}
QListWidget::item {{ background: transparent; padding: 6px; margin: 3px; border-radius: 6px; border: 2px solid transparent; }}
QListWidget::item:selected {{ background: {BG_RAISED}; border: 2px solid {ACCENT}; }}
QListWidget::item:hover {{ background: {BG_HOVER}; }}

QSplitter::handle {{ background: {BORDER_SUBTLE}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}

/* ============== HOME SCREEN ============== */
QFrame#HomeRoot {{ background: {BG_BASE}; }}
QLabel#HomeTitle {{ color: {FG_PRIMARY}; font-size: 32px; font-weight: 300; }}
QLabel#HomeSubtitle {{ color: {FG_SECONDARY}; font-size: 14px; }}
QPushButton#PrimaryCTA {{
    background: {ACCENT_BLUE}; color: white; border: none; padding: 14px 28px;
    border-radius: 22px; font-size: 14px; font-weight: 600; min-width: 200px;
}}
QPushButton#PrimaryCTA:hover {{ background: #2563eb; }}
QPushButton#RecentCard {{
    background: {BG_SURFACE}; color: {FG_PRIMARY}; border: 1px solid {BORDER};
    text-align: left; padding: 12px 16px; border-radius: 8px; font-weight: 500;
}}
QPushButton#RecentCard:hover {{ background: {BG_HOVER}; border: 1px solid {ACCENT_BLUE}; }}
QPushButton#QuickAction {{
    background: {BG_SURFACE}; color: {FG_PRIMARY}; border: 1px solid {BORDER};
    padding: 18px; border-radius: 8px; text-align: center; font-weight: 600;
    min-width: 160px; min-height: 80px;
}}
QPushButton#QuickAction:hover {{ background: {BG_HOVER}; border: 1px solid {ACCENT}; }}
QLabel#ToolGroupHeader {{
    color: {FG_SECONDARY}; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px; padding: 14px 0 6px 0;
}}

/* ============== AI ASSISTANT PANEL ============== */
QFrame#AiPanel {{ background: {BG_RAISED}; border-top: 1px solid {BORDER_SUBTLE}; }}
QLabel#AiTitle {{
    color: {FG_PRIMARY}; font-weight: 600; padding: 6px 12px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 transparent, stop:1 transparent);
}}
QLineEdit#AiInput {{
    background: {BG_SURFACE}; border: 1px solid {BORDER}; color: {FG_PRIMARY};
    padding: 10px 14px; border-radius: 22px; min-height: 24px; font-size: 13px;
}}
QLineEdit#AiInput:focus {{ border: 1px solid {ACCENT}; }}
QPushButton#AiSubmit {{
    background: {ACCENT_BLUE}; color: white; border: none;
    padding: 8px 14px; border-radius: 18px; font-weight: 600;
}}
QPushButton#AiSubmit:hover {{ background: #2563eb; }}
QPushButton#AiSuggestion {{
    background: transparent; color: {FG_SECONDARY}; border: 1px solid {BORDER};
    padding: 6px 12px; border-radius: 14px; font-size: 12px;
}}
QPushButton#AiSuggestion:hover {{ background: {BG_HOVER}; color: {FG_PRIMARY}; }}
QTextBrowser#AiOutput {{
    background: {BG_SURFACE}; border: 1px solid {BORDER}; color: {FG_PRIMARY};
    padding: 12px; border-radius: 8px;
}}
"""
