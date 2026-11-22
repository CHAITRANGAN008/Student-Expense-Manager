from __future__ import annotations

from datetime import date

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.repositories.settings_repository import SettingsRepository
from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.money import set_currency
from student_expense_manager.services.reminder_service import ReminderService
from student_expense_manager.ui.icons import make_icon
from student_expense_manager.ui.pages.analytics import AnalyticsPage
from student_expense_manager.ui.pages.budgets import BudgetsPage
from student_expense_manager.ui.pages.dashboard import DashboardPage
from student_expense_manager.ui.pages.reminders import RemindersPage
from student_expense_manager.ui.pages.reports import ReportsPage
from student_expense_manager.ui.pages.settings import SettingsPage
from student_expense_manager.ui.pages.transactions import TransactionsPage
from student_expense_manager.ui.theme import (
    build_stylesheet,
    current_theme,
    palette,
    set_current_theme,
)
from student_expense_manager.ui.widgets import (
    AnimatedCredit,
    SearchField,
    icon_button,
    repolish,
)

NAV_ITEMS: list[tuple[str, str, str, str]] = [
    ("dashboard", "Dashboard", "dashboard", "WORKSPACE"),
    ("transactions", "Transactions", "transactions", ""),
    ("budgets", "Budgets", "wallet", ""),
    ("reminders", "Payment Reminders", "bell", "REMINDERS"),
    ("analytics", "Analytics", "analytics", "INSIGHTS"),
    ("reports", "Monthly reports", "reports", ""),
    ("settings", "Settings", "settings", "SYSTEM"),
]

PAGE_TITLES = {
    "dashboard": "Dashboard",
    "transactions": "Transactions",
    "budgets": "Budgets",
    "reminders": "Payment Reminders",
    "analytics": "Analytics",
    "reports": "Monthly reports",
    "settings": "Settings",
}


class BrandMark(QWidget):
    """Small painted mark: a rounded tile with a rising chart stroke."""

    def __init__(self, size: int = 38, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor("#8B6CFF"))
        gradient.setColorAt(0.55, QColor("#6D4AFF"))
        gradient.setColorAt(1.0, QColor("#3E7BFA"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 11, 11)

        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawRoundedRect(QRectF(9, 10, 4.2, 12), 2, 2)
        painter.drawRoundedRect(QRectF(16, 15, 4.2, 7), 2, 2)
        painter.drawRoundedRect(QRectF(23, 19, 4.2, 3), 2, 2)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 44))
        painter.drawEllipse(QPointF(35, 5), 12, 12)
        painter.end()


class NavButton(QPushButton):
    def __init__(self, key: str, label: str, icon_kind: str) -> None:
        super().__init__("  " + label)
        self.key = key
        self.label = label
        self.icon_kind = icon_kind
        self.setObjectName("navItem")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(18, 18))
        self.setMinimumHeight(38)
        self.setToolTip(label)
        self.refresh_icon(False)

    def refresh_icon(self, active: bool) -> None:
        p = palette()
        color = "#FFFFFF" if active else p["muted"]
        self.setIcon(make_icon(self.icon_kind, color, 18))

    def set_collapsed(self, collapsed: bool) -> None:
        self.setText("" if collapsed else "  " + self.label)
        self.setToolTip(self.label)


