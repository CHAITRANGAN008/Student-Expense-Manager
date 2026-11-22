# Student Expense Manager

A complete offline-first desktop app for tracking student income, expenses and
budgets. Built with Python 3.12+, PySide6, SQLite and Matplotlib.

## Run it

```bat
py -3 -m pip install -r requirements.txt
run_app.bat
```

Or from this folder:

```bat
py -3 main.py
python -m student_expense_manager
```

## Features

- **Dashboard** — selected-month income, spending, available balance, remaining
  budget, highest spending category, online/offline split, six-month cash-flow
  chart, a spending heat-map calendar and recent transactions.
- **Transactions** — add, edit and delete income or expenses with confirmation;
  search by description, category or method; filter by type, category, payment
  channel, date and date range; export the filtered ledger as UTF-8 CSV.
- **Budgets** — one overall monthly budget plus per-category budgets, progress
  bars, remaining amounts and 80%/100% warnings.
- **Payment Reminders** — a violet animated reminder centre with active,
  upcoming, due-today, overdue and paid-history sections, list/calendar views,
  progress bars, toasts and at-a-glance totals. Add or edit reminders with an
  INR amount, due date/time, category, payment method, 7/3/1/0-day alerts and
  daily/weekly/monthly/yearly recurrence (end date or occurrence count). Status
  updates automatically; marking paid can create exactly one linked expense,
  stores the completion date and cannot be duplicated. Cancellation and undo
  are supported.
- **Analytics** — income vs expenses, category mix, online vs offline, six-month
  trend and payment-method distribution; all react to the selected period.
- **Monthly Reports** — on-screen statement preview plus a print-ready PDF
  (totals, net cash flow, category/online-offline breakdowns, budget
  utilisation, largest transactions) and a monthly-summary CSV.
- **Settings** — dark/light theme, local database details, backup, restore,
  reminder notification preferences and a shortcut to the data folder.

### Notifications

While the app is running, due reminders raise a sliding in-app toast and a
system-tray notification. Delivery is recorded per reminder/day/channel so a
single alert is not repeated. Notifications are **not** delivered while the app
is closed; that would need a Windows Scheduled Task or another OS-level
scheduler, which is not installed. The Settings page says this explicitly.
- **Personal credit** — an animated "MADE BY CHAITRANGAN VIJAYKUMAR THENGEKAR"
  signature in the sidebar footer, with a slow shimmer, breathing dots and a
  sweeping underline. It pauses when the sidebar is hidden.

Money is stored as integer paise and displayed with Indian digit grouping (₹).

## Your data

- Database: `%LOCALAPPDATA%\CraftAnything\StudentExpenseManager\student_expense_manager.db`
- Backups made by the app: `...\StudentExpenseManager\backups\`
- Nothing leaves the computer: no accounts, cloud sync, analytics or telemetry.
- Schema migrations are additive and restores keep a safety copy first.

## Screenshot mode

```bat
py -3 main.py --screenshot shots\dashboard.png
py -3 main.py --screenshot shots\reminders.png --page reminders
```

This starts the real UI with a disposable demo database, renders 120 frames,
writes a 1400×788 PNG (the size of the reference dashboard) and exits without
taking focus. It never touches your real data. `--page` accepts `dashboard`,
`transactions`, `budgets`, `reminders`, `analytics`, `reports` and `settings`.

## Tests

```bat
cd app
py -3 -m pytest -q
```

Twenty-six tests cover transactions (add/edit/delete, income/expense and
online/offline maths, monthly filtering, search, date-range and payment-method
filters), budgets and warnings, CSV export (filtered ledger and complete monthly
summary including largest transactions), daily calendar totals, backup/restore,
schema migrations, persistence, empty/invalid data, reminder status/recurrence
rules, notification delivery, mark-paid/linked-expense protection and
cancellation.

## Project layout

```
main.py                        entry point
student_expense_manager/
  data/         SQLite connection, schema migrations, backup/restore
  repositories/ transactions, budgets, settings, reminders
  services/     finance rules, money formatting, CSV/PDF generation, demo data,
                reminder rules, local notifications
  ui/           theme, reusable widgets, seven pages, reminder widgets/dialogs,
                shell
tests/          pytest suite
```
