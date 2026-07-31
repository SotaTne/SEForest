from pathlib import Path
from typing import Any

import pytest

from forest.controller import Controller
from forest.shared import BBox, Constants, Point
from forest.tree import BaseNode, Leaf


class CommandRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.error: Exception | None = None

    def _record(self, name: str, *arguments: Any) -> None:
        if self.error is not None:
            raise self.error
        self.calls.append((name, arguments))

    def loadFile(self, inputPath: Path) -> None:
        self._record("loadFile", inputPath)

    def selectNode(self, node: BaseNode, popupBBox: BBox) -> None:
        self._record("selectNode", node, popupBBox)

    def clearSelection(self) -> None:
        self._record("clearSelection")

    def clearTree(self) -> None:
        self._record("clearTree")

    def renameSelectedNode(self, text: str) -> None:
        self._record("renameSelectedNode", text)

    def showStep(self, index: int) -> None:
        self._record("showStep", index)

    def showPreviousStep(self) -> None:
        self._record("showPreviousStep")

    def showNextStep(self) -> None:
        self._record("showNextStep")

    def setPlaying(self, isPlaying: bool) -> None:
        self._record("setPlaying", isPlaying)

    def exportCanvas(self, outputPath: Path) -> None:
        self._record("exportCanvas", outputPath)

    def exportSelectedSubgraph(self, outputPath: Path) -> None:
        self._record("exportSelectedSubgraph", outputPath)

    def resizeDesktop(self, width: float, height: float) -> None:
        self._record("resizeDesktop", width, height)

    def panDesktop(self, dx: float, dy: float) -> None:
        self._record("panDesktop", dx, dy)

    def zoomDesktopAt(self, anchor: Point, scaleDelta: float) -> None:
        self._record("zoomDesktopAt", anchor, scaleDelta)

    def resetDesktopViewport(self) -> None:
        self._record("resetDesktopViewport")


@pytest.fixture
def controllerAndCommands() -> tuple[Controller, CommandRecorder]:
    commands = CommandRecorder()
    return Controller(commands), commands


