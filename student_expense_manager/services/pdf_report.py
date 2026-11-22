from __future__ import annotations

import calendar
import tempfile
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from matplotlib import rcParams
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    CondPageBreak,
    Flowable,
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.money import format_money, get_currency

# --------------------------------------------------------------------------- fonts
_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONT_ITALIC = "Helvetica-Oblique"

try:  # DejaVu ships with matplotlib and contains the ₹ glyph.
    import matplotlib

    _ttf_dir = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf"
    _regular = _ttf_dir / "DejaVuSans.ttf"
    _bold = _ttf_dir / "DejaVuSans-Bold.ttf"
    _italic = _ttf_dir / "DejaVuSans-Oblique.ttf"
    _bold_italic = _ttf_dir / "DejaVuSans-BoldOblique.ttf"
    if _regular.exists() and _bold.exists():
        pdfmetrics.registerFont(TTFont("DejaVu", str(_regular)))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(_bold)))
        pdfmetrics.registerFont(TTFont("DejaVu-Oblique", str(_italic)))
        pdfmetrics.registerFont(TTFont("DejaVu-BoldOblique", str(_bold_italic)))
        pdfmetrics.registerFontFamily(
            "DejaVu",
            normal="DejaVu",
            bold="DejaVu-Bold",
            italic="DejaVu-Oblique",
            boldItalic="DejaVu-BoldOblique",
        )
        _FONT = "DejaVu"
        _FONT_BOLD = "DejaVu-Bold"
        _FONT_ITALIC = "DejaVu-Oblique"
except Exception:
    pass

rcParams["font.family"] = "DejaVu Sans"
rcParams["axes.unicode_minus"] = False

# --------------------------------------------------------------------------- palette
INK = colors.HexColor("#171331")
INK_SOFT = colors.HexColor("#3A3460")
MUTED = colors.HexColor("#6F6A94")
VIOLET = colors.HexColor("#6D4AFF")
VIOLET_LIGHT = colors.HexColor("#EDE8FF")
BLUE = colors.HexColor("#3B82F6")
SKY = colors.HexColor("#38BDF8")
MINT = colors.HexColor("#10B981")
AMBER = colors.HexColor("#F59E0B")
ROSE = colors.HexColor("#F43F5E")
BORDER = colors.HexColor("#E5E1F2")
SURFACE = colors.HexColor("#F8F7FC")
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 14 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _money(paise: int, currency: str | None = None) -> str:
    text = format_money(paise, code=currency or get_currency())
    if _FONT == "Helvetica":
        text = text.replace("₹", "Rs ").replace("€", "EUR ").replace("£", "GBP ")
    return text


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "h1": ParagraphStyle(
            "h1", fontName=_FONT_BOLD, fontSize=21, leading=25, textColor=WHITE
        ),
        "h2": ParagraphStyle(
            "h2", fontName=_FONT_BOLD, fontSize=12.5, leading=16, textColor=INK, spaceAfter=2
        ),
        "h3": ParagraphStyle(
            "h3", fontName=_FONT_BOLD, fontSize=9.5, leading=13, textColor=INK
        ),
        "body": ParagraphStyle(
            "body", fontName=_FONT, fontSize=9, leading=13, textColor=colors.HexColor("#2A2547")
        ),
        "small": ParagraphStyle(
            "small", fontName=_FONT, fontSize=7.6, leading=10.5, textColor=MUTED
        ),
        "label": ParagraphStyle(
            "label", fontName=_FONT_BOLD, fontSize=7.2, leading=9, textColor=MUTED
        ),
        "value": ParagraphStyle(
            "value", fontName=_FONT_BOLD, fontSize=14, leading=17, textColor=INK
        ),
        "value_small": ParagraphStyle(
            "value_small", fontName=_FONT_BOLD, fontSize=9.5, leading=12, textColor=INK
        ),
        "th": ParagraphStyle(
            "th", fontName=_FONT_BOLD, fontSize=7.3, leading=9, textColor=WHITE
        ),
        "td": ParagraphStyle(
            "td", fontName=_FONT, fontSize=7.9, leading=10.5, textColor=colors.HexColor("#2A2547")
        ),
        "td_right": ParagraphStyle(
            "td_right",
            fontName=_FONT,
            fontSize=7.9,
            leading=10.5,
            textColor=colors.HexColor("#2A2547"),
            alignment=TA_RIGHT,
        ),
        "td_bold": ParagraphStyle(
            "td_bold", fontName=_FONT_BOLD, fontSize=7.9, leading=10.5, textColor=INK
        ),
    }


