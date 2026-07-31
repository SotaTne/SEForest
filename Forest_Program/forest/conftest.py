"""Qt Widgetを実インスタンスで検証するためのpytest共通設定。"""

import os
from collections.abc import Generator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qtApplication() -> Generator[QApplication]:
    application = QApplication.instance()
    if not isinstance(application, QApplication):
        application = QApplication([])
    yield application
    for widget in application.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    application.processEvents()
    application.shutdown()
