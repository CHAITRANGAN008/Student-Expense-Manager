from __future__ import annotations

import calendar
import math
from datetime import date
from typing import Callable, Iterable

from PySide6.QtCore import (
    QEasingCurve,
    QDate,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.services.money import format_money
from student_expense_manager.ui.icons import make_icon, paint_icon
from student_expense_manager.ui.theme import palette

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def icon_button(kind: str, tooltip: str = "", tone: str = "muted", size: int = 30) -> QPushButton:
    p = palette()
    color = {
        "danger": p["danger"],
        "accent": p["accent_soft"],
        "muted": p["muted"],
        "text": p["text"],
    }.get(tone, p["muted"])
    btn = QPushButton()
    btn.setObjectName("iconBtn")
    btn.setIcon(make_icon(kind, color, 16))
    btn.setIconSize(QSize(16, 16))
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def make_button(text: str, kind: str = "secondary", icon_kind: str | None = None) -> QPushButton:
    p = palette()
    btn = QPushButton(text)
    btn.setObjectName(kind)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if icon_kind:
        color = "#FFFFFF" if kind in ("primary", "danger") else p["muted"]
        btn.setIcon(make_icon(icon_kind, color, 16))
        btn.setIconSize(QSize(16, 16))
    return btn


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, object_name: str = "card") -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


class SectionCard(Card):
    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        parent: QWidget | None = None,
        body_spacing: int = 12,
    ) -> None:
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(20, 17, 20, 18)
        self._root.setSpacing(12)

        self._header = QHBoxLayout()
        self._header.setSpacing(10)
        self._title_box = QVBoxLayout()
        self._title_box.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("cardSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.title_label.setVisible(bool(title))
        self.subtitle_label.setVisible(bool(subtitle))
        self._title_box.addWidget(self.title_label)
        self._title_box.addWidget(self.subtitle_label)
        self._header.addLayout(self._title_box, 1)
        self._root.addLayout(self._header)

        self.body = QVBoxLayout()
        self.body.setSpacing(body_spacing)
        self._root.addLayout(self.body, 1)

    def set_title(self, title: str, subtitle: str | None = None) -> None:
        self.title_label.setText(title)
        self.title_label.setVisible(bool(title))
        if subtitle is not None:
            self.subtitle_label.setText(subtitle)
            self.subtitle_label.setVisible(bool(subtitle))

    def set_subtitle(self, subtitle: str) -> None:
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))

    def add_action(self, widget: QWidget) -> None:
        self._header.addWidget(widget)


class IconChip(QWidget):
    def __init__(
        self,
        kind: str,
        color: str | None = None,
        tint: str | None = None,
        size: int = 38,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        p = palette()
        self._kind = kind
        self._color = QColor(color or p["accent_soft"])
        self._tint = QColor(tint or p["violet_tint"])
        self._radius = 11
        self.setFixedSize(size, size)

    def set_kind(self, kind: str, color: str | None = None, tint: str | None = None) -> None:
        p = palette()
        self._kind = kind
        self._color = QColor(color or p["accent_soft"])
        self._tint = QColor(tint or p["violet_tint"])
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._tint)
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), self._radius, self._radius)
        inset = self.width() * 0.26
        paint_icon(
            painter,
            QRectF(inset, inset, self.width() - 2 * inset, self.height() - 2 * inset),
            self._kind,
            self._color,
            1.75,
        )
        painter.end()


