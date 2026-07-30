"""ノードとCanvasの操作を行うQtフローティングポップアップ。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from forest.model import NodeEditorState
from forest.view.input_normalizer import clampPopupPosition
from forest.view.theme import ViewTheme


class PopupController(Protocol):
    def confirmRename(self, text: str) -> None: ...

    def cancelPopup(self) -> None: ...

    def clearTree(self) -> None: ...

    def exportCanvas(self, outputPath: Path) -> None: ...

    def exportSelectedSubgraph(self, outputPath: Path) -> None: ...


class RenameLineEdit(QLineEdit):
    def __init__(self, confirm: Callable[[], None], cancel: Callable[[], None], parent: QWidget) -> None:
        super().__init__(parent)
        self._confirm = confirm
        self._cancel = cancel

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if callable(self._confirm):
                self._confirm()
            return
        if event.key() == Qt.Key.Key_Escape:
            if callable(self._cancel):
                self._cancel()
            return
        super().keyPressEvent(event)


class NodeEditorPopupView(QFrame):
    """選択ノードの名称変更と部分画像出力を提供する。"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._controller: PopupController | None = None
        self.setFixedSize(ViewTheme.POPOVER_WIDTH, ViewTheme.NODE_POPOVER_HEIGHT)
        self.setStyleSheet(
            f"QFrame {{ background: {ViewTheme.POPOVER_BACKGROUND}; "
            f"border: 1px solid {ViewTheme.POPOVER_BORDER_COLOR}; border-radius: 6px; }}"
            "QPushButton, QLineEdit { border: none; background: transparent; }"
        )
        rootLayout = QVBoxLayout(self)
        rootLayout.setContentsMargins(7, 7, 7, 6)
        rootLayout.setSpacing(4)
        header = QHBoxLayout()
        self._textEntry = RenameLineEdit(self._confirm, self._close, self)
        self._textEntry.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {ViewTheme.TEXT_COLOR};")
        closeButton = QPushButton("×", self)
        closeButton.setFixedSize(28, 28)
        closeButton.clicked.connect(self._close)
        header.addWidget(self._textEntry)
        header.addWidget(closeButton)
        rootLayout.addLayout(header)
        separator = QFrame(self)
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background: {ViewTheme.SEPARATOR_COLOR}; border: none;")
        rootLayout.addWidget(separator)
        exportButton = QPushButton("↧    画像に書き出す\n      このノード以下", self)
        exportButton.setFixedHeight(62)
        exportButton.setStyleSheet(f"text-align: left; color: {ViewTheme.TEXT_COLOR}; border: none;")
        exportButton.clicked.connect(self._export)
        rootLayout.addWidget(exportButton)
        self.hide()

    @property
    def textEntry(self) -> QLineEdit:
        return self._textEntry

    def bindController(self, controller: PopupController) -> None:
        self._controller = controller

    def showState(self, state: NodeEditorState, containerWidth: int, containerHeight: int) -> None:
        self._textEntry.setText(state.editingText)
        x, y = clampPopupPosition(
            state.popupBBox.x,
            state.popupBBox.y,
            ViewTheme.POPOVER_WIDTH,
            ViewTheme.NODE_POPOVER_HEIGHT,
            containerWidth,
            containerHeight,
        )
        self.move(x, y)
        self.show()
        self.raise_()
        self._textEntry.setFocus()
        self._textEntry.selectAll()

    def draftText(self) -> str:
        return self._textEntry.text()

    def _confirm(self) -> None:
        if self._controller is not None:
            self._controller.confirmRename(self.draftText())

    def _close(self) -> None:
        if self._controller is not None:
            self._controller.cancelPopup()

    def _export(self) -> None:
        if self._controller is None:
            return
        output, _ = QFileDialog.getSaveFileName(self, "画像を書き出す", "", "PNG画像 (*.png)")
        if output:
            self._controller.exportSelectedSubgraph(Path(output))


class CanvasPopupView(QFrame):
    """Canvas全体の画像出力操作を提供する。"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._controller: PopupController | None = None
        self.setFixedSize(ViewTheme.POPOVER_WIDTH, ViewTheme.CANVAS_POPOVER_HEIGHT)
        self.setStyleSheet(
            f"QFrame {{ background: {ViewTheme.POPOVER_BACKGROUND}; "
            f"border: 1px solid {ViewTheme.POPOVER_BORDER_COLOR}; border-radius: 6px; }}"
            "QPushButton, QLabel { border: none; background: transparent; }"
        )
        rootLayout = QVBoxLayout(self)
        rootLayout.setContentsMargins(7, 7, 7, 6)
        rootLayout.setSpacing(4)
        header = QHBoxLayout()
        title = QLabel("キャンバス", self)
        title.setStyleSheet(f"color: {ViewTheme.SECONDARY_TEXT_COLOR};")
        closeButton = QPushButton("×", self)
        closeButton.setFixedSize(28, 28)
        closeButton.clicked.connect(self.hide)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(closeButton)
        rootLayout.addLayout(header)
        separator = QFrame(self)
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background: {ViewTheme.SEPARATOR_COLOR}; border: none;")
        rootLayout.addWidget(separator)
        exportButton = QPushButton("↧    画像に書き出す\n      ツリー全体", self)
        exportButton.setFixedHeight(58)
        exportButton.setStyleSheet(f"text-align: left; color: {ViewTheme.TEXT_COLOR}; border: none;")
        exportButton.clicked.connect(self._export)
        rootLayout.addWidget(exportButton)
        self._deleteButton = QPushButton("×    ツリーを削除\n      ファイル選択に戻る", self)
        self._deleteButton.setFixedHeight(58)
        self._deleteButton.setStyleSheet("text-align: left; color: #C0392B; border: none;")
        self._deleteButton.clicked.connect(self._deleteTree)
        rootLayout.addWidget(self._deleteButton)
        self.hide()

    def bindController(self, controller: PopupController) -> None:
        self._controller = controller

    def showAt(
        self,
        x: float,
        y: float,
        containerWidth: int,
        containerHeight: int,
        hasTree: bool,
    ) -> None:
        left, top = clampPopupPosition(
            x,
            y,
            ViewTheme.POPOVER_WIDTH,
            ViewTheme.CANVAS_POPOVER_HEIGHT,
            containerWidth,
            containerHeight,
        )
        self.move(left, top)
        self._deleteButton.setEnabled(hasTree)
        self.show()
        self.raise_()

    def _export(self) -> None:
        if self._controller is None:
            return
        output, _ = QFileDialog.getSaveFileName(self, "画像を書き出す", "", "PNG画像 (*.png)")
        if output:
            self._controller.exportCanvas(Path(output))

    def _deleteTree(self) -> None:
        if self._controller is not None:
            self._controller.clearTree()
        self.hide()
