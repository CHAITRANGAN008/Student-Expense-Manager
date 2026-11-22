from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from student_expense_manager.data.db import get_connection


@dataclass(slots=True)
class Transaction:
    id: int | None
    amount_paise: int
    transaction_type: str  # 'income' | 'expense'
    category: str
    payment_channel: str  # 'online' | 'offline'
    payment_method: str
    description: str
    transaction_date: str  # YYYY-MM-DD
    created_at: str


class TransactionRepository:
    def add(self, tx: Transaction) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO transactions
                (amount_paise, transaction_type, category, payment_channel, payment_method, description, transaction_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx.amount_paise,
                    tx.transaction_type,
                    tx.category,
                    tx.payment_channel,
                    tx.payment_method,
                    tx.description,
                    tx.transaction_date,
                    tx.created_at or now,
                ),
            )
            return int(cur.lastrowid)

    def update(self, tx: Transaction) -> None:
        if tx.id is None:
            raise ValueError("Transaction id required for update")
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE transactions SET
                    amount_paise=?, transaction_type=?, category=?, payment_channel=?, payment_method=?,
                    description=?, transaction_date=?
                WHERE id=?
                """,
                (
                    tx.amount_paise,
                    tx.transaction_type,
                    tx.category,
                    tx.payment_channel,
                    tx.payment_method,
                    tx.description,
                    tx.transaction_date,
                    tx.id,
                ),
            )

    def delete(self, tx_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))

    def get(self, tx_id: int) -> Transaction | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()
        return self._row_to_tx(row) if row else None

    def list(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        category: str | None = None,
        payment_channel: str | None = None,
        payment_method: str | None = None,
        transaction_type: str | None = None,
        search: str | None = None,
        month: int | None = None,
        year: int | None = None,
        limit: int | None = None,
    ) -> list[Transaction]:
        clauses: list[str] = []
        params: list[Any] = []
        if start_date:
            clauses.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("transaction_date <= ?")
            params.append(end_date)
        if category:
            clauses.append("category = ?")
            params.append(category)
        if payment_channel:
            clauses.append("payment_channel = ?")
            params.append(payment_channel)
        if payment_method:
            clauses.append("payment_method = ?")
            params.append(payment_method)
        if transaction_type:
            clauses.append("transaction_type = ?")
            params.append(transaction_type)
        if month and year:
            clauses.append("strftime('%m', transaction_date) = ?")
            clauses.append("strftime('%Y', transaction_date) = ?")
            params.extend([f"{month:02d}", str(year)])
        if search:
            clauses.append("(description LIKE ? OR category LIKE ? OR payment_method LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM transactions {where} ORDER BY transaction_date DESC, id DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_tx(r) for r in rows]

    @staticmethod
    def _row_to_tx(row: Any) -> Transaction:
        return Transaction(
            id=int(row["id"]),
            amount_paise=int(row["amount_paise"]),
            transaction_type=str(row["transaction_type"]),
            category=str(row["category"]),
            payment_channel=str(row["payment_channel"]),
            payment_method=str(row["payment_method"]),
            description=str(row["description"] or ""),
            transaction_date=str(row["transaction_date"]),
            created_at=str(row["created_at"]),
        )
