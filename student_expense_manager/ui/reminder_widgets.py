from __future__ import annotations

import calendar
import math
import os
from datetime import date

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.repositories.reminder_repository import Reminder
from student_expense_manager.services.money import format_money
from student_expense_manager.ui.icons import make_icon
from student_expense_manager.ui.theme import palette
from student_expense_manager.ui.widgets import (
    IconChip,
    PercentBar,
    Pill,
    icon_button,
    repolish,
)


def motion_enabled(settings=None) -> bool:
    """Respect the app setting, the environment and Windows 'MinAnimate'."""
    if settings is not None:
        value = settings.get("reduced_motion")
        if value is not None:
            return str(value) not in {"1", "true", "True"}
    if os.environ.get("QT_REDUCED_MOTION") in {"1", "true", "True"}:
        return False
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop\WindowMetrics"
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MinAnimate")
                if str(value) == "0":
                    return False
        except OSError:
            pass
    return True


_TONES: dict[str, dict[str, str]] = {
    "upcoming": {"color": "accent_soft", "tint": "violet_tint", "icon": "bell", "pill": "accent"},
    "due_today": {"color": "warning", "tint": "amber_tint", "icon": "bell-ring", "pill": "warning"},
    "overdue": {"color": "danger", "tint": "red_tint", "icon": "alert", "pill": "danger"},
    "paid": {"color": "success", "tint": "green_tint", "icon": "check-circle", "pill": "success"},
    "cancelled": {"color": "dim", "tint": "surface2", "icon": "close", "pill": "neutral"},
}


