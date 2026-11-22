from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.ui.widgets import Card, IconChip


class PageHeader(QWidget):
    """Consistent page title block with room for page actions on the right."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        eyebrow: str = "STUDENT FINANCE",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        self.eyebrow = QLabel(eyebrow)
        self.eyebrow.setObjectName("eyebrow")
        self.eyebrow.setVisible(bool(eyebrow))
        self.title = QLabel(title)
        self.title.setObjectName("pageTitle")
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("pageSubtitle")
        self.subtitle.setWordWrap(True)
        text_box.addWidget(self.eyebrow)
        text_box.addWidget(self.title)
        text_box.addWidget(self.subtitle)
        root.addLayout(text_box, 1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(9)
        self.actions.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(self.actions)

    def add_action(self, widget: QWidget) -> None:
        self.actions.addWidget(widget)

    def add_layout(self, layout) -> None:  # noqa: ANN001
        self.actions.addLayout(layout)

    def set_subtitle(self, text: str) -> None:
        self.subtitle.setText(text)


class MiniStat(Card):
    """Compact metric used under page headers."""

    def __init__(
        self,
        label: str,
        value: str = "—",
        caption: str = "",
        icon_kind: str = "info",
        tint: str | None = None,
        icon_color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, "card")
        self.setMinimumHeight(92)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)
        self.chip = IconChip(icon_kind, color=icon_color, tint=tint, size=36)
        root.addWidget(self.chip, 0, Qt.AlignmentFlag.AlignTop)
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        self.label = QLabel(label)
        self.label.setObjectName("statLabel")
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("insightValue")
        self.value_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.value_label.setWordWrap(True)
        self.value_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.caption = QLabel(caption)
        self.caption.setObjectName("dimLabel")
        self.caption.setWordWrap(True)
        self.caption.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        text_box.addWidget(self.label)
        text_box.addWidget(self.value_label)
        text_box.addWidget(self.caption)
        root.addLayout(text_box, 1)

    def set_data(self, value: str, caption: str = "") -> None:
        self.value_label.setText(value)
        if caption:
            self.caption.setText(caption)


def vertical_rule(height: int = 16) -> QFrame:
    rule = QFrame()
    rule.setFixedSize(1, height)
    rule.setStyleSheet("background: rgba(255,255,255,0.10); border: none;")
    return rule


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("softDivider")
    line.setFixedHeight(1)
    return line


def content_layout(
    parent: QWidget,
    *,
    scroll: bool = True,
    margins: tuple[int, int, int, int] = (26, 21, 26, 24),
    spacing: int = 16,
) -> QVBoxLayout:
    """Build a page body, optionally inside a scroll area, and return its layout."""
    parent.setObjectName("pageRoot")
    outer = QVBoxLayout(parent)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    if scroll:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("scrollContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(*margins)
        layout.setSpacing(spacing)
        area.setWidget(content)
        outer.addWidget(area)
        return layout
    layout = QVBoxLayout()
    host = QWidget()
    host.setObjectName("contentHost")
    layout = QVBoxLayout(host)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    outer.addWidget(host, 1)
    return layout
