from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QStandardPaths, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager import __version__
from student_expense_manager.data.db import (
    backup_database,
    database_info,
    get_backups_dir,
    get_data_dir,
    restore_database,
)
from student_expense_manager.repositories.settings_repository import SettingsRepository
from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.money import (
    currency_name,
    currency_symbol,
    get_currency,
    set_currency,
)
from student_expense_manager.services.notifications import setup_instructions
from student_expense_manager.ui.dialogs import ConfirmDialog
from student_expense_manager.ui.page_base import PageHeader, content_layout, divider
from student_expense_manager.ui.theme import current_theme, palette
from student_expense_manager.ui.widgets import (
    IconChip,
    Pill,
    SegmentedControl,
    SectionCard,
    make_button,
)


def _human_size(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


class SettingsPage(QWidget):
    def __init__(
        self,
        service: FinanceService,
        on_theme_change: Callable[..., None] | None = None,
        on_data_change: Callable[[], None] | None = None,
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.on_theme_change = on_theme_change
        self.on_data_change = on_data_change
        self.on_navigate = on_navigate
        self.settings = SettingsRepository()
        self._dirty = True
        p = palette()

        root = content_layout(self)
        self.header = PageHeader(
            "Settings",
            "Make the workspace yours. Everything stays on this computer.",
            "PREFERENCES",
        )
        self.header.add_action(Pill("OFFLINE", "success"))
        root.addWidget(self.header)

        columns = QHBoxLayout()
        columns.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(14)

        # ---------------------------------------------------------- appearance
        self.appearance_card = SectionCard(
            "Appearance",
            "Pick the theme that is easiest on your eyes.",
        )
        self.appearance_chip = IconChip("sparkles", p["accent_soft"], p["violet_tint"], size=34)
        self.appearance_card.add_action(self.appearance_chip)
        theme_head = QHBoxLayout()
        theme_head.setSpacing(10)
        theme_text = QVBoxLayout()
        theme_text.setSpacing(1)
        theme_title = QLabel("Colour theme")
        theme_title.setStyleSheet("font-size:12px; font-weight:600;")
        theme_caption = QLabel("Applies instantly across every page.")
        theme_caption.setObjectName("dimLabel")
        theme_text.addWidget(theme_title)
        theme_text.addWidget(theme_caption)
        theme_head.addLayout(theme_text, 1)
        self.theme_control = SegmentedControl([("Dark", "dark"), ("Light", "light")])
        self.theme_control.changed.connect(self._theme_selected)
        theme_head.addWidget(self.theme_control)
        self.appearance_card.body.addLayout(theme_head)

        self.appearance_card.body.addWidget(divider())

        currency_row = QHBoxLayout()
        currency_row.setSpacing(10)
        currency_text = QVBoxLayout()
        currency_text.setSpacing(1)
        currency_title = QLabel("Currency")
        currency_title.setStyleSheet("font-size:12px; font-weight:600;")
        currency_caption = QLabel(
            "Amounts are stored in whole paise and shown with Indian digit grouping."
        )
        currency_caption.setObjectName("dimLabel")
        currency_caption.setWordWrap(True)
        currency_text.addWidget(currency_title)
        currency_text.addWidget(currency_caption)
        currency_row.addLayout(currency_text, 1)
        self.currency_value = QLabel("")
        self.currency_value.setStyleSheet("font-size:12px; font-weight:700;")
        currency_row.addWidget(self.currency_value, 0, Qt.AlignmentFlag.AlignTop)
        self.appearance_card.body.addLayout(currency_row)
        left.addWidget(self.appearance_card)

        # ---------------------------------------------------------- alerts
        self.alerts_card = SectionCard(
            "Reminder alerts",
            "Choose how the Payment Reminder Center notifies you.",
        )
        self.alerts_chip = IconChip("bell-ring", p["accent_soft"], p["violet_tint"], size=34)
        self.alerts_card.add_action(self.alerts_chip)
        self.alert_options: dict[str, QCheckBox] = {}
        for key, text in (
            ("reminder_notifications", "Enable payment reminders"),
            ("system_notifications", "Show Windows system notifications"),
            ("reduced_motion", "Reduce animations and motion"),
        ):
            check = QCheckBox(text)
            checked = self.settings.get(key, "0" if key == "reduced_motion" else "1") != "0"
            check.setChecked(checked)
            check.toggled.connect(
                lambda on, setting=key: self.settings.set(setting, "1" if on else "0")
            )
            self.alert_options[key] = check
            self.alerts_card.body.addWidget(check)
        note = QLabel(setup_instructions())
        note.setObjectName("dimLabel")
        note.setWordWrap(True)
        self.alerts_card.body.addWidget(note)
        reminders_link = make_button("Open Payment Reminders", "secondary", "bell")
        reminders_link.clicked.connect(lambda: self.on_navigate and self.on_navigate("reminders"))
        self.alerts_card.body.addWidget(reminders_link)
        left.addWidget(self.alerts_card)

        # ---------------------------------------------------------- data
        self.data_card = SectionCard(
            "Data & backups",
            "One local SQLite database holds your transactions and budgets.",
        )
        self.data_chip = IconChip("database", p["accent2"], p["blue_tint"], size=34)
        self.data_card.add_action(self.data_chip)

        path_label = QLabel("DATABASE FILE")
        path_label.setObjectName("sectionLabel")
        self.data_card.body.addWidget(path_label)
        self.path_value = QLineEdit()
        self.path_value.setObjectName("pathField")
        self.path_value.setReadOnly(True)
        self.path_value.setToolTip("Full path to your local database")
        self.data_card.body.addWidget(self.path_value)

        stats = QHBoxLayout()
        stats.setSpacing(18)
        self.stat_values: dict[str, QLabel] = {}
        for key, label in (
            ("transactions", "Transactions"),
            ("budgets", "Budgets"),
            ("size", "Database size"),
            ("backups", "Backup copies"),
        ):
            box = QVBoxLayout()
            box.setSpacing(1)
            value = QLabel("—")
            value.setObjectName("insightValue")
            caption = QLabel(label)
            caption.setObjectName("dimLabel")
            box.addWidget(value)
            box.addWidget(caption)
            stats.addLayout(box)
            self.stat_values[key] = value
        stats.addStretch(1)
        self.data_card.body.addLayout(stats)

        self.data_card.body.addWidget(divider())

        note = QLabel(
            "A safety copy of the current database is saved automatically before "
            "any restore, and nothing is ever deleted by updating the app."
        )
        note.setObjectName("dimLabel")
        note.setWordWrap(True)
        self.data_card.body.addWidget(note)

        buttons = QHBoxLayout()
        buttons.setSpacing(9)
        self.backup_btn = make_button("Back up database", "primary", "database")
        self.backup_btn.clicked.connect(self.backup)
        self.restore_btn = make_button("Restore a backup", "secondary", "upload")
        self.restore_btn.clicked.connect(self.restore)
        self.folder_btn = make_button("Open data folder", "secondary", "arrow-up-right")
        self.folder_btn.clicked.connect(self.open_data_folder)
        buttons.addWidget(self.backup_btn)
        buttons.addWidget(self.restore_btn)
        buttons.addWidget(self.folder_btn)
        buttons.addStretch(1)
        self.data_card.body.addLayout(buttons)
        left.addWidget(self.data_card)

        self.privacy_card = SectionCard(
            "Privacy",
            "No account, no sync, no telemetry.",
        )
        self.privacy_chip = IconChip("shield", p["success"], p["green_tint"], size=34)
        self.privacy_card.add_action(self.privacy_chip)
        for title_text, body_text in (
            (
                "Lives on this device",
                "The database is read and written locally. The app never opens a network connection.",
            ),
            (
                "You own the file",
                "Back up the database whenever you like, or copy it to another computer and restore it there.",
            ),
            (
                "No hidden changes",
                "Schema upgrades are additive. Existing transactions and budgets are preserved.",
            ),
        ):
            row = QHBoxLayout()
            row.setSpacing(10)
            tick = QLabel("✓")
            tick.setStyleSheet(f"color:{p['success']}; font-size:11px; font-weight:700;")
            tick.setFixedWidth(12)
            text = QLabel(f"<b>{title_text}.</b> {body_text}")
            text.setObjectName("cardSubtitle")
            text.setWordWrap(True)
            row.addWidget(tick, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(text, 1)
            self.privacy_card.body.addLayout(row)
        left.addWidget(self.privacy_card)
        left.addStretch(1)
        columns.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(14)

        self.about_card = SectionCard("About", "A small app for everyday student money.")
        self.about_chip = IconChip("analytics", "#FFFFFF", p["accent"], size=38)
        self.about_card.add_action(self.about_chip)
        about_head = QHBoxLayout()
        about_head.setSpacing(10)
        name_box = QVBoxLayout()
        name_box.setSpacing(1)
        app_name = QLabel("Student Expense Manager")
        app_name.setStyleSheet("font-size:14px; font-weight:700;")
        self.version_pill = Pill(f"v{__version__}", "accent")
        name_box.addWidget(app_name)
        name_box.addWidget(self.version_pill, 0, Qt.AlignmentFlag.AlignLeft)
        about_head.addLayout(name_box, 1)
        self.about_card.body.addLayout(about_head)

        about_text = QLabel(
            "Track spending, set monthly budgets and print a clean statement "
            "at the end of the month. Built with Python, PySide6 and SQLite."
        )
        about_text.setObjectName("cardSubtitle")
        about_text.setWordWrap(True)
        self.about_card.body.addWidget(about_text)

        self.about_card.body.addWidget(divider())
        for label, value in (
            ("Storage", "Local SQLite file"),
            ("Money", "Integer paise, no rounding drift"),
            ("Reports", "PDF statements and UTF-8 CSV"),
        ):
            row = QHBoxLayout()
            key_label = QLabel(label)
            key_label.setObjectName("cardSubtitle")
            value_label = QLabel(value)
            value_label.setStyleSheet("font-size:11px; font-weight:600;")
            value_label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            row.addWidget(key_label)
            row.addStretch(1)
            row.addWidget(value_label)
            self.about_card.body.addLayout(row)
        right.addWidget(self.about_card)

        tips = SectionCard("Good to know", "A few shortcuts around the workspace.")
        for icon_kind, title_text, body_text in (
            (
                "search",
                "Search from anywhere",
                "The bar at the top jumps to Transactions and applies your search.",
            ),
            (
                "calendar",
                "Change the month",
                "Period controls on Dashboard, Budgets, Analytics and Reports are independent.",
            ),
            (
                "download",
                "Export your data",
                "Use Export CSV on Transactions for a filtered ledger, or on Reports for a month.",
            ),
        ):
            row = QHBoxLayout()
            row.setSpacing(10)
            chip = IconChip(icon_kind, p["accent_soft"], p["violet_tint"], size=30)
            text_box = QVBoxLayout()
            text_box.setSpacing(1)
            title_label = QLabel(title_text)
            title_label.setStyleSheet("font-size:11.5px; font-weight:600;")
            caption = QLabel(body_text)
            caption.setObjectName("dimLabel")
            caption.setWordWrap(True)
            text_box.addWidget(title_label)
            text_box.addWidget(caption)
            row.addWidget(chip, 0, Qt.AlignmentFlag.AlignTop)
            row.addLayout(text_box, 1)
            tips.body.addLayout(row)
        right.addWidget(tips)
        right.addStretch(1)
        columns.addLayout(right, 2)

        root.addLayout(columns)
        root.addStretch(1)

    # ------------------------------------------------------------------ actions
    def _theme_selected(self, name: str) -> None:
        self.settings.set("theme", name)
        if self.on_theme_change is not None:
            self.on_theme_change(name)
        else:
            from student_expense_manager.ui.theme import set_current_theme

            set_current_theme(name)

    def _default_backup_name(self) -> str:
        return f"StudentExpenseManager-backup-{date.today():%Y-%m-%d}.db"

    def _default_dir(self) -> Path:
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        return Path(documents) if documents else Path.home()

    def _guard(self, title: str, action: Callable[[], None]) -> None:
        try:
            action()
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            QMessageBox.warning(self, title, str(exc))

    def backup(self) -> None:
        default = str(self._default_dir() / self._default_backup_name())
        path, _ = QFileDialog.getSaveFileName(
            self, "Back up database", default, "SQLite database (*.db)"
        )
        if not path:
            return
        if not path.lower().endswith(".db"):
            path += ".db"
        try:
            saved = backup_database(path)
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            QMessageBox.warning(self, "Could not back up", str(exc))
            return
        self.refresh()
        QMessageBox.information(
            self,
            "Backup saved",
            f"A complete copy of your database is now at:\n{saved}",
        )

    def restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore a backup",
            str(get_backups_dir()),
            "SQLite database (*.db *.sqlite *.sqlite3);;All files (*)",
        )
        if not path:
            return
        if not ConfirmDialog.ask(
            self,
            title="Restore this backup?",
            message=(
                "Your current database will be replaced with the selected file. "
                "A safety copy of the current data is saved automatically first."
            ),
            confirm_text="Restore backup",
        ):
            return
        try:
            restore_database(path)
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            QMessageBox.warning(self, "Could not restore", str(exc))
            return

        set_currency(str(self.settings.get("currency", "INR") or "INR"))
        self.refresh()
        if self.on_data_change is not None:
            self.on_data_change()
        theme = str(self.settings.get("theme", "dark") or "dark")
        if self.on_theme_change is not None:
            self.on_theme_change(theme)
        QMessageBox.information(
            self,
            "Backup restored",
            "Your records have been restored. The previous database was kept "
            f"in:\n{get_backups_dir()}",
        )

    def open_data_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_data_dir())))

    # ------------------------------------------------------------------ refresh
    def mark_dirty(self) -> None:
        self._dirty = True

    def refresh(self) -> None:
        self._dirty = False
        info = database_info()
        path = Path(str(info["path"]))
        self.path_value.setText(str(path))
        self.path_value.setCursorPosition(0)
        self.stat_values["transactions"].setText(f"{int(info['transactions']):,}")
        self.stat_values["budgets"].setText(f"{int(info['budgets']):,}")
        self.stat_values["size"].setText(_human_size(int(info["size_bytes"])))
        try:
            backups = len(list(get_backups_dir().glob("*.db")))
        except OSError:
            backups = 0
        self.stat_values["backups"].setText(str(backups))
        self.currency_value.setText(
            f"{currency_symbol()} {currency_name()} ({get_currency()})"
        )
        self.theme_control.set_current(current_theme())

    def apply_theme(self) -> None:
        p = palette()
        self.appearance_chip.set_kind("sparkles", p["accent_soft"], p["violet_tint"])
        self.data_chip.set_kind("database", p["accent2"], p["blue_tint"])
        self.privacy_chip.set_kind("shield", p["success"], p["green_tint"])
        self.about_chip.set_kind("analytics", "#FFFFFF", p["accent"])
        self.refresh()
