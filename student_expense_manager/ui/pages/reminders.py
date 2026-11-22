from __future__ import annotations

from datetime import date
from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.repositories.reminder_repository import Reminder
from student_expense_manager.repositories.settings_repository import SettingsRepository
from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.money import format_money
from student_expense_manager.services.notifications import NotificationCenter
from student_expense_manager.services.reminder_service import ReminderService
from student_expense_manager.ui.dialogs import ConfirmDialog
from student_expense_manager.ui.page_base import PageHeader, content_layout
from student_expense_manager.ui.reminder_dialogs import MarkPaidDialog, ReminderDialog
from student_expense_manager.ui.reminder_widgets import (
    ReminderCalendar,
    ReminderCard,
    ToastHost,
    motion_enabled,
)
from student_expense_manager.ui.widgets import (
    EmptyState,
    PeriodSelector,
    SectionCard,
    SegmentedControl,
    icon_button,
    make_button,
)

# Short labels keep the filter tabs inside the page at the minimum window size;
# the full count and section name are shown in the card heading instead.
_SECTIONS = [
    ("All", "all"),
    ("Upcoming", "upcoming"),
    ("Today", "due_today"),
    ("Overdue", "overdue"),
    ("Paid", "paid"),
]

_TONE_PRIORITY = {"accent": 0, "success": 1, "warning": 2, "danger": 3}