def testFileOperationsForwardOnlyFirstValidDroppedPath(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands
    first = Path("first.txt")
    second = Path("second.txt")

    controller.openFile(first)
    controller.handleDrop([])
    controller.handleDrop([first, second])

    assert commands.calls == [
        ("loadFile", (first,)),
        ("loadFile", (first,)),
    ]


def testDropFiltersInvalidEntries(controllerAndCommands: tuple[Controller, CommandRecorder]) -> None:
    controller, commands = controllerAndCommands
    valid = Path("forest.txt")

    controller.handleDrop(["", valid])  # ty: ignore[invalid-argument-type]

    assert commands.calls == [("loadFile", (valid,))]


def testDropRejectsNonListInput(controllerAndCommands: tuple[Controller, CommandRecorder]) -> None:
    controller, commands = controllerAndCommands

    with pytest.raises(TypeError, match="paths must be a list"):
        controller.handleDrop((Path("forest.txt"),))  # ty: ignore[invalid-argument-type]

    assert commands.calls == []


def testPointerMovementBelowThresholdDoesNotPan(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands
    controller.handlePointerPress(Point(0.0, 0.0))
    controller.handlePointerMove(Point(Constants.DRAG_THRESHOLD - 0.01, 0.0))

    assert commands.calls == []
    assert controller.handlePointerRelease(Point(0.0, 0.0))


def testPointerMovementAtThresholdStartsDrag(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands
    controller.handlePointerPress(Point(10.0, 20.0))
    controller.handlePointerMove(Point(10.0 + Constants.DRAG_THRESHOLD, 20.0))

    assert commands.calls == [
        ("panDesktop", (Constants.DRAG_THRESHOLD, 0.0)),
    ]
    assert not controller.handlePointerRelease(Point(10.0 + Constants.DRAG_THRESHOLD, 20.0))


def testReleaseAtThresholdWithoutMoveIsNotClick(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands
    controller.handlePointerPress(Point(0.0, 0.0))

    assert not controller.handlePointerRelease(Point(Constants.DRAG_THRESHOLD, 0.0))
    assert commands.calls == []


def testDraggingForwardsIncrementalMovement(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands
    controller.handlePointerPress(Point(1.0, 2.0))
    controller.handlePointerMove(Point(6.0, 2.0))
    controller.handlePointerMove(Point(8.0, 5.0))

    assert commands.calls == [
        ("panDesktop", (5.0, 0.0)),
        ("panDesktop", (2.0, 3.0)),
    ]


def testMoveAndReleaseWithoutPressAreIgnored(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands

    controller.handlePointerMove(Point(1.0, 1.0))

    assert not controller.handlePointerRelease(Point(1.0, 1.0))
    assert commands.calls == []


def testPointerOperationsRejectInvalidPoint(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, _ = controllerAndCommands
    with pytest.raises(TypeError):
        controller.handlePointerPress("point")  # ty: ignore[invalid-argument-type]
    with pytest.raises(TypeError):
        controller.handlePointerMove("point")  # ty: ignore[invalid-argument-type]
    with pytest.raises(TypeError):
        controller.handlePointerRelease("point")  # ty: ignore[invalid-argument-type]


def testZeroWheelAndIdentityZoomAreIgnored(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands

    controller.handleWheel(0.0, 0.0)
    controller.handleZoom(Point(1.0, 2.0), 1.0)

    assert commands.calls == []


def testWheelAndZoomAreForwarded(controllerAndCommands: tuple[Controller, CommandRecorder]) -> None:
    controller, commands = controllerAndCommands
    anchor = Point(10.0, 20.0)

    controller.handleWheel(-2.0, 3.0)
    controller.handleZoom(anchor, 1.5)

    assert commands.calls == [
        ("panDesktop", (-2.0, 3.0)),
        ("zoomDesktopAt", (anchor, 1.5)),
    ]


def testSelectionAndRenameMessagesAreForwarded(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands
    node = Leaf("node")
    popupBBox = BBox(1.0, 2.0, 3.0, 4.0)

    controller.handleNodeClick(node, popupBBox)
    controller.confirmRename(" renamed ")
    controller.cancelPopup()
    controller.handleCanvasClick()

    assert commands.calls == [
        ("selectNode", (node, popupBBox)),
        ("renameSelectedNode", (" renamed ",)),
        ("clearSelection", ()),
        ("clearSelection", ()),
    ]


def testClearTreeMessageIsForwarded(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands

    controller.clearTree()

    assert commands.calls == [("clearTree", ())]


def testPlaybackMessagesDoNotReadModelState(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands

    controller.setPlaying(True)
    controller.showPreviousStep()
    controller.showNextStep()
    controller.seekStep(3)
    controller.setPlaying(False)

    assert commands.calls == [
        ("setPlaying", (True,)),
        ("showPreviousStep", ()),
        ("showNextStep", ()),
        ("showStep", (3,)),
        ("setPlaying", (False,)),
    ]


def testExportAndDesktopMessagesAreForwarded(
    controllerAndCommands: tuple[Controller, CommandRecorder],
) -> None:
    controller, commands = controllerAndCommands
    canvasPath = Path("canvas.png")
    subgraphPath = Path("subgraph.png")

    controller.exportCanvas(canvasPath)
    controller.exportSelectedSubgraph(subgraphPath)
    controller.resizeDesktop(800.0, 600.0)
    controller.resetDesktopViewport()

    assert commands.calls == [
        ("exportCanvas", (canvasPath,)),
        ("exportSelectedSubgraph", (subgraphPath,)),
        ("resizeDesktop", (800.0, 600.0)),
        ("resetDesktopViewport", ()),
    ]


def testCommandFailureIsPropagated(controllerAndCommands: tuple[Controller, CommandRecorder]) -> None:
    controller, commands = controllerAndCommands
    commands.error = RuntimeError("model failed")

    with pytest.raises(RuntimeError, match="model failed"):
        controller.openFile(Path("forest.txt"))

    assert commands.calls == []


def testControllerHasNoViewDependency(controllerAndCommands: tuple[Controller, CommandRecorder]) -> None:
    controller, commands = controllerAndCommands

    assert vars(controller) == {
        "_commands": commands,
        "_pressPoint": None,
        "_lastDragPoint": None,
        "_isDragging": False,
    }