class Sidebar(QFrame):
    navigate = Signal(str)
    toggle_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(238)
        self._collapsed = False
        self._buttons: dict[str, NavButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 18, 16, 16)
        root.setSpacing(6)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(11)
        self.mark = BrandMark(38)
        brand_row.addWidget(self.mark)
        self.brand_text = QVBoxLayout()
        self.brand_text.setSpacing(0)
        self.brand_name = QLabel("Student Expense")
        self.brand_name.setObjectName("brandTitle")
        self.brand_tag = QLabel("MANAGER")
        self.brand_tag.setObjectName("brandSubtitle")
        self.brand_text.addWidget(self.brand_name)
        self.brand_text.addWidget(self.brand_tag)
        brand_row.addLayout(self.brand_text, 1)
        self.collapse_btn = icon_button("chevron-left", "Collapse sidebar", size=28)
        self.collapse_btn.clicked.connect(self.toggle_requested)
        brand_row.addWidget(self.collapse_btn)
        root.addLayout(brand_row)
        root.addSpacing(16)

        self.section_labels: list[QLabel] = []
        for key, label, icon_kind, section in NAV_ITEMS:
            if section:
                section_label = QLabel(section)
                section_label.setObjectName("sectionLabel")
                root.addSpacing(5)
                root.addWidget(section_label)
                self.section_labels.append(section_label)
            button = NavButton(key, label, icon_kind)
            button.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
            root.addWidget(button)
            self._buttons[key] = button
        root.addStretch(1)

        self.credit = AnimatedCredit(compact=True)
        root.addWidget(self.credit)
        root.addSpacing(4)

        self.privacy_card = QFrame()
        self.privacy_card.setObjectName("sidebarCard")
        privacy = QHBoxLayout(self.privacy_card)
        privacy.setContentsMargins(11, 10, 11, 10)
        privacy.setSpacing(9)
        from student_expense_manager.ui.widgets import IconChip

        self.shield = IconChip("shield", palette()["success"], palette()["green_tint"], size=28)
        privacy.addWidget(self.shield)
        self.privacy_text = QVBoxLayout()
        self.privacy_text.setSpacing(0)
        title = QLabel("Private by design")
        title.setObjectName("sidebarCardTitle")
        caption = QLabel("Stored only on this device")
        caption.setObjectName("sidebarCardCaption")
        self.privacy_text.addWidget(title)
        self.privacy_text.addWidget(caption)
        privacy.addLayout(self.privacy_text, 1)
        root.addWidget(self.privacy_card)

    def set_active(self, key: str) -> None:
        for item_key, button in self._buttons.items():
            active = item_key == key
            button.blockSignals(True)
            button.setChecked(active)
            button.blockSignals(False)
            button.refresh_icon(active)

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.setFixedWidth(78 if collapsed else 238)
        self.mark.setVisible(not collapsed)
        self.brand_name.setVisible(not collapsed)
        self.brand_tag.setVisible(not collapsed)
        for label in self.section_labels:
            label.setVisible(not collapsed)
        for button in self._buttons.values():
            button.set_collapsed(collapsed)
        self.collapse_btn.setIcon(
            make_icon(
                "chevron-right" if collapsed else "chevron-left",
                palette()["muted"],
                16,
            )
        )
        self.collapse_btn.setToolTip("Expand sidebar" if collapsed else "Collapse sidebar")
        self.credit.setVisible(not collapsed)
        self.privacy_card.setVisible(not collapsed)