# --------------------------------------------------------------------------- flowables
class ReportBanner(Flowable):
    def __init__(self, app_name: str, title: str, period: str, generated: str) -> None:
        super().__init__()
        self.app_name = app_name
        self.title = title
        self.period = period
        self.generated = generated
        self.width = CONTENT_W
        self.height = 94

    def wrap(self, available_width: float, available_height: float):  # noqa: ANN201
        return self.width, self.height

    def draw(self) -> None:
        c = self.canv
        w, h = self.width, self.height
        c.saveState()
        c.setFillColor(colors.HexColor("#171331"))
        c.roundRect(0, 0, w, h, 10, fill=1, stroke=0)
        # soft accent glows
        c.setFillColor(colors.HexColor("#6D4AFF"))
        c.setFillAlpha(0.28)
        c.circle(w - 26, h + 8, 72, fill=1, stroke=0)
        c.circle(w - 112, -26, 46, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(colors.HexColor("#8B5CF6"))
        c.roundRect(18, h - 24, 30, 3, 1.5, fill=1, stroke=0)

        c.setFont(_FONT_BOLD, 7.4)
        c.setFillColor(colors.HexColor("#B9B1EE"))
        c.drawString(18, h - 16, self.app_name.upper())

        c.setFillColor(WHITE)
        c.setFont(_FONT_BOLD, 20)
        c.drawString(18, h - 47, self.title)

        c.setFont(_FONT, 9.5)
        c.setFillColor(colors.HexColor("#DDD8FA"))
        c.drawString(18, h - 64, self.period)

        c.setFont(_FONT, 7.4)
        c.setFillColor(colors.HexColor("#A9A2D8"))
        c.drawRightString(w - 18, 16, f"Generated {self.generated}")
        c.drawRightString(w - 18, 27, "Offline · private · local data")
        c.restoreState()


class ProgressBar(Flowable):
    def __init__(self, fraction: float, width: float = 150, height: float = 6, color: colors.Color = VIOLET) -> None:
        super().__init__()
        self.fraction = max(0.0, min(1.0, float(fraction)))
        self.width = width
        self.height = height
        self.color = color

    def wrap(self, available_width: float, available_height: float):  # noqa: ANN201
        return self.width, self.height

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFillColor(colors.HexColor("#EEEAF8"))
        c.roundRect(0, 0, self.width, self.height, self.height / 2, fill=1, stroke=0)
        if self.fraction > 0:
            c.setFillColor(self.color)
            c.roundRect(0, 0, max(self.height, self.width * self.fraction), self.height, self.height / 2, fill=1, stroke=0)
        c.restoreState()


class SplitBar(Flowable):
    """A two-part bar for online vs offline spending."""

    def __init__(self, online: int, offline: int, width: float = 180, height: float = 8) -> None:
        super().__init__()
        self.online = max(0, online)
        self.offline = max(0, offline)
        self.width = width
        self.height = height

    def wrap(self, available_width: float, available_height: float):  # noqa: ANN201
        return self.width, self.height

    def draw(self) -> None:
        total = self.online + self.offline
        c = self.canv
        c.saveState()
        c.setFillColor(colors.HexColor("#EEEAF8"))
        c.roundRect(0, 0, self.width, self.height, self.height / 2, fill=1, stroke=0)
        if total:
            online_w = self.width * (self.online / total)
            c.setFillColor(VIOLET)
            c.roundRect(0, 0, max(self.height, online_w), self.height, self.height / 2, fill=1, stroke=0)
            if online_w < self.width - self.height:
                c.setFillColor(SKY)
                c.roundRect(online_w, 0, self.width - online_w, self.height, self.height / 2, fill=1, stroke=0)
        c.restoreState()


class MetricCards(Flowable):
    def __init__(self, values: list[tuple[str, str, colors.Color]], width: float = CONTENT_W) -> None:
        super().__init__()
        self.values = values
        self.width = width
        self.height = 58

    def wrap(self, available_width: float, available_height: float):  # noqa: ANN201
        return self.width, self.height

    def draw(self) -> None:
        c = self.canv
        gap = 8
        n = len(self.values)
        cell_w = (self.width - gap * (n - 1)) / n
        c.saveState()
        for i, (label, value, color) in enumerate(self.values):
            x = i * (cell_w + gap)
            c.setFillColor(colors.HexColor("#F7F5FD"))
            c.roundRect(x, 0, cell_w, self.height, 8, fill=1, stroke=0)
            c.setStrokeColor(BORDER)
            c.setLineWidth(0.5)
            c.roundRect(x, 0, cell_w, self.height, 8, fill=0, stroke=1)
            c.setFont(_FONT_BOLD, 6.9)
            c.setFillColor(MUTED)
            c.drawString(x + 12, self.height - 17, label.upper())
            c.setFont(_FONT_BOLD, 12.5)
            c.setFillColor(color)
            c.drawString(x + 12, self.height - 38, value)
        c.restoreState()


class EmptyBox(Flowable):
    def __init__(self, message: str, width: float = CONTENT_W, height: float = 42) -> None:
        super().__init__()
        self.message = message
        self.width = width
        self.height = height

    def wrap(self, available_width: float, available_height: float):  # noqa: ANN201
        return self.width, self.height

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFillColor(colors.HexColor("#FAF9FE"))
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=1)
        c.setFont(_FONT, 8.5)
        c.setFillColor(MUTED)
        c.drawCentredString(self.width / 2, self.height / 2 - 3, self.message)
        c.restoreState()


