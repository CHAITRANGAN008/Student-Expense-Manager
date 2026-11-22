import os
import tempfile
from pathlib import Path

import pytest

from student_expense_manager.data.db import initialize_database


@pytest.fixture()
def temp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("SEM_DATA_DIR", d)
        initialize_database()
        yield Path(d)
