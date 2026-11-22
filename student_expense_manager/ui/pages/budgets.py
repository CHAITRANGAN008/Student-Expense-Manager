from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.money import format_money
from student_expense_manager.ui.constants import CATEGORY_COLORS
from student_expense_manager.ui.dialogs import BudgetDialog, ConfirmDialog
from student_expense_manager.ui.page_base import MiniStat, PageHeader, content_layout
from student_expense_manager.ui.theme import palette
from student_expense_manager.ui.widgets import (
    Card,
    EmptyState,
    IconChip,
    PercentBar,
    PeriodSelector,
    Pill,
    SectionCard,
    clear_layout,
    icon_button,
    make_button,
    repolish,
)

LEVEL_LABELS = {
    "ok": "ON TRACK",
    "warning": "NEAR LIMIT",
    "exceeded": "OVER BUDGET",
}
LEVEL_TONES = {"ok": "success", "warning": "warning", "exceeded": "danger"}


def _level_color(level: str) -> str:
    p = palette()
    return {"ok": p["success"], "warning": p["warning"], "exceeded": p["danger"]}.get(
        level, p["accent"]
    )


class OverallBudgetCard(QFrame):
    def __init__(
        self,
        on_edit: Callable[[], None],
        on_delete: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("accentCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(182)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 17, 20, 17)
        root.setSpacing(11)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.chip = IconChip(
            "wallet",
            color="#FFFFFF",
            tint=QColor(255, 255, 255, 42),
            size=36,
        )
        top.addWidget(self.chip)
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("Overall monthly budget")
        title.setStyleSheet("color:#FFFFFF; font-size:13px; font-weight:700;")
        self.subtitle = QLabel("No overall limit set")
        self.subtitle.setStyleSheet("color:rgba(255,255,255,0.72); font-size:10.5px;")
        title_box.addWidget(title)
        title_box.addWidget(self.subtitle)
        top.addLayout(title_box, 1)
        self.pill = QLabel("SET A LIMIT")
        self.pill.setStyleSheet(
            "background:rgba(255,255,255,0.16); border:1px solid rgba(255,255,255,0.30);"
            "border-radius:8px; padding:3px 9px; color:#FFFFFF; font-size:9.5px; font-weight:700;"
        )
        top.addWidget(self.pill)
        self.edit_btn = icon_button("edit", "Edit overall budget", "text", size=30)
        self.edit_btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.10);border:1px solid rgba(255,255,255,0.16);border-radius:8px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.22);}"
        )
        self.delete_btn = icon_button("trash", "Delete overall budget", "text", size=30)
        self.delete_btn.setStyleSheet(self.edit_btn.styleSheet())
        top.addWidget(self.edit_btn)
        top.addWidget(self.delete_btn)
        root.addLayout(top)

        self.spent = QLabel("—")
        self.spent.setStyleSheet("color:#FFFFFF; font-size:25px; font-weight:700;")
        root.addWidget(self.spent)
        self.caption = QLabel("Add an overall budget to see live progress.")
        self.caption.setStyleSheet("color:rgba(255,255,255,0.76); font-size:11px;")
        root.addWidget(self.caption)
        self.bar = PercentBar(height=9, color="#FFFFFF")
        root.addWidget(self.bar)
        bottom = QHBoxLayout()
        self.used = QLabel("")
        self.used.setStyleSheet("color:rgba(255,255,255,0.86); font-size:11px; font-weight:600;")
        self.remaining = QLabel("")
        self.remaining.setStyleSheet("color:#FFFFFF; font-size:11px; font-weight:700;")
        bottom.addWidget(self.used)
        bottom.addStretch(1)
        bottom.addWidget(self.remaining)
        root.addLayout(bottom)
        self.edit_btn.clicked.connect(on_edit)
        self.delete_btn.clicked.connect(on_delete)
        self.set_status(None)

    def set_status(self, status: dict | None) -> None:
        if status is None:
            self.subtitle.setText("No overall limit set for this month")
            self.pill.setText("SET A LIMIT")
            self.spent.setText("—")
            self.caption.setText("Add an overall budget to track the whole month.")
            self.bar.set_value(0.0, "#FFFFFF", animate=False)
            self.used.setText("")
            self.remaining.setText("")
            self.edit_btn.setText("")
            self.edit_btn.setToolTip("Set overall budget")
            self.delete_btn.setEnabled(False)
            return
        self.delete_btn.setEnabled(True)
        self.subtitle.setText(f"Total spending across every category")
        self.pill.setText(LEVEL_LABELS[status["level"]])
        self.spent.setText(format_money(status["spent_paise"]))
        self.caption.setText(
            f"of {format_money(status['budget_paise'])} planned for this month"
        )
        self.bar.set_value(status["percent"] / 100, "#FFFFFF")
        self.used.setText(f"{status['percent']:.1f}% used")
        remaining = status["remaining_paise"]
        self.remaining.setText(
            f"{format_money(remaining)} left"
            if remaining >= 0
            else f"{format_money(abs(remaining))} over budget"
        )