class Sparkline(QWidget):
    def __init__(self, parent: QWidget | None = None, color: str | None = None) -> None:
        super().__init__(parent)
        p = palette()
        self._series: list[float] = []
        self._color = QColor(color or p["accent"])
        self.setMinimumSize(40, 18)
        self.setMaximumHeight(20)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_series(self, values: Iterable[float], color: str | None = None) -> None:
        self._series = list(values)
        if color:
            self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        if not self._series:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(1, 3, self.width() - 2, self.height() - 6)
        vals = [float(v) for v in self._series]
        lo, hi = min(vals), max(vals)
        span = hi - lo
        if span <= 0:
            span = 1.0
        points = []
        for i, value in enumerate(vals):
            x = rect.left() + (rect.width() * i / max(1, len(vals) - 1))
            y = rect.bottom() - ((value - lo) / span) * (rect.height() - 4) - 2
            points.append(QPointF(x, y))
        path = QPainterPath(points[0])
        for i in range(1, len(points)):
            prev, cur = points[i - 1], points[i]
            mid = (prev.x() + cur.x()) / 2
            path.cubicTo(mid, prev.y(), mid, cur.y(), cur.x(), cur.y())
        fill = QPainterPath(path)
        fill.lineTo(rect.right(), rect.bottom())
        fill.lineTo(rect.left(), rect.bottom())
        fill.closeSubpath()
        grad = QLinearGradient(0, rect.top(), 0, rect.bottom())
        top = QColor(self._color)
        top.setAlpha(70)
        bottom = QColor(self._color)
        bottom.setAlpha(0)
        grad.setColorAt(0, top)
        grad.setColorAt(1, bottom)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawPath(fill)
        pen = QPen(self._color, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.setBrush(self._color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(points[-1], 2.4, 2.4)
        painter.end()


class StatCard(Card):
    def __init__(
        self,
        label: str,
        icon_kind: str,
        accent: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, "accentCard" if accent else "card")
        self.accent = accent
        p = palette()
        self.setMinimumHeight(108)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 13, 18, 12)
        root.setSpacing(5)

        top = QHBoxLayout()
        top.setSpacing(10)
        if accent:
            chip = IconChip(icon_kind, color="#FFFFFF", tint=QColor(255, 255, 255, 38), size=34)
        else:
            chip = IconChip(icon_kind, color=p["accent_soft"], tint=p["violet_tint"], size=34)
        top.addWidget(chip)
        self.label = QLabel(label)
        self.label.setObjectName("statLabel")
        self.label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        if accent:
            self.label.setStyleSheet("color: rgba(255,255,255,0.82); font-size: 10.5px; font-weight: 600;")
        top.addWidget(self.label)
        top.addStretch(1)
        self.delta_pill = QLabel("")
        self.delta_pill.setObjectName("pill")
        self.delta_pill.setVisible(False)
        top.addWidget(self.delta_pill)
        root.addLayout(top)

        value_row = QHBoxLayout()
        value_row.setSpacing(8)
        self.value = QLabel("—")
        self.value.setObjectName("statValue")
        self.value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        if accent:
            self.value.setStyleSheet("color: #FFFFFF; font-size: 19px; font-weight: 700;")
        value_row.addWidget(self.value, 1)
        self.spark = Sparkline(color="#FFFFFF" if accent else p["accent"])
        self.spark.setFixedSize(56, 22)
        value_row.addWidget(self.spark, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(value_row)

        self.delta = QLabel("")
        self.delta.setObjectName("statDelta")
        self.delta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        if accent:
            self.delta.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 10.5px;")
        root.addWidget(self.delta)

    def set_data(
        self,
        value: str,
        delta_text: str = "",
        positive: bool | None = None,
        series: Iterable[float] | None = None,
        pill: str = "",
        pill_tone: str = "neutral",
    ) -> None:
        p = palette()
        self.value.setText(value)
        self.delta.setText(delta_text)
        if self.accent:
            self.delta.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 10.5px;")
            self.spark.set_series(series or [], "#FFFFFF")
        else:
            color = p["muted"]
            if positive is True:
                color = p["success"]
            elif positive is False:
                color = p["danger"]
            self.delta.setStyleSheet(f"color: {color}; font-size: 10.5px;")
            self.spark.set_series(series or [], p["accent"] if positive is not False else p["muted"])
        self.delta_pill.setVisible(bool(pill))
        if pill:
            self.delta_pill.setText(pill)
            self.delta_pill.setProperty("tone", pill_tone)
            repolish(self.delta_pill)

    def resizeEvent(self, event) -> None:  # noqa: N802, ANN001
        # On narrow windows the sparkline would squeeze the rupee value; the
        # value and comparison line matter more, so drop the decorative line.
        if hasattr(self, "spark"):
            self.spark.setVisible(self.width() >= 208)
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        super().paintEvent(event)
        if not self.accent:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 16, 16)
        painter.setClipPath(clip)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 20))
        painter.drawEllipse(QPointF(self.width() - 8, self.height() + 18), 78, 78)
        painter.setBrush(QColor(255, 255, 255, 12))
        painter.drawEllipse(QPointF(self.width() - 118, -18), 46, 46)
        painter.end()


