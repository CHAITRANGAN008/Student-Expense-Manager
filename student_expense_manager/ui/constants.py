from __future__ import annotations

"""Shared UI choices.

Categories are only suggestions: every combo box stays editable so a student
can record something the list does not know about yet.
"""

EXPENSE_CATEGORIES = [
    "Food & Canteen",
    "Groceries",
    "Snacks",
    "Transport",
    "Stationery",
    "Education",
    "Shopping",
    "Subscriptions",
    "Mobile Recharge",
    "Entertainment",
    "Health",
    "Hostel",
    "Other",
]

INCOME_CATEGORIES = [
    "Pocket Money",
    "Scholarship",
    "Freelancing",
    "Part-time Work",
    "Gifts",
    "Other Income",
]

ONLINE_METHODS = ["UPI", "Card", "Net Banking", "Wallet", "Bank Transfer"]
OFFLINE_METHODS = ["Cash", "Card", "Cheque", "Other"]

CATEGORY_COLORS = [
    "#7C5CFF",
    "#4F7CFF",
    "#38BDF8",
    "#34D399",
    "#FBBF24",
    "#FB7185",
    "#A78BFA",
    "#22D3EE",
]

CHANNEL_COLORS = {
    "online": "#4F7CFF",
    "offline": "#FBBF24",
}

TYPE_COLORS = {
    "income": "#34D399",
    "expense": "#FB7185",
}


def categories_for(transaction_type: str) -> list[str]:
    return EXPENSE_CATEGORIES if transaction_type == "expense" else INCOME_CATEGORIES


def methods_for(channel: str) -> list[str]:
    return ONLINE_METHODS if channel == "online" else OFFLINE_METHODS


def month_label(month: int, year: int, short: bool = False) -> str:
    import calendar

    name = calendar.month_abbr[month] if short else calendar.month_name[month]
    return f"{name} {year}"