class ReminderCard(QFrame):
    """A glassy reminder tile with gentle, performance-conscious motion."""

    paid_requested = Signal(int)
    edit_requested = Signal(int)
    delete_requested = Signal(int)
    cancel_requested = Signal(int)
    toggle_requested = Signal(int, bool)

    def __init__(
        self,
        reminder: Reminder,
        status: str,
        days_until: int,
        settings=None,
        parent: QWidget | None = None,
        *,
        animate: bool = True,
    ) -> None:
        super().__init__(parent)
        self.reminder = reminder
        self.status = status
        self.days_until = days_until
        self._motion = motion_enabled(settings)
        self._phase = 0.0
        self._entrance = 1.0 if not (animate and self._motion) else 0.0
        self._base_margins = (15, 12, 15, 12)
        self.setObjectName("reminderCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("tone", status)
        self.setMinimumHeight(96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        root = QHBoxLayout(self)
        root.setContentsMargins(*self._base_margins)
        root.setSpacing(12)
        spec = _TONES.get(status, _TONES["upcoming"])
        p = palette()
        self.chip = IconChip(
            spec["icon"], p[spec["color"]], p[spec["tint"]], size=40
        )
        root.addWidget(self.chip, 0, Qt.AlignmentFlag.AlignTop)

        body = QVBoxLayout()
        body.setSpacing(5)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.title = QLabel(reminder.title)
        self.title.setObjectName("cardTitle")
        self.title.setStyleSheet("font-size: 13.5px; font-weight: 700;")
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title_row.addWidget(self.title, 1)
        self.status_pill = Pill(_status_label(status), spec["pill"])
        title_row.addWidget(self.status_pill, 0, Qt.AlignmentFlag.AlignTop)
        body.addLayout(title_row)

        detail = QLabel(self._detail_text())
        detail.setObjectName("cardSubtitle")
        detail.setWordWrap(True)
        detail.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        body.addWidget(detail)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(9)
        self.progress = PercentBar(height=6, color=p[spec["color"]])
        self.progress.setFixedHeight(6)
        progress_row.addWidget(self.progress, 1)
        self.progress_label = QLabel(self._progress_label())
        self.progress_label.setObjectName("dimLabel")
        progress_row.addWidget(self.progress_label)
        body.addLayout(progress_row)
        self.progress.set_value(self._progress_fraction(), animate=False)
        root.addLayout(body, 1)

        actions = QVBoxLayout()
        actions.setSpacing(6)
        self.pay_btn = QPushButton("Mark paid")
        self.pay_btn.setObjectName("primary" if status in {"due_today", "overdue"} else "secondary")
        self.pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pay_btn.setVisible(status not in {"paid", "cancelled"})
        self.pay_btn.clicked.connect(lambda: self.paid_requested.emit(reminder.id or 0))
        actions.addWidget(self.pay_btn, 0, Qt.AlignmentFlag.AlignRight)

        icons_row = QHBoxLayout()
        icons_row.setSpacing(2)
        self.notify_btn = icon_button(
            "bell" if reminder.notifications_enabled else "bell-off",
            "Turn notifications off" if reminder.notifications_enabled else "Turn notifications on",
            "accent" if reminder.notifications_enabled else "muted",
            size=26,
        )
        self.notify_btn.clicked.connect(self._toggle_notifications)
        self.edit_btn = icon_button("edit", "Edit reminder", size=26)
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(reminder.id or 0))
        self.cancel_btn = icon_button("close", "Cancel this reminder", size=26)
        self.cancel_btn.setVisible(status not in {"paid", "cancelled"})
        self.cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(reminder.id or 0))
        self.delete_btn = icon_button("trash", "Delete reminder", "danger", size=26)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(reminder.id or 0))
        for button in (self.notify_btn, self.edit_btn, self.cancel_btn, self.delete_btn):
            icons_row.addWidget(button)
        actions.addLayout(icons_row)
        root.addLayout(actions, 0)

        if animate and self._motion:
            self.opacity = QGraphicsOpacityEffect(self)
            self.opacity.setOpacity(0.0)
            self.setGraphicsEffect(self.opacity)
            self._anim = QVariantAnimation(self)
            self._anim.setDuration(420)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.valueChanged.connect(self._on_entrance)
            self._anim.finished.connect(self._entrance_finished)
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
        else:
            self.opacity = None
            self._anim = None

        if self._motion and status in {"due_today", "overdue", "paid"}:
            self._pulse = QTimer(self)
            self._pulse.setInterval(70)
            self._pulse.timeout.connect(self._tick)
        else:
            self._pulse = None

    # ------------------------------------------------------------------ details
    def _detail_text(self) -> str:
        r = self.reminder
        due = date.fromisoformat(r.due_date)
        due_text = due.strftime("%a, %d %b %Y")
        if r.due_time:
            due_text += f" · {r.due_time}"
        return f"{format_money(r.amount_paise)}   ·   {due_text}   ·   {r.payment_method}"

    def _progress_fraction(self) -> float:
        if self.status in {"paid", "due_today", "overdue"}:
            return 1.0
        if self.status == "cancelled":
            return 0.0
        return max(0.06, min(1.0, (30 - self.days_until) / 30))

    def _progress_label(self) -> str:
        if self.status == "paid":
            paid = self.reminder.paid_at or ""
            return "Completed" + (f" · {paid[11:16]}" if len(paid) > 16 else "")
        if self.status == "cancelled":
            return "Cancelled"
        if self.status == "overdue":
            return f"{abs(self.days_until)}d overdue"
        if self.status == "due_today":
            return "Due today"
        return f"in {self.days_until} days"

    def _toggle_notifications(self) -> None:
        enabled = not self.reminder.notifications_enabled
        self.reminder.notifications_enabled = enabled
        self.notify_btn.setIcon(
            make_icon("bell" if enabled else "bell-off",
                      palette()["accent_soft"] if enabled else palette()["muted"], 16)
        )
        self.notify_btn.setToolTip("Turn notifications off" if enabled else "Turn notifications on")
        self.toggle_requested.emit(self.reminder.id or 0, enabled)

    # ------------------------------------------------------------------ motion
    def _on_entrance(self, value) -> None:  # noqa: ANN001
        self._entrance = float(value)
        if self.opacity is not None:
            self.opacity.setOpacity(self._entrance)
        slide = int((1.0 - self._entrance) * 22)
        left, top, right, bottom = self._base_margins
        self.setContentsMargins(left + slide, top, right, bottom)

    def _entrance_finished(self) -> None:
        self.setContentsMargins(*self._base_margins)
        if self.opacity is not None:
            self.opacity.setOpacity(1.0)

    def showEvent(self, event) -> None:  # noqa: N802, ANN001
        super().showEvent(event)
        if self._anim is not None:
            self._anim.start()
        if self._pulse is not None:
            self._pulse.start()

    def hideEvent(self, event) -> None:  # noqa: N802, ANN001
        if self._pulse is not None:
            self._pulse.stop()
        super().hideEvent(event)

    def _tick(self) -> None:
        self._phase = (self._phase + 0.035) % 1.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        super().paintEvent(event)
        if not self._motion:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p = palette()
        color = QColor(p[_TONES.get(self.status, _TONES["upcoming"])["color"]])
        if self.status == "due_today":
            alpha = int(16 + 12 * (0.5 + 0.5 * math.sin(self._phase * math.tau)))
        elif self.status == "overdue":
            alpha = int(20 + 10 * (0.5 + 0.5 * math.sin(self._phase * math.tau)))
        elif self.status == "paid":
            alpha = int(10 + 8 * (0.5 + 0.5 * math.sin(self._phase * math.tau)))
        else:
            alpha = 0
        if alpha:
            color.setAlpha(alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 15, 15)
        # A slim accent bar on the leading edge gives each status its own hue.
        accent = QColor(p[_TONES.get(self.status, _TONES["upcoming"])["color"]])
        accent.setAlpha(150)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(QRectF(0, 12, 3, max(12, self.height() - 24)), 1.5, 1.5)
        painter.end()


