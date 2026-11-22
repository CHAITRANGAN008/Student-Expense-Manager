from student_expense_manager.repositories.transaction_repository import Transaction, TransactionRepository
from student_expense_manager.services.finance_service import FinanceService


def make_tx(**overrides):
    data = dict(
        id=None,
        amount_paise=12550,
        transaction_type="expense",
        category="Snacks",
        payment_channel="offline",
        payment_method="Cash",
        description="Samosa",
        transaction_date="2026-11-10",
        created_at="2026-11-10T10:00:00Z",
    )
    data.update(overrides)
    return Transaction(**data)


def test_add_edit_delete_transaction(temp_db):
    repo = TransactionRepository()
    tx_id = repo.add(make_tx())
    assert tx_id > 0
    got = repo.get(tx_id)
    assert got is not None
    assert got.amount_paise == 12550
    assert got.description == "Samosa"

    got.description = "Updated"
    got.amount_paise = 15000
    repo.update(got)
    got2 = repo.get(tx_id)
    assert got2.description == "Updated"
    assert got2.amount_paise == 15000

    repo.delete(tx_id)
    assert repo.get(tx_id) is None


def test_income_expense_and_online_offline_calculations(temp_db):
    svc = FinanceService()
    svc.add_transaction(make_tx(transaction_type="income", category="Pocket Money", payment_channel="online", payment_method="UPI", amount_paise=100000, transaction_date="2026-11-01"))
    svc.add_transaction(make_tx(transaction_type="expense", category="Snacks", payment_channel="offline", payment_method="Cash", amount_paise=5000, transaction_date="2026-11-02"))
    svc.add_transaction(make_tx(transaction_type="expense", category="Subscriptions", payment_channel="online", payment_method="UPI", amount_paise=3000, transaction_date="2026-11-03"))
    summary = svc.month_summary(11, 2026)
    assert summary.total_income_paise == 100000
    assert summary.total_expense_paise == 8000
    assert summary.balance_paise == 92000
    assert summary.online_expense_paise == 3000
    assert summary.offline_expense_paise == 5000


def test_monthly_filtering(temp_db):
    svc = FinanceService()
    svc.add_transaction(make_tx(transaction_date="2026-10-31"))
    svc.add_transaction(make_tx(transaction_date="2026-11-01", amount_paise=1000))
    svc.add_transaction(make_tx(transaction_date="2026-11-30", amount_paise=2000))
    svc.add_transaction(make_tx(transaction_date="2026-12-01", amount_paise=3000))
    nov = svc.list_transactions(month=11, year=2026)
    assert len(nov) == 2
    assert sum(t.amount_paise for t in nov) == 3000


def test_search_and_filters(temp_db):
    svc = FinanceService()
    svc.add_transaction(make_tx(description="Canteen lunch", category="Food & Canteen", payment_channel="offline", payment_method="Cash"))
    svc.add_transaction(make_tx(description="Bus pass", category="Transport", payment_channel="online", payment_method="UPI"))
    assert len(svc.list_transactions(search="canteen")) == 1
    assert len(svc.list_transactions(category="Transport")) == 1
    assert len(svc.list_transactions(payment_channel="online")) == 1


def test_date_range_and_payment_method_filters(temp_db):
    svc = FinanceService()
    svc.add_transaction(make_tx(transaction_date="2026-10-31", payment_method="Cash"))
    svc.add_transaction(make_tx(transaction_date="2026-11-05", payment_method="UPI"))
    svc.add_transaction(make_tx(transaction_date="2026-11-20", payment_method="Card"))
    svc.add_transaction(make_tx(transaction_date="2026-12-01", payment_method="UPI"))

    november = svc.list_transactions(start_date="2026-11-01", end_date="2026-11-30")
    assert len(november) == 2
    assert len(svc.list_transactions(payment_method="UPI")) == 2
    assert len(svc.list_transactions(start_date="2026-11-01", end_date="2026-11-30", payment_method="UPI")) == 1
