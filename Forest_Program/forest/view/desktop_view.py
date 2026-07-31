"""PySide6 Graphics Viewを使用したメイン画面。"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
    QNativeGestureEvent,
    QPainter,
    QPen,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from forest.model import Model, ModelEvent
from forest.shared import BBox, Constants, Point
from forest.tree import BaseNode
from forest.view.canvas_renderer import CanvasRenderer
from forest.view.popups import CanvasPopupView, NodeEditorPopupView
from forest.view.theme import ViewTheme


class ControllerInputPort(Protocol):
    def openFile(self, inputPath: Path) -> None: ...

    def handleDrop(self, paths: list[Path]) -> None: ...

    def handlePointerPress(self, point: Point) -> None: ...

    def handlePointerMove(self, point: Point) -> None: ...

    def handlePointerRelease(self, point: Point) -> bool: ...

    def handleWheel(self, deltaX: float, deltaY: float) -> None: ...

    def handleZoom(self, anchor: Point, scaleDelta: float) -> None: ...

    def handleNodeClick(self, node: BaseNode, popupBBox: BBox) -> None: ...

    def handleCanvasClick(self) -> None: ...

    def clearTree(self) -> None: ...

    def confirmRename(self, text: str) -> None: ...

    def cancelPopup(self) -> None: ...

    def setPlaying(self, isPlaying: bool) -> None: ...

    def showNextStep(self) -> None: ...

    def exportCanvas(self, outputPath: Path) -> None: ...

    def exportSelectedSubgraph(self, outputPath: Path) -> None: ...

    def resizeDesktop(self, width: float, height: float) -> None: ...


class DesktopGraphicsView(QGraphicsView):
    """Qtネイティブのホイール、ピンチ、DnDをDesktopViewへ渡す。"""

    def __init__(self, owner: DesktopView, scene: QGraphicsScene) -> None:
        super().__init__(scene, owner)
        self._owner = owner
        self._contextClickActive = False
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setBackgroundBrush(QColor(ViewTheme.CANVAS_BACKGROUND))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

    def drawBackground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        sceneRect = QRectF(rect)
        painter.fillRect(sceneRect, QColor(ViewTheme.CANVAS_BACKGROUND))
        spacing = ViewTheme.GRID_SPACING
        left = int(sceneRect.left() // spacing) * spacing
        top = int(sceneRect.top() // spacing) * spacing
        painter.setPen(QPen(QColor(ViewTheme.GRID_COLOR), ViewTheme.GRID_DOT_RADIUS))
        x = left
        while x <= sceneRect.right():
            y = top
            while y <= sceneRect.bottom():
                painter.drawPoint(QPointF(float(x), float(y)))
                y += spacing
            x += spacing

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._contextClickActive = True
                self._owner.showCanvasMenu(event.position())
                event.accept()
                return
            self._owner.handlePointerPress(event.position())
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._owner.showCanvasMenu(event.position())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._owner.handlePointerMove(event.position())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._contextClickActive:
                self._contextClickActive = False
                event.accept()
                return
            self._owner.handlePointerRelease(event.position())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._owner.handleWheelEvent(event):
            event.accept()
            return
        super().wheelEvent(event)

    def viewportEvent(self, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Type.NativeGesture
            and isinstance(event, QNativeGestureEvent)
            and self._owner.handleNativeGesture(event)
        ):
            return True
        return super().viewportEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        self._owner.handleDrop(paths)
        event.acceptProposedAction()


class DesktopView(QWidget):
    """Modelを読み取り、入力をControllerへ渡すQtメイン画面。"""

    def __init__(self, _application: object, model: Model) -> None:
        super().__init__()
        self._model = model
        self._controller: ControllerInputPort | None = None
        self.setWindowTitle("樹状整列")
        self.resize(1180, 740)
        self.setMinimumSize(760, 480)
        self.setAcceptDrops(True)
        self.setStyleSheet(f"background: {ViewTheme.WINDOW_BACKGROUND};")

        self._scene = QGraphicsScene(self)
        self._canvas = DesktopGraphicsView(self, self._scene)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(self._canvas)
        self._renderer = CanvasRenderer(self._scene, model, self._canvas)

        self._stepLabel = QLabel("", self)
        self._stepLabel.setStyleSheet(f"color: {ViewTheme.SECONDARY_TEXT_COLOR}; background: transparent;")
        self._stepLabel.hide()

        self._playbackFrame = QFrame(self)
        self._playbackFrame.setFixedSize(ViewTheme.PLAYBACK_WIDTH, ViewTheme.PLAYBACK_HEIGHT)
        self._playbackFrame.setStyleSheet(
            f"QFrame {{ background: {ViewTheme.CONTROL_BACKGROUND}; border: 1px solid #E8E8E6; border-radius: 8px; }}"
        )
        playbackLayout = QHBoxLayout(self._playbackFrame)
        playbackLayout.setContentsMargins(7, 5, 8, 5)
        playbackLayout.setSpacing(2)
        self._playbackButton = QPushButton("▶", self._playbackFrame)
        self._playbackButton.setFixedSize(34, 30)
        self._playbackButton.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self._playbackButton.clicked.connect(self._togglePlayback)
        self._playbackLabel = QLabel("", self._playbackFrame)
        self._playbackLabel.setStyleSheet(f"color: {ViewTheme.SECONDARY_TEXT_COLOR}; border: none;")
        playbackLayout.addWidget(self._playbackButton)
        playbackLayout.addWidget(self._playbackLabel)
        self._playbackFrame.hide()

        self._playbackTimer = QTimer(self)
        self._playbackTimer.setSingleShot(True)
        self._playbackTimer.timeout.connect(self._advancePlayback)
        self._nodeEditorPopupView = NodeEditorPopupView(self)
        self._canvasPopupView = CanvasPopupView(self)
        self._subscribeToModel()
        self.renderCanvas()
        self.renderPlaybackControls()

    def bindController(self, controller: ControllerInputPort) -> None:
        self._controller = controller
        self._nodeEditorPopupView.bindController(controller)
        self._canvasPopupView.bindController(controller)
        QTimer.singleShot(0, self._syncDesktopSize)

    def chooseInputFile(self) -> Path | None:
        selected, _ = QFileDialog.getOpenFileName(self, "Forestファイルを開く", "", "テキストファイル (*.txt);;すべて")
        return Path(selected) if selected else None

    def chooseOutputFile(self) -> Path | None:
        selected, _ = QFileDialog.getSaveFileName(self, "画像を書き出す", "", "PNG画像 (*.png)")
        return Path(selected) if selected else None

    def renderCanvas(self) -> None:
        width, height = self._viewportSize()
        self._renderer.render(width, height)
        self._renderSelectionPopup()

    def renderPlaybackControls(self) -> None:
        total = self._model.totalSteps
        current = self._model.currentStep + 1 if total else 0
        text = f"{current:02d} / {total:02d}"
        self._stepLabel.setText(text)
        self._playbackLabel.setText(text)
        self._playbackButton.setText("Ⅱ" if self._model.isPlaying else "▶")
        self._stepLabel.setVisible(bool(total))
        self._playbackFrame.setVisible(bool(total))
        self._positionOverlays()
        self._syncPlaybackTimer()

    def nodeAt(self, viewPoint: Point) -> BaseNode | None:
        return self._renderer.nodeAt(viewPoint)

    def handlePointerPress(self, position: QPointF) -> None:
        self._canvasPopupView.hide()
        if self._controller is not None:
            self._controller.handlePointerPress(Point(position.x(), position.y()))

    def handlePointerMove(self, position: QPointF) -> None:
        if self._controller is not None:
            self._controller.handlePointerMove(Point(position.x(), position.y()))

    def handlePointerRelease(self, position: QPointF) -> None:
        if self._controller is None:
            return
        point = Point(position.x(), position.y())
        if not self._controller.handlePointerRelease(point):
            return
        node = self.nodeAt(point)
        if node is None:
            if not self._model.nodes:
                selected = self.chooseInputFile()
                if selected is not None:
                    self._controller.openFile(selected)
            else:
                self._controller.handleCanvasClick()
            return
        self._controller.handleNodeClick(
            node,
            BBox(point.x + 14, point.y + 8, ViewTheme.POPOVER_WIDTH, ViewTheme.NODE_POPOVER_HEIGHT),
        )

    def showCanvasMenu(self, position: QPointF) -> None:
        if self._controller is not None:
            self._controller.handleCanvasClick()
        self._canvasPopupView.showAt(
            position.x() + 10,
            position.y() + 8,
            self.width(),
            self.height(),
            bool(self._model.nodes),
        )

    def handleWheelEvent(self, event: QWheelEvent) -> bool:
        if self._controller is None:
            return False
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y() or event.pixelDelta().y()
            if delta:
                scaleDelta = 1.1 if delta > 0 else 1 / 1.1
                position = event.position()
                self._controller.handleZoom(Point(position.x(), position.y()), scaleDelta)
            return True
        pixelDelta = event.pixelDelta()
        angleDelta = event.angleDelta()
        deltaX = float(pixelDelta.x() if not pixelDelta.isNull() else angleDelta.x() / 4)
        deltaY = float(pixelDelta.y() if not pixelDelta.isNull() else angleDelta.y() / 4)
        self._controller.handleWheel(deltaX, deltaY)
        return True

    def handleNativeGesture(self, event: QNativeGestureEvent) -> bool:
        if self._controller is None or event.gestureType() != Qt.NativeGestureType.ZoomNativeGesture:
            return False
        position = event.position()
        self._controller.handleZoom(Point(position.x(), position.y()), max(0.01, 1.0 + event.value()))
        event.accept()
        return True

    def handleDrop(self, paths: list[Path]) -> None:
        if self._controller is not None:
            self._controller.handleDrop(paths)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._positionOverlays()
        QTimer.singleShot(0, self._syncDesktopSize)

    def _syncDesktopSize(self) -> None:
        width, height = self._viewportSize()
        if self._controller is not None:
            current = self._model.desktop.windowSizeBBox
            if current.width != width or current.height != height:
                self._controller.resizeDesktop(float(width), float(height))
        else:
            self._renderer.render(width, height)

    def _viewportSize(self) -> tuple[int, int]:
        return max(1, self._canvas.viewport().width()), max(1, self._canvas.viewport().height())

    def _positionOverlays(self) -> None:
        self._playbackFrame.move(
            max(0, (self.width() - self._playbackFrame.width()) // 2),
            max(0, self.height() - self._playbackFrame.height() - 28),
        )
        self._stepLabel.adjustSize()
        self._stepLabel.move(
            max(0, self.width() - self._stepLabel.width() - 32),
            max(0, self.height() - self._stepLabel.height() - 30),
        )
        self._playbackFrame.raise_()
        self._stepLabel.raise_()

    def _subscribeToModel(self) -> None:
        self._model.events.subscribe(ModelEvent.NODES_CHANGED, self._onNodesChanged)
        self._model.events.subscribe(ModelEvent.LAYOUT_CHANGED, self._onLayoutChanged)
        self._model.events.subscribe(ModelEvent.SELECTION_CHANGED, self._onSelectionChanged)
        self._model.events.subscribe(ModelEvent.EDITOR_CHANGED, self._onEditorChanged)
        self._model.events.subscribe(ModelEvent.PLAYBACK_CHANGED, self._onPlaybackChanged)
        self._model.events.subscribe(ModelEvent.DESKTOP_CHANGED, self._onDesktopChanged)

    def _togglePlayback(self) -> None:
        if self._controller is not None:
            self._controller.setPlaying(not self._model.isPlaying)

    def _syncPlaybackTimer(self) -> None:
        self._playbackTimer.stop()
        if not self._model.isPlaying or self._controller is None:
            return
        if self._model.currentStep + 1 >= self._model.totalSteps:
            self._controller.setPlaying(False)
            return
        self._playbackTimer.start(Constants.PLAYBACK_STEP_INTERVAL_MS)

    def _advancePlayback(self) -> None:
        if self._controller is not None:
            self._controller.showNextStep()
            self._canvas.viewport().repaint()
            QApplication.processEvents()

    def _renderSelectionPopup(self) -> None:
        state = self._model.nodeEditorState
        if state is None:
            self._nodeEditorPopupView.hide()
            return
        self._nodeEditorPopupView.showState(state, self.width(), self.height())

    def _onNodesChanged(self) -> None:
        self.renderCanvas()

    def _onLayoutChanged(self) -> None:
        width, height = self._viewportSize()
        self._renderer.syncLayout(width, height)

    def _onSelectionChanged(self) -> None:
        self.renderCanvas()

    def _onEditorChanged(self) -> None:
        self._renderSelectionPopup()

    def _onPlaybackChanged(self) -> None:
        self.renderPlaybackControls()

    def _onDesktopChanged(self) -> None:
        width, height = self._viewportSize()
        self._renderer.syncViewport(width, height)