def _status_label(status: str) -> str:
    return {
        "upcoming": "UPCOMING",
        "due_today": "DUE TODAY",
        "overdue": "OVERDUE",
        "paid": "PAID",
        "cancelled": "CANCELLED",
    }.get(status, status.upper())


class ReminderCalendar(QWidget):
    """Month grid with coloured markers on days that have reminders."""

    day_selected = Signal(int)
    WEEKDAYS = ("M", "T", "W", "T", "F", "S", "S")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        today = date.today()
        self._month = today.month
        self._year = today.year
        self._days: dict[int, str] = {}
        self._hover = 0
        self._cells: list[tuple[QRectF, int]] = []
        self.setMinimumHeight(210)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_period(self, month: int, year: int, days: dict[int, str]) -> None:
        self._month = month
        self._year = year
        self._days = dict(days)
        self._hover = 0
        self.update()

    def _layout_cells(self) -> QRectF:
        header = 20.0
        grid = QRectF(2, header + 2, self.width() - 4, self.height() - header - 4)
        cell_w = grid.width() / 7
        rows = 6
        cell_h = grid.height() / rows
        self._cells = []
        first = date(self._year, self._month, 1).weekday()
        days = calendar.monthrange(self._year, self._month)[1]
        for day in range(1, days + 1):
            row, col = divmod(first + day - 1, 7)
            self._cells.append(
                (
                    QRectF(
                        grid.left() + col * cell_w + 2,
                        grid.top() + row * cell_h + 2,
                        cell_w - 4,
                        cell_h - 4,
                    ),
                    day,
                )
            )
        return grid

    def _day_at(self, pos: QPointF) -> int:
        for rect, day in self._cells:
            if rect.contains(pos):
                return day
        return 0

    def mouseMoveEvent(self, event) -> None:  # noqa: N802, ANN001
        day = self._day_at(event.position())
        if day != self._hover:
            self._hover = day
            self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802, ANN001
        day = self._day_at(event.position())
        if day:
            self.day_selected.emit(day)

    def leaveEvent(self, event) -> None:  # noqa: N802, ANN001
        self._hover = 0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p = palette()
        grid = self._layout_cells()
        cell_w = grid.width() / 7

        header_font = QFont("Segoe UI")
        header_font.setPixelSize(9)
        header_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(header_font)
        for column, label in enumerate(self.WEEKDAYS):
            painter.setPen(QColor(p["dim"] if column < 5 else p["muted"]))
            painter.drawText(
                QRectF(grid.left() + column * cell_w, 0, cell_w, 16),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        today = date.today()
        font = QFont("Segoe UI")
        font.setPixelSize(10)
        for rect, day in self._cells:
            tone = self._days.get(day)
            fill = QColor(p["surface2"])
            if tone == "danger":
                fill = QColor(p["red_tint"])
            elif tone == "warning":
                fill = QColor(p["amber_tint"])
            elif tone == "success":
                fill = QColor(p["green_tint"])
            elif tone:
                fill = QColor(p["violet_tint"])
            if day == self._hover:
                fill = fill.lighter(125)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, 7, 7)
            is_today = (today.year, today.month, today.day) == (self._year, self._month, day)
            if is_today:
                painter.setPen(QPen(QColor(p["accent3"]), 1.3))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(rect.adjusted(0.7, 0.7, -0.7, -0.7), 6, 6)
            painter.setFont(font)
            painter.setPen(QColor(p["text"] if tone else p["muted"]))
            painter.drawText(rect.adjusted(0, -3, 0, 3), Qt.AlignmentFlag.AlignCenter, str(day))
            if tone:
                color = QColor(p[_TONES.get(tone, _TONES["upcoming"])["color"]])
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(QPointF(rect.center().x(), rect.bottom() - 8), 2.4, 2.4)
        painter.end()


