from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QDate, QStandardPaths, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.repositories.transaction_repository import Transaction
from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.money import format_money
from student_expense_manager.ui.dialogs import ConfirmDialog, TransactionDialog
from student_expense_manager.ui.page_base import PageHeader, content_layout
from student_expense_manager.ui.theme import palette
from student_expense_manager.ui.widgets import (
    Pill,
    SearchField,
    SectionCard,
    configure_table,
    date_edit,
    icon_button,
    make_button,
    repolish,
)


class TransactionsPage(QWidget):
    def __init__(
        self,
        service: FinanceService,
        on_changed: Callable[[], None],
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.on_changed = on_changed
        self._dirty = True
        p = palette()

        root = content_layout(
            self, scroll=False, margins=(26, 21, 26, 20), spacing=14
        )
        self.header = PageHeader(
            "Transactions",
            "Search, filter and keep every entry accurate.",
            "LEDGER",
        )
        self.add_btn = make_button("Add transaction", "primary", "plus")
        self.add_btn.clicked.connect(self.add_transaction)
        self.edit_btn = make_button("Edit", "secondary", "edit")
        self.edit_btn.clicked.connect(self.edit_transaction)
        self.delete_btn = make_button("Delete", "danger", "trash")
        self.delete_btn.clicked.connect(self.delete_transaction)
        self.header.add_action(self.edit_btn)
        self.header.add_action(self.delete_btn)
        self.header.add_action(self.add_btn)
        root.addWidget(self.header)

        filter_card = QFrame()
        filter_card.setObjectName("filterBar")
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setContentsMargins(14, 12, 14, 12)
        filter_layout.setSpacing(8)
        filter_top = QHBoxLayout()
        filter_top.setSpacing(9)
        filter_bottom = QHBoxLayout()
        filter_bottom.setSpacing(9)

        self.search = SearchField("Search description, category or method…")
        filter_top.addWidget(self.search, 1)

        self.type_filter = QComboBox()
        self.type_filter.addItem("All types", None)
        self.type_filter.addItem("Expenses", "expense")
        self.type_filter.addItem("Income", "income")
        self.type_filter.setMinimumWidth(112)
        self.channel_filter = QComboBox()
        self.channel_filter.addItem("All channels", None)
        self.channel_filter.addItem("Online", "online")
        self.channel_filter.addItem("Offline", "offline")
        self.channel_filter.setMinimumWidth(120)
        self.category_filter = QComboBox()
        self.category_filter.addItem("All categories", None)
        self.category_filter.setMinimumWidth(148)
        self.date_filter = QComboBox()
        self.date_filter.addItem("All dates", "all")
        self.date_filter.addItem("This month", "month")
        self.date_filter.addItem("Last 30 days", "30")
        self.date_filter.addItem("This year", "year")
        self.date_filter.addItem("Custom range", "custom")
        self.date_filter.setMinimumWidth(134)
        self.from_date = date_edit()
        self.to_date = date_edit()
        self.from_date.setEnabled(False)
        self.to_date.setEnabled(False)
        self.from_date.setToolTip("Start of the custom date range")
        self.to_date.setToolTip("End of the custom date range")
        today = QDate.currentDate()
        self.from_date.setDate(QDate(today.year(), today.month(), 1))
        self.to_date.setDate(today)
        self.clear_btn = icon_button("close", "Clear filters", size=32)

        for widget in (self.type_filter, self.channel_filter):
            filter_top.addWidget(widget)
        for widget in (
            self.category_filter,
            self.date_filter,
            self.from_date,
            self.to_date,
        ):
            filter_bottom.addWidget(widget)
        filter_bottom.addStretch(1)
        filter_bottom.addWidget(self.clear_btn)
        filter_layout.addLayout(filter_top)
        filter_layout.addLayout(filter_bottom)
        root.addWidget(filter_card)

        self.table_card = SectionCard("All transactions", "Newest activity first.")
        self.export_btn = make_button("Export CSV", "ghost", "download")
        self.export_btn.setToolTip("Save the transactions matching these filters as UTF-8 CSV")
        self.export_btn.clicked.connect(self.export_csv)
        self.table_card.add_action(Pill("UTF-8", "neutral"))
        self.table_card.add_action(self.export_btn)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Description", "Category", "Channel", "Method", "Type", "Amount"]
        )
        configure_table(self.table, row_height=49)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (0, 2, 3, 4, 5, 6):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(250)
        self.table_card.body.addWidget(self.table, 1)

        footer = QHBoxLayout()
        footer.setSpacing(12)
        self.count_label = QLabel("")
        self.count_label.setObjectName("cardSubtitle")
        footer.addWidget(self.count_label)
        footer.addStretch(1)
        self.income_total = QLabel("")
        self.income_total.setObjectName("successLabel")
        self.expense_total = QLabel("")
        self.expense_total.setObjectName("errorLabel")
        footer.addWidget(self.income_total)
        footer.addWidget(self.expense_total)
        self.table_card.body.addLayout(footer)
        root.addWidget(self.table_card, 1)

        self.search.textChanged.connect(self.refresh)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        self.channel_filter.currentIndexChanged.connect(self.refresh)
        self.category_filter.currentIndexChanged.connect(self.refresh)
        self.date_filter.currentIndexChanged.connect(self._date_preset_changed)
        self.from_date.dateChanged.connect(self._custom_date_changed)
        self.to_date.dateChanged.connect(self._custom_date_changed)
        self.clear_btn.clicked.connect(self.clear_filters)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self.edit_transaction())
        self._selection_changed()

    # ------------------------------------------------------------------ filters
    def _date_preset_changed(self) -> None:
        preset = self.date_filter.currentData()
        today = date.today()
        if preset == "month":
            self.from_date.setDate(QDate(today.year, today.month, 1))
            self.to_date.setDate(QDate(today.year, today.month, today.day))
        elif preset == "30":
            start = today - timedelta(days=29)
            self.from_date.setDate(QDate(start.year, start.month, start.day))
            self.to_date.setDate(QDate(today.year, today.month, today.day))
        elif preset == "year":
            self.from_date.setDate(QDate(today.year, 1, 1))
            self.to_date.setDate(QDate(today.year, today.month, today.day))
        custom = preset == "custom"
        self.from_date.setEnabled(custom)
        self.to_date.setEnabled(custom)
        self.refresh()

    def _custom_date_changed(self) -> None:
        if self.date_filter.currentData() == "custom":
            self.refresh()

    def clear_filters(self) -> None:
        for combo in (self.type_filter, self.channel_filter, self.category_filter, self.date_filter):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.from_date.setEnabled(False)
        self.to_date.setEnabled(False)
        self.refresh()

    def set_search(self, text: str) -> None:
        """Apply a search coming from the global search bar."""
        for combo in (
            self.type_filter,
            self.channel_filter,
            self.category_filter,
            self.date_filter,
        ):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.from_date.setEnabled(False)
        self.to_date.setEnabled(False)
        self.search.blockSignals(True)
        self.search.setText(text)
        self.search.blockSignals(False)
        self.refresh()

    def export_csv(self) -> None:
        filters = self._filters()
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        base = Path(documents) if documents else Path.home()
        default = str(base / f"Transactions_{date.today():%Y-%m-%d}.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export transactions", default, "CSV files (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            saved = self.service.export_transactions_csv(path, **filters)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Could not export", str(exc))
            return
        QMessageBox.information(
            self,
            "Export complete",
            f"{self.table.rowCount()} transaction"
            f"{'s' if self.table.rowCount() != 1 else ''} exported to:\n{saved}",
        )

    def _filters(self) -> dict:
        filters: dict = {}
        text = self.search.text().strip()
        if text:
            filters["search"] = text
        for key, combo in (
            ("transaction_type", self.type_filter),
            ("payment_channel", self.channel_filter),
            ("category", self.category_filter),
        ):
            value = combo.currentData()
            if value:
                filters[key] = value
        preset = self.date_filter.currentData()
        if preset == "custom":
            filters["start_date"] = self.from_date.date().toString("yyyy-MM-dd")
            filters["end_date"] = self.to_date.date().toString("yyyy-MM-dd")
        elif preset in ("month", "30", "year"):
            filters["start_date"] = self.from_date.date().toString("yyyy-MM-dd")
            filters["end_date"] = self.to_date.date().toString("yyyy-MM-dd")
        return filters

    # ------------------------------------------------------------------ actions
    def _selected_transaction(self) -> Transaction | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        if item is None:
            return None
        tx_id = item.data(Qt.ItemDataRole.UserRole)
        if tx_id is None:
            return None
        return self.service.get_transaction(int(tx_id))

    def _selection_changed(self) -> None:
        has_selection = self._selected_transaction() is not None
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    def add_transaction(self) -> None:
        dialog = TransactionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.service.add_transaction(dialog.transaction())
            except ValueError as exc:
                QMessageBox.warning(self, "Could not save", str(exc))
                return
            self.refresh()
            self.on_changed()

    def edit_transaction(self) -> None:
        tx = self._selected_transaction()
        if tx is None:
            return
        dialog = TransactionDialog(self, tx)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.service.update_transaction(dialog.transaction())
            except ValueError as exc:
                QMessageBox.warning(self, "Could not save", str(exc))
                return
            self.refresh()
            self.on_changed()

    def delete_transaction(self) -> None:
        tx = self._selected_transaction()
        if tx is None:
            return
        message = (
            f"Delete “{tx.description or tx.category}” "
            f"for {format_money(tx.amount_paise)}? This cannot be undone."
        )
        if not ConfirmDialog.ask(
            self,
            title="Delete transaction",
            message=message,
            confirm_text="Delete transaction",
        ):
            return
        self.service.delete_transaction(int(tx.id))
        self.refresh()
        self.on_changed()

    def mark_dirty(self) -> None:
        self._dirty = True

    # ------------------------------------------------------------------ refresh
    def refresh(self) -> None:
        self._dirty = False
        p = palette()
        current_category = self.category_filter.currentData()
        categories = self.service.categories()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All categories", None)
        for category in categories:
            self.category_filter.addItem(category, category)
        idx = self.category_filter.findData(current_category)
        self.category_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self.category_filter.blockSignals(False)

        transactions = self.service.list_transactions(**self._filters())
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(transactions))
        income_total = 0
        expense_total = 0
        for row, tx in enumerate(transactions):
            if tx.transaction_type == "income":
                income_total += tx.amount_paise
            else:
                expense_total += tx.amount_paise
            date_item = QTableWidgetItem(tx.transaction_date)
            date_item.setData(Qt.ItemDataRole.UserRole, tx.id)
            desc_item = QTableWidgetItem(tx.description or "—")
            cat_item = QTableWidgetItem(tx.category)
            channel_item = QTableWidgetItem(
                f"●  {'Online' if tx.payment_channel == 'online' else 'Offline'}"
            )
            channel_item.setForeground(
                QColor(p["accent2"] if tx.payment_channel == "online" else p["warning"])
            )
            method_item = QTableWidgetItem(tx.payment_method)
            type_item = QTableWidgetItem(tx.transaction_type.upper())
            type_item.setForeground(
                QColor(p["income"] if tx.transaction_type == "income" else p["expense"])
            )
            sign = "+" if tx.transaction_type == "income" else "−"
            amount_item = QTableWidgetItem(f"{sign}{format_money(tx.amount_paise)}")
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            amount_item.setForeground(
                QColor(p["income"] if tx.transaction_type == "income" else p["expense"])
            )
            for column, item in enumerate(
                [
                    date_item,
                    desc_item,
                    cat_item,
                    channel_item,
                    method_item,
                    type_item,
                    amount_item,
                ]
            ):
                if column in (1, 2):
                    font = item.font()
                    font.setWeight(
                        QFont.Weight.DemiBold if column == 2 else QFont.Weight.Medium
                    )
                    item.setFont(font)
                self.table.setItem(row, column, item)
        self.table.setUpdatesEnabled(True)

        self.table_card.set_subtitle(
            "Newest activity first."
            if transactions
            else "No transactions match these filters yet."
        )
        self.count_label.setText(
            f"{len(transactions)} transaction{'s' if len(transactions) != 1 else ''} shown"
        )
        self.income_total.setText(f"IN  {format_money(income_total)}")
        self.expense_total.setText(f"OUT  {format_money(expense_total)}")
        self._selection_changed()

    def apply_theme(self) -> None:
        self.refresh()