# --------------------------------------------------------------------------- charts
def _style_axes(ax) -> None:  # noqa: ANN001
    ax.set_facecolor("#FFFFFF")
    ax.grid(True, axis="y", color="#EEEAF8", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#DED9EF")
    ax.tick_params(colors="#6F6A94", labelsize=7, length=0)
    for label in ax.get_yticklabels():
        label.set_fontname("DejaVu Sans")


def _chart_daily(daily: list[dict], currency: str, path: Path) -> Path:
    fig = Figure(figsize=(7.2, 2.15), facecolor="#FFFFFF")
    ax = fig.add_subplot(111)
    _style_axes(ax)
    if daily:
        x = list(range(len(daily)))
        y = [d["expense_paise"] / 100 for d in daily]
        ax.fill_between(x, y, color="#8B5CF6", alpha=0.14)
        ax.plot(x, y, color="#6D4AFF", linewidth=1.8, solid_capstyle="round")
        ax.scatter([x[-1]], [y[-1]], s=16, color="#6D4AFF", zorder=3)
        step = max(1, len(daily) // 8)
        ticks = list(range(0, len(daily), step))
        labels = []
        for idx in ticks:
            raw = daily[idx]["date"]
            try:
                labels.append(date.fromisoformat(raw).strftime("%d %b"))
            except ValueError:
                labels.append(str(idx + 1))
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels)
        ax.set_ylim(bottom=0)
        ymax = max(y) if max(y) > 0 else 1
        ax.set_yticks([0, ymax * 0.5, ymax])
        ax.set_yticklabels([
            _money(0, currency),
            _money(int(ymax * 50), currency),
            _money(int(ymax * 100), currency),
        ])
    fig.savefig(path, dpi=200, facecolor="#FFFFFF", bbox_inches="tight")
    return path


def _chart_categories(categories: dict[str, int], currency: str, path: Path) -> Path:
    fig = Figure(figsize=(3.6, 2.15), facecolor="#FFFFFF")
    ax = fig.add_subplot(111)
    _style_axes(ax)
    items = sorted(categories.items(), key=lambda kv: kv[1], reverse=True)[:7]
    items.reverse()
    if items:
        labels = [k for k, _ in items]
        values = [v / 100 for _, v in items]
        shades = ["#C9BCFF", "#B7A5FF", "#A48DFF", "#9075FF", "#7C5CFF", "#6D4AFF", "#5B36F0"]
        cols = shades[-len(items):]
        bars = ax.barh(labels, values, color=cols, height=0.58)
        ax.set_xlim(0, max(values) * 1.22 if max(values) > 0 else 1)
        ax.grid(False)
        ax.set_xticks([])
        for bar, value in zip(bars, values):
            ax.text(
                value + max(values) * 0.03,
                bar.get_y() + bar.get_height() / 2,
                _money(int(value * 100), currency),
                va="center",
                fontsize=6.5,
                color="#3A3460",
                fontname="DejaVu Sans",
            )
        for label in ax.get_yticklabels():
            label.set_fontname("DejaVu Sans")
    fig.savefig(path, dpi=200, facecolor="#FFFFFF", bbox_inches="tight")
    return path


def _chart_split(online: int, offline: int, currency: str, path: Path) -> Path:
    fig = Figure(figsize=(3.4, 2.15), facecolor="#FFFFFF")
    ax = fig.add_subplot(111)
    total = online + offline
    if total > 0:
        ax.pie(
            [online, offline],
            colors=["#6D4AFF", "#38BDF8"],
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.34, "edgecolor": "#FFFFFF", "linewidth": 2},
        )
        ax.text(0, 0.08, _money(total, currency), ha="center", va="center", fontsize=9.5, fontweight="bold", color="#171331", fontname="DejaVu Sans")
        ax.text(0, -0.16, "total spend", ha="center", va="center", fontsize=6.5, color="#6F6A94", fontname="DejaVu Sans")
        ax.legend(
            ["Online", "Offline"],
            loc="lower center",
            bbox_to_anchor=(0.5, -0.12),
            ncol=2,
            frameon=False,
            fontsize=7,
            handlelength=1.2,
            prop={"family": "DejaVu Sans"},
        )
    else:
        ax.text(0.5, 0.5, "No spending", ha="center", va="center", color="#6F6A94", fontname="DejaVu Sans")
        ax.axis("off")
    fig.savefig(path, dpi=200, facecolor="#FFFFFF", bbox_inches="tight")
    return path


