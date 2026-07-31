from collections.abc import Generator
from itertools import pairwise
from pathlib import Path
from time import monotonic, sleep
from typing import Any

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QFontMetrics, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import main as mainModule
from forest.application import ForestApp
from forest.controller import Controller
from forest.model import Model, ModelEvent
from forest.shared import BBox, Constants, Point
from forest.view import DesktopView


class ApplicationFake:
    def __init__(self) -> None:
        self.execCalls = 0

    def exec(self) -> int:
        self.execCalls += 1
        return 0


class ControllerFake:
    def __init__(self, commands: Any) -> None:
        self.commands = commands


class ViewFake:
    def __init__(self, application: Any, model: Model) -> None:
        self.application = application
        self.model = model
        self.controllers: list[ControllerFake] = []
        self.showCalls = 0

    def bindController(self, controller: ControllerFake) -> None:
        self.controllers.append(controller)

    def show(self) -> None:
        self.showCalls += 1


def buildApplicationFakes() -> tuple[ForestApp, ApplicationFake, Model, list[ControllerFake], list[ViewFake]]:
    qtApplication = ApplicationFake()
    model = Model()
    controllers: list[ControllerFake] = []
    views: list[ViewFake] = []

    def createController(commands: Any) -> ControllerFake:
        controller = ControllerFake(commands)
        controllers.append(controller)
        return controller

    def createView(application: Any, viewModel: Model) -> ViewFake:
        view = ViewFake(application, viewModel)
        views.append(view)
        return view

    application = ForestApp(
        applicationFactory=lambda: qtApplication,
        modelFactory=lambda: model,
        controllerFactory=createController,  # ty: ignore[invalid-argument-type]
        viewFactory=createView,  # ty: ignore[invalid-argument-type]
    )
    return application, qtApplication, model, controllers, views


def testBuildCreatesAndConnectsMvcExactlyOnce() -> None:
    application, qtApplication, model, controllers, views = buildApplicationFakes()

    application.build()
    application.build()

    assert len(controllers) == 1
    assert len(views) == 1
    assert controllers[0].commands is model
    assert views[0].application is qtApplication
    assert views[0].model is model
    assert views[0].controllers == [controllers[0]]


def testRunShowsViewAndStartsQtEventLoop() -> None:
    application, qtApplication, _, _, views = buildApplicationFakes()

    application.run()

    assert qtApplication.execCalls == 1
    assert views[0].showCalls == 1


def testMainCreatesAndRunsForestApplication(monkeypatch: Any) -> None:
    calls: list[str] = []

    class ForestApplicationFake:
        def run(self) -> None:
            calls.append("run")

    monkeypatch.setattr(mainModule, "ForestApp", ForestApplicationFake)

    mainModule.main()

    assert calls == ["run"]


def testCreateApplicationReusesSingleQtApplication(qtApplication: QApplication) -> None:
    first = ForestApp._createApplication()
    second = ForestApp._createApplication()

    assert first is qtApplication
    assert second is first
    assert first.applicationName() == "Forest"


def testRunPropagatesBuildFailureWithoutStartingEventLoop() -> None:
    application, qtApplication, _, _, _ = buildApplicationFakes()

    def failToBuild() -> Any:
        raise RuntimeError("cannot create model")

    application._modelFactory = failToBuild

    with pytest.raises(RuntimeError, match="cannot create model"):
        application.run()

    assert qtApplication.execCalls == 0
    assert application._application is None
    assert application._desktopView is None


def waitUntil(application: QApplication, predicate: Any, timeout: float = 3.0) -> None:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        application.processEvents()
        if predicate():
            return
        sleep(0.01)
    raise AssertionError("condition was not met")


@pytest.fixture
def realApplication(
    qtApplication: QApplication,
) -> Generator[tuple[ForestApp, QApplication, Model, Controller, DesktopView]]:
    application = ForestApp()
    application.build()
    model = application._model
    controller = application._controller
    view = application._desktopView
    assert model is not None
    assert controller is not None
    assert view is not None
    view.show()
    waitUntil(qtApplication, view.isVisible)
    try:
        yield application, qtApplication, model, controller, view
    finally:
        view.close()
        qtApplication.processEvents()


def treeInputPath() -> Path:
    return Path(__file__).parents[2] / "Forest_Document" / "Requirement" / "texts" / "tree.txt"


