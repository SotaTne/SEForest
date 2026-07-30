"""MVCの各要素を構成し、Qtデスクトップアプリケーションを起動する。"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from forest.controller import Controller
from forest.model import Model
from forest.shared import Constants
from forest.view import DesktopView


class ForestApp:
    """Model、Qt View、Controllerを生成して接続するComposition Root。"""

    def __init__(
        self,
        applicationFactory: Callable[[], Any] | None = None,
        modelFactory: Callable[[], Model] | None = None,
        controllerFactory: Callable[[Any], Controller] | None = None,
        viewFactory: Callable[[Any, Model], DesktopView] | None = None,
    ) -> None:
        self._applicationFactory = applicationFactory or self._createApplication
        self._modelFactory = modelFactory or Model
        self._controllerFactory = controllerFactory or Controller
        self._viewFactory = viewFactory or DesktopView
        self._application: Any | None = None
        self._model: Model | None = None
        self._desktopView: DesktopView | None = None
        self._controller: Controller | None = None

    def build(self) -> None:
        """MVCを一度だけ生成し、ViewからControllerへ入力を渡せるよう接続する。"""

        if self._application is not None:
            return
        application = self._applicationFactory()
        model = self._modelFactory()
        controller = self._controllerFactory(model)
        desktopView = self._viewFactory(application, model)
        desktopView.bindController(controller)
        self._application = application
        self._model = model
        self._desktopView = desktopView
        self._controller = controller

    def run(self) -> None:
        """MVCを構成してQtイベントループを開始する。"""

        self.build()
        if self._application is None or self._desktopView is None:
            raise RuntimeError("application was not built")
        self._desktopView.show()
        self._application.exec()

    @staticmethod
    def _createApplication() -> QApplication:
        """既存インスタンスを再利用してQt Applicationを1つだけ生成する。"""

        existing = QApplication.instance()
        application = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
        application.setApplicationName("Forest")
        application.setOrganizationName("SEForest")
        application.setStyle("Fusion")
        fontPath = Constants.applicationRoot() / Constants.FONT_PATH
        if QFontDatabase.addApplicationFont(str(fontPath)) < 0:
            raise RuntimeError(f"failed to register bundled font: {fontPath}")
        application.setFont(QFont(Constants.FONT_FAMILY))
        return application
