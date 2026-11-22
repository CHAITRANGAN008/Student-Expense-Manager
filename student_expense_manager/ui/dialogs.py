from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate, QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.repositories.transaction_repository import Transaction
from student_expense_manager.services.money import currency_symbol, rupees_to_paise
from student_expense_manager.ui.constants import (
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    categories_for,
    methods_for,
)
from student_expense_manager.ui.widgets import (
    IconChip,
    SegmentedControl,
    date_edit,
    icon_button,
    make_button,
    repolish,
)


class FocusLineEdit(QLineEdit):
    focus_changed = Signal(bool)

    def focusInEvent(self, event) -> None:  # noqa: N802, ANN001
        super().focusInEvent(event)
        self.focus_changed.emit(True)

    def focusOutEvent(self, event) -> None:  # noqa: N802, ANN001
        super().focusOutEvent(event)
        self.focus_changed.emit(False)


def field_label(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("sectionLabel")
    return label


def field_box(label: str, widget: QWidget) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(field_label(label))
    layout.addWidget(widget)
    return box


class BaseDialog(QDialog):
    """Frameless card dialog with a soft shadow and a draggable header."""

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        subtitle: str = "",
        width: int = 520,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setObjectName("framelessDialog")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self._drag_offset: QPoint | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(26, 26, 26, 26)
        self.card = QFrame()
        self.card.setObjectName("dialogCard")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(46)
        shadow.setOffset(0, 16)
        shadow.setColor(QColor(5, 3, 15, 170))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        self._root = QVBoxLayout(self.card)
        self._root.setContentsMargins(24, 21, 24, 22)
        self._root.setSpacing(17)

        header = QHBoxLayout()
        header.setSpacing(12)
        self.header_icon = IconChip("sparkles", size=38)
        self.header_icon.setVisible(False)
        header.addWidget(self.header_icon, 0, Qt.AlignmentFlag.AlignTop)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        self.title_label.setStyleSheet("font-size: 17px;")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("pageSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.subtitle_label)
        header.addLayout(title_box, 1)
        self.close_btn = icon_button("close", "Close", size=30)
        self.close_btn.clicked.connect(self.reject)
        header.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignTop)
        self._root.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setSpacing(14)
        self._root.addLayout(self.body, 1)

        self.footer = QHBoxLayout()
        self.footer.setSpacing(10)
        self.footer.addStretch(1)
        self._root.addLayout(self.footer)

        self.setFixedWidth(width)
        self.adjustSize()

    def add_footer(self, *widgets: QWidget) -> None:
        for widget in widgets:
            self.footer.addWidget(widget)

    def set_header_icon(self, kind: str, color: str | None = None, tint: str | None = None) -> None:
        self.header_icon.set_kind(kind, color, tint)
        self.header_icon.setVisible(True)

    # -- window dragging --------------------------------------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802, ANN001
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 100:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802, ANN001
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802, ANN001
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class TransactionDialog(BaseDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        tx: Transaction | None = None,
    ) -> None:
        title = "Edit transaction" if tx else "Add transaction"
        subtitle = (
            "Update the details and save your changes."
            if tx
            else "Record money coming in or going out. Everything stays on this computer."
        )
        super().__init__(parent, title, subtitle, width=540)
        self.tx = tx
        self.set_header_icon("transactions")

        self.type_control = SegmentedControl(
            [("Expense", "expense"), ("Income", "income")], compact=True
        )
        self.type_control.setMinimumWidth(200)
        self.body.addWidget(field_box("Transaction type", self.type_control))

        # ---- amount ------------------------------------------------------
        amount_box = QWidget()
        amount_layout = QVBoxLayout(amount_box)
        amount_layout.setContentsMargins(0, 0, 0, 0)
        amount_layout.setSpacing(6)
        amount_layout.addWidget(field_label("Amount"))
        amount_frame = QFrame()
        amount_frame.setObjectName("amountFrame")
        amount_frame.setMinimumHeight(54)
        row = QHBoxLayout(amount_frame)
        row.setContentsMargins(14, 6, 14, 6)
        row.setSpacing(8)
        symbol = QLabel(currency_symbol())
        symbol.setStyleSheet("font-size: 21px; font-weight: 700;")
        row.addWidget(symbol)
        self.amount_edit = FocusLineEdit()
        self.amount_edit.setObjectName("amountInput")
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setClearButtonEnabled(False)
        row.addWidget(self.amount_edit, 1)
        note = QLabel("INR")
        note.setObjectName("dimLabel")
        row.addWidget(note)
        self.amount_edit.focus_changed.connect(self._focus_amount)
        amount_layout.addWidget(amount_frame)
        self.body.addWidget(amount_box)
        self._amount_frame = amount_frame

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.method_combo = QComboBox()
        self.method_combo.setEditable(True)
        self.method_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.channel_control = SegmentedControl(
            [("Online", "online"), ("Offline", "offline")], compact=True
        )
        self.date_edit = date_edit()

        grid.addWidget(field_box("Category", self.category_combo), 0, 0)
        grid.addWidget(field_box("Payment method", self.method_combo), 0, 1)
        grid.addWidget(field_box("Channel", self.channel_control), 1, 0)
        grid.addWidget(field_box("Date", self.date_edit), 1, 1)
        self.body.addLayout(grid)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("What was this for? (optional)")
        self.description_edit.setFixedHeight(74)
        self.body.addWidget(field_box("Note", self.description_edit))

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        self.body.addWidget(self.error_label)

        self.cancel_btn = make_button("Cancel", "secondary")
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn = make_button("Save changes" if tx else "Add transaction", "primary", "check")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save)
        self.add_footer(self.cancel_btn, self.save_btn)

        self.type_control.changed.connect(self._type_changed)
        self.channel_control.changed.connect(self._channel_changed)
        self.amount_edit.returnPressed.connect(self._save)
        self._refresh_categories(EXPENSE_CATEGORIES)
        self._refresh_methods("online")
        if tx:
            self._load(tx)

    def _focus_amount(self, focused: bool) -> None:
        self._amount_frame.setProperty("focused", "true" if focused else "false")
        repolish(self._amount_frame)

    def _refresh_categories(self, items: list[str], keep: str = "") -> None:
        current = keep or self.category_combo.currentText()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItems(items)
        if current:
            idx = self.category_combo.findText(current)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            else:
                self.category_combo.setEditText(current)
        self.category_combo.blockSignals(False)

    def _refresh_methods(self, channel: str, keep: str = "") -> None:
        current = keep or self.method_combo.currentText()
        self.method_combo.blockSignals(True)
        self.method_combo.clear()
        self.method_combo.addItems(methods_for(channel))
        if current:
            idx = self.method_combo.findText(current)
            if idx >= 0:
                self.method_combo.setCurrentIndex(idx)
            else:
                self.method_combo.setEditText(current)
        self.method_combo.blockSignals(False)

    def _type_changed(self, value: str) -> None:
        self._refresh_categories(
            EXPENSE_CATEGORIES if value == "expense" else INCOME_CATEGORIES
        )

    def _channel_changed(self, value: str) -> None:
        self._refresh_methods(value)

    def _load(self, tx: Transaction) -> None:
        self.type_control.set_current(tx.transaction_type)
        self._refresh_categories(categories_for(tx.transaction_type), tx.category)
        self.channel_control.set_current(tx.payment_channel)
        self._refresh_methods(tx.payment_channel, tx.payment_method)
        self.amount_edit.setText(f"{tx.amount_paise // 100}.{tx.amount_paise % 100:02d}")
        year, month, day = (int(part) for part in tx.transaction_date.split("-"))
        self.date_edit.setDate(QDate(year, month, day))
        self.description_edit.setPlainText(tx.description)
        self.save_btn.setText("Save changes")

    def _clear_invalid(self) -> None:
        for widget in (self.amount_edit, self.category_combo, self.method_combo):
            widget.setProperty("invalid", "false")
            repolish(widget)
        self.error_label.setVisible(False)

    def _mark_invalid(self, widget: QWidget, message: str) -> None:
        widget.setProperty("invalid", "true")
        repolish(widget)
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        widget.setFocus()

    def _save(self) -> None:
        self._clear_invalid()
        try:
            amount = rupees_to_paise(self.amount_edit.text())
        except ValueError as exc:
            self._mark_invalid(self.amount_edit, str(exc))
            return
        category = self.category_combo.currentText().strip()
        if not category:
            self._mark_invalid(self.category_combo, "Choose or type a category.")
            return
        method = self.method_combo.currentText().strip()
        if not method:
            self._mark_invalid(self.method_combo, "Choose or type a payment method.")
            return
        self._tx = Transaction(
            id=self.tx.id if self.tx else None,
            amount_paise=amount,
            transaction_type=self.type_control.current() or "expense",
            category=category,
            payment_channel=self.channel_control.current() or "online",
            payment_method=method,
            description=self.description_edit.toPlainText().strip(),
            transaction_date=self.date_edit.date().toString("yyyy-MM-dd"),
            created_at=self.tx.created_at if self.tx else datetime.now().isoformat(),
        )
        self.accept()

    def transaction(self) -> Transaction:
        return self._tx