# --------------------------------------------------------------------------- canvas
class NumberedCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, footer_note: str = "", **kwargs):  # noqa: ANN002, ANN003
        self._saved_page_states: list[dict] = []
        self._footer_note = footer_note
        super().__init__(*args, **kwargs)

    def showPage(self):  # noqa: N802
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):  # noqa: ANN201
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total: int) -> None:
        self.saveState()
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.5)
        self.line(MARGIN, 34, PAGE_W - MARGIN, 34)
        self.setFont(_FONT, 7.2)
        self.setFillColor(MUTED)
        self.drawString(MARGIN, 23, "Student Expense Manager")
        self.drawCentredString(PAGE_W / 2, 23, self._footer_note)
        self.drawRightString(PAGE_W - MARGIN, 23, f"Page {self._pageNumber} of {total}")
        self.restoreState()


# --------------------------------------------------------------------------- service
class PdfReportService:
    """Builds designed PDF statements from real database data."""

    def __init__(self, finance: FinanceService | None = None, currency: str | None = None) -> None:
        self.finance = finance or FinanceService()
        self.currency = (currency or get_currency()).upper()

    # -- data helpers -----------------------------------------------------
    def _month_daily(self, report: dict) -> list[dict]:
        month, year = report["month"], report["year"]
        days = calendar.monthrange(year, month)[1]
        by_day: dict[str, int] = {}
        for tx in report["transactions"]:
            if tx.transaction_type == "expense":
                by_day[tx.transaction_date] = by_day.get(tx.transaction_date, 0) + tx.amount_paise
        out = []
        for day in range(1, days + 1):
            key = date(year, month, day).isoformat()
            out.append({"date": key, "expense_paise": by_day.get(key, 0)})
        return out

    # -- public API -------------------------------------------------------
    def monthly(self, path: str | Path, month: int, year: int) -> Path:
        report = self.finance.monthly_report(month, year)
        report["daily"] = self._month_daily(report)
        title = "Monthly Financial Report"
        period = f"{calendar.month_name[month]} {year}"
        return self._build(path, report, title, period, "monthly", month=month, year=year)

    def range(self, path: str | Path, start_date: str, end_date: str) -> Path:
        report = self.finance.range_report(start_date, end_date)
        title = "Financial Statement"
        period = str(report["period_label"])
        return self._build(path, report, title, period, "range")

    # -- builder ----------------------------------------------------------
    def _build(
        self,
        path: str | Path,
        report: dict,
        title: str,
        period: str,
        kind: str,
        month: int | None = None,
        year: int | None = None,
    ) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix.lower() != ".pdf":
            out = out.with_suffix(".pdf")

        styles = _styles()
        generated = datetime.now().strftime("%d %b %Y, %H:%M")
        tmp_ctx = tempfile.TemporaryDirectory(prefix="sem_pdf_")
        tmp_dir = Path(tmp_ctx.name)
        income = int(report["total_income_paise"])
        expense = int(report["total_expense_paise"])
        net = int(report["net_cash_flow_paise"])
        online = int(report["online_expense_paise"])
        offline = int(report["offline_expense_paise"])
        transactions = list(report.get("transactions", []))
        categories: dict[str, int] = dict(report.get("category_breakdown", {}))
        budgets = list(report.get("budget_utilization", []))
        savings_rate = float(report.get("savings_rate", 0.0))

        story: list[Flowable] = []
        story.append(ReportBanner("Student Expense Manager", title, period, generated))
        story.append(Spacer(1, 14))

        story.append(
            MetricCards(
                [
                    ("Total income", _money(income, self.currency), colors.HexColor("#0F9F6E")),
                    ("Total expenses", _money(expense, self.currency), colors.HexColor("#E23D5C")),
                    ("Net cash flow", _money(net, self.currency), colors.HexColor("#6D4AFF") if net >= 0 else colors.HexColor("#E23D5C")),
                    ("Savings rate", f"{savings_rate:.1f}%", colors.HexColor("#3B82F6")),
                ]
            )
        )
        story.append(Spacer(1, 14))

        # -- overview -----------------------------------------------------
        story.append(_p("Spending overview", styles["h2"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER, spaceBefore=2, spaceAfter=7))
        total_spend = online + offline
        online_pct = (online / total_spend * 100) if total_spend else 0.0
        overview_rows = [
            [_p("Channel", styles["label"]), _p("Amount", styles["label"]), _p("Share of spending", styles["label"])],
            [_p("Online payments", styles["td_bold"]), _p(_money(online, self.currency), styles["td"]), _p(f"{online_pct:.1f}%", styles["td"])],
            [_p("Offline payments", styles["td_bold"]), _p(_money(offline, self.currency), styles["td"]), _p(f"{100 - online_pct:.1f}%" if total_spend else "0.0%", styles["td"])],
        ]
        overview = Table(overview_rows, colWidths=[90, 80, 70])
        overview.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2EFFC")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        budget_data: list[list] = []
        if budgets:
            budget_data = [[
                _p("Budget", styles["label"]),
                _p("Limit", styles["label"]),
                _p("Spent", styles["label"]),
                _p("Used", styles["label"]),
            ]]
            for b in budgets:
                budget_data.append(
                    [
                        _p(escape(str(b["label"])), styles["td_bold"]),
                        _p(_money(int(b["budget_paise"]), self.currency), styles["td"]),
                        _p(_money(int(b["spent_paise"]), self.currency), styles["td"]),
                        _p(f"{float(b['percent']):.0f}%", styles["td"]),
                    ]
                )
            budget_table = Table(budget_data, colWidths=[72, 58, 58, 34])
            budget_table.setStyle(self._table_style())
        else:
            budget_table = EmptyBox("No budgets were set for this period.", width=222, height=34)

        left = [
            _p("Online vs offline", styles["h3"]),
            Spacer(1, 4),
            overview,
            Spacer(1, 8),
            SplitBar(online, offline, width=235, height=7),
            Spacer(1, 6),
            _p(
                f"{online_pct:.0f}% online · {100 - online_pct:.0f}% offline" if total_spend else "No spending in this period",
                styles["small"],
            ),
        ]
        right = [
            _p("Budget utilization", styles["h3"]),
            Spacer(1, 4),
            budget_table,
        ]
        split_table = Table([[left, right]], colWidths=[CONTENT_W / 2, CONTENT_W / 2])
        split_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (1, 0), (1, 0), 0),
                    ("LEFTPADDING", (1, 0), (1, 0), 14),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(split_table)
        story.append(Spacer(1, 16))

        # -- category breakdown ------------------------------------------
        story.append(_p("Category-wise spending", styles["h2"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER, spaceBefore=2, spaceAfter=7))
        if categories:
            cat_rows = [[
                _p("Category", styles["label"]),
                _p("Amount", styles["label"]),
                _p("Share", styles["label"]),
                _p("", styles["label"]),
            ]]
            total_cat = sum(categories.values()) or 1
            for name, amount in categories.items():
                cat_rows.append(
                    [
                        _p(escape(str(name)), styles["td_bold"]),
                        _p(_money(int(amount), self.currency), styles["td"]),
                        _p(f"{amount / total_cat * 100:.1f}%", styles["td"]),
                        ProgressBar(amount / total_cat, width=180, height=6, color=VIOLET),
                    ]
                )
            cat_table = Table(cat_rows, colWidths=[150, 85, 50, 226])
            cat_table.setStyle(self._table_style(align_right=(1, 2)))
            story.append(cat_table)
        else:
            story.append(EmptyBox("No expenses recorded for this period. Your report is still complete."))
        story.append(Spacer(1, 16))

        # -- charts -------------------------------------------------------
        if expense > 0:
            story.append(CondPageBreak(250))
            story.append(_p("Spending charts", styles["h2"]))
            story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER, spaceBefore=2, spaceAfter=7))
            daily = report.get("daily") or []
            daily_path = _chart_daily(daily, self.currency, tmp_dir / "daily.png")
            cat_path = _chart_categories(categories, self.currency, tmp_dir / "categories.png")
            split_path = _chart_split(online, offline, self.currency, tmp_dir / "split.png")
            story.append(Image(str(daily_path), width=CONTENT_W, height=CONTENT_W * 0.30))
            row = Table(
                [
                    [
                        Image(str(cat_path), width=CONTENT_W / 2 - 6),
                        Image(str(split_path), width=CONTENT_W / 2 - 6),
                    ]
                ],
                colWidths=[CONTENT_W / 2, CONTENT_W / 2],
            )
            row.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(row)
            story.append(Spacer(1, 10))
        else:
            story.append(EmptyBox("Charts appear once there are expenses to visualise.", height=36))
            story.append(Spacer(1, 10))

        # -- largest transactions ----------------------------------------
        largest = list(report.get("largest_transactions", []))
        if largest:
            story.append(CondPageBreak(140))
            story.append(_p("Largest transactions", styles["h2"]))
            story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER, spaceBefore=2, spaceAfter=6))
            rows = [[
                _p("Date", styles["label"]),
                _p("Description", styles["label"]),
                _p("Category", styles["label"]),
                _p("Amount", styles["label"]),
            ]]
            for tx in largest:
                rows.append(
                    [
                        _p(tx.transaction_date, styles["td"]),
                        _p(escape(tx.description or "—"), styles["td"]),
                        _p(escape(tx.category), styles["td"]),
                        _p(_money(tx.amount_paise, self.currency), styles["td_bold"]),
                    ]
                )
            table = Table(rows, colWidths=[62, 250, 100, 99])
            table.setStyle(self._table_style(align_right=(3,)))
            story.append(table)
            story.append(Spacer(1, 16))

        # -- full transaction details ------------------------------------
        story.append(CondPageBreak(150))
        story.append(_p("Transaction details", styles["h2"]))
        story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER, spaceBefore=2, spaceAfter=6))
        if transactions:
            tx_rows = [[
                _p("Date", styles["label"]),
                _p("Description", styles["label"]),
                _p("Category", styles["label"]),
                _p("Channel", styles["label"]),
                _p("Method", styles["label"]),
                _p("Amount", styles["label"]),
            ]]
            income_amount_style = ParagraphStyle(
                "amt_income",
                parent=styles["td_right"],
                textColor=colors.HexColor("#0F9F6E"),
                fontName=_FONT_BOLD,
            )
            expense_amount_style = ParagraphStyle(
                "amt_expense",
                parent=styles["td_right"],
                textColor=colors.HexColor("#2A2547"),
                fontName=_FONT_BOLD,
            )
            for tx in transactions:
                try:
                    date_text = date.fromisoformat(tx.transaction_date).strftime("%d %b %y")
                except ValueError:
                    date_text = tx.transaction_date
                tx_rows.append(
                    [
                        _p(date_text, styles["td"]),
                        _p(escape(tx.description or "—"), styles["td"]),
                        _p(escape(tx.category), styles["td"]),
                        _p(tx.payment_channel.title(), styles["td"]),
                        _p(escape(tx.payment_method), styles["td"]),
                        _p(
                            ("+" if tx.transaction_type == "income" else "−") + _money(tx.amount_paise, self.currency),
                            income_amount_style if tx.transaction_type == "income" else expense_amount_style,
                        ),
                    ]
                )
            tx_table = Table(tx_rows, colWidths=[62, 150, 92, 48, 63, 95], repeatRows=1)
            tx_table.setStyle(self._table_style(align_right=(5,)))
            story.append(tx_table)
            story.append(Spacer(1, 8))
            story.append(
                _p(
                    f"{len(transactions)} transaction{'s' if len(transactions) != 1 else ''} in this report. Amounts are stored in integer paise and shown in {self.currency}.",
                    styles["small"],
                )
            )
        else:
            story.append(EmptyBox("No transactions were recorded in this period. This is a valid, empty report.", height=46))

        story.append(Spacer(1, 6))
        story.append(
            _p(
                "This statement was generated locally on your computer. No financial data was uploaded or shared.",
                styles["small"],
            )
        )

        doc = SimpleDocTemplate(
            str(out),
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=13 * mm,
            bottomMargin=15 * mm,
            title=f"{title} — {period}",
            author="Student Expense Manager",
            subject="Offline personal finance report",
        )
        try:
            doc.build(
                story,
                onFirstPage=lambda c, d: None,
                onLaterPages=self._later_page_callback(title, period),
                canvasmaker=lambda *a, **k: NumberedCanvas(*a, footer_note=f"Generated {generated}", **k),
            )
        finally:
            tmp_ctx.cleanup()
        return out

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _table_style(align_right: tuple[int, ...] = ()) -> TableStyle:
        commands: list[tuple] = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2EFFC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#FAF9FE")]),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        for col in align_right:
            commands.append(("ALIGN", (col, 0), (col, -1), "RIGHT"))
        return TableStyle(commands)

    @staticmethod
    def _later_page_callback(title: str, period: str):  # noqa: ANN205
        def draw(c: pdfcanvas.Canvas, doc) -> None:  # noqa: ANN001
            c.saveState()
            c.setStrokeColor(BORDER)
            c.setLineWidth(0.5)
            c.line(MARGIN, PAGE_H - 30, PAGE_W - MARGIN, PAGE_H - 30)
            c.setFont(_FONT_BOLD, 7.2)
            c.setFillColor(MUTED)
            c.drawString(MARGIN, PAGE_H - 25, "Student Expense Manager")
            c.drawRightString(PAGE_W - MARGIN, PAGE_H - 25, f"{title} · {period}")
            c.restoreState()

        return draw
