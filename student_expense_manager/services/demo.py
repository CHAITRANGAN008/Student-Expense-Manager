from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone

from student_expense_manager.repositories.reminder_repository import Reminder
from student_expense_manager.repositories.transaction_repository import Transaction
from student_expense_manager.services.finance_service import FinanceService


def _tx(day: date, hour: int, amount_paise: int, tx_type: str, category: str, channel: str, method: str, description: str) -> Transaction:
    created = datetime(day.year, day.month, day.day, hour, 15, tzinfo=timezone.utc).isoformat()
    return Transaction(
        id=None,
        amount_paise=amount_paise,
        transaction_type=tx_type,
        category=category,
        payment_channel=channel,
        payment_method=method,
        description=description,
        transaction_date=day.isoformat(),
        created_at=created,
    )


def seed_demo_data(service: FinanceService, today: date | None = None) -> bool:
    """Populate a friendly demo dataset into an empty database.

    Used only by screenshot mode (which points at a disposable demo data
    folder), never by the normal application launch.
    """
    if service.list_transactions():
        return False

    today = today or date.today()
    year, month = today.year, today.month
    last_day = min(today.day, calendar.monthrange(year, month)[1])

    def d(day: int, month_offset: int = 0) -> date:
        m, y = month, year
        for _ in range(month_offset):
            m, y = (12, y - 1) if m == 1 else (m - 1, y)
        max_day = calendar.monthrange(y, m)[1]
        return date(y, m, min(day, max_day))

    def safe_day(day: int, month_offset: int = 0) -> int:
        target = d(day, month_offset)
        return max(1, min(day, last_day if month_offset == 0 else target.day))

    rows = [
        # current month income
        _tx(d(1), 9, 1800000, "income", "Scholarship", "online", "Bank Transfer", "Merit scholarship credit"),
        _tx(d(3), 10, 600000, "income", "Pocket Money", "online", "UPI", "Monthly pocket money"),
        _tx(d(8), 18, 450000, "income", "Freelancing", "online", "Bank Transfer", "Landing page project"),
        # current month expenses
        _tx(d(2), 8, 320000, "expense", "Food & Canteen", "offline", "Cash", "Hostel mess subscription"),
        _tx(d(safe_day(4)), 11, 28000, "expense", "Food & Canteen", "online", "UPI", "Cafe coffee with friends"),
        _tx(d(5), 9, 65000, "expense", "Transport", "offline", "Cash", "Monthly bus pass"),
        _tx(d(6), 16, 42000, "expense", "Stationery", "offline", "Cash", "Notebooks and pens"),
        _tx(d(7), 21, 11900, "expense", "Subscriptions", "online", "UPI", "Music streaming plan"),
        _tx(d(9), 12, 29900, "expense", "Mobile Recharge", "online", "UPI", "Data pack recharge"),
        _tx(d(11), 19, 145000, "expense", "Groceries", "online", "Card", "Weekly groceries"),
        _tx(d(12), 20, 38000, "expense", "Entertainment", "online", "UPI", "Movie tickets"),
        _tx(d(13), 13, 18000, "expense", "Food & Canteen", "offline", "Cash", "Canteen lunch"),
        _tx(d(14), 17, 299900, "expense", "Shopping", "online", "Card", "Running shoes"),
        _tx(d(15), 10, 12000, "expense", "Snacks", "offline", "Cash", "Samosa and chai"),
        _tx(d(safe_day(16)), 15, 35000, "expense", "Stationery", "offline", "Cash", "Lab manual"),
        # previous month
        _tx(d(1, 1), 9, 1800000, "income", "Scholarship", "online", "Bank Transfer", "Scholarship instalment"),
        _tx(d(4, 1), 10, 600000, "income", "Pocket Money", "online", "UPI", "Monthly pocket money"),
        _tx(d(6, 1), 14, 240000, "expense", "Food & Canteen", "offline", "Cash", "Mess and canteen"),
        _tx(d(9, 1), 18, 189000, "expense", "Shopping", "online", "Card", "Winter jacket"),
        _tx(d(14, 1), 11, 90000, "expense", "Transport", "offline", "Cash", "Train tickets home"),
        _tx(d(21, 1), 20, 56000, "expense", "Entertainment", "online", "UPI", "Concert tickets"),
        # two months back
        _tx(d(2, 2), 9, 1800000, "income", "Scholarship", "online", "Bank Transfer", "Scholarship instalment"),
        _tx(d(7, 2), 12, 600000, "income", "Pocket Money", "online", "UPI", "Monthly pocket money"),
        _tx(d(10, 2), 13, 320000, "expense", "Food & Canteen", "offline", "Cash", "Mess subscription"),
        _tx(d(16, 2), 17, 129000, "expense", "Groceries", "online", "Card", "Monthly groceries"),
        # three months back
        _tx(d(3, 3), 9, 1500000, "income", "Scholarship", "online", "Bank Transfer", "Scholarship instalment"),
        _tx(d(5, 3), 10, 500000, "income", "Gifts", "offline", "Cash", "Birthday gift"),
        _tx(d(12, 3), 15, 280000, "expense", "Food & Canteen", "offline", "Cash", "Mess and snacks"),
        _tx(d(19, 3), 18, 99000, "expense", "Subscriptions", "online", "UPI", "Annual app plan"),
        # older income for a healthy all-time balance
        _tx(d(10, 4), 10, 1200000, "income", "Freelancing", "online", "Bank Transfer", "Poster design work"),
    ]
    for tx in rows:
        service.add_transaction(tx)

    service.set_budget(month, year, 1200000, None)
    service.set_budget(month, year, 400000, "Food & Canteen")
    service.set_budget(month, year, 300000, "Shopping")
    service.set_budget(month, year, 120000, "Transport")
    return True


def seed_demo_reminders(service, today: date | None = None) -> bool:
    """Populate a friendly reminder set for screenshot mode only."""
    if service.list_reminders():
        return False
    today = today or date.today()

    def reminder(
        title: str,
        amount_paise: int,
        offset: int,
        category: str,
        method: str,
        channel: str,
        description: str,
        **extra,
    ) -> Reminder:
        return Reminder(
            id=None,
            title=title,
            amount_paise=amount_paise,
            due_date=(today + timedelta(days=offset)).isoformat(),
            due_time=None,
            category=category,
            payment_method=method,
            payment_channel=channel,
            description=description,
            **extra,
        )

    rows = [
        reminder("Hostel mess bill", 320000, 0, "Food & Canteen", "Cash", "offline",
                 "Pay the warden before 6 PM."),
        reminder("Music subscription", 49900, 1, "Subscriptions", "UPI", "online",
                 "Auto-renewal for the student plan."),
        reminder("Late library fine", 150000, -2, "Education", "Cash", "offline",
                 "Returned the book two days late."),
        reminder("Semester fee instalment", 1200000, 7, "Education", "Bank Transfer", "online",
                 "Installment two of four.", recurrence="monthly", recurrence_count=4,
                 notification_days="7,3,1,0"),
        reminder("Mobile recharge", 89900, -5, "Mobile Recharge", "UPI", "online",
                 "Monthly data pack."),
        reminder("Stationery restock", 245000, 14, "Stationery", "Card", "online",
                 "Notebooks, pens and a sketchbook.", recurrence="none"),
    ]
    created = [service.add_reminder(row) for row in rows]
    service.mark_paid(created[4], create_expense=False, completion_date=today - timedelta(days=5))
    service.cancel_reminder(created[5])
    return True