class BudgetCard(Card):
    def __init__(
        self,
        status: dict,
        on_edit: Callable[[], None],
        on_delete: Callable[[], None],
        color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, "card")
        self.status = status
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(9)

        top = QHBoxLayout()
        top.setSpacing(10)
        tint = {
            "ok": palette()["violet_tint"],
            "warning": palette()["amber_tint"],
            "exceeded": palette()["red_tint"],
        }[status["level"]]
        top.addWidget(IconChip("dot", color=color, tint=tint, size=32))
        name = QLabel(status["label"])
        name.setObjectName("cardTitle")
        top.addWidget(name, 1)
        pill = Pill(LEVEL_LABELS[status["level"]], LEVEL_TONES[status["level"]])
        top.addWidget(pill)
        edit_btn = icon_button("edit", "Edit budget", size=28)
        delete_btn = icon_button("trash", "Delete budget", "danger", size=28)
        edit_btn.clicked.connect(on_edit)
        delete_btn.clicked.connect(on_delete)
        top.addWidget(edit_btn)
        top.addWidget(delete_btn)
        root.addLayout(top)

        amounts = QHBoxLayout()
        spent = QLabel(format_money(status["spent_paise"]))
        spent.setStyleSheet("font-size:18px; font-weight:700;")
        amounts.addWidget(spent)
        of = QLabel(f"of {format_money(status['budget_paise'])}")
        of.setObjectName("cardSubtitle")
        amounts.addWidget(of)
        amounts.addStretch(1)
        percent = QLabel(f"{status['percent']:.0f}%")
        percent.setStyleSheet(f"color:{_level_color(status['level'])}; font-size:13px; font-weight:700;")
        amounts.addWidget(percent)
        root.addLayout(amounts)

        bar = PercentBar(height=8, color=color)
        bar.set_value(status["percent"] / 100)
        root.addWidget(bar)

        remaining = status["remaining_paise"]
        caption = (
            f"{format_money(abs(remaining))} over budget"
            if remaining < 0
            else f"{format_money(remaining)} remaining"
        )
        footer = QLabel(caption)
        footer.setObjectName("dimLabel")
        root.addWidget(footer)


