from __future__ import annotations

from datetime import date, timedelta

import pytest

from student_expense_manager.data.db import get_db_path, initialize_database
from student_expense_manager.repositories.reminder_repository import Reminder, ReminderRepository
from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.reminder_service import ReminderService, recurrence_dates


def make_reminder(
    title: str = "Hostel fee",
    amount_paise: int = 125000,
    due: date | None = None,
    category: str = "Education",
    payment_method: str = "UPI",
    payment_channel: str = "online",
    **kwargs,
) -> Reminder:
    return Reminder(
        id=None,
        title=title,
        amount_paise=amount_paise,
        due_date=(due or date.today()).isoformat(),
        due_time=None,
        category=category,
        payment_method=payment_method,
        payment_channel=payment_channel,
        description="Test payment",
        **kwargs,
    )


@pytest.fixture()
def services(temp_db):
    finance = FinanceService()
    reminders = ReminderService(finance=finance)
    return finance, reminders


def test_add_edit_and_delete_reminder(services):
    _finance, reminders = services
    reminder_id = reminders.add_reminder(make_reminder())
    stored = reminders.get(reminder_id)
    assert stored is not None
    assert stored.title == "Hostel fee"
    assert stored.amount_paise == 125000

    stored.title = "Hostel fee (revised)"
    stored.amount_paise = 130000
    reminders.update_reminder(stored)
    assert reminders.get(reminder_id).title == "Hostel fee (revised)"
    assert reminders.get(reminder_id).amount_paise == 130000

    reminders.delete_reminder(reminder_id)
    assert reminders.get(reminder_id) is None
    assert reminders.summary()["total"] == 0


def test_due_date_status_calculation(services):
    _finance, reminders = services
    today = date.today()
    ids = [
        reminders.add_reminder(make_reminder("Future", due=today + timedelta(days=3))),
        reminders.add_reminder(make_reminder("Today", due=today)),
        reminders.add_reminder(make_reminder("Past", due=today - timedelta(days=1))),
    ]
    statuses = [reminders.effective_status(reminders.get(i), today) for i in ids]
    assert statuses == ["upcoming", "due_today", "overdue"]
    assert reminders.days_until_due(reminders.get(ids[0]), today) == 3


def test_overdue_is_derived_from_date_not_stored_value(services):
    _finance, reminders = services
    yesterday = date.today() - timedelta(days=1)
    reminder_id = reminders.add_reminder(make_reminder("Overdue", due=yesterday))
    assert reminders.get(reminder_id).status == "upcoming"
    assert reminders.effective_status(reminders.get(reminder_id)) == "overdue"
    assert len(reminders.overdue_reminders()) == 1


def test_notification_schedule_is_delivered_once(services):
    _finance, reminders = services
    reminder_id = reminders.add_reminder(
        make_reminder("Due now", due=date.today(), notification_days="7,3,1,0")
    )
    first = reminders.poll_notifications()
    assert any(message["reminder_id"] == reminder_id for message in first)
    assert reminders.poll_notifications() == []
    assert ReminderRepository().delivery_count() == 1


def test_notifications_after_restart_are_not_duplicated(services):
    _finance, reminders = services
    reminder_id = reminders.add_reminder(make_reminder("Restart", due=date.today() - timedelta(days=2)))
    reminders.poll_notifications()
    assert reminders.poll_notifications() == []
    # A fresh service instance models an application restart.
    restarted = ReminderService(finance=FinanceService())
    messages = restarted.poll_notifications()
    assert all(message["reminder_id"] != reminder_id for message in messages)


def test_disabled_notifications_are_skipped(services):
    _finance, reminders = services
    reminders.add_reminder(
        make_reminder("Quiet", due=date.today(), notifications_enabled=False)
    )
    assert reminders.poll_notifications() == []


def test_recurrence_creates_future_occurrences_without_duplicates(services):
    _finance, reminders = services
    start = date.today() + timedelta(days=2)
    root_id = reminders.add_reminder(
        make_reminder("Rent", amount_paise=900000, due=start,
                      recurrence="monthly", recurrence_count=4)
    )
    series = reminders.list_reminders(series_id=root_id)
    assert len(series) == 4
    assert len({reminder.due_date for reminder in series}) == 4

    root = reminders.get(root_id)
    root.amount_paise = 950000
    reminders.update_reminder(root)
    updated = reminders.list_reminders(series_id=root_id)
    assert len(updated) == 4
    assert all(item.amount_paise == 950000 for item in updated)