def testRealApplicationLoadsForestAndDrawsGraphicsScene(
    realApplication: tuple[ForestApp, QApplication, Model, Controller, DesktopView],
) -> None:
    _, application, model, controller, view = realApplication
    inputPath = treeInputPath()

    controller.openFile(inputPath)
    application.processEvents()

    viewportWidth, viewportHeight = view._viewportSize()
    assert model.desktop.windowSizeBBox == BBox(0.0, 0.0, float(viewportWidth), float(viewportHeight))
    assert model.sourceText == inputPath.read_text(encoding="utf-8")
    assert model.nodes
    assert model.totalSteps > 1
    assert len(view._renderer.nodeItems) == 70
    assert view._renderer.edgeItems
    rootItem = view._renderer.nodeItems[model.nodes[0]]
    labelFont = rootItem._label.font()
    assert labelFont.family() == Constants.FONT_FAMILY
    assert QFontMetrics(labelFont).horizontalAdvance(model.nodes[0].text) <= (
        model.nodes[0].bbox.width - Constants.NODE_HORIZONTAL_PADDING
    )
    assert view._stepLabel.text() == f"01 / {model.totalSteps:02d}"
    assert view._playbackFrame.isVisible()
    assert view._canvas.acceptDrops()


def testInitialLayoutFlowsDownwardAndWrapsOnlyAtViewportBottom(
    realApplication: tuple[ForestApp, QApplication, Model, Controller, DesktopView],
) -> None:
    _, application, model, controller, _ = realApplication

    controller.openFile(treeInputPath())
    application.processEvents()
    initialBoxes = list(model.layoutSteps[0].positions.values())
    firstColumnX = initialBoxes[0].x
    firstColumn = [box for box in initialBoxes if box.x == firstColumnX]

    assert len(firstColumn) > 1
    assert all(current.y > previous.y for previous, current in pairwise(firstColumn))
    assert max(box.y + box.height for box in firstColumn) <= model.desktop.windowCanvasBBox.height
    assert len({box.x for box in initialBoxes}) > 1


