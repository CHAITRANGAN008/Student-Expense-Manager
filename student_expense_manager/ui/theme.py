from __future__ import annotations

from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"

PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "name": "dark",
        "bg": "#1C183B",
        "bg_alt": "#1F1A42",
        "sidebar": "#15112F",
        "surface": "#241F4D",
        "surface2": "#2A2456",
        "surface3": "#322A62",
        "card_top": "#282250",
        "card_bottom": "#201B45",
        "border": "#393160",
        "border_soft": "#302A58",
        "text": "#F4F2FF",
        "muted": "#B9B3D8",
        "dim": "#857DAE",
        "accent": "#7C5CFF",
        "accent_soft": "#9B85FF",
        "accent2": "#4F7CFF",
        "accent3": "#38BDF8",
        "success": "#34D399",
        "warning": "#FBBF24",
        "danger": "#FB7185",
        "income": "#34D399",
        "expense": "#FB7185",
        "violet_tint": "#2A2456",
        "blue_tint": "#1F2850",
        "green_tint": "#163B34",
        "red_tint": "#402034",
        "amber_tint": "#40311C",
        "chart_grid": "#393160",
        "selection": "#3A3168",
        "input": "#1F1A42",
        "shadow": "#100C24",
    },
    "light": {
        "name": "light",
        "bg": "#F5F4FB",
        "bg_alt": "#EEEBF8",
        "sidebar": "#FFFFFF",
        "surface": "#FFFFFF",
        "surface2": "#F8F7FE",
        "surface3": "#EFECFA",
        "card_top": "#FFFFFF",
        "card_bottom": "#FBF9FF",
        "border": "#E5E0F3",
        "border_soft": "#EEEAF8",
        "text": "#191434",
        "muted": "#686182",
        "dim": "#9A93B3",
        "accent": "#6D4AFF",
        "accent_soft": "#8567FF",
        "accent2": "#3B82F6",
        "accent3": "#0EA5E9",
        "success": "#0D9F6E",
        "warning": "#D97706",
        "danger": "#E11D48",
        "income": "#0D9F6E",
        "expense": "#E11D48",
        "violet_tint": "#F0EBFF",
        "blue_tint": "#E8F1FF",
        "green_tint": "#E7F8F1",
        "red_tint": "#FDEBF0",
        "amber_tint": "#FFF4DC",
        "chart_grid": "#E9E4F5",
        "selection": "#EDE7FF",
        "input": "#FFFFFF",
        "shadow": "#D9D3EC",
    },
}

_current = "dark"


def set_current_theme(name: str) -> None:
    global _current
    _current = name if name in PALETTES else "dark"


def current_theme() -> str:
    return _current


def palette(name: str | None = None) -> dict[str, str]:
    return PALETTES[name or _current]