class PercentBar(QWidget):
    def __init__(self, parent: QWidget | None = None, height: int = 8, color: str | None = None) -> None:
        super().__init__(parent)
        self._fraction = 0.0
        self._display = 0.0
        self._color = QColor(color or palette()["accent"])
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

    def _on_anim(self, value) -> None:  # noqa: ANN001
        self._display = float(value)
        self.update()

    def set_value(self, fraction: float, color: str | None = None, animate: bool = True) -> None:
        target = max(0.0, min(1.0, float(fraction)))
        if color:
            self._color = QColor(color)
        if not animate:
            self._display = target
            self._fraction = target
            self.update()
            return
        self._fraction = target
        self._anim.stop()
        self._anim.setStartValue(self._display)
        self._anim.setEndValue(target)
        self._anim.start()

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        h = self.height()
        m = h / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette()["surface3"]))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), h), m, m)
        if self._display > 0:
            w = max(h, self.width() * self._display)
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0, self._color)
            lighter = QColor(self._color).lighter(130)
            grad.setColorAt(1, lighter)
            painter.setBrush(grad)
            painter.drawRoundedRect(QRectF(0, 0, w, h), m, m)
        painter.end()


class DonutChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[tuple[str, int, str]] = []
        self._center_caption = "Total spend"
        self._hover = -1
        self._last_tip = -1
        self.setMinimumSize(120, 104)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, items: list[tuple[str, int, str]], center_caption: str = "Total spend") -> None:
        self._items = items
        self._center_caption = center_caption
        self._hover = -1
        self.update()

    def _geometry(self) -> tuple[QRectF, float]:
        side = min(self.width(), self.height()) - 22
        side = max(90, side)
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        thickness = max(13.0, side * 0.095)
        return rect, thickness

    def _index_at(self, pos: QPointF) -> int:  # noqa: ANN001
        total = sum(max(0, v) for _, v, _ in self._items)
        if total <= 0:
            return -1
        rect, thickness = self._geometry()
        center = rect.center()
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        dist = math.hypot(dx, dy)
        outer = rect.width() / 2
        inner = outer - thickness - 6
        if dist < inner or dist > outer + 6:
            return -1
        ang = (math.degrees(math.atan2(-dy, dx)) - 90) % 360
        acc = 0.0
        for idx, (_, value, _) in enumerate(self._items):
            span = max(0, value) / total * 360
            if acc <= ang < acc + span:
                return idx
            acc += span
        return -1

    def mouseMoveEvent(self, event) -> None:  # noqa: N802, ANN001
        idx = self._index_at(event.position())
        if idx != self._hover:
            self._hover = idx
            self.update()
        if idx >= 0 and idx != self._last_tip:
            total = sum(max(0, v) for _, v, _ in self._items) or 1
            label, value, _ = self._items[idx]
            pct = value / total * 100
            QToolTip.showText(
                event.globalPosition().toPoint(),
                f"{label}\n{format_money(value)}  ·  {pct:.1f}%",
                self,
            )
            self._last_tip = idx
        elif idx < 0 and self._last_tip != -1:
            QToolTip.hideText()
            self._last_tip = -1

    def leaveEvent(self, event) -> None:  # noqa: N802, ANN001
        self._hover = -1
        self._last_tip = -1
        QToolTip.hideText()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        p = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect, thickness = self._geometry()
        total = sum(max(0, v) for _, v, _ in self._items)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        track = QPen(QColor(p["surface3"]), thickness)
        track.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track)
        painter.drawArc(rect, 0, 360 * 16)

        if total > 0:
            start = 90.0
            for idx, (_, value, color) in enumerate(self._items):
                span = max(0, value) / total * 360
                if span <= 0:
                    continue
                gap = min(3.0, max(1.2, span * 0.02))
                pen = QPen(QColor(color), thickness + (3 if idx == self._hover else 0))
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawArc(rect, int((start - gap / 2) * 16), int(-(span - gap) * 16))
                start -= span
        else:
            painter.setPen(QColor(p["dim"]))
            f = QFont("Segoe UI", 10)
            painter.setFont(f)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No data yet")

        if total > 0:
            center = rect.center()
            value_font = QFont("Segoe UI", max(12, int(rect.width() * 0.085)))
            value_font.setWeight(QFont.Weight.Bold)
            painter.setFont(value_font)
            painter.setPen(QColor(p["text"]))
            painter.drawText(
                QRectF(center.x() - rect.width() / 3, center.y() - 22, rect.width() * 0.66, 30),
                Qt.AlignmentFlag.AlignCenter,
                format_money(total),
            )
            cap_font = QFont("Segoe UI", 8)
            painter.setFont(cap_font)
            painter.setPen(QColor(p["muted"]))
            painter.drawText(
                QRectF(center.x() - rect.width() / 3, center.y() + 9, rect.width() * 0.66, 18),
                Qt.AlignmentFlag.AlignCenter,
                self._center_caption,
            )
        painter.end()