class MainWindow(QMainWindow):
    def __init__(self, service: FinanceService | None = None) -> None:
        super().__init__()
        self.settings = SettingsRepository()
        set_current_theme(self.settings.get("theme", "dark") or "dark")
        set_currency(self.settings.get("currency", "INR") or "INR")

        self.service = service or FinanceService()
        self.reminder_service = ReminderService(finance=self.service)
        self.setWindowTitle("Student Expense Manager")
        self.resize(1240, 800)
        self.setMinimumSize(1100, 700)

        self._pages: dict[str, QWidget] = {}
        self._active = "dashboard"

        root = QWidget()
        root.setObjectName("appRoot")
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.setCentralWidget(root)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.switch_page)
        self.sidebar.toggle_requested.connect(self.toggle_sidebar)
        shell.addWidget(self.sidebar)

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        shell.addLayout(content, 1)

        self.topbar = self._build_topbar()
        content.addWidget(self.topbar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("stack")
        content.addWidget(self.stack, 1)

        self._build_pages()
        self.switch_page("dashboard")
        self.apply_theme(save=False)

    # ------------------------------------------------------------------ chrome
    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(60)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(26, 10, 22, 10)
        layout.setSpacing(12)

        crumb = QVBoxLayout()
        crumb.setSpacing(1)
        self.crumb_eyebrow = QLabel("STUDENT EXPENSE  /  WORKSPACE")
        self.crumb_eyebrow.setObjectName("crumb")
        self.crumb_title = QLabel("Dashboard")
        self.crumb_title.setObjectName("crumbCurrent")
        crumb.addWidget(self.crumb_eyebrow)
        crumb.addWidget(self.crumb_title)
        layout.addLayout(crumb)
        layout.addSpacing(16)

        self.search = SearchField("Search transactions, categories…")
        self.search.setObjectName("topSearch")
        self.search.setMinimumWidth(280)
        self.search.setMaximumWidth(400)
        self.search.returnPressed.connect(self._global_search)
        layout.addWidget(self.search, 1)
        layout.addStretch(1)

        today = QLabel(date.today().strftime("%a, %d %b %Y"))
        today.setObjectName("topbarMeta")
        layout.addWidget(today)

        divider = QFrame()
        divider.setFixedSize(1, 22)
        divider.setObjectName("topbarDivider")
        layout.addWidget(divider)

        offline = QLabel("●  Offline")
        offline.setObjectName("topbarMeta")
        offline.setStyleSheet(f"color: {palette()['success']};")
        layout.addWidget(offline)

        self.theme_btn = icon_button(
            "moon" if current_theme() == "dark" else "sun",
            "Switch theme",
            "muted",
            32,
        )
        self.theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_btn)

        avatar = QLabel("ST")
        avatar.setObjectName("avatar")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(34, 34)
        layout.addWidget(avatar)
        return bar

    def _build_pages(self) -> None:
        self._pages = {
            "dashboard": DashboardPage(
                self.service, self._data_changed, self.switch_page
            ),
            "transactions": TransactionsPage(
                self.service, self._data_changed, self.switch_page
            ),
            "budgets": BudgetsPage(self.service, self._data_changed, self.switch_page),
            "reminders": RemindersPage(
                self.reminder_service,
                self.service,
                self.settings,
                self._data_changed,
                self.switch_page,
            ),
            "analytics": AnalyticsPage(
                self.service, self._data_changed, self.switch_page
            ),
            "reports": ReportsPage(self.service, self._data_changed, self.switch_page),
            "settings": SettingsPage(
                self.service,
                on_theme_change=self.apply_theme,
                on_data_change=self._data_changed,
                on_navigate=self.switch_page,
            ),
        }
        for page in self._pages.values():
            self.stack.addWidget(page)

    # ------------------------------------------------------------------ actions
    def toggle_sidebar(self) -> None:
        self.sidebar.set_collapsed(not self.sidebar._collapsed)
        self.sidebar.set_active(self._active)

    def switch_page(self, key: str) -> None:
        page = self._pages.get(key)
        if page is None:
            return
        self._active = key
        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(key)
        self.crumb_title.setText(PAGE_TITLES[key])
        sections = {
            "dashboard": "WORKSPACE",
            "transactions": "WORKSPACE",
            "budgets": "WORKSPACE",
            "reminders": "REMINDERS",
            "analytics": "INSIGHTS",
            "reports": "INSIGHTS",
            "settings": "SYSTEM",
        }
        self.crumb_eyebrow.setText(f"STUDENT EXPENSE  /  {sections.get(key, 'WORKSPACE')}")
        if hasattr(page, "mark_dirty") and getattr(page, "_dirty", False):
            page.refresh()  # type: ignore[attr-defined]

    def _global_search(self) -> None:
        text = self.search.text().strip()
        self.switch_page("transactions")
        page = self._pages["transactions"]
        if hasattr(page, "set_search"):
            page.set_search(text)  # type: ignore[attr-defined]

    def _data_changed(self) -> None:
        for key, page in self._pages.items():
            if key == self._active:
                if hasattr(page, "refresh"):
                    page.refresh()  # type: ignore[attr-defined]
            elif hasattr(page, "mark_dirty"):
                page.mark_dirty()  # type: ignore[attr-defined]

    def refresh_all(self) -> None:
        for page in self._pages.values():
            if hasattr(page, "refresh"):
                page.refresh()  # type: ignore[attr-defined]
            if hasattr(page, "mark_dirty"):
                page.mark_dirty()  # type: ignore[attr-defined]

    def toggle_theme(self) -> None:
        new_theme = "light" if current_theme() == "dark" else "dark"
        self.apply_theme(new_theme)

    def apply_theme(self, name: str | None = None, save: bool = True) -> None:
        theme = name or current_theme()
        set_current_theme(theme)
        if save:
            self.settings.set("theme", theme)
        self.setStyleSheet(build_stylesheet(theme))
        self.theme_btn.setIcon(
            make_icon(
                "moon" if theme == "dark" else "sun",
                palette()["muted"],
                16,
            )
        )
        for key, button in self.sidebar._buttons.items():
            button.refresh_icon(key == self._active)
        repolish(self.topbar)
        for page in self._pages.values():
            if hasattr(page, "apply_theme"):
                page.apply_theme()  # type: ignore[attr-defined]
        self.sidebar.set_collapsed(self.sidebar._collapsed)

    # ------------------------------------------------------------------ lifecycle
    def closeEvent(self, event) -> None:  # noqa: N802, ANN001
        # Flush nothing manually: every repository call commits its own transaction.
        super().closeEvent(event)
