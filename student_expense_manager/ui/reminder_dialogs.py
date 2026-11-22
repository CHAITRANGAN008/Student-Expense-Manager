from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.repositories.reminder_repository import Reminder
from student_expense_manager.services.money import currency_symbol, rupees_to_paise
from student_expense_manager.ui.constants import EXPENSE_CATEGORIES, methods_for
from student_expense_manager.ui.dialogs import (
    BaseDialog,
    FocusLineEdit,
    field_box,
    field_label,
)
from student_expense_manager.ui.widgets import (
    SegmentedControl,
    date_edit,
    make_button,
    repolish,
)

_RECURSIONS = [
    ("Does not repeat", "none"),
    ("Every day", "daily"),
    ("Every week", "weekly"),
    ("Every month", "monthly"),
    ("Every year", "yearly"),
]


class ReminderDialog(BaseDialog):
    """Add or edit one payment reminder, including recurrence and alerts."""

    def __init__(
        self,
        parent: QWidget | None = None,
        reminder: Reminder | None = None,
        today: date | None = None,
    ) -> None:
        title = "Edit reminder" if reminder else "New payment reminder"
        subtitle = (
            "Adjust the details and save your changes."
            if reminder
            else "Set a payment you don't want to forget. Everything stays on this device."
        )
        super().__init__(parent, title, subtitle, width=560)
        self.set_header_icon("bell-ring")
        today = today or date.today()
        self.reminder = reminder

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Hostel fees, Netflix, library fine")
        self.body.addWidget(field_box("Payment title", self.title_edit))

        amount_box = QWidget()
        amount_layout = QVBoxLayout(amount_box)
        amount_layout.setContentsMargins(0, 0, 0, 0)
        amount_layout.setSpacing(6)
        amount_layout.addWidget(field_label("Amount"))
        amount_frame = QFrame()
        amount_frame.setObjectName("amountFrame")
        amount_frame.setMinimumHeight(54)
        amount_row = QHBoxLayout(amount_frame)
        amount_row.setContentsMargins(14, 6, 14, 6)
        amount_row.setSpacing(8)
        symbol = QLabel(currency_symbol())
        symbol.setStyleSheet("font-size: 21px; font-weight: 700;")
        amount_row.addWidget(symbol)
        self.amount_edit = FocusLineEdit()
        self.amount_edit.setObjectName("amountInput")
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setClearButtonEnabled(False)
        amount_row.addWidget(self.amount_edit, 1)
        amount_row.addWidget(QLabel("INR"))
        self.amount_edit.focus_changed.connect(
            lambda focused: (
                amount_frame.setProperty("focused", "true" if focused else "false"),
                repolish(amount_frame),
            )
        )
        amount_layout.addWidget(amount_frame)
        self.body.addWidget(amount_box)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(13)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self.date_field = date_edit(QDate(today.year, today.month, today.day))
        self.time_check = QCheckBox("Add a due time")
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(18, 0))
        self.time_edit.setEnabled(False)
        self.time_check.toggled.connect(self.time_edit.setEnabled)
        time_box = QWidget()
        time_layout = QVBoxLayout(time_box)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(4)
        time_layout.addWidget(self.time_check)
        time_layout.addWidget(self.time_edit)

        self.channel_control = SegmentedControl(
            [("Online", "online"), ("Offline", "offline")], compact=True
        )
        self.method_combo = QComboBox()
        self.method_combo.setEditable(True)
        self.method_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.method_combo.addItems(methods_for("online"))
        self.channel_control.changed.connect(
            lambda channel: self._refresh_methods(channel)
        )
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.category_combo.addItems(EXPENSE_CATEGORIES)

        grid.addWidget(field_box("Due date", self.date_field), 0, 0)
        grid.addWidget(field_box("Due time", time_box), 0, 1)
        grid.addWidget(field_box("Payment channel", self.channel_control), 1, 0)
        grid.addWidget(field_box("Payment method", self.method_combo), 1, 1)
        grid.addWidget(field_box("Category", self.category_combo), 2, 0)
        self.body.addLayout(grid)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Anything useful to remember (optional)")
        self.description_edit.setFixedHeight(62)
        self.body.addWidget(field_box("Description", self.description_edit))

        alert_box = QWidget()
        alert_layout = QVBoxLayout(alert_box)
        alert_layout.setContentsMargins(0, 0, 0, 0)
        alert_layout.setSpacing(7)
        alert_layout.addWidget(field_label("Remind me"))
        checks = QHBoxLayout()
        checks.setSpacing(8)
        self.alert_checks: dict[int, QCheckBox] = {}
        for days, label in ((7, "7 days before"), (3, "3 days before"),
                            (1, "1 day before"), (0, "On due date")):
            check = QCheckBox(label)
            check.setChecked(True)
            self.alert_checks[days] = check
            checks.addWidget(check)
        alert_layout.addLayout(checks)
        self.notify_enabled = QCheckBox("Enable notifications for this reminder")
        self.notify_enabled.setChecked(True)
        alert_layout.addWidget(self.notify_enabled)
        self.body.addWidget(alert_box)

        recurring_box = QWidget()
        recurring_layout = QVBoxLayout(recurring_box)
        recurring_layout.setContentsMargins(0, 0, 0, 0)
        recurring_layout.setSpacing(7)
        recurring_layout.addWidget(field_label("Recurring payment"))
        self.recurrence_combo = QComboBox()
        for label, value in _RECURRENCES:
            self.recurrence_combo.addItem(label, value)
        recurring_layout.addWidget(self.recurrence_combo)

        limit_row = QHBoxLayout()
        limit_row.setSpacing(10)
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(["No end", "End on date", "Number of payments"])
        self.end_date = date_edit(QDate(today.year, today.month, today.day))

        self.limit_combo.currentIndexChanged.connect(self._limit_changed)
        limit_row.addWidget(self.limit_combo, 1)
        limit_row.addWidget(self.end_date, 1)
        self.occurrences = QSpinBox()
        self.occurrences.setRange(1, 240)
        self.occurrences.setValue(12)
        limit_row.addWidget(self.occurrences, 1)
        recurring_layout.addLayout(limit_row)
        hint = QLabel("If both are set, the earlier limit wins.")
        hint.setObjectName("dimLabel")
        recurring_layout.addWidget(hint)
        self.body.addWidget(recurring_box)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        self.body.addWidget(self.error_label)

        cancel = make_button("Cancel", "secondary")
        cancel.clicked.connect(self.reject)
        save = make_button("Save changes" if reminder else "Add reminder", "primary", "check")
        save.clicked.connect(self._save)
        self.add_footer(cancel, save)

        if reminder:
            self._load(reminder)
        else:
            self.date_field.setDate(QDate(today.year, today.month, today.day))
        self._limit_changed(self.limit_combo.currentIndex())

    # ------------------------------------------------------------------ helpers
    def _refresh_methods(self, channel: str, keep: str = "") -> None:
        current = keep or self.method_combo.currentText()
        self.method_combo.blockSignals(True)
        self.method_combo.clear()
        self.method_combo.addItems(methods_for(channel))
        if current:
            index = self.method_combo.findText(current)
            if index >= 0:
                self.method_combo.setCurrentIndex(index)
            else:
                self.method_combo.setEditText(current)
        self.method_combo.blockSignals(False)

    def _limit_changed(self, index: int) -> None:
        self.end_date.setEnabled(index == 1)
        self.occurrences.setEnabled(index == 2)

    def _load(self, reminder: Reminder) -> None:
        self.title_edit.setText(reminder.title)
        self.amount_edit.setText(f"{reminder.amount_paise // 100}.{reminder.amount_paise % 100:02d}")
        year, month, day = (int(part) for part in reminder.due_date.split("-"))
        self.date_field.setDate(QDate(year, month, day))
        if reminder.due_time:
            self.time_check.setChecked(True)
            hours, minutes = (int(part) for part in reminder.due_time.split(":"))
            self.time_edit.setTime(QTime(hours, minutes))
        self.channel_control.set_current(reminder.payment_channel)
        self._refresh_methods(reminder.payment_channel, reminder.payment_method)
        index = self.category_combo.findText(reminder.category)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
        else:
            self.category_combo.setEditText(reminder.category)
        self.description_edit.setPlainText(reminder.description)
        offsets = reminder.schedule_offsets()
        for days, check in self.alert_checks.items():
            check.setChecked(days in offsets)
        self.notify_enabled.setChecked(reminder.notifications_enabled)
        recurrence_index = self.recurrence_combo.findData(reminder.recurrence)
        if recurrence_index >= 0:
            self.recurrence_combo.setCurrentIndex(recurrence_index)
        if reminder.recurrence_end_date:
            self.limit_combo.setCurrentIndex(1)
            year, month, day = (int(part) for part in reminder.recurrence_end_date.split("-"))
            self.end_date.setDate(QDate(year, month, day))
        elif reminder.recurrence_count:
            self.limit_combo.setCurrentIndex(2)
            self.occurrences.setValue(reminder.recurrence_count)

    def _invalid(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def _save(self) -> None:
        self.error_label.setVisible(False)
        title = self.title_edit.text().strip()
        if not title:
            self._invalid("Give this payment a title.")
            self.title_edit.setFocus()
            return
        try:
            amount = rupees_to_paise(self.amount_edit.text())
        except ValueError as exc:
            self._invalid(str(exc))
            self.amount_edit.setFocus()
            return
        category = self.category_combo.currentText().strip()
        method = self.method_combo.currentText().strip()
        if not category or not method:
            self._invalid("Choose a category and a payment method.")
            return
        selected_days = [days for days, check in self.alert_checks.items() if check.isChecked()]
        if 0 not in selected_days:
            selected_days.append(0)
        schedule = ",".join(str(days) for days in sorted(set(selected_days), reverse=True))
        recurrence = str(self.recurrence_combo.currentData() or "none")
        end_date = None
        count = None
        if self.limit_combo.currentIndex() == 1:
            end_date = self.end_date.date().toString("yyyy-MM-dd")
        elif self.limit_combo.currentIndex() == 2:
            count = self.occurrences.value()
        source = self.reminder
        self._result = Reminder(
            id=source.id if source else None,
            title=title,
            amount_paise=amount,
            due_date=self.date_field.date().toString("yyyy-MM-dd"),
            due_time=(
                self.time_edit.time().toString("HH:mm") if self.time_check.isChecked() else None
            ),
            category=category,
            payment_method=method,
            payment_channel=self.channel_control.current() or "online",
            description=self.description_edit.toPlainText().strip(),
            status=source.status if source else "upcoming",
            recurrence=recurrence,
            recurrence_end_date=end_date if recurrence != "none" else None,
            recurrence_count=count if recurrence != "none" else None,
            occurrence_index=source.occurrence_index if source else 0,
            series_id=source.series_id if source else 0,
            notification_days=schedule,
            notifications_enabled=self.notify_enabled.isChecked(),
            created_at=source.created_at if source else "",
            updated_at="",
            paid_at=source.paid_at if source else None,
            linked_transaction_id=source.linked_transaction_id if source else None,
        )
        self.accept()

    def reminder(self) -> Reminder:
        return self._result


class MarkPaidDialog(BaseDialog):
    """Ask whether paying a reminder should also create one expense."""

    def __init__(
        self,
        parent: QWidget | None,
        reminder: Reminder,
        today: date | None = None,
    ) -> None:
        super().__init__(parent, "Mark as paid", "", width=460)
        self.set_header_icon("check-circle", "#34D399", "#12362F")
        today = today or date.today()
        self.completion_date = date_edit(QDate(today.year, today.month, today.day))
        label = QLabel(
            f"<b>{reminder.title}</b><br>{currency_symbol()}"
            f"{reminder.amount_paise / 100:,.2f} due on {reminder.due_date}"
        )
        label.setObjectName("pageSubtitle")
        label.setWordWrap(True)
        self.body.addWidget(label)
        self.body.addWidget(field_box("Payment completion date", self.completion_date))
        note = QLabel(
            "Create exactly one expense transaction linked to this reminder? "
            "Choosing this adds the payment to your ledger and prevents duplicates."
        )
        note.setObjectName("cardSubtitle")
        note.setWordWrap(True)
        self.body.addWidget(note)

        cancel = make_button("Cancel", "secondary")
        cancel.clicked.connect(self.reject)
        paid_only = make_button("Paid only", "secondary")
        paid_only.clicked.connect(lambda: self._finish(False))
        paid_expense = make_button("Paid + add expense", "primary", "check")
        paid_expense.clicked.connect(lambda: self._finish(True))
        self.add_footer(cancel, paid_only, paid_expense)
        self._create_expense = False

    def _finish(self, create_expense: bool) -> None:
        self._create_expense = create_expense
        self.accept()

    def values(self) -> tuple[bool, date]:
        qdate = self.completion_date.date()
        return self._create_expense, date(qdate.year(), qdate.month(), qdate.day())