class SegmentedControl(QFrame):
    changed = Signal(str)

    def __init__(
        self,
        items: list[tuple[str, str]],
        parent: QWidget | None = None,
        compact: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("segContainer")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(3, 3, 3, 3)
        self._layout.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._values: list[str] = []
        self._buttons: list[QPushButton] = []
        for label, value in items:
            btn = QPushButton(label)
            btn.setObjectName("segBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(27 if not compact else 24)
            btn.clicked.connect(lambda _=False, v=value: self._select(v))
            self._group.addButton(btn)
            self._layout.addWidget(btn)
            self._buttons.append(btn)
            self._values.append(value)
        if self._buttons:
            self._buttons[0].setChecked(True)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def _select(self, value: str) -> None:
        self.changed.emit(value)

    def current(self) -> str:
        for btn, value in zip(self._buttons, self._values):
            if btn.isChecked():
                return value
        return self._values[0] if self._values else ""

    def set_current(self, value: str) -> None:
        for btn, val in zip(self._buttons, self._values):
            btn.blockSignals(True)
            btn.setChecked(val == value)
            btn.blockSignals(False)

    def set_labels(self, labels: list[str]) -> None:
        for btn, label in zip(self._buttons, labels):
            btn.setText(label)


class PeriodSelector(QFrame):
    changed = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("segContainer")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        self.prev_btn = icon_button("chevron-left", "Previous month", size=28)
        self.next_btn = icon_button("chevron-right", "Next month", size=28)
        self.month_combo = QComboBox()
        self.month_combo.setMinimumWidth(112)
        self.month_combo.addItems(MONTHS)
        self.year_combo = QComboBox()
        self.year_combo.setMinimumWidth(76)
        today = QDate.currentDate()
        for year in range(today.year() - 6, today.year() + 3):
            self.year_combo.addItem(str(year), year)
        self.month_combo.setCurrentIndex(today.month() - 1)
        idx = self.year_combo.findData(today.year())
        if idx >= 0:
            self.year_combo.setCurrentIndex(idx)

        layout.addWidget(self.prev_btn)
        layout.addWidget(self.month_combo)
        layout.addWidget(self.year_combo)
        layout.addWidget(self.next_btn)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

        self.prev_btn.clicked.connect(self._prev)
        self.next_btn.clicked.connect(self._next)
        self.month_combo.currentIndexChanged.connect(self._emit)
        self.year_combo.currentIndexChanged.connect(self._emit)

    def _emit(self) -> None:
        self.changed.emit(*self.period())

    def _prev(self) -> None:
        m, y = self.period()
        m -= 1
        if m < 1:
            m, y = 12, y - 1
        self.set_period(m, y)
        self._emit()

    def _next(self) -> None:
        m, y = self.period()
        m += 1
        if m > 12:
            m, y = 1, y + 1
        self.set_period(m, y)
        self._emit()

    def period(self) -> tuple[int, int]:
        return self.month_combo.currentIndex() + 1, int(self.year_combo.currentData() or QDate.currentDate().year())

    def set_period(self, month: int, year: int) -> None:
        self.blockSignals(True)
        self.month_combo.blockSignals(True)
        self.year_combo.blockSignals(True)
        self.month_combo.setCurrentIndex(max(0, min(11, month - 1)))
        idx = self.year_combo.findData(year)
        if idx < 0:
            self.year_combo.addItem(str(year), year)
            idx = self.year_combo.findData(year)
        self.year_combo.setCurrentIndex(idx)
        self.month_combo.blockSignals(False)
        self.year_combo.blockSignals(False)
        self.blockSignals(False)


class SearchField(QLineEdit):
    def __init__(self, placeholder: str = "Search…", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        p = palette()
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.addAction(make_icon("search", p["dim"], 16), QLineEdit.ActionPosition.LeadingPosition)
        self.setMinimumWidth(210)


class AnimatedCredit(QWidget):
    """Designer credit with a gradient highlight that sweeps across the name.

    The motion is deliberately gentle: a highlight travels through the lettering,
    the two accent dots breathe, and the name floats by less than a pixel.  The
    timer only runs while the widget is visible, so hidden pages cost nothing.
    """

    CAPTION = "MADE BY"
    NAME_LINES = ("CHAITRANGAN VIJAYKUMAR", "THENGEKAR")
    FULL_NAME = "Chaitrangan Vijaykumar Thengekar"

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        compact: bool = True,
        caption: str = CAPTION,
        name_lines: tuple[str, ...] = NAME_LINES,
    ) -> None:
        super().__init__(parent)
        self.compact = compact
        self.caption = caption
        self.name_lines = name_lines
        self._phase = 0.0
        self.setToolTip(f"Made by {self.FULL_NAME}")
        self.setAccessibleName(f"Made by {self.FULL_NAME}")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(66 if compact else 36)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------ animation
    def _tick(self) -> None:
        self._phase = (self._phase + 0.012) % 1.0
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802, ANN001
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802, ANN001
        self._timer.stop()
        super().hideEvent(event)

    # ------------------------------------------------------------------ painting
    def _shimmer_pen(self, rect: QRectF) -> QPen:
        p = palette()
        if p["name"] == "dark":
            base, bright, tail = "#8B6CFF", "#FFFFFF", "#5EEBFF"
        else:
            base, bright, tail = "#6D4AFF", "#FFFFFF", "#0EA5E9"
        span = max(1.0, rect.width())
        start = rect.left() - span * 0.7 + self._phase * span * 1.4
        gradient = QLinearGradient(start, 0.0, start + span, 0.0)
        gradient.setColorAt(0.0, QColor(base))
        gradient.setColorAt(0.30, QColor("#B9A7FF" if p["name"] == "dark" else "#8B6CFF"))
        gradient.setColorAt(0.46, QColor(bright))
        gradient.setColorAt(0.56, QColor(tail))
        gradient.setColorAt(0.74, QColor(base))
        gradient.setColorAt(1.0, QColor("#A78BFA" if p["name"] == "dark" else "#5B3BE8"))
        pen = QPen(gradient, 0)
        return pen

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        p = palette()
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        bob = math.sin(self._phase * math.tau) * 0.8
        pulse = 0.5 + 0.5 * math.sin(self._phase * math.tau * 2)

        if self.compact:
            card = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
            painter.setPen(QPen(QColor(p["border_soft"]), 1))
            painter.setBrush(QColor(p["surface2"]))
            painter.drawRoundedRect(card, 11, 11)
            glow = QLinearGradient(card.topLeft(), card.bottomRight())
            top = QColor(p["accent"])
            top.setAlpha(30)
            glow.setColorAt(0.0, top)
            glow.setColorAt(0.55, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawRoundedRect(card.adjusted(1, 1, -1, -1), 10, 10)

        caption_font = QFont("Segoe UI")
        caption_font.setPixelSize(7)
        caption_font.setWeight(QFont.Weight.DemiBold)
        caption_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.8)
        painter.setFont(caption_font)
        caption_color = QColor(p["dim"])
        caption_rect = QRectF(0, 8 if self.compact else 0, self.width(), 12)
        painter.setPen(caption_color)
        painter.drawText(caption_rect, Qt.AlignmentFlag.AlignHCenter, self.caption)

        caption_width = QFontMetricsF(caption_font).horizontalAdvance(self.caption)
        if self.compact:
            dot_y = caption_rect.center().y() + 0.5
            for direction in (-1, 1):
                dot = QColor(p["accent_soft"])
                dot.setAlpha(int(70 + 120 * pulse))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(dot)
                x = self.width() / 2 + direction * (caption_width / 2 + 9)
                painter.drawEllipse(QPointF(x, dot_y), 1.6, 1.6)

        painter.setPen(self._shimmer_pen(rect))
        if self.compact:
            font_a = QFont("Segoe UI")
            font_a.setPixelSize(10)
            font_a.setWeight(QFont.Weight.DemiBold)
            font_a.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
            y_a = 28 + bob
            painter.setFont(font_a)
            if self.name_lines:
                painter.drawText(
                    QRectF(4, y_a, self.width() - 8, 14),
                    Qt.AlignmentFlag.AlignHCenter,
                    self.name_lines[0],
                )
            font_b = QFont("Segoe UI")
            font_b.setPixelSize(12)
            font_b.setWeight(QFont.Weight.Bold)
            font_b.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
            painter.setFont(font_b)
            if len(self.name_lines) > 1:
                painter.drawText(
                    QRectF(4, y_a + 13, self.width() - 8, 16),
                    Qt.AlignmentFlag.AlignHCenter,
                    self.name_lines[1],
                )

            # A hairline whose bright spot follows the highlight through the name.
            line_y = self.height() - 8
            track = QColor(p["border_soft"])
            painter.setPen(QPen(track, 1))
            painter.drawLine(QPointF(16, line_y), QPointF(self.width() - 16, line_y))
            sweep_x = 16 + (self.width() - 32) * self._phase
            glow_pen = QPen(QColor(p["accent_soft"]), 2)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawLine(
                QPointF(max(16, sweep_x - 12), line_y),
                QPointF(min(self.width() - 16, sweep_x + 12), line_y),
            )
        else:
            font_cap = QFont("Segoe UI")
            font_cap.setPixelSize(8)
            font_cap.setWeight(QFont.Weight.DemiBold)
            font_cap.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
            font_name = QFont("Segoe UI")
            font_name.setPixelSize(10)
            font_name.setWeight(QFont.Weight.DemiBold)
            font_name.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
            cap = self.caption + "   "
            cap_width = QFontMetricsF(font_cap).horizontalAdvance(cap)
            name = " ".join(self.name_lines)
            name_width = QFontMetricsF(font_name).horizontalAdvance(name)
            total = cap_width + name_width
            x = max(0.0, (self.width() - total) / 2)
            painter.setFont(font_cap)
            painter.setPen(QColor(p["dim"]))
            painter.drawText(QPointF(x, 21 + bob), cap)
            painter.setFont(font_name)
            painter.setPen(self._shimmer_pen(rect))
            painter.drawText(QPointF(x + cap_width, 21 + bob), name)
            line_y = self.height() - 5
            painter.setPen(QPen(QColor(p["border_soft"]), 1))
            painter.drawLine(QPointF(0, line_y), QPointF(self.width(), line_y))
            sweep_x = self.width() * self._phase
            glow_pen = QPen(QColor(p["accent_soft"]), 1.6)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawLine(
                QPointF(max(0.0, sweep_x - 40), line_y),
                QPointF(min(float(self.width()), sweep_x + 40), line_y),
            )
        painter.end()


class SpendingCalendar(QWidget):
    """A compact month grid that shades each day by how much was spent.

    It mirrors the small "today" calendar in the reference dashboards while
    staying useful: hovering a day reveals its exact expense total.
    """

    WEEKDAYS = ("M", "T", "W", "T", "F", "S", "S")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        today = date.today()
        self._month = today.month
        self._year = today.year
        self._values: dict[int, int] = {}
        self._hover = 0
        self._cells: list[tuple[QRectF, int]] = []
        self.setMinimumHeight(136)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setToolTip("Daily spending")

    def set_period(self, month: int, year: int, values: dict[int, int]) -> None:
        self._month = month
        self._year = year
        self._values = dict(values)
        self._hover = 0
        self.update()

    def _layout_cells(self) -> tuple[QRectF, float, float]:
        header = 16.0
        rows = 6
        grid = QRectF(2, header + 2, self.width() - 4, self.height() - header - 4)
        cell_w = grid.width() / 7
        cell_h = grid.height() / rows
        self._cells = []
        first = date(self._year, self._month, 1).weekday()
        days = calendar.monthrange(self._year, self._month)[1]
        for day in range(1, days + 1):
            index = first + day - 1
            row, col = divmod(index, 7)
            self._cells.append(
                (
                    QRectF(
                        grid.left() + col * cell_w + 1.5,
                        grid.top() + row * cell_h + 1.5,
                        cell_w - 3,
                        cell_h - 3,
                    ),
                    day,
                )
            )
        return grid, cell_w, cell_h

    def _day_at(self, pos: QPointF) -> int:
        for rect, day in self._cells:
            if rect.contains(pos):
                return day
        return 0

    def mouseMoveEvent(self, event) -> None:  # noqa: N802, ANN001
        day = self._day_at(event.position())
        if day and day != self._hover:
            self._hover = day
            amount = self._values.get(day, 0)
            label = (
                f"{day} {calendar.month_abbr[self._month]} · {format_money(amount)} spent"
                if amount
                else f"{day} {calendar.month_abbr[self._month]} · no spending"
            )
            QToolTip.showText(event.globalPosition().toPoint(), label, self)
            self.update()
        elif not day and self._hover:
            self._hover = 0
            QToolTip.hideText()
            self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802, ANN001
        self._hover = 0
        QToolTip.hideText()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p = palette()
        grid, cell_w, _cell_h = self._layout_cells()
        today = date.today()

        header_font = QFont("Segoe UI")
        header_font.setPixelSize(8)
        header_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(header_font)
        for column, label in enumerate(self.WEEKDAYS):
            color = QColor(p["dim"])
            if column >= 5:
                color = QColor(p["muted"])
            painter.setPen(color)
            painter.drawText(
                QRectF(grid.left() + column * cell_w, 0, cell_w, 14),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        peak = max(self._values.values(), default=0)
        day_font = QFont("Segoe UI")
        day_font.setPixelSize(9)
        day_font.setWeight(QFont.Weight.Medium)
        for rect, day in self._cells:
            amount = self._values.get(day, 0)
            is_today = (today.year, today.month, today.day) == (
                self._year,
                self._month,
                day,
            )
            if amount and peak > 0:
                intensity = 0.22 + 0.62 * (amount / peak)
                fill = QColor(p["accent"])
                fill.setAlpha(int(45 + 165 * intensity))
            else:
                fill = QColor(p["surface2"])
                fill.setAlpha(210)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, 5, 5)

            if is_today:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(p["accent3"]), 1.3))
                painter.drawRoundedRect(rect.adjusted(0.7, 0.7, -0.7, -0.7), 4, 4)

            if day == self._hover:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(p["accent_soft"]), 1.2))
                painter.drawRoundedRect(rect.adjusted(0.7, 0.7, -0.7, -0.7), 4, 4)

            if amount and intensity > 0.55:
                text_color = QColor("#FFFFFF")
            elif amount:
                text_color = QColor(p["text"])
            else:
                text_color = QColor(p["muted"])
            painter.setFont(day_font)
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(day))
            if amount:
                dot = QColor("#FFFFFF" if intensity > 0.55 else p["accent_soft"])
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(dot)
                painter.drawEllipse(
                    QPointF(rect.center().x(), rect.bottom() - 4.2), 1.3, 1.3
                )
        painter.end()


