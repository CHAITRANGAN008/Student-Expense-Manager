from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QDate, QRectF, QStandardPaths, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.money import format_money
from student_expense_manager.services.pdf_report import PdfReportService
from student_expense_manager.ui.page_base import PageHeader, content_layout, divider
from student_expense_manager.ui.theme import palette
from student_expense_manager.ui.widgets import (
    Card,
    IconChip,
    Pill,
    SectionCard,
    SegmentedControl,
    PeriodSelector,
    date_edit,
    make_button,
    repolish,
)


class ReportWorker(QThread):
    completed = Signal(str, str)
    failed = Signal(str)

    def __init__(
        self,
        *,
        kind: str,
        path: str,
        action: str,
        month: int = 1,
        year: int = 2026,
        start_date: str = "",
        end_date: str = "",
    ) -> None:
        super().__init__()
        self.kind = kind
        self.path = path
        self.action = action
        self.month = month
        self.year = year
        self.start_date = start_date
        self.end_date = end_date

    def run(self) -> None:
        try:
            service = PdfReportService()
            if self.kind == "monthly":
                out = service.monthly(self.path, self.month, self.year)
            else:
                out = service.range(self.path, self.start_date, self.end_date)
            self.completed.emit(str(out), self.action)
        except Exception as exc:  # pragma: no cover - defensive UI path
            self.failed.emit(str(exc))


