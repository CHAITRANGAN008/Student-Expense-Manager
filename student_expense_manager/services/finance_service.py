from __future__ import annotations

import calendar
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from student_expense_manager.repositories.budget_repository import Budget, BudgetRepository
from student_expense_manager.repositories.transaction_repository import Transaction, TransactionRepository
from student_expense_manager.services.money import paise_to_rupees_float_str


@dataclass(slots=True)
class PeriodSummary:
    total_income_paise: int
    total_expense_paise: int
    balance_paise: int
    online_expense_paise: int
    offline_expense_paise: int
    category_expenses: dict[str, int]
    payment_method_expenses: dict[str, int]

    @property
    def savings_rate(self) -> float:
        if self.total_income_paise <= 0:
            return 0.0
        return (self.balance_paise / self.total_income_paise) * 100


class FinanceService:
    def __init__(
        self,
        tx_repo: TransactionRepository | None = None,
        budget_repo: BudgetRepository | None = None,
    ) -> None:
        self.tx_repo = tx_repo or TransactionRepository()
        self.budget_repo = budget_repo or BudgetRepository()

    # ------------------------------------------------------------------ transactions
    def add_transaction(self, tx: Transaction) -> int:
        self._validate_transaction(tx)
        return self.tx_repo.add(tx)

    def update_transaction(self, tx: Transaction) -> None:
        self._validate_transaction(tx)
        if tx.id is None:
            raise ValueError("Transaction id required")
        self.tx_repo.update(tx)

    def delete_transaction(self, tx_id: int) -> None:
        self.tx_repo.delete(tx_id)

    def get_transaction(self, tx_id: int) -> Transaction | None:
        return self.tx_repo.get(tx_id)

    def list_transactions(self, **filters) -> list[Transaction]:
        return self.tx_repo.list(**filters)

    def categories(self, transaction_type: str | None = None) -> list[str]:
        txs = self.tx_repo.list(transaction_type=transaction_type)
        return sorted({t.category for t in txs if t.category})

    def payment_methods(self) -> list[str]:
        txs = self.tx_repo.list()
        return sorted({t.payment_method for t in txs if t.payment_method})

    # ------------------------------------------------------------------ budgets
    def set_budget(self, month: int, year: int, amount_paise: int, category: str | None = None) -> int:
        if amount_paise <= 0:
            raise ValueError("Budget amount must be greater than zero")
        if not (1 <= int(month) <= 12):
            raise ValueError("Invalid month")
        if not (2000 <= int(year) <= 2100):
            raise ValueError("Invalid year")
        return self.budget_repo.upsert(
            Budget(id=None, month=month, year=year, category=category, amount_paise=amount_paise)
        )

    def delete_budget(self, budget_id: int) -> None:
        self.budget_repo.delete(budget_id)

    def list_budgets(self, month: int, year: int) -> list[Budget]:
        return self.budget_repo.list_for_period(month, year)

    def overall_budget(self, month: int, year: int) -> Budget | None:
        return self.budget_repo.get_overall(month, year)

    # ------------------------------------------------------------------ analytics
    def summarize(self, txs: list[Transaction]) -> PeriodSummary:
        total_income = sum(t.amount_paise for t in txs if t.transaction_type == "income")
        total_expense = sum(t.amount_paise for t in txs if t.transaction_type == "expense")
        online = sum(
            t.amount_paise
            for t in txs
            if t.transaction_type == "expense" and t.payment_channel == "online"
        )
        offline = sum(
            t.amount_paise
            for t in txs
            if t.transaction_type == "expense" and t.payment_channel == "offline"
        )
        cat: dict[str, int] = defaultdict(int)
        pm: dict[str, int] = defaultdict(int)
        for t in txs:
            if t.transaction_type == "expense":
                cat[t.category] += t.amount_paise
                pm[t.payment_method] += t.amount_paise
        return PeriodSummary(
            total_income_paise=total_income,
            total_expense_paise=total_expense,
            balance_paise=total_income - total_expense,
            online_expense_paise=online,
            offline_expense_paise=offline,
            category_expenses=dict(sorted(cat.items(), key=lambda kv: kv[1], reverse=True)),
            payment_method_expenses=dict(sorted(pm.items(), key=lambda kv: kv[1], reverse=True)),
        )

    def month_summary(self, month: int, year: int) -> PeriodSummary:
        return self.summarize(self.tx_repo.list(month=month, year=year))

    def range_summary(self, start_date: str, end_date: str) -> PeriodSummary:
        return self.summarize(self.tx_repo.list(start_date=start_date, end_date=end_date))

    def overall_summary(self) -> PeriodSummary:
        return self.summarize(self.tx_repo.list())

    def previous_month(self, month: int, year: int) -> tuple[int, int]:
        if month == 1:
            return 12, year - 1
        return month - 1, year

    def month_delta(self, month: int, year: int, field: str) -> tuple[int, int]:
        """Return (current, previous) paise for income/expense/balance."""
        cur = self.month_summary(month, year)
        pm, py = self.previous_month(month, year)
        prev = self.month_summary(pm, py)
        return int(getattr(cur, field)), int(getattr(prev, field))

    def highest_spending_category(self, month: int, year: int) -> tuple[str, int] | None:
        summary = self.month_summary(month, year)
        if not summary.category_expenses:
            return None
        cat = max(summary.category_expenses, key=summary.category_expenses.get)
        return cat, summary.category_expenses[cat]

    def daily_expenses(self, month: int, year: int) -> dict[int, int]:
        """Expense totals per day of the month, used by the dashboard calendar."""
        daily: dict[int, int] = defaultdict(int)
        for tx in self.tx_repo.list(month=month, year=year):
            if tx.transaction_type != "expense":
                continue
            try:
                day = int(tx.transaction_date.rsplit("-", 1)[1])
            except (IndexError, ValueError):
                continue
            daily[day] += tx.amount_paise
        return dict(daily)

    def budget_status(self, month: int, year: int) -> list[dict]:
        budgets = self.budget_repo.list_for_period(month, year)
        summary = self.month_summary(month, year)
        statuses = []
        for b in budgets:
            if b.category is None:
                spent = summary.total_expense_paise
                label = "Overall"
            else:
                spent = summary.category_expenses.get(b.category, 0)
                label = b.category
            pct = (spent / b.amount_paise * 100) if b.amount_paise else 0.0
            level = "ok"
            if pct >= 100:
                level = "exceeded"
            elif pct >= 80:
                level = "warning"
            statuses.append(
                {
                    "id": b.id,
                    "label": label,
                    "category": b.category,
                    "budget_paise": b.amount_paise,
                    "spent_paise": spent,
                    "remaining_paise": b.amount_paise - spent,
                    "percent": pct,
                    "level": level,
                }
            )
        return statuses

    def monthly_trends(self, year: int) -> list[dict]:
        trends = []
        for m in range(1, 13):
            s = self.month_summary(m, year)
            trends.append(
                {
                    "month": m,
                    "income_paise": s.total_income_paise,
                    "expense_paise": s.total_expense_paise,
                }
            )
        return trends

    def rolling_trends(self, month: int, year: int, count: int = 6) -> list[dict]:
        """The `count` months ending at the selected month, oldest first."""
        points: list[tuple[int, int]] = []
        m, y = month, year
        for _ in range(count):
            points.append((m, y))
            m, y = (12, y - 1) if m == 1 else (m - 1, y)
        points.reverse()
        result = []
        for m, y in points:
            s = self.month_summary(m, y)
            result.append(
                {
                    "month": m,
                    "year": y,
                    "label": calendar.month_abbr[m],
                    "income_paise": s.total_income_paise,
                    "expense_paise": s.total_expense_paise,
                }
            )
        return result

    def monthly_report(self, month: int, year: int) -> dict:
        s = self.month_summary(month, year)
        txs = self.tx_repo.list(month=month, year=year)
        expenses = [t for t in txs if t.transaction_type == "expense"]
        largest = sorted(expenses, key=lambda t: t.amount_paise, reverse=True)[:5]
        return {
            "month": month,
            "year": year,
            "month_name": calendar.month_name[month],
            "total_income_paise": s.total_income_paise,
            "total_expense_paise": s.total_expense_paise,
            "net_cash_flow_paise": s.total_income_paise - s.total_expense_paise,
            "savings_rate": s.savings_rate,
            "category_breakdown": s.category_expenses,
            "online_expense_paise": s.online_expense_paise,
            "offline_expense_paise": s.offline_expense_paise,
            "payment_method_expenses": s.payment_method_expenses,
            "budget_utilization": self.budget_status(month, year),
            "largest_transactions": largest,
            "transactions": txs,
        }

    def range_report(self, start_date: str, end_date: str) -> dict:
        txs = self.tx_repo.list(start_date=start_date, end_date=end_date)
        s = self.summarize(txs)
        expenses = [t for t in txs if t.transaction_type == "expense"]
        largest = sorted(expenses, key=lambda t: t.amount_paise, reverse=True)[:5]
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if end < start:
            raise ValueError("End date must be on or after the start date")

        # Budgets only make sense for a single calendar month.
        budget_rows: list[dict] = []
        if (start.year, start.month) == (end.year, end.month):
            budget_rows = self.budget_status(start.month, start.year)

        daily: list[dict] = []
        day = start
        by_day: dict[str, int] = defaultdict(int)
        for t in txs:
            if t.transaction_type == "expense":
                by_day[t.transaction_date] += t.amount_paise
        while day <= end:
            key = day.isoformat()
            daily.append({"date": key, "expense_paise": by_day.get(key, 0)})
            day += timedelta(days=1)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "period_label": f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}",
            "total_income_paise": s.total_income_paise,
            "total_expense_paise": s.total_expense_paise,
            "net_cash_flow_paise": s.total_income_paise - s.total_expense_paise,
            "savings_rate": s.savings_rate,
            "category_breakdown": s.category_expenses,
            "online_expense_paise": s.online_expense_paise,
            "offline_expense_paise": s.offline_expense_paise,
            "payment_method_expenses": s.payment_method_expenses,
            "budget_utilization": budget_rows,
            "largest_transactions": largest,
            "transactions": txs,
            "daily": daily,
        }

    def day_count(self, month: int, year: int) -> int:
        return calendar.monthrange(year, month)[1]

    # ------------------------------------------------------------------ CSV (kept for data portability)
    def export_transactions_csv(self, path: str | Path, **filters) -> Path:
        txs = self.list_transactions(**filters)
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "ID",
                    "Date",
                    "Type",
                    "Category",
                    "Payment Channel",
                    "Payment Method",
                    "Description",
                    "Amount",
                    "Created At",
                ]
            )
            for t in txs:
                writer.writerow(
                    [
                        t.id,
                        t.transaction_date,
                        t.transaction_type,
                        t.category,
                        t.payment_channel,
                        t.payment_method,
                        t.description,
                        paise_to_rupees_float_str(t.amount_paise),
                        t.created_at,
                    ]
                )
        return out

    def export_monthly_summary_csv(self, path: str | Path, month: int, year: int) -> Path:
        report = self.monthly_report(month, year)
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Student Expense Manager - Monthly Summary"])
            writer.writerow(["Month", f"{report['month_name']} {report['year']}"])
            writer.writerow(["Total Income", paise_to_rupees_float_str(report["total_income_paise"])])
            writer.writerow(["Total Expenses", paise_to_rupees_float_str(report["total_expense_paise"])])
            writer.writerow(["Net Cash Flow", paise_to_rupees_float_str(report["net_cash_flow_paise"])])
            writer.writerow([])
            writer.writerow(["Category Breakdown"])
            writer.writerow(["Category", "Amount"])
            for cat, amt in report["category_breakdown"].items():
                writer.writerow([cat, paise_to_rupees_float_str(amt)])
            writer.writerow([])
            writer.writerow(["Online/Offline Breakdown"])
            writer.writerow(["Online Expenses", paise_to_rupees_float_str(report["online_expense_paise"])])
            writer.writerow(["Offline Expenses", paise_to_rupees_float_str(report["offline_expense_paise"])])
            writer.writerow([])
            writer.writerow(["Budget Utilization"])
            writer.writerow(["Budget", "Limit", "Spent", "Used %", "Status"])
            for b in report["budget_utilization"]:
                writer.writerow(
                    [
                        b["label"],
                        paise_to_rupees_float_str(b["budget_paise"]),
                        paise_to_rupees_float_str(b["spent_paise"]),
                        f"{b['percent']:.1f}",
                        b["level"],
                    ]
                )
            writer.writerow([])
            writer.writerow(["Largest Transactions"])
            writer.writerow(["Date", "Description", "Category", "Payment Method", "Amount"])
            for t in report["largest_transactions"]:
                writer.writerow(
                    [
                        t.transaction_date,
                        t.description,
                        t.category,
                        t.payment_method,
                        paise_to_rupees_float_str(t.amount_paise),
                    ]
                )
        return out

    # ------------------------------------------------------------------ validation
    @staticmethod
    def _validate_transaction(tx: Transaction) -> None:
        if tx.amount_paise <= 0:
            raise ValueError("Amount must be greater than zero")
        if tx.transaction_type not in {"income", "expense"}:
            raise ValueError("Invalid transaction type")
        if tx.payment_channel not in {"online", "offline"}:
            raise ValueError("Invalid payment channel")
        if not tx.category.strip():
            raise ValueError("Category is required")
        if not tx.payment_method.strip():
            raise ValueError("Payment method is required")
        date.fromisoformat(tx.transaction_date)
