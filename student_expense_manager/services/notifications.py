from __future__ import annotations

import sys
from typing import Callable

from PySide6.QtCore import QObject, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSystemTrayIcon

_TONE_LABELS = {
    "accent": "Upcoming",
    "warning": "Due soon",
    "danger": "Overdue",
    "success": "Paid",
}


def _tray_icon() -> QIcon:
    """A simple violet bell tile; no external artwork or network access."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#7C5CFF"))
    painter.drawRoundedRect(QRectF(2, 2, 60, 60), 16, 16)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#FFFFFF"), 3.2, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawArc(QRectF(20, 16, 24, 26), 15 * 16, 150 * 16)
    painter.drawLine(24, 45, 40, 45)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawEllipse(QRectF(30, 11, 4, 4))
    painter.end()
    return QIcon(pixmap)


class NotificationCenter(QObject):
    """Local-only notifications while the application is running.

    Messages are shown as in-app sliding toasts and, where available, through
    the operating system's notification area via ``QSystemTrayIcon``. Nothing
    is transmitted and no cloud service is used.

    Notifications while the application is fully closed are deliberately NOT
    claimed: they would require an OS scheduler that starts the app at the
    alert time, which this offline build does not install.
    """

    def __init__(self, on_toast: Callable[[str, str, str], None] | None = None) -> None:
        super().__init__()
        self.on_toast = on_toast
        self.enabled = True
        self.system_enabled = True
        self._tray: QSystemTrayIcon | None = None
        self._last: tuple[str, str, str] | None = None

    def system_available(self) -> bool:
        return (
            QGuiApplication.instance() is not None
            and QSystemTrayIcon.isSystemTrayAvailable()
        )

    def show(self, title: str, body: str, tone: str = "accent") -> bool:
        """Deliver one notification; returns False if notifications are off."""
        if not self.enabled:
            return False
        key = (title, body, tone)
        if key == self._last:
            return False
        self._last = key
        if self.on_toast:
            self.on_toast(title, body, tone)
        if self.system_enabled and self.system_available():
            if self._tray is None:
                self._tray = QSystemTrayIcon(_tray_icon(), self)
                self._tray.setToolTip("Student Expense Manager")
                self._tray.show()
            icon = {
                "danger": QSystemTrayIcon.MessageIcon.Critical,
                "warning": QSystemTrayIcon.MessageIcon.Warning,
            }.get(tone, QSystemTrayIcon.MessageIcon.Information)
            self._tray.showMessage(
                f"{_TONE_LABELS.get(tone, 'Reminder')} · {title}",
                body,
                icon,
                8000,
            )
        return True

    def shutdown(self) -> None:
        if self._tray is not None:
            self._tray.hide()
            self._tray = None


def setup_instructions() -> str:
    """Plain-language setup notes shown in Settings."""
    lines = [
        "Notifications are checked every minute while the app is open.",
        "Windows: messages appear through the system notification area and as",
        "in-app toasts. Keep the app running to receive them.",
    ]
    if sys.platform.startswith("win"):
        lines += [
            "For alerts while the app is closed, a Windows Scheduled Task would",
            "need to launch this app at the alert time. That integration is not",
            "installed here, so closed-app notifications are not available.",
        ]
    return "\n".join(lines)
