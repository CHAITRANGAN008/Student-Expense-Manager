from __future__ import annotations

import calendar
from typing import Iterable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QSizePolicy, QWidget

from student_expense_manager.services.money import compact_money, format_money
from student_expense_manager.ui.theme import palette

# A calm, modern chart typeface.  Segoe UI carries the rupee glyph on Windows.
_FONT = "Segoe UI"


class ChartCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas tuned for the app's dark/light cards.

    Charts are intentionally transparent-feeling (they use the card colour) and
    expose hover tooltips for bars, points and lines.
    """

    def __init__(self, parent: QWidget | None = None, min_height: int = 210) -> None:
        p = palette()
        self.fig = Figure(figsize=(5, 2.6), dpi=100)
        self.fig.patch.set_facecolor(p["card_bottom"])
        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumHeight(min_height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {p['card_bottom']}; border-radius: 8px;")
        self.ax = self.fig.add_subplot(111)
        self._points: list[tuple[float, float, str]] = []
        self._annotation = None
        self._hovering = False
        self.mpl_connect("motion_notify_event", self._on_move)
        self.mpl_connect("axes_leave_event", self._on_leave)
        self._style_axes(self.ax)
        self.fig.tight_layout(pad=1.0)

    # ------------------------------------------------------------------ styling
    def _style_axes(self, ax) -> None:  # noqa: ANN001
        p = palette()
        ax.set_facecolor(p["card_bottom"])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(colors=p["muted"], labelsize=8, length=0, pad=5)
        ax.grid(True, axis="y", color=p["chart_grid"], linewidth=0.8, linestyle=(0, (2, 4)))
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: compact_money(int(value * 100))))
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontfamily(_FONT)

    def _reset(self):  # noqa: ANN202
        p = palette()
        self.fig.clear()
        self.fig.patch.set_facecolor(p["card_bottom"])
        self.setStyleSheet(f"background-color: {p['card_bottom']}; border-radius: 8px;")
        self.ax = self.fig.add_subplot(111)
        self._style_axes(self.ax)
        self._points = []
        self._annotation = None
        self._hovering = False
        return self.ax

    def _finish(self) -> None:
        self.fig.tight_layout(pad=1.0)
        self.draw_idle()

    def _legend(self, ax) -> None:  # noqa: ANN001
        p = palette()
        legend = ax.legend(
            loc="upper left",
            frameon=False,
            ncol=2,
            fontsize=8,
            handlelength=1.2,
            columnspacing=1.2,
            labelcolor=p["muted"],
        )
        for text in legend.get_texts():
            text.set_fontfamily(_FONT)

    def _empty(self, message: str = "No data for this period") -> None:
        ax = self._reset()
        p = palette()
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        ax.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            color=p["dim"],
            fontsize=9,
            fontfamily=_FONT,
            transform=ax.transAxes,
        )
        self._finish()

    # ------------------------------------------------------------------ tooltips
    def _on_move(self, event) -> None:  # noqa: ANN001
        if event.inaxes is None or not self._points or event.x is None or event.y is None:
            self._hide_tip()
            return
        to_display = self.ax.transData.transform
        best = None
        best_dist = 36.0
        for x, y, text in self._points:
            px, py = to_display((x, y))
            dist = ((px - event.x) ** 2 + (py - event.y) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = (x, y, text)
        if best is None:
            self._hide_tip()
            return
        p = palette()
        x, y, text = best
        if self._annotation is None:
            self._annotation = self.ax.annotate(
                text,
                xy=(x, y),
                xytext=(10, 14),
                textcoords="offset points",
                fontsize=8,
                color=p["text"],
                fontfamily=_FONT,
                bbox=dict(
                    boxstyle="round,pad=0.45",
                    fc=p["surface3"],
                    ec=p["border"],
                    alpha=0.98,
                ),
                arrowprops=dict(arrowstyle="-", color=p["accent"], lw=0.8),
                zorder=20,
            )
        else:
            self._annotation.xy = (x, y)
            self._annotation.set_text(text)
            self._annotation.set_visible(True)
        self._annotation.get_bbox_patch().set_facecolor(p["surface3"])
        self._annotation.get_bbox_patch().set_edgecolor(p["border"])
        self._annotation.set_color(p["text"])
        self._hovering = True
        self.draw_idle()

    def _hide_tip(self) -> None:
        if self._annotation is not None and self._hovering:
            self._annotation.set_visible(False)
            self._hovering = False
            self.draw_idle()

    def _on_leave(self, event) -> None:  # noqa: ANN001
        self._hide_tip()

    # ------------------------------------------------------------------ charts
    def render_cash_flow(self, trends: list[dict], selected_month: int) -> None:
        if not any(t["income_paise"] or t["expense_paise"] for t in trends):
            self._empty()
            return
        ax = self._reset()
        p = palette()
        months = [calendar.month_abbr[t["month"]] for t in trends]
        x = list(range(len(trends)))
        income = [t["income_paise"] / 100 for t in trends]
        expense = [t["expense_paise"] / 100 for t in trends]

        ax.axvspan(selected_month - 1.45, selected_month - 0.55, color=p["accent"], alpha=0.07, lw=0)
        ax.fill_between(x, income, color="#34D399", alpha=0.10)
        ax.plot(x, income, color="#34D399", linewidth=2.0, marker="o", markersize=3.5, label="Income", zorder=3)
        ax.fill_between(x, expense, color="#7C5CFF", alpha=0.13)
        ax.plot(x, expense, color="#8B5CFF", linewidth=2.0, marker="o", markersize=3.5, label="Expenses", zorder=3)

        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.set_xlim(-0.4, len(trends) - 0.6)
        ax.set_ylim(bottom=0)
        self._legend(ax)
        self._points = []
        for i, t in enumerate(trends):
            if t["income_paise"]:
                self._points.append((i, income[i], f"{calendar.month_abbr[t['month']]} income · {format_money(t['income_paise'])}"))
            if t["expense_paise"]:
                self._points.append((i, expense[i], f"{calendar.month_abbr[t['month']]} spend · {format_money(t['expense_paise'])}"))
        self._finish()

    def render_income_expense(self, trends: list[dict]) -> None:
        if not any(t["income_paise"] or t["expense_paise"] for t in trends):
            self._empty()
            return
        ax = self._reset()
        labels = [t["label"] for t in trends]
        x = list(range(len(trends)))
        income = [t["income_paise"] / 100 for t in trends]
        expense = [t["expense_paise"] / 100 for t in trends]
        width = 0.34
        ax.bar([i - width / 2 for i in x], income, width=width, color="#34D399", label="Income", zorder=3)
        ax.bar([i + width / 2 for i in x], expense, width=width, color="#8B5CFF", label="Expenses", zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylim(bottom=0)
        self._legend(ax)
        self._points = []
        for i, t in enumerate(trends):
            if t["income_paise"]:
                self._points.append((i - width / 2, income[i], f"Income · {format_money(t['income_paise'])}"))
            if t["expense_paise"]:
                self._points.append((i + width / 2, expense[i], f"Expenses · {format_money(t['expense_paise'])}"))
        self._finish()

    def render_category(self, categories: dict[str, int], max_items: int = 6) -> None:
        if not categories:
            self._empty("No spending categories yet")
            return
        ax = self._reset()
        items = sorted(categories.items(), key=lambda kv: kv[1], reverse=True)[:max_items]
        items.reverse()
        labels = [name for name, _ in items]
        values = [value / 100 for _, value in items]
        base = ["#5B36F0", "#6D4AFF", "#7C5CFF", "#9075FF", "#A48DFF", "#B7A5FF", "#C9BCFF"]
        colors = base[-len(items):]
        bars = ax.barh(labels, values, color=colors, height=0.58, zorder=3)
        ax.set_xlim(0, max(values) * 1.26 if values else 1)
        ax.grid(False)
        ax.set_xticks([])
        ax.tick_params(axis="y", labelsize=8.5)
        for bar, value in zip(bars, values):
            ax.text(
                value + max(values) * 0.025,
                bar.get_y() + bar.get_height() / 2,
                compact_money(int(value * 100)),
                va="center",
                fontsize=8,
                color=palette()["muted"],
                fontfamily=_FONT,
            )
        self._points = []
        for i, (name, amount) in enumerate(items):
            self._points.append((amount / 100, i, f"{name} · {format_money(amount)}"))
        self._finish()

    def render_expense_trend(self, trends: list[dict]) -> None:
        if not any(t["expense_paise"] for t in trends):
            self._empty("No expenses to trend yet")
            return
        ax = self._reset()
        p = palette()
        months = [calendar.month_abbr[t["month"]] for t in trends]
        x = list(range(len(trends)))
        expense = [t["expense_paise"] / 100 for t in trends]
        ax.fill_between(x, expense, color="#7C5CFF", alpha=0.16)
        ax.plot(x, expense, color="#8B5CFF", linewidth=2.2, marker="o", markersize=3.5, label="Expenses", zorder=3)
        # Three month rolling average, only once there is enough history.
        if len(expense) >= 3:
            rolling = []
            for i in range(len(expense)):
                window = expense[max(0, i - 2) : i + 1]
                rolling.append(sum(window) / len(window))
            ax.plot(x, rolling, color="#38BDF8", linewidth=1.4, linestyle=(0, (3, 3)), label="3-mo average", zorder=4)
        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.set_ylim(bottom=0)
        self._legend(ax)
        self._points = []
        for i, t in enumerate(trends):
            if t["expense_paise"]:
                self._points.append((i, expense[i], f"{months[i]} spend · {format_money(t['expense_paise'])}"))
        self._finish()


def rebuild_chart_theme(canvas: ChartCanvas) -> None:
    """Re-colour an existing canvas after a theme switch."""
    p = palette()
    canvas.fig.patch.set_facecolor(p["card_bottom"])
    canvas.setStyleSheet(f"background-color: {p['card_bottom']}; border-radius: 8px;")
    canvas.ax.set_facecolor(p["card_bottom"])
    canvas._style_axes(canvas.ax)  # noqa: SLF001
    canvas._finish()  # noqa: SLF001
