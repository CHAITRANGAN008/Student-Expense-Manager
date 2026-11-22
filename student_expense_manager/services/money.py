from __future__ import annotations

"""Money helpers.

Amounts are always stored in integer minor units (paise) and converted to text
only at the presentation boundary.  No floating point maths is used.
"""

CURRENCIES: dict[str, dict[str, str | bool]] = {
    "INR": {"symbol": "₹", "name": "Indian Rupee", "indian_grouping": True},
    "USD": {"symbol": "$", "name": "US Dollar", "indian_grouping": False},
    "EUR": {"symbol": "€", "name": "Euro", "indian_grouping": False},
    "GBP": {"symbol": "£", "name": "British Pound", "indian_grouping": False},
    "AED": {"symbol": "د.إ", "name": "UAE Dirham", "indian_grouping": False},
}

DEFAULT_CURRENCY = "INR"
_active_currency = DEFAULT_CURRENCY


def set_currency(code: str) -> None:
    """Switch the display currency (storage stays in minor units)."""
    global _active_currency
    code = (code or DEFAULT_CURRENCY).upper()
    if code not in CURRENCIES:
        code = DEFAULT_CURRENCY
    _active_currency = code


def get_currency() -> str:
    return _active_currency


def currency_symbol(code: str | None = None) -> str:
    meta = CURRENCIES.get((code or _active_currency).upper(), CURRENCIES[DEFAULT_CURRENCY])
    return str(meta["symbol"])


def currency_name(code: str | None = None) -> str:
    meta = CURRENCIES.get((code or _active_currency).upper(), CURRENCIES[DEFAULT_CURRENCY])
    return str(meta["name"])


def rupees_to_paise(rupees: float | str) -> int:
    """Convert a user-entered amount to integer minor units.

    Accepts an optional rupee sign and thousands separators.  Rejects
    negative, zero, malformed and over-precise values.
    """
    s = str(rupees).strip().replace(",", "").replace("₹", "").replace(" ", "")
    if not s:
        raise ValueError("Amount is required")
    if s.startswith("-"):
        raise ValueError("Amount must be positive")
    if s.count(".") > 1:
        raise ValueError("Invalid amount")
    if "." in s:
        whole, frac = s.split(".", 1)
    else:
        whole, frac = s, ""
    if whole == "":
        whole = "0"
    if not whole.isdigit() or (frac and not frac.isdigit()):
        raise ValueError("Invalid amount")
    if len(frac) > 2:
        raise ValueError("Use at most 2 decimal places")
    frac = (frac + "00")[:2]
    paise = int(whole) * 100 + int(frac)
    if paise <= 0:
        raise ValueError("Amount must be greater than zero")
    return paise


def _group_indian(digits: str) -> str:
    if len(digits) <= 3:
        return digits
    last3 = digits[-3:]
    rest = digits[:-3]
    parts: list[str] = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts) + "," + last3


def _group_western(digits: str) -> str:
    parts: list[str] = []
    while len(digits) > 3:
        parts.insert(0, digits[-3:])
        digits = digits[:-3]
    parts.insert(0, digits)
    return ",".join(parts)


def format_money(paise: int, *, symbol: str | None = None, code: str | None = None, decimals: bool = True) -> str:
    """Format minor units as a currency string, e.g. ₹1,23,456.78."""
    code = (code or _active_currency).upper()
    meta = CURRENCIES.get(code, CURRENCIES[DEFAULT_CURRENCY])
    sym = symbol if symbol is not None else str(meta["symbol"])
    p = int(paise)
    sign = "-" if p < 0 else ""
    p = abs(p)
    rupees = p // 100
    rem = p % 100
    raw = str(rupees)
    if bool(meta["indian_grouping"]):
        grouped = _group_indian(raw)
    else:
        grouped = _group_western(raw)
    if decimals:
        return f"{sign}{sym}{grouped}.{rem:02d}"
    return f"{sign}{sym}{grouped}"


def paise_to_rupees_str(paise: int) -> str:
    """Backwards-compatible rupee formatter used by services and tests."""
    return format_money(paise)


def paise_to_rupees_float_str(paise: int) -> str:
    """Plain decimal text without a symbol (UTF-8 exports)."""
    p = int(paise)
    sign = "-" if p < 0 else ""
    p = abs(p)
    return f"{sign}{p // 100}.{p % 100:02d}"


def compact_money(paise: int, symbol: str | None = None) -> str:
    """Short form for chart axes: ₹1.2k, ₹1.4L, ₹2.3Cr."""
    sym = symbol if symbol is not None else currency_symbol()
    p = abs(int(paise))
    sign = "-" if paise < 0 else ""
    if p >= 1_000_000_000:
        return f"{sign}{sym}{p / 1_000_000_000:.1f}Cr"
    if p >= 10_000_000:
        return f"{sign}{sym}{p / 10_000_000:.1f}L"
    if p >= 100_000:
        value = p / 100 / 1000
        return f"{sign}{sym}{value:.1f}k"
    return f"{sign}{sym}{p // 100}"
