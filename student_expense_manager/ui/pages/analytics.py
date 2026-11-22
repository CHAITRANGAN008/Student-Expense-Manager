from __future__ import annotations

import calendar
from datetime import date
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.money import format_money
from student_expense_manager.ui.charts import ChartCanvas
from student_expense_manager.ui.constants import CATEGORY_COLORS
from student_expense_manager.ui.page_base import MiniStat, PageHeader, content_layout
from student_expense_manager.ui.theme import palette
from student_expense_manager.ui.widgets import (
    DonutChart,
    HBarList,
    LegendRow,
    PeriodSelector,
    Pill,
    SectionCard,
)


class AnalyticsPage(QWidget):
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
        self._row_widgets: list[QWidget] = []

        root = content_layout(self)
        self.header = PageHeader(
            "Analytics",
            "Understand the rhythm behind your spending.",
            "INSIGHTS",
        )
        self.period = PeriodSelector()
        self.period.changed.connect(lambda *_: self.refresh())
        self.header.add_action(self.period)
        root.addWidget(self.header)

        stats = QGridLayout()
        stats.setSpacing(12)
        self.avg_stat = MiniStat("Average day", "—", "Daily spend this month", "calendar")
        self.top_stat = MiniStat("Top category", "—", "Highest spending area", "analytics")
        self.online_stat = MiniStat("Online share", "—", "Of total spending", "wallet")
        self.savings_stat = MiniStat("Savings rate", "—", "Income kept this month", "trend-up")
        for column, card in enumerate(
            [self.avg_stat, self.top_stat, self.online_stat, self.savings_stat]
        ):
            stats.addWidget(card, 0, column)
            stats.setColumnStretch(column, 1)
        root.addLayout(stats)

        first = QHBoxLayout()
        first.setSpacing(14)
        self.trend_card = SectionCard(
            "Spending trend",
            "Expenses across the last six months.",
        )
        self.trend_card.add_action(Pill("6 MONTHS", "accent"))
        self.trend_chart = ChartCanvas(min_height=222)
        self.trend_card.body.addWidget(self.trend_chart)
        first.addWidget(self.trend_card, 2)

        self.channel_card = SectionCard(
            "Channel mix",
            "Online versus cash spending.",
        )
        channel_body = QVBoxLayout()
        channel_body.setSpacing(4)
        self.channel_donut = DonutChart()
        self.channel_donut.setMinimumHeight(150)
        channel_body.addWidget(self.channel_donut, 1)
        self.channel_legend = QVBoxLayout()
        self.channel_legend.setSpacing(1)
        channel_body.addLayout(self.channel_legend)
        self.channel_card.body.addLayout(channel_body)
        first.addWidget(self.channel_card, 1)
        root.addLayout(first)

        second = QHBoxLayout()
        second.setSpacing(14)
        self.compare_card = SectionCard(
            "Income vs expenses",
            "A six-month side-by-side comparison.",
        )
        self.compare_chart = ChartCanvas(min_height=210)
        self.compare_card.body.addWidget(self.compare_chart)
        second.addWidget(self.compare_card, 3)

        self.methods_card = SectionCard(
            "Payment methods",
            "How the money left your pocket.",
        )
        self.methods_list = HBarList()
        self.methods_card.body.addWidget(self.methods_list)
        self.methods_card.body.addStretch(1)
        second.addWidget(self.methods_card, 2)
        root.addLayout(second)

        self.categories_card = SectionCard(
            "Category breakdown",
            "The shape of this month's spending.",
        )
        category_body = QHBoxLayout()
        category_body.setSpacing(18)
        self.category_donut = DonutChart()
        self.category_donut.setMinimumSize(210, 200)
        category_body.addWidget(self.category_donut, 0)
        self.category_legend = QVBoxLayout()
        self.category_legend.setSpacing(2)
        category_body.addLayout(self.category_legend, 1)
        self.categories_card.body.addLayout(category_body)
        root.addWidget(self.categories_card)
        root.addStretch(1)

    # ------------------------------------------------------------------ refresh
    def refresh(self) -> None:
        self._dirty = False
        p = palette()
        month, year = self.period.period()
        summary = self.service.month_summary(month, year)
        prev_month, prev_year = self.service.previous_month(month, year)
        previous = self.service.month_summary(prev_month, prev_year)
        trends = self.service.rolling_trends(month, year, 6)
        expenses = [
            tx
            for tx in self.service.list_transactions(month=month, year=year)
            if tx.transaction_type == "expense"
        ]
        largest = max(expenses, key=lambda tx: tx.amount_paise) if expenses else None

        if (year, month) == (date.today().year, date.today().month):
            active_days = max(1, date.today().day)
        else:
            active_days = calendar.monthrange(year, month)[1]
        average = summary.total_expense_paise // active_days
        previous_average = (
            previous.total_expense_paise // calendar.monthrange(prev_year, prev_month)[1]
            if previous.total_expense_paise
            else 0
        )
        self.avg_stat.set_data(
            format_money(average),
            f"vs {format_money(previous_average)} last month"
            if previous_average
            else "No prior month to compare",
        )
        if summary.category_expenses:
            top_name, top_amount = next(iter(summary.category_expenses.items()))
            self.top_stat.set_data(top_name, format_money(top_amount))
        else:
            self.top_stat.set_data("—", "No expenses recorded")
        total = summary.total_expense_paise
        online_share = (summary.online_expense_paise / total * 100) if total else 0.0
        self.online_stat.set_data(
            f"{online_share:.0f}%",
            f"{format_money(summary.online_expense_paise)} online"
            if total
            else "No spending yet",
        )
        self.savings_stat.set_data(
            f"{summary.savings_rate:.0f}%"
            if summary.total_income_paise
            else "—",
            f"{format_money(summary.balance_paise)} net cash flow"
            if summary.total_income_paise
            else "No income this month",
        )

        self.trend_chart.render_expense_trend(trends)
        self.compare_chart.render_income_expense(trends)

        self.channel_donut.set_data(
            [
                ("Online", summary.online_expense_paise, p["accent2"]),
                ("Offline", summary.offline_expense_paise, p["warning"]),
            ],
            "This month",
        )
        self._clear_legend(self.channel_legend)
        for label, value, color in (
            ("Online", summary.online_expense_paise, p["accent2"]),
            ("Offline", summary.offline_expense_paise, p["warning"]),
        ):
            share = (value / total * 100) if total else 0.0
            self._add_legend(
                self.channel_legend,
                LegendRow(label, format_money(value), color, f"{share:.0f}% of spend"),
            )

        category_items = [
            (name, amount, CATEGORY_COLORS[i % len(CATEGORY_COLORS)])
            for i, (name, amount) in enumerate(summary.category_expenses.items())
        ]
        self.category_donut.set_data(category_items, "Total spend")
        self._clear_legend(self.category_legend)
        for name, amount, color in category_items[:5]:
            share = (amount / total * 100) if total else 0.0
            self._add_legend(
                self.category_legend,
                LegendRow(name, format_money(amount), color, f"{share:.1f}%"),
            )
        if not category_items:
            empty = QLabel("No spending recorded for this month yet.")
            empty.setObjectName("cardSubtitle")
            self.category_legend.addWidget(empty)

        method_items = [
            (name, amount, CATEGORY_COLORS[(i + 1) % len(CATEGORY_COLORS)])
            for i, (name, amount) in enumerate(summary.payment_method_expenses.items())
        ]
        self.methods_list.set_items(method_items)
        self.categories_card.set_subtitle(
            f"Your largest expense was {format_money(largest.amount_paise)} — {largest.category}."
            if largest
            else "The shape of this month's spending."
        )

    def _clear_legend(self, layout) -> None:  # noqa: ANN001
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _add_legend(self, layout, row: QWidget) -> None:  # noqa: ANN001
        layout.addWidget(row)

    def mark_dirty(self) -> None:
        self._dirty = True

    def apply_theme(self) -> None:
        self.refresh()
