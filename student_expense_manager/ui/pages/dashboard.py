from __future__ import annotations

import calendar
from datetime import date
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.money import format_money
from student_expense_manager.ui.charts import ChartCanvas
from student_expense_manager.ui.constants import CATEGORY_COLORS
from student_expense_manager.ui.dialogs import TransactionDialog
from student_expense_manager.ui.page_base import PageHeader, content_layout
from student_expense_manager.ui.theme import palette
from student_expense_manager.ui.widgets import (
    BudgetMiniList,
    DonutChart,
    HBarList,
    LegendRow,
    PeriodSelector,
    Pill,
    SectionCard,
    SpendingCalendar,
    StatCard,
    configure_table,
    icon_button,
    make_button,
)


def _delta(cur: int, prev: int, up_is_good: bool = True) -> tuple[str, bool | None]:
    if prev <= 0:
        return ("No prior month", None if cur <= 0 else True)
    change = (cur - prev) / prev * 100
    arrow = "↑" if change >= 0 else "↓"
    text = f"{arrow} {abs(change):.1f}% vs last month"
    good = change >= 0 if up_is_good else change <= 0
    return (text, good)


class DashboardPage(QWidget):
    def __init__(
        self,
        service: FinanceService,
        on_changed: Callable[[], None],
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.on_changed = on_changed
        self.on_navigate = on_navigate
        self._dirty = True

        root = content_layout(self, margins=(26, 12, 26, 14), spacing=13)
        self.header = PageHeader(
            "Dashboard",
            "A clear view of your money this month.",
            "OVERVIEW",
        )
        self.period = PeriodSelector()
        self.period.changed.connect(self._period_changed)
        self.header.add_action(self.period)
        add_btn = make_button("Add transaction", "primary", "plus")
        add_btn.clicked.connect(self.add_transaction)
        self.header.add_action(add_btn)
        root.addWidget(self.header)

        stats = QGridLayout()
        stats.setHorizontalSpacing(12)
        stats.setVerticalSpacing(12)
        self.balance_card = StatCard("Total balance", "wallet", accent=True)
        self.income_card = StatCard("Monthly income", "trend-up")
        self.expense_card = StatCard("Monthly spend", "trend-down")
        self.net_card = StatCard("Budget left", "shield")
        for column, card in enumerate(
            [self.balance_card, self.income_card, self.expense_card, self.net_card]
        ):
            card.setFixedHeight(108)
            card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            stats.addWidget(card, 0, column)
            stats.setColumnStretch(column, 1)
        root.addLayout(stats)

        middle = QHBoxLayout()
        middle.setSpacing(14)
        self.cashflow_card = SectionCard(
            "Cash flow",
            "Income and spending across the last six months.",
        )
        self.cashflow_card.add_action(Pill("6 MONTHS", "accent"))
        self.cashflow_chart = ChartCanvas(min_height=152)
        self.cashflow_chart.setFixedHeight(152)
        self.cashflow_card.body.addWidget(self.cashflow_chart)
        middle.addWidget(self.cashflow_card, 2)

        self.channel_card = SectionCard(
            "Online vs offline",
            "This month's spending split.",
        )
        channel_body = QVBoxLayout()
        channel_body.setSpacing(2)
        self.channel_donut = DonutChart()
        self.channel_donut.setMinimumHeight(104)
        channel_body.addWidget(self.channel_donut, 1)
        self.channel_legend = QVBoxLayout()
        self.channel_legend.setSpacing(2)
        channel_body.addLayout(self.channel_legend)
        self.channel_card.body.addLayout(channel_body)
        middle.addWidget(self.channel_card, 1)

        self.calendar_card = SectionCard(
            "Spending calendar",
            "Darker days mean heavier spending.",
        )
        self.calendar = SpendingCalendar()
        self.calendar_card.body.addWidget(self.calendar)
        middle.addWidget(self.calendar_card, 1)
        root.addLayout(middle)

        lower = QHBoxLayout()
        lower.setSpacing(14)
        self.category_card = SectionCard("Top categories", "Where most of your money goes.")
        self.category_list = HBarList(max_items=4)
        self.category_card.body.addWidget(self.category_list)
        lower.addWidget(self.category_card, 11)

        self.budget_card = SectionCard("Budget health", "This month at a glance.")
        manage = icon_button("arrow-up-right", "Open budgets", "accent")
        manage.clicked.connect(lambda: self._navigate("budgets"))
        self.budget_card.add_action(manage)
        self.budget_list = BudgetMiniList()
        self.budget_card.body.addWidget(self.budget_list)
        self.budget_card.body.addStretch(1)
        lower.addWidget(self.budget_card, 11)

        self.recent_card = SectionCard(
            "Recent transactions",
            "The latest activity recorded for this month.",
        )
        view_all = make_button("View all", "ghost")
        view_all.clicked.connect(lambda: self._navigate("transactions"))
        self.recent_card.add_action(view_all)
        self.recent_table = QTableWidget(0, 4)
        self.recent_table.setHorizontalHeaderLabels(
            ["Date", "Description", "Category", "Amount"]
        )
        configure_table(self.recent_table, row_height=33)
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (0, 2, 3):
            self.recent_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self.recent_table.setFixedHeight(142)
        self.recent_table.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.recent_card.body.addWidget(self.recent_table)
        lower.addWidget(self.recent_card, 18)
        root.addLayout(lower)
        root.addStretch(1)

        for card in (
            self.cashflow_card,
            self.channel_card,
            self.calendar_card,
            self.category_card,
            self.budget_card,
            self.recent_card,
        ):
            card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self._channel_rows: list[QWidget] = []

    # ------------------------------------------------------------------ actions
    def _navigate(self, name: str) -> None:
        if self.on_navigate:
            self.on_navigate(name)

    def _period_changed(self, _month: int, _year: int) -> None:
        self.refresh()

    def add_transaction(self) -> None:
        dialog = TransactionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.service.add_transaction(dialog.transaction())
            except ValueError as exc:
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(self, "Could not save", str(exc))
                return
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
        previous_month, previous_year = self.service.previous_month(month, year)
        previous = self.service.month_summary(previous_month, previous_year)
        overall = self.service.overall_summary()
        trends = self.service.rolling_trends(month, year, 6)
        net_series = [t["income_paise"] - t["expense_paise"] for t in trends]
        income_series = [t["income_paise"] for t in trends]
        expense_series = [t["expense_paise"] for t in trends]

        self.balance_card.set_data(
            format_money(overall.balance_paise),
            f"{len(self.service.list_transactions())} transactions recorded",
            None,
            net_series,
            "",
            "neutral",
        )
        income_text, income_good = _delta(
            summary.total_income_paise, previous.total_income_paise, up_is_good=True
        )
        self.income_card.set_data(
            format_money(summary.total_income_paise),
            income_text,
            income_good,
            income_series,
        )
        expense_text, expense_good = _delta(
            summary.total_expense_paise, previous.total_expense_paise, up_is_good=False
        )
        self.expense_card.set_data(
            format_money(summary.total_expense_paise),
            expense_text,
            expense_good,
            expense_series,
        )
        statuses = self.service.budget_status(month, year)
        overall_budget = next(
            (s for s in statuses if s["category"] is None), None
        )
        if overall_budget is None:
            budget_value = "Not set"
            budget_caption = "Add an overall limit in Budgets"
            budget_good = None
        else:
            budget_value = format_money(int(overall_budget["remaining_paise"]))
            budget_caption = (
                f"{overall_budget['percent']:.0f}% of "
                f"{format_money(int(overall_budget['budget_paise']))} used"
            )
            budget_good = overall_budget["level"] == "ok"
        self.net_card.set_data(
            budget_value,
            budget_caption,
            budget_good,
            expense_series,
            "",
            "neutral",
        )

        self.cashflow_card.set_subtitle(
            f"Income and spending, {trends[0]['label']} – {trends[-1]['label']}."
        )
        self.cashflow_chart.render_cash_flow(trends, len(trends))

        total_channel = summary.online_expense_paise + summary.offline_expense_paise
        self.channel_donut.set_data(
            [
                ("Online", summary.online_expense_paise, p["accent2"]),
                ("Offline", summary.offline_expense_paise, p["warning"]),
            ],
            "This month",
        )
        self._clear_channel_legend()
        for label, value, color in (
            ("Online", summary.online_expense_paise, p["accent2"]),
            ("Offline", summary.offline_expense_paise, p["warning"]),
        ):
            share = (value / total_channel * 100) if total_channel else 0.0
            row = LegendRow(
                f"{label} · {share:.0f}%",
                format_money(value),
                color,
            )
            self.channel_legend.addWidget(row)
            self._channel_rows.append(row)

        categories = [
            (name, amount, CATEGORY_COLORS[i % len(CATEGORY_COLORS)])
            for i, (name, amount) in enumerate(summary.category_expenses.items())
        ]
        self.category_list.set_items(categories)
        if categories:
            top_name, top_amount, _ = categories[0]
            self.category_card.set_subtitle(
                f"{top_name} leads at {format_money(top_amount)} this month."
            )
        else:
            self.category_card.set_subtitle("No spending recorded for this month yet.")

        daily = self.service.daily_expenses(month, year)
        self.calendar.set_period(month, year, daily)
        if daily:
            peak_day = max(daily, key=daily.get)
            self.calendar_card.set_subtitle(
                f"Peak: {peak_day} {calendar.month_abbr[month]} · {format_money(daily[peak_day])}"
            )
        else:
            self.calendar_card.set_subtitle("Darker days mean heavier spending.")

        self.budget_list.set_statuses(statuses)
        alarm = [s for s in statuses if s["level"] in ("warning", "exceeded")]
        self.budget_card.set_subtitle(
            f"{len(alarm)} budget{'s' if len(alarm) != 1 else ''} need attention."
            if alarm
            else "All budgets are within their limits."
        )

        recent = self.service.list_transactions(month=month, year=year, limit=3)
        self.recent_card.set_subtitle(
            f"{len(recent)} most recent entries for this month."
            if recent
            else "Nothing recorded for this month yet."
        )
        self.recent_table.setRowCount(len(recent))
        for row, tx in enumerate(recent):
            try:
                pretty_date = date.fromisoformat(tx.transaction_date).strftime("%d %b")
            except ValueError:
                pretty_date = tx.transaction_date
            date_item = QTableWidgetItem(pretty_date)
            desc_item = QTableWidgetItem(tx.description or "—")
            desc_item.setToolTip(tx.description or "")
            cat_item = QTableWidgetItem(tx.category)
            sign = "+" if tx.transaction_type == "income" else "−"
            amount_item = QTableWidgetItem(f"{sign}{format_money(tx.amount_paise)}")
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            amount_item.setForeground(
                QColor(p["income"] if tx.transaction_type == "income" else p["expense"])
            )
            for column, item in enumerate([date_item, desc_item, cat_item, amount_item]):
                if column == 1:
                    font = item.font()
                    font.setWeight(QFont.Weight.DemiBold)
                    item.setFont(font)
                self.recent_table.setItem(row, column, item)

    def _clear_channel_legend(self) -> None:
        for row in self._channel_rows:
            self.channel_legend.removeWidget(row)
            row.deleteLater()
        self._channel_rows.clear()

    def apply_theme(self) -> None:
        self.refresh()
