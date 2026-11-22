import os
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["SEM_DATA_DIR"] = tempfile.mkdtemp(prefix="sem-diag-")

from PySide6.QtWidgets import QApplication

from student_expense_manager.data.db import initialize_database
from student_expense_manager.services.demo import seed_demo_data, seed_demo_reminders
from student_expense_manager.services.finance_service import FinanceService
from student_expense_manager.services.reminder_service import ReminderService
from student_expense_manager.ui.main_window import MainWindow

initialize_database()
finance = FinanceService()
seed_demo_data(finance)
seed_demo_reminders(ReminderService(finance=finance))
app = QApplication([])
window = MainWindow()
window.resize(1240, 800)
window.switch_page("reminders")
window.show()
app.processEvents()
page = window._pages["reminders"]
print("page", page.geometry().getRect(), "host", page.toast_host.geometry().getRect())
for toast in page.toast_host._toasts:
    print("toast", toast.geometry().getRect(), "parent", type(toast.parent()).__name__)
