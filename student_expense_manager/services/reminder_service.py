from __future__ import annotations

import calendar
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from student_expense_manager.repositories.reminder_repository import Reminder, ReminderRepository
from student_expense_manager.repositories.transaction_repository import Transaction
from student_expense_manager.services.finance_service import FinanceService

ACTIVE_STATUSES = {"upcoming", "due_today", "overdue"}
STATUSES = {"upcoming", "due_today", "overdue", "paid", "cancelled"}
RECURRENCES = {"none", "daily", "weekly", "monthly", "yearly"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _add_months(day: date, count: int) -> date:
    month_index = day.month - 1 + count
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def recurrence_dates(
    start: date,
    recurrence: str,
    end_date: date | None = None,
    count: int | None = None,
    *,
    max_occurrences: int = 240,
) -> list[date]:
    """Return future dates for a recurring payment, including the first one.

    Month-end and leap-day starts are clamped to the last valid day of the
    target month, so a 31 January reminder becomes 28/29 February rather than
    silently skipping a period.  A hard cap keeps a bad configuration from
    filling the database.
    """
    if recurrence not in RECURRENCES:
        raise ValueError("Invalid recurrence")
    if recurrence == "none":
        return [start]
    if count is not None and count < 1:
        raise ValueError("Occurrences must be at least 1")

    dates = [start]
    limit = count if count is not None else max_occurrences
    limit = min(limit, max_occurrences)
    horizon = start + timedelta(days=366 * 5)
    while len(dates) < limit:
        if recurrence == "daily":
            following = dates[-1] + timedelta(days=1)
        elif recurrence == "weekly":
            following = dates[-1] + timedelta(days=7)
        elif recurrence == "monthly":
            following = _add_months(start, len(dates))
        else:
            following = date(
                start.year + len(dates),
                start.month,
                min(start.day, calendar.monthrange(start.year + len(dates), start.month)[1]),
            )
        if following > horizon:
            break
        if end_date is not None and following > end_date:
            break
        dates.append(following)
    return dates


class ReminderService:
    """Business rules for the Payment Reminder Center.

    The service never touches Qt: it is usable from the UI, from tests and
    from a future command-line maintenance tool alike.
    """

    def __init__(
        self,
        repo: ReminderRepository | None = None,
        finance: FinanceService | None = None,
    ) -> None:
        self.repo = repo or ReminderRepository()
        self.finance = finance or FinanceService()

    # ------------------------------------------------------------------ CRUD
    def add_reminder(self, reminder: Reminder, today: date | None = None) -> int:
        """Store a reminder and safely expand its future occurrences."""
        self._validate(reminder)
        today = today or date.today()
        clean = replace(reminder, id=None, status="upcoming", created_at=_now(), updated_at=_now())
        root_id = self.repo.add(clean)
        clean.series_id = clean.series_id or root_id

        if clean.recurrence != "none":
            start = date.fromisoformat(clean.due_date)
            end = date.fromisoformat(clean.recurrence_end_date) if clean.recurrence_end_date else None
            dates = recurrence_dates(start, clean.recurrence, end, clean.recurrence_count)
            occurrences: list[Reminder] = []
            for index, occurrence_date in enumerate(dates[1:], start=1):
                key = occurrence_date.isoformat()
                if self.repo.count_on_date(clean.series_id, key):
                    continue  # already present: never create a duplicate
                occurrences.append(
                    replace(
                        clean,
                        id=None,
                        due_date=key,
                        occurrence_index=index,
                        status="upcoming",
                        paid_at=None,
                        linked_transaction_id=None,
                    )
                )
            if occurrences:
                self.repo.add_batch(occurrences)
        return root_id

    def update_reminder(self, reminder: Reminder, today: date | None = None) -> None:
        if reminder.id is None:
            raise ValueError("Reminder id is required")
        self._validate(reminder)
        today = today or date.today()
        original = self.repo.get(reminder.id)
        if original is None:
            raise ValueError("Reminder no longer exists")

        if original.status in {"paid", "cancelled"}:
            updated = replace(
                reminder,
                status=original.status,
                created_at=original.created_at,
                paid_at=original.paid_at,
                linked_transaction_id=original.linked_transaction_id,
                series_id=original.series_id,
                occurrence_index=original.occurrence_index,
            )
            self.repo.update(updated)
            return

        updated = replace(
            reminder,
            status=original.status,
            created_at=original.created_at,
            paid_at=original.paid_at,
            linked_transaction_id=original.linked_transaction_id,
            series_id=original.series_id,
            occurrence_index=original.occurrence_index,
        )
        self.repo.update(updated)

        if original.occurrence_index != 0 or original.recurrence == "none":
            return

        # The root of a recurring series controls all its future occurrences.
        self.repo.propagate_series_details(original.series_id, updated, today.isoformat())
        schedule_changed = (
            original.due_date != updated.due_date
            or original.recurrence != updated.recurrence
            or original.recurrence_end_date != updated.recurrence_end_date
            or original.recurrence_count != updated.recurrence_count
        )
        if not schedule_changed:
            return

        self.repo.delete_future_occurrences(original.series_id, today.isoformat())
        if updated.recurrence == "none":
            return
        start = date.fromisoformat(updated.due_date)
        end = date.fromisoformat(updated.recurrence_end_date) if updated.recurrence_end_date else None
        generated = recurrence_dates(start, updated.recurrence, end, updated.recurrence_count)
        for index, day in enumerate(generated[1:], start=1):
            key = day.isoformat()
            if self.repo.count_on_date(updated.series_id, key):
                continue
            self.repo.add_batch(
                [
                    replace(
                        updated,
                        id=None,
                        due_date=key,
                        occurrence_index=index,
                        status="upcoming",
                        paid_at=None,
                        linked_transaction_id=None,
                    )
                ]
            )

    def delete_reminder(self, reminder_id: int, whole_series: bool = False) -> None:
        reminder = self.repo.get(reminder_id)
        if reminder is None:
            return
        if whole_series and reminder.series_id:
            self.repo.delete_series(reminder.series_id)
        else:
            self.repo.delete(reminder_id)

    def get(self, reminder_id: int) -> Reminder | None:
        return self.repo.get(reminder_id)

    def list_reminders(self, **filters) -> list[Reminder]:
        return self.repo.list(**filters)

    def cancel_reminder(self, reminder_id: int) -> None:
        reminder = self.repo.get(reminder_id)
        if reminder is None:
            return
        self.repo.update(replace(reminder, status="cancelled"))

    # ------------------------------------------------------------------ status
    @staticmethod
    def effective_status(reminder: Reminder, today: date | None = None) -> str:
        if reminder.status in {"paid", "cancelled"}:
            return reminder.status
        today = today or date.today()
        due = date.fromisoformat(reminder.due_date)
        if due < today:
            return "overdue"
        if due == today:
            return "due_today"
        return "upcoming"

    def sections(self, today: date | None = None) -> dict[str, list[Reminder]]:
        today = today or date.today()
        buckets: dict[str, list[Reminder]] = {
            "all": [],
            "upcoming": [],
            "due_today": [],
            "overdue": [],
            "paid": [],
            "cancelled": [],
        }
        for reminder in self.repo.list():
            status = self.effective_status(reminder, today)
            buckets["all"].append(reminder)
            buckets.setdefault(status, []).append(reminder)
        return buckets

    def summary(self, today: date | None = None) -> dict[str, int]:
        sections = self.sections(today)
        pending = sum(
            r.amount_paise
            for status in ("upcoming", "due_today", "overdue")
            for r in sections[status]
        )
        return {
            "active": len(sections["upcoming"]) + len(sections["due_today"]) + len(sections["overdue"]),
            "upcoming": len(sections["upcoming"]),
            "due_today": len(sections["due_today"]),
            "overdue": len(sections["overdue"]),
            "paid": len(sections["paid"]),
            "cancelled": len(sections["cancelled"]),
            "total": len(sections["all"]),
            "pending_paise": pending,
        }

    def overdue_reminders(self, today: date | None = None) -> list[Reminder]:
        return self.sections(today)["overdue"]

    def days_until_due(self, reminder: Reminder, today: date | None = None) -> int:
        today = today or date.today()
        return (date.fromisoformat(reminder.due_date) - today).days

    # ---------------------------------------------------------- notifications
    def notifications_due(
        self, reminder: Reminder, today: date | None = None
    ) -> list[dict]:
        """Alerts whose scheduled day is today and that were never delivered."""
        today = today or date.today()
        if not reminder.notifications_enabled:
            return []
        status = self.effective_status(reminder, today)
        if status in {"paid", "cancelled"}:
            return []
        due = date.fromisoformat(reminder.due_date)
        messages: list[dict] = []
        for offset in reminder.schedule_offsets():
            target = due - timedelta(days=offset)
            if target != today:
                continue
            if self.repo.mark_delivered(reminder.id, offset, reminder.due_date):
                when = "today" if offset == 0 else f"in {offset} day{'s' if offset != 1 else ''}"
                messages.append(
                    {
                        "reminder_id": reminder.id,
                        "title": f"Payment due {when}",
                        "body": f"{reminder.title} · ₹{reminder.amount_paise / 100:,.2f}",
                        "tone": "warning" if offset <= 1 else "accent",
                        "offset": offset,
                    }
                )
        # A reminder that became overdue while the app was closed still needs
        # one catch-up alert, recorded against its original due date so the
        # restart check never repeats it.
        if status == "overdue" and self.repo.mark_delivered(reminder.id, 0, reminder.due_date):
            messages.append(
                {
                    "reminder_id": reminder.id,
                    "title": "Payment is overdue",
                    "body": f"{reminder.title} was due on {due.strftime('%d %b %Y')}",
                    "tone": "danger",
                    "offset": 0,
                }
            )
        return messages

    def poll_notifications(self, today: date | None = None) -> list[dict]:
        today = today or date.today()
        messages: list[dict] = []
        overdue = self.overdue_reminders(today)
        for reminder in self.sections(today)["all"]:
            messages.extend(self.notifications_due(reminder, today))
        if overdue and self.repo.mark_delivered(
            overdue[0].id, -1, today.isoformat()
        ):
            messages.append(
                {
                    "reminder_id": overdue[0].id,
                    "title": "Overdue payments",
                    "body": (
                        f"{len(overdue)} payment{'s' if len(overdue) != 1 else ''} need attention"
                    ),
                    "tone": "danger",
                    "offset": -1,
                }
            )
        return messages

    def startup_check(self, today: date | None = None) -> dict:
        """Called when the app opens: catches up on missed and overdue alerts."""
        today = today or date.today()
        return {
            "overdue": self.overdue_reminders(today),
            "due_today": self.sections(today)["due_today"],
            "notifications": self.poll_notifications(today),
        }

    def toggle_notifications(self, reminder_id: int, enabled: bool) -> None:
        reminder = self.repo.get(reminder_id)
        if reminder is not None:
            self.repo.update(replace(reminder, notifications_enabled=bool(enabled)))

    # ------------------------------------------------------------------ paid
    def mark_paid(
        self,
        reminder_id: int,
        create_expense: bool,
        completion_date: date | None = None,
    ) -> tuple[Reminder, int | None, bool]:
        """Mark a reminder paid, optionally creating exactly one expense.

        Returns (reminder, linked_transaction_id, changed).  Calling this a
        second time is harmless: it reports ``changed=False`` and never
        creates another transaction.
        """
        reminder = self.repo.get(reminder_id)
        if reminder is None:
            raise ValueError("Reminder not found")
        status = self.effective_status(reminder)
        if status == "paid":
            return reminder, reminder.linked_transaction_id, False
        if status == "cancelled":
            raise ValueError("A cancelled reminder cannot be paid")

        completed = completion_date or date.today()
        paid_at = _now()
        linked_id = reminder.linked_transaction_id
        if create_expense:
            if linked_id is not None:
                raise ValueError("An expense is already linked to this reminder")
            tx = Transaction(
                id=None,
                amount_paise=reminder.amount_paise,
                transaction_type="expense",
                category=reminder.category,
                payment_channel=reminder.payment_channel,
                payment_method=reminder.payment_method,
                description=f"Payment: {reminder.title}",
                transaction_date=completed.isoformat(),
                created_at=paid_at,
            )
            linked_id = self.finance.add_transaction(tx)
        updated = replace(
            reminder,
            status="paid",
            paid_at=paid_at,
            linked_transaction_id=linked_id,
        )
        self.repo.update(updated)
        return updated, linked_id, True

    # ------------------------------------------------------------------ rules
    @staticmethod
    def _validate(reminder: Reminder) -> None:
        if not reminder.title.strip():
            raise ValueError("Payment title is required")
        if not isinstance(reminder.amount_paise, int) or reminder.amount_paise <= 0:
            raise ValueError("Amount must be a positive whole number of paise")
        try:
            date.fromisoformat(reminder.due_date)
        except (TypeError, ValueError) as exc:
            raise ValueError("Enter a valid due date") from exc
        if reminder.due_time:
            try:
                hours, minutes = (int(part) for part in reminder.due_time.split(":"))
            except (TypeError, ValueError) as exc:
                raise ValueError("Enter a valid due time") from exc
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError("Enter a valid due time")
        if not reminder.category.strip():
            raise ValueError("Category is required")
        if not reminder.payment_method.strip():
            raise ValueError("Payment method is required")
        if reminder.payment_channel not in {"online", "offline"}:
            raise ValueError("Invalid payment channel")
        if reminder.recurrence not in RECURRENCES:
            raise ValueError("Invalid recurrence")
        if reminder.recurrence_end_date:
            try:
                date.fromisoformat(reminder.recurrence_end_date)
            except (TypeError, ValueError) as exc:
                raise ValueError("Enter a valid recurrence end date") from exc
        if reminder.recurrence_count is not None and reminder.recurrence_count < 1:
            raise ValueError("Occurrences must be at least 1")
        offsets = reminder.schedule_offsets()
        if any(value > 365 for value in offsets):
            raise ValueError("Notification offset is too large")
