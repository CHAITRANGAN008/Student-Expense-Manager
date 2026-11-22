from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the app directory is on sys.path so running main.py from any working
# directory (e.g. double-clicking in Explorer) can import the package.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from student_expense_manager.data.db import initialize_database
from student_expense_manager.ui.main_window import MainWindow


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Student Expense Manager")
    parser.add_argument(
        "--screenshot",
        metavar="FILE",
        help="Render the app, save a PNG screenshot to FILE, then exit.",
    )
    parser.add_argument(
        "--page",
        choices=(
            "dashboard", "transactions", "budgets", "reminders",
            "analytics", "reports", "settings",
        ),
        default="dashboard",
        help="Which page to show in screenshot mode (default: dashboard).",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    import os
    import tempfile

    argv = sys.argv if argv is None else argv
    args = parse_args(argv)

    # Screenshot mode uses a disposable data folder and a small demo dataset so
    # the real database is never touched and the picture has something to show.
    if args.screenshot:
        demo_dir = tempfile.mkdtemp(prefix="sem-screenshot-")
        os.environ["SEM_DATA_DIR"] = demo_dir
        # Render offscreen: the real widget tree is built and painted at full
        # size, but the capture can never steal focus or appear above the
        # user's windows.
        if "QT_QPA_PLATFORM" not in os.environ:
            os.environ["QT_QPA_PLATFORM"] = "offscreen"

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(argv)
    app.setApplicationName("Student Expense Manager")
    if args.screenshot and sys.platform.startswith("win"):
        # The offscreen platform ships no font database of its own. Register the
        # real Windows UI fonts so the capture shows the same type as the app.
        from PySide6.QtGui import QFont, QFontDatabase

        font_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for font_file in ("segoeui.ttf", "segoeuib.ttf", "segoeuisl.ttf", "seguisym.ttf"):
            candidate = font_dir / font_file
            if candidate.exists():
                QFontDatabase.addApplicationFont(str(candidate))
        app.setFont(QFont("Segoe UI", 9))
    initialize_database()

    if args.screenshot:
        from student_expense_manager.services.demo import seed_demo_data, seed_demo_reminders
        from student_expense_manager.services.finance_service import FinanceService
        from student_expense_manager.services.reminder_service import ReminderService

        finance = FinanceService()
        seed_demo_data(finance)
        seed_demo_reminders(ReminderService(finance=finance))

    window = MainWindow()

    if args.screenshot:
        window.switch_page(args.page)
        out_path = Path(args.screenshot)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        window.resize(1400, 788)
        window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        if sys.platform.startswith("win"):
            window.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
            window.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint, True)
        window.show()
        # Keep drawing while unfocused; ~120 frames then capture.
        frames = {"count": 0}
        saved = {"ok": False}

        def tick() -> None:
            frames["count"] += 1
            window.update()
            app.processEvents()
            if frames["count"] >= 120:
                timer.stop()
                pixmap = window.grab()
                ok = pixmap.save(str(out_path), "PNG")
                if not ok:
                    from PySide6.QtGui import QImage

                    img = QImage(window.size(), QImage.Format.Format_ARGB32)
                    window.render(img)
                    ok = img.save(str(out_path), "PNG")
                saved["ok"] = ok
                app.quit()

        timer = QTimer(window)
        timer.timeout.connect(tick)
        timer.start(16)
        app.exec()
        return 0 if saved["ok"] else 1

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