def test_recurrence_dates_clamp_month_end():
    dates = recurrence_dates(date(2026, 1, 31), "monthly", count=3)
    assert [item.day for item in dates] == [31, 28, 31]


def test_mark_paid_creates_exactly_one_linked_expense(services):
    finance, reminders = services
    reminder_id = reminders.add_reminder(make_reminder("Electricity", amount_paise=240000))
    updated, tx_id, changed = reminders.mark_paid(reminder_id, True)
    assert changed is True
    assert tx_id is not None
    assert updated.paid_at
    assert updated.linked_transaction_id == tx_id
    assert len(finance.list_transactions()) == 1

    again, second_tx, changed_again = reminders.mark_paid(reminder_id, True)
    assert changed_again is False
    assert second_tx == tx_id
    assert len(finance.list_transactions()) == 1
    assert reminders.effective_status(again) == "paid"


def test_mark_paid_without_expense_does_not_touch_ledger(services):
    finance, reminders = services
    reminder_id = reminders.add_reminder(make_reminder("Gift", amount_paise=10000))
    _updated, tx_id, changed = reminders.mark_paid(reminder_id, False)
    assert changed is True
    assert tx_id is None
    assert finance.list_transactions() == []


def test_summary_counts_and_pending_amount(services):
    _finance, reminders = services
    assert reminders.summary()["active"] == 0
    assert reminders.summary()["pending_paise"] == 0
    reminders.add_reminder(make_reminder("A", 10000, due=date.today() + timedelta(days=2)))
    reminders.add_reminder(make_reminder("B", 20000, due=date.today()))
    reminders.add_reminder(make_reminder("C", 30000, due=date.today() - timedelta(days=1)))
    summary = reminders.summary()
    assert summary["active"] == 3
    assert summary["upcoming"] == 1
    assert summary["due_today"] == 1
    assert summary["overdue"] == 1
    assert summary["pending_paise"] == 60000


def test_invalid_reminders_are_rejected(services):
    _finance, reminders = services
    with pytest.raises(ValueError):
        reminders.add_reminder(make_reminder("", amount_paise=100))
    with pytest.raises(ValueError):
        reminders.add_reminder(make_reminder("Zero", amount_paise=0))
    with pytest.raises(ValueError):
        reminders.add_reminder(make_reminder("Bad date", due=date.today(), payment_method=""))
    with pytest.raises(ValueError):
        reminders.add_reminder(make_reminder("Bad date", payment_channel="carrier-pigeon"))


def test_persistence_across_instances(services):
    _finance, reminders = services
    reminder_id = reminders.add_reminder(make_reminder("Persist", amount_paise=55500))
    reloaded = ReminderService(finance=FinanceService()).get(reminder_id)
    assert reloaded is not None
    assert reloaded.title == "Persist"
    assert reloaded.amount_paise == 55500


def test_migration_adds_reminder_tables_without_deleting_data(temp_db):
    path = get_db_path()
    path.unlink(missing_ok=True)
    # Simulate a version-2 database containing one precious transaction.
    import sqlite3

    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE schema_meta (id INTEGER PRIMARY KEY CHECK (id=1), version INTEGER NOT NULL,
                                  updated_at TEXT NOT NULL);
        INSERT INTO schema_meta VALUES (1, 2, '2026-01-01T00:00:00+00:00');
        CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
            transaction_type TEXT NOT NULL, category TEXT NOT NULL,
            payment_channel TEXT NOT NULL, payment_method TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '', transaction_date TEXT NOT NULL,
            created_at TEXT NOT NULL);
        INSERT INTO transactions (amount_paise, transaction_type, category, payment_channel,
                                  payment_method, description, transaction_date, created_at)
        VALUES (987654, 'expense', 'Food', 'offline', 'Cash', 'precious', '2026-01-01',
                '2026-01-01T00:00:00+00:00');
        """
    )
    connection.commit()
    connection.close()

    initialize_database()
    finance = FinanceService()
    assert len(finance.list_transactions()) == 1
    assert finance.list_transactions()[0].amount_paise == 987654
    assert ReminderService(finance=finance).summary()["total"] == 0