class Pill(QLabel):
    def __init__(self, text: str = "", tone: str = "neutral", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("pill")
        self.setProperty("tone", tone)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        repolish(self)


class EmptyState(QWidget):
    def __init__(
        self,
        icon_kind: str,
        title: str,
        message: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        p = palette()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 24, 18, 24)
        layout.setSpacing(7)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip = IconChip(icon_kind, p["dim"], p["surface2"], size=44)
        layout.addWidget(chip, 0, Qt.AlignmentFlag.AlignHCenter)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        msg = QLabel(message)
        msg.setObjectName("cardSubtitle")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)


class LegendRow(QWidget):
    def __init__(
        self,
        label: str,
        value: str,
        color: str,
        caption: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(9)
        dot = QLabel()
        dot.setFixedSize(9, 9)
        dot.setStyleSheet(f"background: {color}; border-radius: 4px;")
        layout.addWidget(dot)
        text_box = QVBoxLayout()
        text_box.setSpacing(0)
        name = QLabel(label)
        name.setStyleSheet("font-size: 11.5px; font-weight: 600;")
        text_box.addWidget(name)
        if caption:
            cap = QLabel(caption)
            cap.setObjectName("dimLabel")
            text_box.addWidget(cap)
        layout.addLayout(text_box, 1)
        amount = QLabel(value)
        amount.setStyleSheet("font-size: 11.5px; font-weight: 700;")
        layout.addWidget(amount)


class HBarList(QWidget):
    def __init__(self, parent: QWidget | None = None, max_items: int = 6) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(11)
        self._max_items = max_items
        self._empty: QLabel | None = None

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._empty = None

    def set_items(self, items: list[tuple[str, int, str]]) -> None:
        self.clear()
        p = palette()
        if not items:
            empty = QLabel("No expenses in this period yet.")
            empty.setObjectName("cardSubtitle")
            self._layout.addWidget(empty)
            return
        total = sum(v for _, v, _ in items) or 1
        for label, value, color in items[: self._max_items]:
            row = QWidget()
            v = QVBoxLayout(row)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(5)
            top = QHBoxLayout()
            name = QLabel(label)
            name.setStyleSheet("font-size: 11.5px; font-weight: 600;")
            amount = QLabel(format_money(value))
            amount.setStyleSheet("font-size: 11.5px; font-weight: 700;")
            top.addWidget(name)
            top.addStretch(1)
            top.addWidget(amount)
            v.addLayout(top)
            bar = PercentBar(height=6, color=color)
            bar.set_value(value / total, animate=False)
            v.addWidget(bar)
            self._layout.addWidget(row)


class BudgetMiniList(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def set_statuses(self, statuses: list[dict]) -> None:
        self.clear()
        p = palette()
        if not statuses:
            empty = QLabel("No budgets set for this month.")
            empty.setObjectName("cardSubtitle")
            self._layout.addWidget(empty)
            return
        for status in statuses[:3]:
            level = status["level"]
            color = {"ok": p["accent"], "warning": p["warning"], "exceeded": p["danger"]}.get(level, p["accent"])
            row = QWidget()
            v = QVBoxLayout(row)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(5)
            top = QHBoxLayout()
            name = QLabel(status["label"])
            name.setStyleSheet("font-size: 11.5px; font-weight: 600;")
            pct = QLabel(f"{status['percent']:.0f}%")
            pct.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {color};")
            top.addWidget(name)
            top.addStretch(1)
            top.addWidget(pct)
            v.addLayout(top)
            bar = PercentBar(height=7, color=color)
            bar.set_value(status["percent"] / 100)
            v.addWidget(bar)
            remaining = status["remaining_paise"]
            caption = (
                f"{format_money(abs(remaining))} over budget"
                if remaining < 0
                else f"{format_money(remaining)} left of {format_money(status['budget_paise'])}"
            )
            sub = QLabel(caption)
            sub.setObjectName("dimLabel")
            v.addWidget(sub)
            self._layout.addWidget(row)


def configure_table(table: QTableWidget, row_height: int = 46) -> None:
    table.setShowGrid(False)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(row_height)
    table.horizontalHeader().setHighlightSections(False)
    table.horizontalHeader().setMinimumHeight(34)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setWordWrap(False)


def clear_layout(layout) -> None:  # noqa: ANN001
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


def apply_shadow(widget: QWidget, blur: int = 30, y: int = 8, alpha: int = 90) -> None:
    from PySide6.QtWidgets import QGraphicsDropShadowEffect

    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(5, 3, 15, alpha))
    widget.setGraphicsEffect(effect)


def date_edit(initial: QDate | None = None) -> QDateEdit:
    edit = QDateEdit()
    edit.setCalendarPopup(True)
    edit.setDisplayFormat("dd MMM yyyy")
    edit.setDate(initial or QDate.currentDate())
    edit.setMinimumWidth(128)
    return edit