def build_stylesheet(name: str | None = None) -> str:
    p = palette(name)
    chevron = (ASSETS / "chevron-down.svg").as_posix()
    check = (ASSETS / "check.svg").as_posix()
    arrow_up = (ASSETS / "chevron-up.svg").as_posix()

    return f"""
    * {{
        font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", Arial, sans-serif;
        outline: none;
    }}
    QWidget {{
        color: {p['text']};
        font-size: 13px;
    }}
    QMainWindow, QWidget#appRoot, QWidget#pageRoot, QWidget#scrollContent {{
        background-color: {p['bg']};
    }}
    QWidget#pageRoot {{
        background: transparent;
    }}
    QWidget#contentHost {{
        background-color: {p['bg']};
    }}
    QFrame#topBar {{
        background-color: {p['bg']};
        border-bottom: 1px solid {p['border_soft']};
    }}
    QLabel#crumb {{
        color: {p['dim']};
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel#crumbCurrent {{
        color: {p['text']};
        font-size: 11px;
        font-weight: 700;
    }}
    QLabel#topbarMeta {{
        color: {p['muted']};
        font-size: 10.5px;
        font-weight: 600;
    }}
    QFrame#topbarDivider {{
        background: {p['border']};
        border: none;
        max-width: 1px;
        min-width: 1px;
    }}
    QLineEdit#topSearch {{
        background: {p['surface2']};
        border: 1px solid {p['border_soft']};
        border-radius: 10px;
        padding: 6px 10px;
        min-height: 20px;
    }}
    QLineEdit#topSearch:focus {{
        background: {p['input']};
        border-color: {p['accent']};
    }}
    QLabel#avatar {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #7C5CFF, stop:1 #4F7CFF);
        border: 1px solid #8B6DFF;
        border-radius: 17px;
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 700;
    }}
    QLineEdit#pathField {{
        background: {p['surface2']};
        border: 1px solid {p['border_soft']};
        border-radius: 9px;
        padding: 8px 10px;
        color: {p['muted']};
        font-family: "Cascadia Mono", "Consolas", "Courier New", monospace;
        font-size: 10.5px;
    }}
    QLineEdit#pathField:focus {{
        border-color: {p['accent']};
    }}
    QStackedWidget#stack {{
        background: transparent;
    }}
    QLabel#brandTitle {{
        color: {p['text']};
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#brandSubtitle {{
        color: {p['dim']};
        font-size: 9px;
        font-weight: 600;
    }}
    QPushButton#navItem {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 10px;
        color: {p['muted']};
        padding: 8px 11px;
        text-align: left;
        font-size: 12px;
        font-weight: 600;
        min-height: 20px;
    }}
    QPushButton#navItem:hover {{
        background: {p['surface2']};
        border-color: {p['border_soft']};
        color: {p['text']};
    }}
    QPushButton#navItem:checked {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #7C5CFF, stop:1 #5F5BFF);
        border: 1px solid #8B6DFF;
        color: #FFFFFF;
    }}
    QPushButton#navItem:checked:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #8B6CFF, stop:1 #6E6AFF);
    }}
    QFrame#sidebarCard {{
        background: {p['surface2']};
        border: 1px solid {p['border_soft']};
        border-radius: 12px;
    }}
    QLabel#sidebarCardTitle {{
        color: {p['text']};
        font-size: 10.5px;
        font-weight: 600;
    }}
    QLabel#sidebarCardCaption {{
        color: {p['dim']};
        font-size: 9px;
    }}
    QLabel#sectionLabel {{
        color: {p['dim']};
        font-size: 9.5px;
        font-weight: 700;
    }}
    QLabel#insightValue {{
        color: {p['text']};
        font-size: 17px;
        font-weight: 700;
    }}
    QLabel#moneyLarge {{
        color: {p['text']};
        font-size: 21px;
        font-weight: 700;
    }}
    QLabel#errorLabel {{
        color: {p['danger']};
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel#successLabel {{
        color: {p['success']};
        font-size: 11px;
        font-weight: 600;
    }}
    QFrame#dialogCard {{
        background: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 20px;
    }}
    QDialog#framelessDialog {{
        background: transparent;
    }}
    QFrame#fieldBox {{
        background: {p['input']};
        border: 1px solid {p['border']};
        border-radius: 10px;
    }}
    QFrame#fieldBox[focused="true"] {{ border: 1px solid {p['accent']}; }}
    QFrame#softDivider {{
        background: {p['border_soft']};
        max-height: 1px;
        min-height: 1px;
        border: none;
    }}
    QFrame#heroPanel {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #2A1E63, stop:0.55 #251A57, stop:1 #171237);
        border: 1px solid {p['border']};
        border-radius: 18px;
    }}
    QLabel {{
        background: transparent;
        color: {p['text']};
    }}
    QLabel#eyebrow {{
        color: {p['accent_soft']};
        font-size: 10px;
        font-weight: 700;
    }}
    QLabel#pageTitle {{
        color: {p['text']};
        font-size: 27px;
        font-weight: 700;
    }}
    QLabel#pageSubtitle {{
        color: {p['muted']};
        font-size: 12.5px;
    }}
    QLabel#cardTitle {{
        color: {p['text']};
        font-size: 14px;
        font-weight: 700;
    }}
    QLabel#cardSubtitle, QLabel#mutedLabel {{
        color: {p['muted']};
        font-size: 11px;
    }}
    QLabel#dimLabel {{
        color: {p['dim']};
        font-size: 10.5px;
    }}
    QLabel#statLabel {{
        color: {p['muted']};
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel#statValue {{
        color: {p['text']};
        font-size: 19px;
        font-weight: 700;
    }}
    QLabel#statDelta {{
        color: {p['muted']};
        font-size: 10.5px;
    }}
    QLabel#incomeLabel {{ color: {p['income']}; }}
    QLabel#expenseLabel {{ color: {p['expense']}; }}
    QLabel#pill {{
        background: {p['surface2']};
        border: 1px solid {p['border_soft']};
        border-radius: 8px;
        padding: 2px 8px;
        font-size: 10px;
        font-weight: 700;
        color: {p['muted']};
    }}
    QLabel#pill[tone="success"] {{
        background: {p['green_tint']};
        border-color: {p['success']};
        color: {p['success']};
    }}
    QLabel#pill[tone="warning"] {{
        background: {p['amber_tint']};
        border-color: {p['warning']};
        color: {p['warning']};
    }}
    QLabel#pill[tone="danger"] {{
        background: {p['red_tint']};
        border-color: {p['danger']};
        color: {p['danger']};
    }}
    QLabel#pill[tone="accent"] {{
        background: {p['violet_tint']};
        border-color: {p['accent']};
        color: {p['accent_soft']};
    }}

    QFrame#sidebar {{
        background-color: {p['sidebar']};
        border-right: 1px solid {p['border_soft']};
    }}
    QFrame#card, QFrame#innerCard, QFrame#filterBar, QFrame#panel {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {p['card_top']}, stop:1 {p['card_bottom']});
        border: 1px solid {p['border_soft']};
        border-radius: 16px;
    }}
    QFrame#innerCard {{
        background: {p['surface2']};
        border: 1px solid {p['border_soft']};
        border-radius: 12px;
    }}
    QFrame#accentCard {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #7C5CFF, stop:0.55 #5F5BFF, stop:1 #3E7BFA);
        border: 1px solid #8B6DFF;
        border-radius: 16px;
    }}
    QFrame#alertCard {{
        border-radius: 14px;
        border: 1px solid {p['border']};
        background: {p['surface2']};
    }}
    QFrame#alertCard[tone="warning"] {{
        background: {p['amber_tint']};
        border: 1px solid #8A6420;
    }}
    QFrame#alertCard[tone="danger"] {{
        background: {p['red_tint']};
        border: 1px solid #74263E;
    }}
    QFrame#alertCard[tone="success"] {{
        background: {p['green_tint']};
        border: 1px solid #1D5A4A;
    }}
    QFrame#divider {{
        background: {p['border_soft']};
        max-height: 1px;
        border: none;
    }}
    QFrame#reminderCard {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {p['surface2']}, stop:1 {p['surface']});
        border: 1px solid {p['border_soft']};
        border-radius: 15px;
    }}
    QFrame#reminderCard[tone="due_today"] {{ border: 1px solid #8A6420; }}
    QFrame#reminderCard[tone="overdue"] {{ border: 1px solid #74263E; }}
    QFrame#reminderCard[tone="paid"] {{ border: 1px solid #1D5A4A; }}
    QFrame#reminderCard[tone="cancelled"] {{ border: 1px dashed {p['border']}; }}
    QFrame#toastCard {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #2A1E63, stop:1 #151131);
        border: 1px solid #6D4AFF;
        border-radius: 14px;
    }}
    QFrame#toastCard[tone="danger"] {{ border: 1px solid #FB7185; }}
    QFrame#toastCard[tone="warning"] {{ border: 1px solid #FBBF24; }}
    QFrame#toastCard[tone="success"] {{ border: 1px solid #34D399; }}
    QLabel#reminderHeadline {{
        color: {p['text']};
        font-size: 13px;
        font-weight: 700;
    }}

    QPushButton {{
        background: {p['surface2']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 10px;
        padding: 8px 14px;
        font-weight: 600;
        min-height: 18px;
    }}
    QPushButton:hover {{
        background: {p['surface3']};
        border-color: {p['accent']};
    }}
    QPushButton:pressed {{
        background: {p['violet_tint']};
    }}
    QPushButton#primary {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #7C5CFF, stop:1 #4F7CFF);
        color: #FFFFFF;
        border: 1px solid #8B6DFF;
        padding: 9px 18px;
    }}
    QPushButton#primary:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #8D71FF, stop:1 #628BFF);
    }}
    QPushButton#primary:pressed {{ background: #5A3BE6; }}
    QPushButton#secondary {{ background: {p['surface2']}; }}
    QPushButton#ghost {{
        background: transparent;
        border: 1px solid transparent;
        color: {p['muted']};
        padding: 6px 10px;
    }}
    QPushButton#ghost:hover {{
        color: {p['text']};
        background: {p['surface2']};
        border-color: {p['border_soft']};
    }}
    QPushButton#linkBtn {{
        background: transparent;
        border: none;
        color: {p['accent_soft']};
        padding: 2px;
        font-weight: 600;
    }}
    QPushButton#linkBtn:hover {{ color: {p['text']}; }}
    QPushButton#danger {{
        background: {p['red_tint']};
        color: {p['danger']};
        border: 1px solid {p['danger']};
    }}
    QPushButton#danger:hover {{ background: {p['danger']}; color: white; }}
    QPushButton#iconBtn {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 4px;
        min-width: 18px;
    }}
    QPushButton#iconBtn:hover {{
        background: {p['surface2']};
        border-color: {p['border_soft']};
    }}
    QPushButton:disabled {{
        color: {p['dim']};
        background: {p['bg_alt']};
        border-color: {p['border_soft']};
    }}
    QPushButton#segBtn {{
        background: transparent;
        border: none;
        border-radius: 8px;
        color: {p['muted']};
        padding: 6px 14px;
        font-weight: 600;
        font-size: 11.5px;
    }}
    QPushButton#segBtn:hover {{ color: {p['text']}; }}
    QPushButton#segBtn:checked {{
        background: {p['surface3']};
        color: {p['text']};
        border: 1px solid {p['border']};
    }}
    QFrame#segContainer {{
        background: {p['input']};
        border: 1px solid {p['border_soft']};
        border-radius: 10px;
    }}
    QPushButton#navToggle {{
        background: {p['surface2']};
        border: 1px solid {p['border_soft']};
        border-radius: 9px;
        padding: 5px;
    }}
    QPushButton#navToggle:hover {{ background: {p['surface3']}; border-color: {p['accent']}; }}

    QLineEdit, QComboBox, QDateEdit, QSpinBox, QTextEdit {{
        background: {p['input']};
        border: 1px solid {p['border']};
        border-radius: 10px;
        padding: 7px 10px;
        color: {p['text']};
        selection-background-color: {p['accent']};
        selection-color: #FFFFFF;
        min-height: 18px;
    }}
    QLineEdit:hover, QComboBox:hover, QDateEdit:hover, QSpinBox:hover, QTextEdit:hover {{
        border-color: {p['dim']};
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QTextEdit:focus {{
        border: 1px solid {p['accent']};
    }}
    QLineEdit[invalid="true"] {{ border: 1px solid {p['danger']}; }}
    QLineEdit#amountInput {{
        border: none;
        background: transparent;
        padding: 0;
        font-size: 20px;
        font-weight: 700;
    }}
    QFrame#amountFrame {{
        background: {p['input']};
        border: 1px solid {p['border']};
        border-radius: 10px;
    }}
    QFrame#amountFrame[focused="true"] {{ border: 1px solid {p['accent']}; }}
    QComboBox::drop-down, QDateEdit::drop-down {{
        border: none;
        width: 24px;
        subcontrol-origin: padding;
        subcontrol-position: center right;
    }}
    QComboBox::down-arrow, QDateEdit::down-arrow {{
        image: url("{chevron}");
        width: 10px;
        height: 10px;
    }}
    QComboBox QAbstractItemView {{
        background: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 10px;
        padding: 4px;
        selection-background-color: {p['violet_tint']};
        selection-color: {p['text']};
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{ min-height: 26px; padding: 2px 8px; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}
    QTextEdit {{ padding: 8px; }}

    QCheckBox {{ color: {p['muted']}; spacing: 8px; font-size: 11.5px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border: 1px solid {p['border']};
        border-radius: 5px;
        background: {p['input']};
    }}
    QCheckBox::indicator:checked {{
        background: {p['accent']};
        border-color: {p['accent']};
        image: url("{check}");
    }}

    QTableWidget, QTableView {{
        background: transparent;
        alternate-background-color: {p['surface2']};
        border: none;
        gridline-color: transparent;
        color: {p['text']};
        selection-background-color: {p['selection']};
        selection-color: {p['text']};
    }}
    QTableWidget::item, QTableView::item {{
        padding: 4px 8px;
        border: none;
        border-bottom: 1px solid {p['border_soft']};
    }}
    QTableWidget::item:selected, QTableView::item:selected {{
        background: {p['selection']};
        color: {p['text']};
    }}
    QHeaderView {{ background: transparent; }}
    QHeaderView::section {{
        background: transparent;
        color: {p['dim']};
        padding: 7px 8px;
        border: none;
        border-bottom: 1px solid {p['border']};
        font-size: 10px;
        font-weight: 700;
    }}
    QTableCornerButton::section {{ background: transparent; border: none; }}

    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{
        background: transparent; width: 11px; margin: 3px;
    }}
    QScrollBar::handle:vertical {{
        background: {p['surface3']}; border-radius: 4px; min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p['accent']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 3px; }}
    QScrollBar::handle:horizontal {{ background: {p['surface3']}; border-radius: 4px; min-width: 32px; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    QToolTip {{
        background: {p['surface3']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 6px 8px;
        font-size: 11px;
    }}
    QDialog {{ background: {p['bg']}; }}
    QMessageBox {{ background: {p['bg']}; }}
    QMessageBox QLabel {{ color: {p['text']}; font-size: 12px; }}
    QMenu {{
        background: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{ padding: 7px 22px 7px 12px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {p['violet_tint']}; }}

    QCalendarWidget QWidget#qt_calendar_navigationbar {{
        background: {p['surface2']};
        border-radius: 8px;
    }}
    QCalendarWidget QToolButton {{
        color: {p['text']}; background: transparent; border: none; padding: 4px 8px;
    }}
    QCalendarWidget QAbstractItemView {{
        background: {p['surface']};
        color: {p['text']};
        selection-background-color: {p['accent']};
        selection-color: white;
        outline: none;
    }}
    QCalendarWidget QMenu {{ background: {p['surface']}; }}
    QStatusBar {{
        background: {p['sidebar']};
        color: {p['muted']};
        border-top: 1px solid {p['border_soft']};
        font-size: 10.5px;
    }}
    QStatusBar::item {{ border: none; }}
    """