class RemindersPage(QWidget):
    """Premium Payment Reminder Center with list and calendar views."""

    def __init__(
        self,
        service: ReminderService,
        finance: FinanceService,
        settings: SettingsRepository,
        on_changed: Callable[[], None],
        on_navigate: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.finance = finance
        self.settings = settings
        self.on_changed = on_changed
        self.on_navigate = on_navigate
        self._dirty = True
        self._section = "all"
        self._selected_day: int | None = None

        root = content_layout(self, margins=(26, 12, 26, 14), spacing=13)
        # A safety net for very narrow windows or large system fonts: no control
        # should ever be unreachable simply because it was clipped.
        scroll_area = self.findChild(QScrollArea)
        if scroll_area is not None:
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.header = PageHeader(
            "Payment Reminders",
            "A calm, timely view of every payment coming your way.",
            "PAYMENT CENTRE",
        )
        self.period = PeriodSelector()
        self.period.changed.connect(lambda *_: self.refresh())
        self.view_control = SegmentedControl(
            [("List", "list"), ("Calendar", "calendar")], compact=True
        )
        self.view_control.changed.connect(self._view_changed)
        # The period, view and notification controls live in the compact bar
        # below the header so the header never overflows the window.
        add_btn = make_button("Add reminder", "primary", "plus")
        add_btn.clicked.connect(self.add_reminder)
        self.header.add_action(add_btn)
        root.addWidget(self.header)

        self.alert_bar = self._build_alert_bar()
        root.addWidget(self.alert_bar)

        stats = QHBoxLayout()
        stats.setSpacing(11)
        from student_expense_manager.ui.page_base import MiniStat

        self.active_stat = MiniStat("Active reminders", "0", "not paid or cancelled", "bell-ring",
                                    icon_color="#9B85FF")
        self.upcoming_stat = MiniStat("Upcoming", "0", "later this month", "clock",
                                      icon_color="#4F7CFF", tint="#172A4D")
        self.today_stat = MiniStat("Due today", "0", "needs your attention", "bell",
                                   icon_color="#FBBF24", tint="#3A2C14")
        self.overdue_stat = MiniStat("Overdue", "0", "payments past due", "alert",
                                     icon_color="#FB7185", tint="#3B1728")
        self.pending_stat = MiniStat("Pending amount", "₹0.00", "across active reminders", "wallet",
                                     icon_color="#34D399", tint="#12362F")
        for stat in (
            self.active_stat,
            self.upcoming_stat,
            self.today_stat,
            self.overdue_stat,
            self.pending_stat,
        ):
            stat.setFixedHeight(92)
            stats.addWidget(stat)
        root.addLayout(stats)

        self.views = QStackedWidget()
        self.list_view = self._build_list_view()
        self.calendar_view = self._build_calendar_view()
        self.views.addWidget(self.list_view)
        self.views.addWidget(self.calendar_view)
        root.addWidget(self.views, 1)
        root.addStretch(1)

        self.toast_host = ToastHost(self)
        self.toast_host.set_motion(motion_enabled(self.settings))
        self.notification_center = NotificationCenter(self._show_toast)
        self.notification_center.enabled = self._alerts_enabled()
        self.notification_center.system_enabled = (
            self.settings.get("system_notifications", "1") != "0"
        )

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(60_000)
        self.poll_timer.timeout.connect(self._poll_notifications)
        self.poll_timer.start()
        QTimer.singleShot(900, self._poll_notifications)

    # ------------------------------------------------------------------ chrome
    def _build_alert_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("filterBar")
        bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = QVBoxLayout(bar)
        outer.setContentsMargins(13, 8, 13, 8)
        outer.setSpacing(7)

        # Row 1 keeps the view switch and reporting period close to the cards
        # they control, instead of crowding the page title.
        view_row = QHBoxLayout()
        view_row.setSpacing(8)
        view_row.addWidget(self.view_control)
        view_row.addStretch(1)
        view_row.addWidget(self.period)
        outer.addLayout(view_row)

        # Row 2: notification controls. Labels can shrink rather than forcing
        # the whole page wider than the window.
        alert_row = QHBoxLayout()
        alert_row.setSpacing(8)
        self.alert_dot = QLabel("● Alerts on")
        self.alert_dot.setObjectName("statLabel")
        self.alert_dot.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.alert_dot.setStyleSheet(f"color: {'#34D399' if self._alerts_enabled() else '#736C9B'};")
        alert_row.addWidget(self.alert_dot)
        self.alerts_check = QCheckBox("Enable alerts")
        self.alerts_check.setToolTip("Turn reminder notifications on or off")
        self.alerts_check.setChecked(self._alerts_enabled())
        self.alerts_check.toggled.connect(self._toggle_alerts)
        alert_row.addWidget(self.alerts_check)
        alert_row.addStretch(1)
        hint = QLabel("Checks every minute")
        hint.setObjectName("dimLabel")
        hint.setToolTip("Due reminders are checked every minute while the app is open")
        hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        alert_row.addWidget(hint)
        test_btn = make_button("Test alert", "secondary", "bell-ring")
        test_btn.clicked.connect(
            lambda: self._show_toast("Reminder center", "Notifications are working.", "success")
        )
        alert_row.addWidget(test_btn)
        settings_btn = icon_button("settings", "Notification settings", size=28)
        settings_btn.clicked.connect(lambda: self._navigate("settings"))
        alert_row.addWidget(settings_btn)
        outer.addLayout(alert_row)
        return bar

    def _build_list_view(self) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.section_card = SectionCard(
            "All reminders",
            "Upcoming, due today and overdue payments in one place.",
        )
        self.section_control = SegmentedControl(_SECTIONS, compact=True)
        self.section_control.changed.connect(self._section_changed)
        self.section_card.add_action(self.section_control)
        self.card_host = QWidget()
        self.card_layout = QVBoxLayout(self.card_host)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(9)
        self.section_card.body.addWidget(self.card_host)
        layout.addWidget(self.section_card)
        return host

    def _build_calendar_view(self) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        card = SectionCard(
            "Payment calendar",
            "Coloured dots show due payments. Click a day to inspect it.",
        )
        self.calendar = ReminderCalendar()
        self.calendar.day_selected.connect(self._day_selected)
        card.body.addWidget(self.calendar)
        self.day_label = QLabel("Choose a day to see its reminders.")
        self.day_label.setObjectName("cardSubtitle")
        card.body.addWidget(self.day_label)
        self.day_host = QWidget()
        self.day_layout = QVBoxLayout(self.day_host)
        self.day_layout.setContentsMargins(0, 0, 0, 0)
        self.day_layout.setSpacing(8)
        card.body.addWidget(self.day_host)
        layout.addWidget(card)
        return host

    # ------------------------------------------------------------------ actions
    def _alerts_enabled(self) -> bool:
        return self.settings.get("reminder_notifications", "1") != "0"

    def _toggle_alerts(self, enabled: bool) -> None:
        self.settings.set("reminder_notifications", "1" if enabled else "0")
        self.notification_center.enabled = enabled
        color = "#34D399" if enabled else "#736C9B"
        self.alert_dot.setText("● Alerts on" if enabled else "○ Alerts paused")
        self.alert_dot.setStyleSheet(f"color: {color};")

    def _navigate(self, name: str) -> None:
        if self.on_navigate:
            self.on_navigate(name)

    def _view_changed(self, value: str) -> None:
        self.views.setCurrentIndex(1 if value == "calendar" else 0)
        self.refresh()

    def _section_changed(self, value: str) -> None:
        self._section = value
        self._selected_day = None
        self.refresh()

    def _day_selected(self, day: int) -> None:
        self._selected_day = day
        self._render_day(day)

    def add_reminder(self) -> None:
        dialog = ReminderDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.add_reminder(dialog.reminder())
        except ValueError as exc:
            QMessageBox.warning(self, "Could not add reminder", str(exc))
            return
        self._show_toast("Reminder added", "Your payment is on the radar.", "success")
        self._data_changed()

    def edit_reminder(self, reminder_id: int) -> None:
        reminder = self.service.get(reminder_id)
        if reminder is None:
            return
        dialog = ReminderDialog(self, reminder)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.update_reminder(dialog.reminder())
        except ValueError as exc:
            QMessageBox.warning(self, "Could not save reminder", str(exc))
            return
        self._show_toast("Reminder updated", "Changes saved on this device.", "accent")
        self._data_changed()

    def delete_reminder(self, reminder_id: int) -> None:
        reminder = self.service.get(reminder_id)
        if reminder is None:
            return
        if not ConfirmDialog.ask(
            self,
            title="Delete reminder?",
            message=f"“{reminder.title}” will be removed. This cannot be undone.",
            confirm_text="Delete reminder",
        ):
            return
        whole_series = False
        if reminder.series_id and reminder.recurrence != "none":
            whole_series = ConfirmDialog.ask(
                self,
                title="Delete the whole series?",
                message="Choose Yes to remove every future payment in this series, or No to "
                "remove only this one.",
                confirm_text="Whole series",
            )
        self.service.delete_reminder(reminder_id, whole_series=whole_series)
        self._data_changed()

    def cancel_reminder(self, reminder_id: int) -> None:
        self.service.cancel_reminder(reminder_id)
        self._show_toast("Reminder cancelled", "It stays in your history.", "accent")
        self._data_changed()

    def toggle_notifications(self, reminder_id: int, enabled: bool) -> None:
        self.service.toggle_notifications(reminder_id, enabled)
        self.refresh()

    def mark_paid(self, reminder_id: int) -> None:
        reminder = self.service.get(reminder_id)
        if reminder is None:
            return
        dialog = MarkPaidDialog(self, reminder)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        create_expense, completed = dialog.values()
        try:
            _updated, tx_id, changed = self.service.mark_paid(
                reminder_id, create_expense, completed
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Could not mark as paid", str(exc))
            return
        if changed:
            message = (
                "One expense was added to your ledger."
                if tx_id is not None
                else "Marked paid without creating an expense."
            )
            self._show_toast("Payment complete", message, "success")
            self._data_changed()
        else:
            self._show_toast("Already paid", "No duplicate expense was created.", "accent")

    def _show_toast(self, title: str, body: str, tone: str = "accent") -> None:
        self.toast_host.show_toast(title, body, tone)

    def _poll_notifications(self) -> None:
        if not self.notification_center.enabled:
            return
        messages = self.service.poll_notifications()
        for message in messages:
            self.notification_center.show(
                message["title"], message["body"], message["tone"]
            )
        if messages:
            self.refresh()

    def _data_changed(self) -> None:
        self.refresh()
        self.on_changed()

    # ------------------------------------------------------------------ render
    def refresh(self) -> None:
        self._alerts_check_sync()
        today = date.today()
        summary = self.service.summary(today)
        self.active_stat.set_data(str(summary["active"]),
                                  f"{summary['total']} reminders in total")
        self.upcoming_stat.set_data(str(summary["upcoming"]), "scheduled ahead")
        self.today_stat.set_data(str(summary["due_today"]), "due on " + today.strftime("%d %b"))
        self.overdue_stat.set_data(str(summary["overdue"]), "past their due date")
        self.pending_stat.set_data(format_money(summary["pending_paise"]), "still to be paid")

        sections = self.service.sections(today)

        self._clear(self.card_layout)
        items = list(sections.get(self._section, sections["all"]))
        if self._section == "all":
            items = sorted(items, key=lambda r: (self.service.effective_status(r, today) == "paid",
                                                 r.due_date))
        section_label = next(
            (label for label, value in _SECTIONS if value == self._section), "All"
        )
        self.section_card.set_title(
            f"{section_label}  ·  {len(items)}",
            "Tap a card to edit, pay or remove a payment.",
        )
        if not items:
            self.card_layout.addWidget(
                EmptyState(
                    "sparkles",
                    "Nothing here yet",
                    "Add a reminder to keep this section useful.",
                    self.card_host,
                )
            )
        else:
            for reminder in items[:60]:
                status = self.service.effective_status(reminder, today)
                card = ReminderCard(
                    reminder,
                    status,
                    self.service.days_until_due(reminder, today),
                    self.settings,
                    self.card_host,
                )
                card.paid_requested.connect(self.mark_paid)
                card.edit_requested.connect(self.edit_reminder)
                card.delete_requested.connect(self.delete_reminder)
                card.cancel_requested.connect(self.cancel_reminder)
                card.toggle_requested.connect(self.toggle_notifications)
                self.card_layout.addWidget(card)

        self._render_calendar(sections, today)
        if self._selected_day is not None:
            self._render_day(self._selected_day)
        self._dirty = False

    def _render_calendar(self, sections: dict[str, list[Reminder]], today: date) -> None:
        month, year = self.period.period()
        days: dict[int, str] = {}
        for status in ("upcoming", "due_today", "overdue", "paid", "cancelled"):
            for reminder in sections.get(status, []):
                due = date.fromisoformat(reminder.due_date)
                if (due.month, due.year) != (month, year):
                    continue
                day = due.day
                current = days.get(day)
                if current is None or _TONE_PRIORITY.get(status, 0) > _TONE_PRIORITY.get(current, 0):
                    days[day] = status
        self.calendar.set_period(month, year, days)

    def _render_day(self, day: int) -> None:
        month, year = self.period.period()
        try:
            target = date(year, month, day)
        except ValueError:
            return
        today = date.today()
        matches = [
            reminder
            for reminder in self.service.list_reminders()
            if date.fromisoformat(reminder.due_date) == target
        ]
        self.day_label.setText(
            f"{target.strftime('%A, %d %B %Y')} · {len(matches)} reminder(s)"
        )
        self._clear(self.day_layout)
        if not matches:
            label = QLabel("No payments due on this day.")
            label.setObjectName("cardSubtitle")
            self.day_layout.addWidget(label)
            return
        for reminder in matches:
            status = self.service.effective_status(reminder, today)
            card = ReminderCard(
                reminder, status, self.service.days_until_due(reminder, today),
                self.settings, self.day_host, animate=False,
            )
            card.paid_requested.connect(self.mark_paid)
            card.edit_requested.connect(self.edit_reminder)
            card.delete_requested.connect(self.delete_reminder)
            card.cancel_requested.connect(self.cancel_reminder)
            card.toggle_requested.connect(self.toggle_notifications)
            self.day_layout.addWidget(card)

    def _clear(self, layout) -> None:  # noqa: ANN001
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def mark_dirty(self) -> None:
        self._dirty = True

    def apply_theme(self) -> None:
        self.toast_host.set_motion(motion_enabled(self.settings))
        self._alerts_check_sync()

    def _alerts_check_sync(self) -> None:
        enabled = self._alerts_enabled()
        self.alerts_check.blockSignals(True)
        self.alerts_check.setChecked(enabled)
        self.alerts_check.blockSignals(False)
        self.notification_center.enabled = enabled

    def resizeEvent(self, event) -> None:  # noqa: N802, ANN001
        self.toast_host.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)
