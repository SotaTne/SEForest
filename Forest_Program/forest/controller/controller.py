"""Viewの入力を正規化し、Model用の更新メッセージへ変換する。"""

from __future__ import annotations

from math import hypot
from pathlib import Path

from forest.controller.command_port import ModelCommandPort
from forest.shared import BBox, Constants, Point
from forest.tree import BaseNode


class Controller:
    """ModelやViewの状態を参照せず、入力メッセージを転送する薄いController。"""

    def __init__(self, commands: ModelCommandPort) -> None:
        self._commands = commands
        self._pressPoint: Point | None = None
        self._lastDragPoint: Point | None = None
        self._isDragging = False

    def openFile(self, inputPath: Path) -> None:
        self._commands.loadFile(inputPath)

    def handleDrop(self, paths: list[Path]) -> None:
        """空の入力を除き、先頭のファイルだけを開く。"""

        if not isinstance(paths, list):
            raise TypeError("paths must be a list")
        normalizedPaths = [path for path in paths if isinstance(path, Path)]
        if normalizedPaths:
            self.openFile(normalizedPaths[0])

    def handlePointerPress(self, point: Point) -> None:
        self._validatePoint(point)
        self._pressPoint = point
        self._lastDragPoint = point
        self._isDragging = False

    def handlePointerMove(self, point: Point) -> None:
        """閾値を超えた移動だけをパン操作として転送する。"""

        self._validatePoint(point)
        if self._pressPoint is None or self._lastDragPoint is None:
            return
        if not self._isDragging:
            distance = hypot(point.x - self._pressPoint.x, point.y - self._pressPoint.y)
            if distance < Constants.DRAG_THRESHOLD:
                return
            self._isDragging = True
        dx = point.x - self._lastDragPoint.x
        dy = point.y - self._lastDragPoint.y
        self._lastDragPoint = point
        if dx != 0.0 or dy != 0.0:
            self._commands.panDesktop(dx, dy)

    def handlePointerRelease(self, point: Point) -> bool:
        """一連のポインター操作を終了し、クリックだったかを返す。"""

        self._validatePoint(point)
        if self._pressPoint is None:
            return False
        if not self._isDragging:
            distance = hypot(point.x - self._pressPoint.x, point.y - self._pressPoint.y)
            isClick = distance < Constants.DRAG_THRESHOLD
        else:
            isClick = False
        self._pressPoint = None
        self._lastDragPoint = None
        self._isDragging = False
        return isClick

    def handleWheel(self, deltaX: float, deltaY: float) -> None:
        if deltaX != 0.0 or deltaY != 0.0:
            self._commands.panDesktop(deltaX, deltaY)

    def handleZoom(self, anchor: Point, scaleDelta: float) -> None:
        if scaleDelta != 1.0:
            self._commands.zoomDesktopAt(anchor, scaleDelta)

    def handleNodeClick(self, node: BaseNode, popupBBox: BBox) -> None:
        self._commands.selectNode(node, popupBBox)

    def handleCanvasClick(self) -> None:
        self._commands.clearSelection()

    def clearTree(self) -> None:
        self._commands.clearTree()

    def confirmRename(self, text: str) -> None:
        self._commands.renameSelectedNode(text)

    def cancelPopup(self) -> None:
        self._commands.clearSelection()

    def setPlaying(self, isPlaying: bool) -> None:
        self._commands.setPlaying(isPlaying)

    def showPreviousStep(self) -> None:
        self._commands.showPreviousStep()

    def showNextStep(self) -> None:
        self._commands.showNextStep()

    def seekStep(self, index: int) -> None:
        self._commands.showStep(index)

    def exportCanvas(self, outputPath: Path) -> None:
        self._commands.exportCanvas(outputPath)

    def exportSelectedSubgraph(self, outputPath: Path) -> None:
        self._commands.exportSelectedSubgraph(outputPath)

    def resizeDesktop(self, width: float, height: float) -> None:
        self._commands.resizeDesktop(width, height)

    def resetDesktopViewport(self) -> None:
        self._commands.resetDesktopViewport()

    @staticmethod
    def _validatePoint(point: Point) -> None:
        if not isinstance(point, Point):
            raise TypeError("point must be a Point")