class BudgetDialog(BaseDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        month: int,
        year: int,
        category: str | None = None,
        amount_paise: int | None = None,
        editing: bool = False,
    ) -> None:
        title = "Edit budget" if editing else "New budget"
        subtitle = f"Set a monthly spending limit for {month:02d}/{year}."
        super().__init__(parent, title, subtitle, width=480)
        self.set_header_icon("wallet")
        self.category_value = category
        self.editing = editing

        self.scope_control = SegmentedControl(
            [("Overall", "overall"), ("Category", "category")], compact=True
        )
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.category_combo.addItems(EXPENSE_CATEGORIES)
        self.body.addWidget(field_box("Budget scope", self.scope_control))

        self.category_box = field_box("Category", self.category_combo)
        self.body.addWidget(self.category_box)

        amount_box = QWidget()
        amount_layout = QVBoxLayout(amount_box)
        amount_layout.setContentsMargins(0, 0, 0, 0)
        amount_layout.setSpacing(6)
        amount_layout.addWidget(field_label("Monthly limit"))
        amount_frame = QFrame()
        amount_frame.setObjectName("amountFrame")
        amount_frame.setMinimumHeight(54)
        row = QHBoxLayout(amount_frame)
        row.setContentsMargins(14, 6, 14, 6)
        symbol = QLabel(currency_symbol())
        symbol.setStyleSheet("font-size: 21px; font-weight: 700;")
        row.addWidget(symbol)
        self.amount_edit = FocusLineEdit()
        self.amount_edit.setObjectName("amountInput")
        self.amount_edit.setPlaceholderText("0.00")
        row.addWidget(self.amount_edit, 1)
        self.amount_edit.focus_changed.connect(self._focus_amount)
        amount_layout.addWidget(amount_frame)
        self.body.addWidget(amount_box)
        self._amount_frame = amount_frame

        self.hint = QLabel("You will be warned at 80% and 100% of this budget.")
        self.hint.setObjectName("cardSubtitle")
        self.hint.setWordWrap(True)
        self.body.addWidget(self.hint)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setVisible(False)
        self.body.addWidget(self.error_label)

        cancel = make_button("Cancel", "secondary")
        cancel.clicked.connect(self.reject)
        save = make_button("Save budget", "primary", "check")
        save.clicked.connect(self._save)
        self.add_footer(cancel, save)

        self.scope_control.changed.connect(self._scope_changed)
        if category is not None:
            self.scope_control.set_current("category")
            self.category_combo.setEditText(category)
        elif editing:
            self.scope_control.set_current("overall")
        if amount_paise is not None:
            self.amount_edit.setText(f"{amount_paise // 100}.{amount_paise % 100:02d}")
        self._scope_changed("category" if category is not None else "overall")

    def _focus_amount(self, focused: bool) -> None:
        self._amount_frame.setProperty("focused", "true" if focused else "false")
        repolish(self._amount_frame)

    def _scope_changed(self, value: str) -> None:
        self.category_box.setEnabled(value == "category")
        self.category_combo.setEnabled(value == "category")

    def _save(self) -> None:
        self.error_label.setVisible(False)
        self.amount_edit.setProperty("invalid", "false")
        self.category_combo.setProperty("invalid", "false")
        repolish(self.amount_edit)
        repolish(self.category_combo)
        try:
            amount = rupees_to_paise(self.amount_edit.text())
        except ValueError as exc:
            self.amount_edit.setProperty("invalid", "true")
            repolish(self.amount_edit)
            self.error_label.setText(str(exc))
            self.error_label.setVisible(True)
            self.amount_edit.setFocus()
            return
        category = None
        if self.scope_control.current() == "category":
            category = self.category_combo.currentText().strip()
            if not category:
                self.category_combo.setProperty("invalid", "true")
                repolish(self.category_combo)
                self.error_label.setText("Choose or type a category for this budget.")
                self.error_label.setVisible(True)
                return
        self._amount = amount
        self._category = category
        self.accept()

    def values(self) -> tuple[str | None, int]:
        return self._category, self._amount


class ConfirmDialog(BaseDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        message: str,
        confirm_text: str = "Delete",
        icon_kind: str = "trash",
        danger: bool = True,
    ) -> None:
        super().__init__(parent, title, "", width=440)
        self.set_header_icon(icon_kind)
        label = QLabel(message)
        label.setObjectName("pageSubtitle")
        label.setWordWrap(True)
        label.setMinimumHeight(38)
        self.body.addWidget(label)
        cancel = make_button("Cancel", "secondary")
        cancel.clicked.connect(self.reject)
        confirm = make_button(confirm_text, "danger" if danger else "primary")
        confirm.clicked.connect(self.accept)
        self.add_footer(cancel, confirm)

    @classmethod
    def ask(
        cls,
        parent: QWidget | None,
        *,
        title: str,
        message: str,
        confirm_text: str = "Delete",
        danger: bool = True,
    ) -> bool:
        dialog = cls(
            parent,
            title=title,
            message=message,
            confirm_text=confirm_text,
            danger=danger,
        )
        return dialog.exec() == QDialog.DialogCode.Accepted
