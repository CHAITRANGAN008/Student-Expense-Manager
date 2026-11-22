from __future__ import annotations

import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from platformdirs import user_data_dir

APP_NAME = "StudentExpenseManager"
APP_AUTHOR = "CraftAnything"
SCHEMA_VERSION = 3
MIN_SCHEMA_VERSION = 1


def get_data_dir() -> Path:
    override = os.environ.get("SEM_DATA_DIR")
    if override:
        path = Path(override)
    else:
        path = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    return get_data_dir() / "student_expense_manager.db"


def get_backups_dir() -> Path:
    path = get_data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


@contextmanager
def get_connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database(db_path: Path | None = None) -> None:
    """Create or upgrade the database in place.  Existing rows are never removed."""
    with get_connection(db_path) as conn:
        _ensure_meta(conn)
        current = _get_schema_version(conn)
        if current < 1:
            _migrate_to_v1(conn)
            _set_schema_version(conn, 1)
            current = 1
        if current < 2:
            _migrate_to_v2(conn)
            _set_schema_version(conn, 2)
            current = 2
        if current < 3:
            _migrate_to_v3(conn)
            _set_schema_version(conn, 3)
            current = 3
        if current > SCHEMA_VERSION:
            # A newer app created this file; leave it untouched rather than risk data.
            raise RuntimeError(
                f"Database schema {current} is newer than this app supports ({SCHEMA_VERSION})."
            )


def _ensure_meta(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    row = conn.execute("SELECT version FROM schema_meta WHERE id = 1").fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO schema_meta (id, version, updated_at) VALUES (1, 0, ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )


def _get_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT version FROM schema_meta WHERE id = 1").fetchone()
    return int(row["version"]) if row else 0


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "UPDATE schema_meta SET version = ?, updated_at = ? WHERE id = 1",
        (version, datetime.now(timezone.utc).isoformat()),
    )


def _migrate_to_v1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
            transaction_type TEXT NOT NULL CHECK (transaction_type IN ('income', 'expense')),
            category TEXT NOT NULL,
            payment_channel TEXT NOT NULL CHECK (payment_channel IN ('online', 'offline')),
            payment_method TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            transaction_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
        CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);
        CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
        CREATE INDEX IF NOT EXISTS idx_transactions_channel ON transactions(payment_channel);

        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
            year INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 2100),
            category TEXT,
            amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(month, year, category)
        );

        CREATE INDEX IF NOT EXISTS idx_budgets_period ON budgets(year, month);
        """
    )


def _migrate_to_v2(conn: sqlite3.Connection) -> None:
    """Additive migration: preferences live beside financial data."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )


def _migrate_to_v3(conn: sqlite3.Connection) -> None:
    """Add the Payment Reminder Center.

    Purely additive: no existing transaction, budget or setting is touched.
    A reminder may point at one expense transaction, and each linked expense
    may belong to at most one reminder, so a payment can never be recorded
    twice.  Notification deliveries are tracked separately so restarting the
    application cannot produce duplicate alerts.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
            due_date TEXT NOT NULL,
            due_time TEXT,
            category TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            payment_channel TEXT NOT NULL CHECK (payment_channel IN ('online', 'offline')),
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'upcoming'
                CHECK (status IN ('upcoming', 'due_today', 'overdue', 'paid', 'cancelled')),
            recurrence TEXT NOT NULL DEFAULT 'none'
                CHECK (recurrence IN ('none', 'daily', 'weekly', 'monthly', 'yearly')),
            recurrence_end_date TEXT,
            recurrence_count INTEGER CHECK (recurrence_count IS NULL OR recurrence_count > 0),
            occurrence_index INTEGER NOT NULL DEFAULT 0,
            series_id INTEGER NOT NULL DEFAULT 0,
            notification_days TEXT NOT NULL DEFAULT '7,3,1,0',
            notifications_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            paid_at TEXT,
            linked_transaction_id INTEGER UNIQUE REFERENCES transactions(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_reminders_due_date ON reminders(due_date);
        CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);
        CREATE INDEX IF NOT EXISTS idx_reminders_series ON reminders(series_id, occurrence_index);
        CREATE INDEX IF NOT EXISTS idx_reminders_category ON reminders(category);

        CREATE TABLE IF NOT EXISTS notification_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reminder_id INTEGER NOT NULL REFERENCES reminders(id) ON DELETE CASCADE,
            offset_days INTEGER NOT NULL,
            due_date TEXT NOT NULL,
            delivered_at TEXT NOT NULL,
            UNIQUE(reminder_id, offset_days, due_date)
        );

        CREATE INDEX IF NOT EXISTS idx_notification_deliveries_reminder
            ON notification_deliveries(reminder_id);
        """
    )


def _validate_database_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Backup not found at {path}")
    conn = sqlite3.connect(path)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if not result or str(result[0]).lower() != "ok":
            raise ValueError("The selected file is not a healthy SQLite database")
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
        ).fetchone()
        if row is None:
            raise ValueError("The selected file does not contain Student Expense Manager data")
    finally:
        conn.close()


def backup_database(target_path: str | Path, db_path: Path | None = None) -> Path:
    src = db_path or get_db_path()
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise FileNotFoundError(f"Database not found at {src}")
    # SQLite's online backup API copies committed pages consistently.  Closing
    # both handles matters on Windows, where an open handle blocks deletes.
    with closing(sqlite3.connect(src)) as src_conn:
        with closing(sqlite3.connect(target)) as dst_conn:
            src_conn.backup(dst_conn)
    return target


def restore_database(source_path: str | Path, db_path: Path | None = None) -> Path:
    """Restore a backup without ever discarding the current data silently.

    A safety copy of the current database is written into the app's backups
    folder before the selected backup replaces it.
    """
    src = Path(source_path)
    dst = db_path or get_db_path()
    _validate_database_file(src)
    dst.parent.mkdir(parents=True, exist_ok=True)

    safety_dir = get_backups_dir() if db_path is None else dst.parent / "backups"
    safety_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    safety_copy = safety_dir / f"pre-restore-{stamp}.db"
    if dst.exists():
        backup_database(safety_copy, db_path=dst)

    # Copy through SQLite rather than shutil so WAL sidecar files stay coherent.
    with closing(sqlite3.connect(src)) as src_conn:
        with closing(sqlite3.connect(dst)) as dst_conn:
            src_conn.backup(dst_conn)
    initialize_database(db_path=dst)
    return dst


def database_info() -> dict[str, object]:
    path = get_db_path()
    size = path.stat().st_size if path.exists() else 0
    counts = {"transactions": 0, "budgets": 0, "reminders": 0}
    if path.exists():
        try:
            with get_connection() as conn:
                for table in ("transactions", "budgets", "reminders"):
                    row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
                    counts[table] = int(row["n"]) if row else 0
        except sqlite3.Error:
            pass
    return {"path": path, "size_bytes": size, **counts}
