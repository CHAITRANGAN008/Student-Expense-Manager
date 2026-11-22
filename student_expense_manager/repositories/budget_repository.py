from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from student_expense_manager.data.db import get_connection


@dataclass(slots=True)
class Budget:
    id: int | None
    month: int
    year: int
    category: str | None  # None = overall
    amount_paise: int
    created_at: str = ""
    updated_at: str = ""


class BudgetRepository:
    def upsert(self, budget: Budget) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO budgets (month, year, category, amount_paise, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(month, year, category) DO UPDATE SET
                    amount_paise=excluded.amount_paise,
                    updated_at=excluded.updated_at
                """,
                (budget.month, budget.year, budget.category, budget.amount_paise, now, now),
            )
            if cur.lastrowid:
                return int(cur.lastrowid)
            row = conn.execute(
                "SELECT id FROM budgets WHERE month=? AND year=? AND ((category IS NULL AND ? IS NULL) OR category=?)",
                (budget.month, budget.year, budget.category, budget.category),
            ).fetchone()
            return int(row["id"]) if row else 0

    def delete(self, budget_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM budgets WHERE id=?", (budget_id,))

    def list_for_period(self, month: int, year: int) -> list[Budget]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM budgets WHERE month=? AND year=? ORDER BY category IS NOT NULL, category",
                (month, year),
            ).fetchall()
        return [self._row_to_budget(r) for r in rows]

    def get_overall(self, month: int, year: int) -> Budget | None:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM budgets WHERE month=? AND year=? AND category IS NULL",
                (month, year),
            ).fetchone()
        return self._row_to_budget(row) if row else None

    @staticmethod
    def _row_to_budget(row: Any) -> Budget:
        return Budget(
            id=int(row["id"]),
            month=int(row["month"]),
            year=int(row["year"]),
            category=row["category"],
            amount_paise=int(row["amount_paise"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
