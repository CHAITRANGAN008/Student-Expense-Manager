from __future__ import annotations

from datetime import datetime, timezone

from student_expense_manager.data.db import get_connection

DEFAULTS: dict[str, str] = {
    "theme": "dark",
    "currency": "INR",
}


class SettingsRepository:
    """Small key/value store for display preferences.

    Financial data stays in the transactions and budgets tables; nothing here
    is sent anywhere.
    """

    def get(self, key: str, default: str | None = None) -> str | None:
        with get_connection() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default if default is not None else DEFAULTS.get(key)
        return str(row["value"])

    def get_all(self) -> dict[str, str]:
        with get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
        values = dict(DEFAULTS)
        values.update({str(r["key"]): str(r["value"]) for r in rows})
        return values

    def set(self, key: str, value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
