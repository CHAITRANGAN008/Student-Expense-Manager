from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from student_expense_manager.data.db import get_connection


@dataclass(slots=True)
class Reminder:
    id: int | None
    title: str
    amount_paise: int
    due_date: str  # YYYY-MM-DD
    due_time: str | None  # HH:MM, optional
    category: str
    payment_method: str
    payment_channel: str  # 'online' | 'offline'
    description: str
    status: str = "upcoming"
    recurrence: str = "none"
    recurrence_end_date: str | None = None
    recurrence_count: int | None = None
    occurrence_index: int = 0
    series_id: int = 0
    notification_days: str = "7,3,1,0"
    notifications_enabled: bool = True
    created_at: str = ""
    updated_at: str = ""
    paid_at: str | None = None
    linked_transaction_id: int | None = None

    def schedule_offsets(self) -> list[int]:
        """Notification offsets, largest first, always including the due date."""
        offsets: list[int] = []
        for part in self.notification_days.split(","):
            part = part.strip()
            if part.isdigit():
                value = int(part)
                if value >= 0 and value not in offsets:
                    offsets.append(value)
        offsets.sort(reverse=True)
        if 0 not in offsets:
            offsets.append(0)
        return offsets


class ReminderRepository:
    """Data access for reminders and their delivered-notification ledger."""

    def add(self, reminder: Reminder) -> int:
        now = reminder.created_at or datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO reminders (
                    title, amount_paise, due_date, due_time, category, payment_method,
                    payment_channel, description, status, recurrence, recurrence_end_date,
                    recurrence_count, occurrence_index, series_id, notification_days,
                    notifications_enabled, created_at, updated_at, paid_at,
                    linked_transaction_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reminder.title,
                    reminder.amount_paise,
                    reminder.due_date,
                    reminder.due_time,
                    reminder.category,
                    reminder.payment_method,
                    reminder.payment_channel,
                    reminder.description,
                    reminder.status,
                    reminder.recurrence,
                    reminder.recurrence_end_date,
                    reminder.recurrence_count,
                    reminder.occurrence_index,
                    reminder.series_id,
                    reminder.notification_days,
                    1 if reminder.notifications_enabled else 0,
                    now,
                    reminder.updated_at or now,
                    reminder.paid_at,
                    reminder.linked_transaction_id,
                ),
            )
            reminder_id = int(cur.lastrowid)
            # A new series anchors itself; occurrences share this id so they can
            # be edited or removed together without touching other reminders.
            if reminder.series_id == 0:
                conn.execute(
                    "UPDATE reminders SET series_id=? WHERE id=?", (reminder_id, reminder_id)
                )
                reminder.series_id = reminder_id
            return reminder_id

    def add_batch(self, reminders: Iterable[Reminder]) -> list[int]:
        ids: list[int] = []
        with get_connection() as conn:
            for reminder in reminders:
                now = reminder.created_at or datetime.now(timezone.utc).isoformat()
                cur = conn.execute(
                    """
                    INSERT INTO reminders (
                        title, amount_paise, due_date, due_time, category, payment_method,
                        payment_channel, description, status, recurrence, recurrence_end_date,
                        recurrence_count, occurrence_index, series_id, notification_days,
                        notifications_enabled, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        reminder.title,
                        reminder.amount_paise,
                        reminder.due_date,
                        reminder.due_time,
                        reminder.category,
                        reminder.payment_method,
                        reminder.payment_channel,
                        reminder.description,
                        reminder.status,
                        reminder.recurrence,
                        reminder.recurrence_end_date,
                        reminder.recurrence_count,
                        reminder.occurrence_index,
                        reminder.series_id,
                        reminder.notification_days,
                        1 if reminder.notifications_enabled else 0,
                        now,
                        now,
                    ),
                )
                ids.append(int(cur.lastrowid))
        return ids

    def update(self, reminder: Reminder) -> None:
        if reminder.id is None:
            raise ValueError("Reminder id is required for update")
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE reminders SET
                    title=?, amount_paise=?, due_date=?, due_time=?, category=?,
                    payment_method=?, payment_channel=?, description=?, status=?,
                    recurrence=?, recurrence_end_date=?, recurrence_count=?,
                    notification_days=?, notifications_enabled=?, updated_at=?,
                    paid_at=?, linked_transaction_id=?
                WHERE id=?
                """,
                (
                    reminder.title,
                    reminder.amount_paise,
                    reminder.due_date,
                    reminder.due_time,
                    reminder.category,
                    reminder.payment_method,
                    reminder.payment_channel,
                    reminder.description,
                    reminder.status,
                    reminder.recurrence,
                    reminder.recurrence_end_date,
                    reminder.recurrence_count,
                    reminder.notification_days,
                    1 if reminder.notifications_enabled else 0,
                    datetime.now(timezone.utc).isoformat(),
                    reminder.paid_at,
                    reminder.linked_transaction_id,
                    reminder.id,
                ),
            )

    def propagate_series_details(self, series_id: int, reminder: Reminder, after_date: str) -> None:
        """Keep future occurrences in step with an edited root reminder."""
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE reminders SET
                    title=?, amount_paise=?, due_time=?, category=?, payment_method=?,
                    payment_channel=?, description=?, notification_days=?,
                    notifications_enabled=?, recurrence_end_date=?, recurrence_count=?,
                    updated_at=?
                WHERE series_id=? AND id<>? AND due_date>=?
                  AND status NOT IN ('paid', 'cancelled')
                """,
                (
                    reminder.title,
                    reminder.amount_paise,
                    reminder.due_time,
                    reminder.category,
                    reminder.payment_method,
                    reminder.payment_channel,
                    reminder.description,
                    reminder.notification_days,
                    1 if reminder.notifications_enabled else 0,
                    reminder.recurrence_end_date,
                    reminder.recurrence_count,
                    datetime.now(timezone.utc).isoformat(),
                    series_id,
                    reminder.id,
                    after_date,
                ),
            )

    def delete(self, reminder_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))

    def delete_series(self, series_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM reminders WHERE series_id=?", (series_id,))

    def delete_future_occurrences(self, series_id: int, after_date: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                DELETE FROM reminders
                WHERE series_id=? AND occurrence_index>0 AND due_date>=?
                  AND status NOT IN ('paid', 'cancelled')
                """,
                (series_id, after_date),
            )

    def get(self, reminder_id: int) -> Reminder | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM reminders WHERE id=?", (reminder_id,)
            ).fetchone()
        return self._row_to_reminder(row) if row else None

    def list(
        self,
        *,
        status: str | None = None,
        series_id: int | None = None,
        due_before: str | None = None,
        due_after: str | None = None,
        category: str | None = None,
        search: str | None = None,
        limit: int | None = None,
    ) -> list[Reminder]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if series_id is not None:
            clauses.append("series_id = ?")
            params.append(series_id)
        if due_before:
            clauses.append("due_date < ?")
            params.append(due_before)
        if due_after:
            clauses.append("due_date > ?")
            params.append(due_after)
        if category:
            clauses.append("category = ?")
            params.append(category)
        if search:
            clauses.append("(title LIKE ? OR category LIKE ? OR description LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = "SELECT * FROM reminders " + where + " ORDER BY due_date, due_time, id"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_reminder(row) for row in rows]

    def count_on_date(self, series_id: int, due_date: str) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM reminders WHERE series_id=? AND due_date=?",
                (series_id, due_date),
            ).fetchone()
        return int(row["n"]) if row else 0

    def mark_delivered(self, reminder_id: int, offset_days: int, due_date: str) -> bool:
        """Return True only when this alert was not already recorded."""
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO notification_deliveries
                    (reminder_id, offset_days, due_date, delivered_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    reminder_id,
                    offset_days,
                    due_date,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return cur.rowcount > 0

    def delivery_count(self) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM notification_deliveries"
            ).fetchone()
        return int(row["n"]) if row else 0

    @staticmethod
    def _row_to_reminder(row: Any) -> Reminder:
        return Reminder(
            id=int(row["id"]),
            title=str(row["title"]),
            amount_paise=int(row["amount_paise"]),
            due_date=str(row["due_date"]),
            due_time=str(row["due_time"]) if row["due_time"] else None,
            category=str(row["category"]),
            payment_method=str(row["payment_method"]),
            payment_channel=str(row["payment_channel"]),
            description=str(row["description"] or ""),
            status=str(row["status"]),
            recurrence=str(row["recurrence"]),
            recurrence_end_date=(
                str(row["recurrence_end_date"]) if row["recurrence_end_date"] else None
            ),
            recurrence_count=(
                int(row["recurrence_count"]) if row["recurrence_count"] is not None else None
            ),
            occurrence_index=int(row["occurrence_index"]),
            series_id=int(row["series_id"]),
            notification_days=str(row["notification_days"]),
            notifications_enabled=bool(row["notifications_enabled"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            paid_at=str(row["paid_at"]) if row["paid_at"] else None,
            linked_transaction_id=(
                int(row["linked_transaction_id"]) if row["linked_transaction_id"] else None
            ),
        )