class Toast(QFrame):
    """One sliding notification tile."""

    dismissed = Signal(object)

    def __init__(self, title: str, body: str, tone: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # The host is click-through; each toast opts back in so its dismiss
        # button and hover events keep working.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setObjectName("toastCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("tone", tone)
        self.setFixedSize(330, 76)
        p = palette()
        spec = _TONES.get(tone, _TONES["upcoming"])
        root = QHBoxLayout(self)
        root.setContentsMargins(13, 11, 13, 11)
        root.setSpacing(11)
        chip = IconChip(spec["icon"], p[spec["color"]], p[spec["tint"]], size=34)
        root.addWidget(chip, 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(3)
        heading = QLabel(title)
        heading.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {p[spec['color']]};"
        )
        message = QLabel(body)
        message.setObjectName("cardSubtitle")
        message.setWordWrap(True)
        message.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        text.addWidget(heading)
        text.addWidget(message)
        root.addLayout(text, 1)
        close = icon_button("close", "Dismiss", size=22)
        close.clicked.connect(self.dismiss)
        root.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)

        self.opacity = QGraphicsOpacityEffect(self)
        self.opacity.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity)
        self._fade_in = QPropertyAnimation(self.opacity, b"opacity", self)
        self._fade_in.setDuration(280)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.start()
        QTimer.singleShot(5600, self.dismiss)

    def dismiss(self) -> None:
        if not hasattr(self, "_fade_out"):
            self._fade_out = QPropertyAnimation(self.opacity, b"opacity", self)
            self._fade_out.setDuration(240)
            self._fade_out.setStartValue(self.opacity.opacity())
            self._fade_out.setEndValue(0.0)
            self._fade_out.finished.connect(lambda: self.dismissed.emit(self))
            self._fade_out.start()


class ToastHost(QWidget):
    """Overlay that stacks toasts in the top-right corner of its parent."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        # This overlay covers the whole page. It must never steal clicks from
        # the real controls underneath; individual Toast children opt back in.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._toasts: list[Toast] = []
        self._motion = True

    def set_motion(self, enabled: bool) -> None:
        self._motion = enabled

    def show_toast(self, title: str, body: str, tone: str = "accent") -> None:
        toast = Toast(title, body, tone, self)
        toast.dismissed.connect(self._remove)
        self._toasts.append(toast)
        self._place(toast, entering=True)
        toast.raise_()
        toast.show()

    def _place(self, toast: Toast, entering: bool = False) -> None:
        width = max(220, min(330, self.width() - 32))
        if toast.width() != width:
            toast.resize(width, 76)
        index = self._toasts.index(toast)
        target = QPoint(self.width() - width - 14, 14 + index * 84)
        if entering and self._motion:
            start = QPoint(target.x() + width + 30, target.y())
            toast.move(start)
            animation = QPropertyAnimation(toast, b"pos", self)
            animation.setDuration(360)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.setStartValue(start)
            animation.setEndValue(target)
            animation.start()
            toast._slide = animation  # keep a reference until it finishes
        else:
            toast.move(target)

    def _remove(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        toast.deleteLater()
        for remaining in self._toasts:
            self._place(remaining)

    def resizeEvent(self, event) -> None:  # noqa: N802, ANN001
        for toast in self._toasts:
            self._place(toast)
        super().resizeEvent(event)