class BudgetsPage(QWidget):
    def __init__(
        self,
        service: FinanceService,
        on_changed: Callable[[], None],
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.on_changed = on_changed
        self._dirty = True
        p = palette()

        root = content_layout(self)
        self.header = PageHeader(
            "Budgets",
            "Set limits, spot overspending early and stay in control.",
            "PLANNING",
        )
        self.period = PeriodSelector()
        self.period.changed.connect(lambda *_: self.refresh())
        self.header.add_action(self.period)
        new_btn = make_button("New budget", "primary", "plus")
        new_btn.clicked.connect(lambda: self.open_dialog())
        self.header.add_action(new_btn)
        root.addWidget(self.header)

        self.alert_card = QFrame()
        self.alert_card.setObjectName("alertCard")
        alert_layout = QHBoxLayout(self.alert_card)
        alert_layout.setContentsMargins(16, 12, 16, 12)
        alert_layout.setSpacing(11)
        self.alert_icon = IconChip("bell", size=34)
        alert_layout.addWidget(self.alert_icon)
        alert_text = QVBoxLayout()
        alert_text.setSpacing(1)
        self.alert_title = QLabel("")
        self.alert_title.setStyleSheet("font-size:12px;font-weight:700;")
        self.alert_detail = QLabel("")
        self.alert_detail.setObjectName("cardSubtitle")
        self.alert_detail.setWordWrap(True)
        alert_text.addWidget(self.alert_title)
        alert_text.addWidget(self.alert_detail)
        alert_layout.addLayout(alert_text, 1)
        self.alert_card.setVisible(False)
        root.addWidget(self.alert_card)

        summary = QGridLayout()
        summary.setHorizontalSpacing(12)
        summary.setVerticalSpacing(12)
        self.planned_stat = MiniStat(
            "Planned budget", "—", "Across all limits", "wallet"
        )
        self.spent_stat = MiniStat("Spent so far", "—", "Expenses this month", "trend-down")
        self.remaining_stat = MiniStat("Remaining", "—", "Available to spend", "shield")
        self.risk_stat = MiniStat("At risk", "0", "Budgets near or over limit", "bell")
        for column, card in enumerate(
            [self.planned_stat, self.spent_stat, self.remaining_stat, self.risk_stat]
        ):
            summary.addWidget(card, 0, column)
            summary.setColumnStretch(column, 1)
        root.addLayout(summary)

        self.overall_card = OverallBudgetCard(
            on_edit=lambda: self.edit_budget(None),
            on_delete=lambda: self.delete_budget(None),
        )
        root.addWidget(self.overall_card)

        self.category_card = SectionCard(
            "Category budgets",
            "Limits for the categories you care about most.",
        )
        add_category = make_button("Add category budget", "secondary", "plus")
        add_category.clicked.connect(lambda: self.open_dialog(scope="category"))
        self.category_card.add_action(add_category)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 2, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.category_card.body.addWidget(self.grid_host)
        root.addWidget(self.category_card)
        root.addStretch(1)

        self._statuses: list[dict] = []

    # ------------------------------------------------------------------ helpers
    def _status_for(self, category: str | None) -> dict | None:
        for status in self._statuses:
            if status["category"] == category:
                return status
        return None

    def open_dialog(
        self,
        *,
        scope: str = "overall",
        status: dict | None = None,
    ) -> None:
        month, year = self.period.period()
        if status is not None:
            category = status["category"]
        elif scope == "overall":
            category = None
        else:
            category = "Food & Canteen"
        amount = status["budget_paise"] if status else None
        dialog = BudgetDialog(
            self,
            month=month,
            year=year,
            category=category,
            amount_paise=amount,
            editing=status is not None,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_category, amount_paise = dialog.values()
        try:
            if status is not None and status["id"] is not None:
                self.service.delete_budget(int(status["id"]))
            self.service.set_budget(month, year, amount_paise, new_category)
        except ValueError as exc:
            QMessageBox.warning(self, "Could not save budget", str(exc))
            return
        self.refresh()
        self.on_changed()

    def edit_budget(self, category: str | None) -> None:
        status = self._status_for(category)
        if status is None:
            self.open_dialog(scope="overall" if category is None else "category")
            return
        self.open_dialog(scope="overall" if category is None else "category", status=status)

    def delete_budget(self, category: str | None) -> None:
        status = self._status_for(category)
        if status is None or status["id"] is None:
            return
        label = "overall budget" if category is None else f"{category} budget"
        if not ConfirmDialog.ask(
            self,
            title="Delete budget",
            message=f"Remove the {label} for this month? Your transactions will not be affected.",
            confirm_text="Delete budget",
        ):
            return
        self.service.delete_budget(int(status["id"]))
        self.refresh()
        self.on_changed()

    def mark_dirty(self) -> None:
        self._dirty = True

    # ------------------------------------------------------------------ refresh
    def refresh(self) -> None:
        self._dirty = False
        p = palette()
        month, year = self.period.period()
        summary = self.service.month_summary(month, year)
        self._statuses = self.service.budget_status(month, year)
        overall = self._status_for(None)
        category_statuses = [s for s in self._statuses if s["category"] is not None]

        self.overall_card.set_status(overall)

        planned = (
            overall["budget_paise"]
            if overall
            else sum(s["budget_paise"] for s in category_statuses)
        )
        spent = summary.total_expense_paise
        remaining = planned - spent
        at_risk = [s for s in self._statuses if s["level"] in ("warning", "exceeded")]
        self.planned_stat.set_data(
            format_money(planned) if planned else "Not set",
            "Overall monthly cap"
            if overall
            else "Category limits only",
        )
        self.spent_stat.set_data(format_money(spent), f"{month:02d}/{year} expenses")
        self.remaining_stat.set_data(
            format_money(remaining) if planned else "—",
            "Over budget" if planned and remaining < 0 else "Available to spend",
        )
        self.risk_stat.set_data(
            str(len(at_risk)),
            "Budgets need attention" if at_risk else "Everything is on track",
        )

        if at_risk:
            danger = any(s["level"] == "exceeded" for s in at_risk)
            self.alert_card.setProperty("tone", "danger" if danger else "warning")
            repolish(self.alert_card)
            self.alert_icon.set_kind(
                "bell",
                p["danger"] if danger else p["warning"],
                p["red_tint"] if danger else p["amber_tint"],
            )
            self.alert_title.setText(
                f"{len(at_risk)} budget{'s' if len(at_risk) != 1 else ''} need your attention"
            )
            detail = " · ".join(
                f"{s['label']} is at {s['percent']:.0f}%"
                + (" (over limit)" if s["level"] == "exceeded" else "")
                for s in at_risk[:3]
            )
            self.alert_detail.setText(detail)
            self.alert_card.setVisible(True)
        else:
            self.alert_card.setVisible(False)

        # Rebuild the category grid.
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not category_statuses:
            empty = EmptyState(
                "wallet",
                "No category budgets yet",
                "Add a limit for food, transport or anything you want to watch more closely.",
            )
            self.grid.addWidget(empty, 0, 0, 1, 2)
        for index, status in enumerate(category_statuses):
            color = _level_color(status["level"])
            card = BudgetCard(
                status,
                on_edit=lambda _=None, c=status["category"]: self.edit_budget(c),
                on_delete=lambda _=None, c=status["category"]: self.delete_budget(c),
                color=color,
            )
            self.grid.addWidget(card, index // 2, index % 2)
        self.category_card.set_subtitle(
            f"{len(category_statuses)} category limit{'s' if len(category_statuses) != 1 else ''} for this month."
            if category_statuses
            else "Limits for the categories you care about most."
        )

    def apply_theme(self) -> None:
        self.refresh()