class ReportPreview(QWidget):
    """A small painted mock of the PDF page, filled from real values."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(322)
        self._period = "November 2026"
        self._income = 0
        self._expense = 0
        self._net = 0
        self._transactions = 0

    def set_data(
        self, period: str, income: int, expense: int, net: int, transactions: int
    ) -> None:
        self._period = period
        self._income = income
        self._expense = expense
        self._net = net
        self._transactions = transactions
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802, ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = min(372, self.width() - 28)
        height = min(330, self.height() - 16)
        x = (self.width() - width) / 2
        y = (self.height() - height) / 2
        page = QRectF(x, y, width, height)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(5, 3, 15, 110))
        painter.drawRoundedRect(page.translated(0, 8), 8, 8)

        clip = QPainterPath()
        clip.addRoundedRect(page, 8, 8)
        painter.save()
        painter.setClipPath(clip)
        painter.fillRect(page, QColor("#FFFFFF"))

        banner_height = height * 0.29
        banner = QRectF(page.left(), page.top(), page.width(), banner_height)
        gradient = QLinearGradient(banner.topLeft(), banner.topRight())
        gradient.setColorAt(0.0, QColor("#7C5CFF"))
        gradient.setColorAt(0.6, QColor("#5F5BFF"))
        gradient.setColorAt(1.0, QColor("#3E7BFA"))
        painter.fillRect(banner, gradient)
        painter.setBrush(QColor(255, 255, 255, 26))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(page.right() - 110, page.top() - 40, 150, 150))

        painter.setPen(QColor(255, 255, 255, 205))
        f = QFont("Segoe UI", 5, QFont.Weight.DemiBold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        painter.setFont(f)
        painter.drawText(
            QRectF(page.left() + 16, page.top() + 13, page.width() - 32, 12),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "EXPENSE MANAGER  ·  STUDENT EDITION",
        )
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.drawText(
            QRectF(page.left() + 16, page.top() + 27, page.width() - 32, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Monthly Financial Report",
        )
        painter.setPen(QColor(255, 255, 255, 210))
        painter.setFont(QFont("Segoe UI", 6))
        painter.drawText(
            QRectF(page.left() + 16, page.top() + 49, page.width() - 32, 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._period,
        )

        # Metric boxes
        metrics = [
            ("INCOME", format_money(self._income), QColor("#0D9F6E")),
            ("EXPENSES", format_money(self._expense), QColor("#E11D48")),
            ("NET FLOW", format_money(self._net), QColor("#6D4AFF")),
        ]
        box_top = page.top() + banner_height + 12
        box_width = (page.width() - 32 - 12) / 3
        for index, (label, value, color) in enumerate(metrics):
            box = QRectF(
                page.left() + 16 + index * (box_width + 6),
                box_top,
                box_width,
                height * 0.17,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#F6F4FE"))
            painter.drawRoundedRect(box, 4, 4)
            painter.setPen(color)
            painter.setFont(QFont("Segoe UI", 4.6, QFont.Weight.Bold))
            painter.drawText(
                box.adjusted(7, 5, -7, -7),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                label,
            )
            painter.setPen(QColor("#1B1633"))
            painter.setFont(QFont("Segoe UI", 6.4, QFont.Weight.Bold))
            painter.drawText(
                box.adjusted(7, 14, -7, -4),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                value,
            )

        # Chart
        chart_top = box_top + height * 0.17 + 13
        chart = QRectF(page.left() + 16, chart_top, page.width() - 32, height * 0.25)
        painter.setPen(QPen(QColor("#EEEAF8"), 0.6))
        for i in range(4):
            line_y = chart.top() + chart.height() * i / 3
            painter.drawLine(
                chart.left(), line_y, chart.right(), line_y
            )
        path = QPainterPath()
        values = [0.62, 0.5, 0.72, 0.42, 0.6, 0.34, 0.47]
        for i, value in enumerate(values):
            px = chart.left() + chart.width() * i / (len(values) - 1)
            py = chart.bottom() - chart.height() * value
            if i == 0:
                path.moveTo(px, py)
            else:
                path.lineTo(px, py)
        painter.setPen(QPen(QColor("#7C5CFF"), 1.4))
        painter.drawPath(path)
        painter.setPen(QColor("#9A93B3"))
        painter.setFont(QFont("Segoe UI", 4.4))
        painter.drawText(
            QRectF(chart.left(), chart.bottom() + 2, chart.width(), 10),
            Qt.AlignmentFlag.AlignLeft,
            "Spending over the period",
        )

        # Ledger rows
        table_top = chart.bottom() + 18
        painter.setPen(QColor("#6B647F"))
        painter.setFont(QFont("Segoe UI", 4.8, QFont.Weight.Bold))
        painter.drawText(
            QRectF(page.left() + 16, table_top, page.width() - 32, 10),
            Qt.AlignmentFlag.AlignLeft,
            "RECENT TRANSACTIONS",
        )
        row_top = table_top + 13
        row_height = 12
        max_rows = max(2, int((page.bottom() - 18 - row_top) / row_height))
        for index in range(min(max_rows, 5)):
            if index % 2:
                painter.fillRect(
                    QRectF(page.left() + 16, row_top + index * row_height, page.width() - 32, row_height),
                    QColor("#F8F7FE"),
                )
            painter.setPen(QColor("#8A84A0"))
            painter.setFont(QFont("Segoe UI", 4.5))
            painter.drawText(
                QRectF(page.left() + 20, row_top + index * row_height, 40, row_height),
                Qt.AlignmentFlag.AlignVCenter,
                f"{index + 1:02d} Nov",
            )
            painter.setPen(QColor("#3A3357"))
            painter.drawText(
                QRectF(page.left() + 62, row_top + index * row_height, page.width() * 0.45, row_height),
                Qt.AlignmentFlag.AlignVCenter,
                "Category entry",
            )
            painter.setPen(QColor("#1B1633"))
            painter.drawText(
                QRectF(page.right() - 88, row_top + index * row_height, 68, row_height),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                format_money(self._expense // 9),
            )
        painter.setPen(QColor("#B7B0C9"))
        painter.setFont(QFont("Segoe UI", 4.2))
        painter.drawText(
            QRectF(page.left() + 16, page.bottom() - 12, page.width() - 32, 8),
            Qt.AlignmentFlag.AlignCenter,
            f"{self._transactions} transactions  ·  generated from your local records  ·  page 1",
        )
        painter.restore()
        painter.setPen(QPen(QColor(150, 140, 180, 70), 0.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(page, 8, 8)
        painter.end()


class FeatureRow(QWidget):
    def __init__(self, title: str, caption: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(10)
        p = palette()
        row.addWidget(IconChip("check", p["success"], p["green_tint"], size=28))
        text = QVBoxLayout()
        text.setSpacing(0)
        name = QLabel(title)
        name.setStyleSheet("font-size:11.5px;font-weight:600;")
        cap = QLabel(caption)
        cap.setObjectName("dimLabel")
        cap.setWordWrap(True)
        text.addWidget(name)
        text.addWidget(cap)
        row.addLayout(text, 1)


class ReportsPage(QWidget):
    def __init__(
        self,
        service: FinanceService,
        on_changed,
        on_navigate=None,
    ) -> None:
        super().__init__()
        self.service = service
        self.on_changed = on_changed
        self._worker: ReportWorker | None = None
        self._dirty = True

        root = content_layout(self)
        self.header = PageHeader(
            "Reports",
            "Print-ready statements built from your real records.",
            "STATEMENTS",
        )
        self.header.add_action(Pill("PDF · A4", "accent"))
        self.print_btn = make_button("Print", "secondary", "print")
        self.print_btn.clicked.connect(self.print_report)
        self.header.add_action(self.print_btn)
        self.save_btn = make_button("Save as PDF", "primary", "download")
        self.save_btn.clicked.connect(self.save_report)
        self.header.add_action(self.save_btn)
        root.addWidget(self.header)

        columns = QHBoxLayout()
        columns.setSpacing(14)

        self.builder_card = SectionCard(
            "Build a statement",
            "Choose a period. The PDF is created from your live data.",
        )
        self.export_btn = make_button("Export CSV", "ghost", "download")
        self.export_btn.setToolTip("Save this period's data as a UTF-8 CSV file")
        self.export_btn.clicked.connect(self.export_csv)
        self.builder_card.add_action(Pill("CSV · UTF-8", "neutral"))
        self.builder_card.add_action(self.export_btn)
        self.kind = SegmentedControl(
            [("Monthly", "monthly"), ("Custom range", "custom")], compact=True
        )
        self.kind.changed.connect(self._kind_changed)
        self.builder_card.body.addWidget(self.kind)

        self.monthly_box = QWidget()
        monthly_layout = QVBoxLayout(self.monthly_box)
        monthly_layout.setContentsMargins(0, 2, 0, 0)
        monthly_layout.setSpacing(8)
        monthly_label = QLabel("REPORT MONTH")
        monthly_label.setObjectName("sectionLabel")
        monthly_layout.addWidget(monthly_label)
        self.period = PeriodSelector()
        self.period.changed.connect(lambda *_: self._update_preview())
        monthly_layout.addWidget(self.period, 0, Qt.AlignmentFlag.AlignLeft)
        self.builder_card.body.addWidget(self.monthly_box)

        self.custom_box = QWidget()
        custom_layout = QVBoxLayout(self.custom_box)
        custom_layout.setContentsMargins(0, 2, 0, 0)
        custom_layout.setSpacing(8)
        dates = QHBoxLayout()
        dates.setSpacing(10)
        from_box = QVBoxLayout()
        from_box.setSpacing(5)
        from_label = QLabel("FROM")
        from_label.setObjectName("sectionLabel")
        self.from_date = date_edit(QDate.currentDate().addMonths(-1))
        from_box.addWidget(from_label)
        from_box.addWidget(self.from_date)
        to_box = QVBoxLayout()
        to_box.setSpacing(5)
        to_label = QLabel("TO")
        to_label.setObjectName("sectionLabel")
        self.to_date = date_edit()
        to_box.addWidget(to_label)
        to_box.addWidget(self.to_date)
        dates.addLayout(from_box)
        dates.addLayout(to_box)
        dates.addStretch(1)
        custom_layout.addLayout(dates)
        self.custom_note = QLabel("Custom statements can span any date range.")
        self.custom_note.setObjectName("dimLabel")
        custom_layout.addWidget(self.custom_note)
        self.from_date.dateChanged.connect(self._custom_dates_changed)
        self.to_date.dateChanged.connect(self._custom_dates_changed)
        self.builder_card.body.addWidget(self.custom_box)
        self.custom_box.setVisible(False)

        self.builder_card.body.addWidget(divider())

        summary_head = QHBoxLayout()
        summary_head.setSpacing(8)
        summary_title = QLabel("Preview")
        summary_title.setObjectName("cardTitle")
        summary_head.addWidget(summary_title)
        summary_head.addStretch(1)
        self.preview_period = QLabel("")
        self.preview_period.setObjectName("cardSubtitle")
        summary_head.addWidget(self.preview_period)
        self.builder_card.body.addLayout(summary_head)

        self.preview_rows = QVBoxLayout()
        self.preview_rows.setSpacing(7)
        self.builder_card.body.addLayout(self.preview_rows)
        self.preview_values: dict[str, QLabel] = {}
        for key, label in (
            ("income", "Total income"),
            ("expense", "Total expenses"),
            ("net", "Net cash flow"),
            ("count", "Transactions"),
        ):
            row = QHBoxLayout()
            name = QLabel(label)
            name.setObjectName("cardSubtitle")
            value = QLabel("—")
            value.setStyleSheet("font-size:12px;font-weight:700;")
            row.addWidget(name)
            row.addStretch(1)
            row.addWidget(value)
            self.preview_rows.addLayout(row)
            self.preview_values[key] = value
        self.builder_card.body.addStretch(1)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.status_pill = Pill("READY", "success")
        self.status_label = QLabel("Choose Save as PDF or Print when you are ready.")
        self.status_label.setObjectName("cardSubtitle")
        self.status_label.setWordWrap(True)
        status_row.addWidget(self.status_pill, 0, Qt.AlignmentFlag.AlignTop)
        status_row.addWidget(self.status_label, 1)
        self.builder_card.body.addLayout(status_row)
        columns.addWidget(self.builder_card, 1)

        right = QVBoxLayout()
        right.setSpacing(14)
        preview_card = Card()
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(18, 14, 18, 12)
        preview_layout.setSpacing(8)
        preview_head = QHBoxLayout()
        title = QLabel("Statement preview")
        title.setObjectName("cardTitle")
        preview_head.addWidget(title)
        preview_head.addStretch(1)
        self.preview_badge = Pill("LIVE DATA", "accent")
        preview_head.addWidget(self.preview_badge)
        preview_layout.addLayout(preview_head)
        self.report_preview = ReportPreview()
        preview_layout.addWidget(self.report_preview, 1)
        right.addWidget(preview_card, 2)

        features = SectionCard(
            "Included in every statement",
            "Designed for printing, sharing and record keeping.",
        )
        features.body.setSpacing(8)
        for title_text, caption in (
            ("Summary metrics", "Income, expenses and net cash flow for the period."),
            ("Category breakdown", "Ranked spending with proportions and amounts."),
            ("Charts", "Trend, categories and channel split, rendered at print quality."),
            ("Budget utilisation", "Progress against every limit set for the month."),
            ("Full ledger", "Every transaction in a clean, alternating table."),
            ("Page numbers & date", "Generated timestamp and numbered pages on every sheet."),
        ):
            features.body.addWidget(FeatureRow(title_text, caption))
        right.addWidget(features, 3)
        columns.addLayout(right, 1)
        root.addLayout(columns)
        root.addStretch(1)

        self._update_preview()

    # ------------------------------------------------------------------ period
    def _kind_changed(self, kind: str) -> None:
        self.monthly_box.setVisible(kind == "monthly")
        self.custom_box.setVisible(kind == "custom")
        self._update_preview()

    def _custom_dates_changed(self) -> None:
        self._update_preview()

    def _range(self) -> tuple[str, str]:
        return (
            self.from_date.date().toString("yyyy-MM-dd"),
            self.to_date.date().toString("yyyy-MM-dd"),
        )

    def _data(self) -> dict:
        if self.kind.current() == "monthly":
            month, year = self.period.period()
            report = self.service.monthly_report(month, year)
            return {
                "kind": "monthly",
                "month": month,
                "year": year,
                "period": f"{report['month_name']} {year}",
                "income": report["total_income_paise"],
                "expense": report["total_expense_paise"],
                "net": report["net_cash_flow_paise"],
                "count": len(report["transactions"]),
                "valid": True,
            }
        start, end = self._range()
        if end < start:
            return {
                "kind": "range",
                "start": start,
                "end": end,
                "period": "Check the dates",
                "income": 0,
                "expense": 0,
                "net": 0,
                "count": 0,
                "valid": False,
            }
        from datetime import date as date_cls

        report = self.service.range_report(start, end)
        start_dt = date_cls.fromisoformat(start)
        end_dt = date_cls.fromisoformat(end)
        return {
            "kind": "range",
            "start": start,
            "end": end,
            "period": f"{start_dt.strftime('%d %b %Y')} – {end_dt.strftime('%d %b %Y')}",
            "income": report["total_income_paise"],
            "expense": report["total_expense_paise"],
            "net": report["net_cash_flow_paise"],
            "count": len(report["transactions"]),
            "valid": True,
        }

    def _update_preview(self) -> None:
        data = self._data()
        self.preview_period.setText(str(data["period"]))
        self.preview_values["income"].setText(format_money(int(data["income"])))
        self.preview_values["expense"].setText(format_money(int(data["expense"])))
        self.preview_values["net"].setText(format_money(int(data["net"])))
        self.preview_values["count"].setText(str(data["count"]))
        self.report_preview.set_data(
            str(data["period"]),
            int(data["income"]),
            int(data["expense"]),
            int(data["net"]),
            int(data["count"]),
        )
        if not data["valid"]:
            self.status_pill.setText("CHECK DATES")
            self.status_pill.set_tone("danger")
            self.status_label.setText("The end date must be on or after the start date.")
            self.save_btn.setEnabled(False)
            self.print_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
        else:
            self.save_btn.setEnabled(True)
            self.print_btn.setEnabled(True)
            self.export_btn.setEnabled(True)

    # ------------------------------------------------------------------ actions
    def mark_dirty(self) -> None:
        self._dirty = True
        self._update_preview()

    def refresh(self) -> None:
        self._dirty = False
        self._update_preview()

    def _default_name(self, data: dict) -> str:
        if data["kind"] == "monthly":
            return f"Expense_Report_{data['period'].replace(' ', '_')}.pdf"
        return f"Expense_Statement_{data['start']}_to_{data['end']}.pdf"

    def _default_dir(self) -> str:
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        return documents or str(Path.home())

    def _start_worker(self, *, kind: str, path: str, action: str) -> None:
        data = self._data()
        if not data["valid"]:
            return
        self.save_btn.setEnabled(False)
        self.print_btn.setEnabled(False)
        self.status_pill.setText("GENERATING")
        self.status_pill.set_tone("warning")
        self.status_label.setText("Rendering charts and building your PDF…")
        self._worker = ReportWorker(
            kind=kind,
            path=path,
            action=action,
            month=int(data.get("month", 1)),
            year=int(data.get("year", 2026)),
            start_date=str(data.get("start", "")),
            end_date=str(data.get("end", "")),
        )
        self._worker.completed.connect(self._report_ready)
        self._worker.failed.connect(self._report_failed)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def save_report(self) -> None:
        data = self._data()
        if not data["valid"]:
            return
        default = str(Path(self._default_dir()) / self._default_name(data))
        path, _ = QFileDialog.getSaveFileName(
            self, "Save report as PDF", default, "PDF files (*.pdf)"
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self._start_worker(kind=str(data["kind"]), path=path, action="save")

    def print_report(self) -> None:
        data = self._data()
        if not data["valid"]:
            return
        stem = Path(self._default_name(data)).stem
        path = str(
            Path(tempfile.gettempdir())
            / f"sem_{stem}_{datetime.now():%H%M%S}.pdf"
        )
        self._start_worker(kind=str(data["kind"]), path=path, action="print")

    def export_csv(self) -> None:
        data = self._data()
        if not data["valid"]:
            return
        if data["kind"] == "monthly":
            default_name = f"Expense_Summary_{data['period'].replace(' ', '_')}.csv"
        else:
            default_name = (
                f"Expense_Ledger_{data['start']}_to_{data['end']}.csv"
            )
        default = str(Path(self._default_dir()) / default_name)
        path, _ = QFileDialog.getSaveFileName(
            self, "Export this period as CSV", default, "CSV files (*.csv)"
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            if data["kind"] == "monthly":
                saved = self.service.export_monthly_summary_csv(
                    path, int(data["month"]), int(data["year"])
                )
                detail = f"{data['count']} transactions in {data['period']}"
            else:
                saved = self.service.export_transactions_csv(
                    path,
                    start_date=str(data["start"]),
                    end_date=str(data["end"]),
                )
                detail = f"{data['count']} transactions from {data['period']}"
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Could not export", str(exc))
            return
        self.status_pill.setText("EXPORTED")
        self.status_pill.set_tone("success")
        self.status_label.setText(f"CSV saved · {saved}")
        QMessageBox.information(
            self,
            "Export complete",
            f"{detail} exported to:\n{saved}",
        )

    def _report_ready(self, path: str, action: str) -> None:
        self.save_btn.setEnabled(True)
        self.print_btn.setEnabled(True)
        self.status_pill.setText("READY")
        self.status_pill.set_tone("success")
        if action == "print":
            self.status_label.setText("PDF generated. Sending it to your printer…")
            self._print_file(path)
        else:
            self.status_label.setText(f"Saved · {path}")
            QMessageBox.information(
                self,
                "Report saved",
                f"Your PDF statement has been saved to:\n{path}",
            )

    def _report_failed(self, message: str) -> None:
        self.save_btn.setEnabled(True)
        self.print_btn.setEnabled(True)
        self.status_pill.setText("FAILED")
        self.status_pill.set_tone("danger")
        self.status_label.setText(message)
        QMessageBox.warning(self, "Could not create report", message)

    def _print_file(self, path: str) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path, "print")  # noqa: S606
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            self.status_label.setText("Sent to the printer. The PDF copy remains in your temp folder.")
        except OSError as exc:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            self.status_label.setText(
                f"No default PDF printer found ({exc}). The report was opened instead."
            )

    def apply_theme(self) -> None:
        self._update_preview()
