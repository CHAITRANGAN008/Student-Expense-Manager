from pathlib import Path

from student_expense_manager.data.db import (
    SCHEMA_VERSION,
    backup_database,
    get_db_path,
    initialize_database,
    restore_database,
)
from student_expense_manager.repositories.transaction_repository import Transaction
from student_expense_manager.services.finance_service import FinanceService


def tx(**kw):
    base = dict(id=None, amount_paise=1000, transaction_type="expense", category="Snacks", payment_channel="offline", payment_method="Cash", description="", transaction_date="2026-11-05", created_at="2026-11-05T00:00:00Z")
    base.update(kw)
    return Transaction(**base)


def test_budget_calculations_and_warnings(temp_db):
    svc = FinanceService()
    svc.set_budget(11, 2026, 10000, None)  # overall 100
    svc.set_budget(11, 2026, 5000, "Snacks")
    svc.add_transaction(tx(amount_paise=4000, category="Snacks"))  # 80%
    svc.add_transaction(tx(amount_paise=2000, category="Transport"))  # overall 60%? 60
    statuses = {s["label"]: s for s in svc.budget_status(11, 2026)}
    assert statuses["Snacks"]["level"] == "warning"
    assert statuses["Overall"]["level"] == "ok"
    svc.add_transaction(tx(amount_paise=5000, category="Other"))
    statuses = {s["label"]: s for s in svc.budget_status(11, 2026)}
    assert statuses["Overall"]["level"] == "exceeded"


def test_csv_export_and_persistence(temp_db, tmp_path: Path):
    svc = FinanceService()
    svc.add_transaction(tx(amount_paise=12345, description="Chai", transaction_date="2026-11-07"))
    out = tmp_path / "tx.csv"
    svc.export_transactions_csv(out, month=11, year=2026)
    content = out.read_text(encoding="utf-8")
    assert "123.45" in content
    assert "Chai" in content

    summary = tmp_path / "summary.csv"
    svc.export_monthly_summary_csv(summary, 11, 2026)
    scontent = summary.read_text(encoding="utf-8")
    assert "Monthly Summary" in scontent
    assert "123.45" in scontent

    # persistence
    db = get_db_path()
    assert db.exists()
    svc2 = FinanceService()
    assert len(svc2.list_transactions(month=11, year=2026)) == 1


def test_monthly_summary_csv_includes_full_report_sections(temp_db, tmp_path: Path):
    svc = FinanceService()
    svc.set_budget(11, 2026, 10000, None)
    svc.add_transaction(tx(amount_paise=250000, description="Hostel fees", category="Hostel", payment_method="UPI", transaction_date="2026-11-02"))
    svc.add_transaction(tx(amount_paise=750000, description="Laptop", category="Shopping", payment_method="Card", transaction_date="2026-11-06"))
    svc.add_transaction(tx(amount_paise=100000, transaction_type="income", category="Pocket Money", transaction_date="2026-11-01"))

    out = tmp_path / "monthly.csv"
    svc.export_monthly_summary_csv(out, 11, 2026)
    content = out.read_text(encoding="utf-8")
    for section in (
        "Category Breakdown",
        "Online/Offline Breakdown",
        "Budget Utilization",
        "Largest Transactions",
        "Laptop",
        "7500",
    ):
        assert section in content
    assert "Budget,Limit,Spent,Used %,Status" in content
    assert content.index("Laptop") < content.index("Hostel fees")


def test_daily_expenses_groups_only_expense_days(temp_db):
    svc = FinanceService()
    svc.add_transaction(tx(amount_paise=2500, transaction_date="2026-11-03"))
    svc.add_transaction(tx(amount_paise=1500, transaction_date="2026-11-03"))
    svc.add_transaction(tx(amount_paise=900, transaction_date="2026-11-17"))
    svc.add_transaction(
        tx(
            amount_paise=50000,
            transaction_type="income",
            category="Pocket Money",
            transaction_date="2026-11-03",
        )
    )
    svc.add_transaction(tx(amount_paise=700, transaction_date="2026-10-31"))

    assert svc.daily_expenses(11, 2026) == {3: 4000, 17: 900}
    assert svc.daily_expenses(12, 2026) == {}


def test_backup_and_restore_round_trip(temp_db, tmp_path: Path):
    svc = FinanceService()
    svc.add_transaction(tx(amount_paise=1111, description="First"))
    backup = backup_database(tmp_path / "backup.db")
    assert backup.exists()

    svc.add_transaction(tx(amount_paise=2222, description="Second"))
    assert len(svc.list_transactions()) == 2

    restore_database(backup)
    restored = FinanceService().list_transactions()
    assert len(restored) == 1
    assert restored[0].description == "First"

    # A safety copy of the pre-restore database is kept next to the data.
    safety = list((get_db_path().parent / "backups").glob("pre-restore-*.db"))
    assert safety


def test_initialize_database_is_idempotent_and_versioned(temp_db):
    svc = FinanceService()
    svc.add_transaction(tx(description="Keep me"))
    initialize_database()

    import sqlite3

    from contextlib import closing

    with closing(sqlite3.connect(get_db_path())) as conn:
        version = conn.execute("SELECT version FROM schema_meta WHERE id = 1").fetchone()[0]
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert version == SCHEMA_VERSION
    assert {"transactions", "budgets", "app_settings"} <= tables
    assert count == 1


def test_empty_data_and_invalid_amounts(temp_db):
    svc = FinanceService()
    s = svc.month_summary(1, 2026)
    assert s.total_income_paise == 0
    assert s.total_expense_paise == 0
    assert svc.highest_spending_category(1, 2026) is None
    try:
        svc.add_transaction(tx(amount_paise=0))
        assert False, "expected error"
    except ValueError:
        pass
    try:
        svc.add_transaction(tx(amount_paise=-100))
        assert False, "expected error"
    except Exception:
        pass