def testRealWheelScrollMovesVerticallyAndStopsAtCanvasBounds(
    realApplication: tuple[ForestApp, QApplication, Model, Controller, DesktopView],
) -> None:
    _, application, model, controller, view = realApplication
    controller.openFile(treeInputPath())
    controller.seekStep(model.totalSteps - 1)
    application.processEvents()

    scroll = QWheelEvent(
        QPointF(100.0, 100.0),
        QPointF(100.0, 100.0),
        QPoint(0, -120),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    view.handleWheelEvent(scroll)
    assert model.desktop.windowCanvasBBox.y > 0.0

    for _ in range(20):
        view.handleWheelEvent(scroll)
    maximumY = max(
        0.0,
        model.canvasBBox.y
        + model.canvasBBox.height
        + Constants.CANVAS_VIEWPORT_MARGIN / model.desktop.zoomScale
        - model.desktop.windowCanvasBBox.height,
    )
    assert model.desktop.windowCanvasBBox.y == maximumY


def testRealCtrlWheelZoomsAtPointer(
    realApplication: tuple[ForestApp, QApplication, Model, Controller, DesktopView],
) -> None:
    _, _, model, controller, view = realApplication
    controller.openFile(treeInputPath())
    before = model.desktop.zoomScale
    zoom = QWheelEvent(
        QPointF(200.0, 150.0),
        QPointF(200.0, 150.0),
        QPoint(),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )

    view.handleWheelEvent(zoom)

    assert model.desktop.zoomScale > before
    assert view._canvas.transform().m11() == model.desktop.zoomScale


def testRealPlaybackVisitsEveryStepWithoutSkipping(
    realApplication: tuple[ForestApp, QApplication, Model, Controller, DesktopView],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, application, model, controller, view = realApplication
    monkeypatch.setattr(Constants, "PLAYBACK_STEP_INTERVAL_MS", 0)
    controller.openFile(treeInputPath())
    visitedSteps: list[int] = []
    model.events.subscribe(ModelEvent.LAYOUT_CHANGED, lambda: visitedSteps.append(model.currentStep))

    view._playbackButton.click()
    waitUntil(application, lambda: not model.isPlaying)

    assert visitedSteps == list(range(1, model.totalSteps))
    assert model.currentStep == model.totalSteps - 1
    assert view._playbackLabel.text() == f"{model.totalSteps:02d} / {model.totalSteps:02d}"


def testRealPlaybackButtonRestartsCompletedLayoutWithoutLosingRename(
    realApplication: tuple[ForestApp, QApplication, Model, Controller, DesktopView],
    tmp_path: Path,
) -> None:
    _, application, model, controller, view = realApplication
    inputPath = tmp_path / "small-tree.txt"
    inputPath.write_text(
        "trees:\nRoot\n|-- Child\nnodes:\n1, Root\n2, Child\n",
        encoding="utf-8",
    )
    controller.openFile(inputPath)
    renamedNode = model.nodes[0]
    controller.handleNodeClick(renamedNode, BBox(10.0, 10.0, 246.0, 154.0))
    controller.confirmRename("RenamedRoot")
    controller.seekStep(model.totalSteps - 1)
    application.processEvents()

    view._playbackButton.click()

    assert model.isPlaying is True
    assert model.currentStep == 0
    assert renamedNode.text == "RenamedRoot"
    assert view._playbackButton.text() == "Ⅱ"
    assert view._playbackTimer.interval() == 50
    controller.setPlaying(False)


def testRealNodeSelectionPopupReturnRenamesNode(
    realApplication: tuple[ForestApp, QApplication, Model, Controller, DesktopView],
) -> None:
    _, application, model, controller, view = realApplication
    controller.openFile(treeInputPath())
    application.processEvents()
    selectedNode = model.nodes[0]
    viewPoint = model.desktop.canvasToView(
        Point(selectedNode.bbox.x + selectedNode.bbox.width / 2, selectedNode.bbox.y + selectedNode.bbox.height / 2)
    )
    controller.handleNodeClick(
        selectedNode,
        BBox(viewPoint.x + 10, viewPoint.y + 10, 246.0, 154.0),
    )
    application.processEvents()

    popup = view._nodeEditorPopupView
    assert popup.isVisible()
    assert popup.textEntry.text() == selectedNode.text
    popup.textEntry.setText("RenamedRoot")
    QTest.keyClick(popup.textEntry, Qt.Key.Key_Return)
    application.processEvents()

    assert selectedNode.text == "RenamedRoot"
    assert model.nodeEditorState is None
    assert not popup.isVisible()


def testCanvasMenuOpensOnlyWithControlClickOrRightClick(
    realApplication: tuple[ForestApp, QApplication, Model, Controller, DesktopView],
) -> None:
    _, application, _, controller, view = realApplication
    controller.openFile(treeInputPath())
    application.processEvents()
    canvas = view._canvas.viewport()
    clickPoint = QPoint(canvas.width() - 40, canvas.height() - 40)
    popup = view._canvasPopupView

    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, clickPoint)
    application.processEvents()
    assert not popup.isVisible()

    QTest.mouseClick(canvas, Qt.MouseButton.MiddleButton, Qt.KeyboardModifier.NoModifier, clickPoint)
    application.processEvents()
    assert not popup.isVisible()

    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, clickPoint)
    application.processEvents()
    assert popup.isVisible()

    popup.hide()
    QTest.mouseClick(canvas, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, clickPoint)
    application.processEvents()
    assert popup.isVisible()


def testDeleteTreeFromCanvasMenuReturnsToFileSelection(
    realApplication: tuple[ForestApp, QApplication, Model, Controller, DesktopView],
) -> None:
    _, application, model, controller, view = realApplication
    controller.openFile(treeInputPath())
    application.processEvents()
    canvas = view._canvas.viewport()
    clickPoint = QPoint(canvas.width() - 40, canvas.height() - 40)

    QTest.mouseClick(canvas, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, clickPoint)
    application.processEvents()
    popup = view._canvasPopupView
    assert popup.isVisible()
    assert popup._deleteButton.isEnabled()

    popup._deleteButton.click()
    application.processEvents()

    assert model.sourceText == ""
    assert model.nodes == ()
    assert model.currentStep == 0
    assert model.totalSteps == 0
    assert model.isPlaying is False
    assert not view._playbackFrame.isVisible()
    assert not popup.isVisible()
    assert len(view._renderer._promptItems) == 2
