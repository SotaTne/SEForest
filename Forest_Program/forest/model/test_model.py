from pathlib import Path

import pytest

from forest.controller import ModelCommandPort
from forest.image_output import ImageRenderer
from forest.layout import BBoxCalculator, LayoutCalculator
from forest.model import Model, ModelEvent
from forest.parser import ParseError, Parser
from forest.shared import BBox, Constants, Desktop, LayoutStep, Point
from forest.tree import BaseNode, Leaf, Root


class ParserFake(Parser):
    def __init__(self, nodes: list[BaseNode] | None = None, error: Exception | None = None) -> None:
        self.nodes = nodes or []
        self.error = error
        self.sources: list[str] = []

    def parse(self, sourceText: str) -> list[BaseNode]:
        self.sources.append(sourceText)
        if self.error is not None:
            raise self.error
        return self.nodes


class LayoutCalculatorFake(LayoutCalculator):
    def __init__(
        self,
        initialSteps: list[LayoutStep] | None = None,
        recalculatedSteps: list[LayoutStep] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.initialSteps = initialSteps or []
        self.recalculatedSteps = recalculatedSteps or []
        self.error = error
        self.initialCalls: list[tuple[list[BaseNode], object]] = []
        self.recalculateCalls: list[tuple[list[BaseNode], BaseNode]] = []

    def createInitialSteps(self, nodes: list[BaseNode], desktop: object) -> list[LayoutStep]:
        self.initialCalls.append((nodes, desktop))
        return self.initialSteps

    def recalculate(self, nodes: list[BaseNode], changedNode: BaseNode) -> list[LayoutStep]:
        self.recalculateCalls.append((nodes, changedNode))
        if self.error is not None:
            raise self.error
        return self.recalculatedSteps


class ImageRendererFake(ImageRenderer):
    def __init__(self) -> None:
        self.canvasCalls: list[tuple[list[BaseNode], Path]] = []
        self.subgraphCalls: list[tuple[BaseNode, Path]] = []

    def renderCanvas(self, nodes: list[BaseNode], outputPath: Path) -> None:
        self.canvasCalls.append((nodes, outputPath))

    def renderSubgraph(self, start: BaseNode, outputPath: Path) -> None:
        self.subgraphCalls.append((start, outputPath))


def buildModel(
    root: Root | None = None,
    *,
    layoutCalculator: LayoutCalculatorFake | None = None,
    parser: ParserFake | None = None,
    imageRenderer: ImageRendererFake | None = None,
) -> tuple[Model, Root, LayoutCalculatorFake, ParserFake, ImageRendererFake]:
    resolvedRoot = root or Root("root")
    steps = [
        LayoutStep(0, {resolvedRoot: BBox(1.0, 2.0, 30.0, 20.0)}),
        LayoutStep(1, {resolvedRoot: BBox(10.0, 20.0, 30.0, 20.0)}),
    ]
    resolvedLayout = layoutCalculator or LayoutCalculatorFake(steps, [steps[-1]])
    resolvedParser = parser or ParserFake([resolvedRoot])
    resolvedRenderer = imageRenderer or ImageRendererFake()
    model = Model(
        Desktop(800.0, 600.0),
        resolvedParser,
        resolvedLayout,
        BBoxCalculator(),
        resolvedRenderer,
    )
    return model, resolvedRoot, resolvedLayout, resolvedParser, resolvedRenderer


def recordEvents(model: Model) -> list[ModelEvent]:
    received: list[ModelEvent] = []
    for event in ModelEvent:
        model.events.subscribe(event, lambda event=event: received.append(event))
    return received


def testModelExplicitlyImplementsCommandPort() -> None:
    assert ModelCommandPort in Model.__mro__


def testLoadTextReplacesStateAppliesFirstStepAndNotifiesViews() -> None:
    model, root, layout, parser, _ = buildModel()
    events = recordEvents(model)

    model.loadText("trees:\nroot")

    assert parser.sources == ["trees:\nroot"]
    assert layout.initialCalls == [([root], model.desktop)]
    assert model.sourceText == "trees:\nroot"
    assert model.nodes == (root,)
    assert model.currentStep == 0
    assert model.totalSteps == 2
    assert root.bbox == BBox(1.0, 2.0, 30.0, 20.0)
    assert model.canvasBBox == root.bbox
    assert events == [
        ModelEvent.LAYOUT_CHANGED,
        ModelEvent.NODES_CHANGED,
        ModelEvent.SELECTION_CHANGED,
        ModelEvent.PLAYBACK_CHANGED,
    ]


def testLoadFileReadsUtf8(tmp_path: Path) -> None:
    model, _, _, parser, _ = buildModel()
    inputPath = tmp_path / "forest.txt"
    inputPath.write_text("日本語の木", encoding="utf-8")

    model.loadFile(inputPath)

    assert parser.sources == ["日本語の木"]


def testClearTreeReturnsEveryLoadedStateToFileSelection() -> None:
    model, root, _, _, _ = buildModel()
    model.loadText("trees:\nroot")
    model.selectNode(root, BBox(1.0, 2.0, 246.0, 154.0))
    model.setPlaying(True)
    events = recordEvents(model)

    model.clearTree()

    assert model.sourceText == ""
    assert model.nodes == ()
    assert model.canvasBBox == BBox(0.0, 0.0, 0.0, 0.0)
    assert model.outputFile is None
    assert model.nodeEditorState is None
    assert model.currentStep == 0
    assert model.totalSteps == 0
    assert model.layoutSteps == ()
    assert model.isPlaying is False
    assert model.desktop.zoomScale == 1.0
    assert events == [
        ModelEvent.NODES_CHANGED,
        ModelEvent.SELECTION_CHANGED,
        ModelEvent.EDITOR_CHANGED,
        ModelEvent.PLAYBACK_CHANGED,
        ModelEvent.DESKTOP_CHANGED,
    ]


def testClearTreeIsIdempotentBeforeFileSelection() -> None:
    model, _, _, _, _ = buildModel()
    events = recordEvents(model)

    model.clearTree()

    assert events == []


def testFailedParsePreservesExistingState() -> None:
    parser = ParserFake(error=ParseError("invalid"))
    model, _, _, _, _ = buildModel(parser=parser)

    with pytest.raises(ParseError):
        model.loadText("invalid")

    assert model.sourceText == ""
    assert model.nodes == ()
    assert model.totalSteps == 0


def testEmptyLoadClearsLayoutAndCanvas() -> None:
    model, _, layout, parser, _ = buildModel()
    model.loadText("source")
    parser.nodes = []
    layout.initialSteps = []

    model.loadText("")

    assert model.nodes == ()
    assert model.layoutSteps == ()
    assert model.totalSteps == 0
    assert model.canvasBBox == BBox(0.0, 0.0, 0.0, 0.0)


def testShowStepAndBoundaryNavigation() -> None:
    model, root, _, _, _ = buildModel()
    model.loadText("source")
    events = recordEvents(model)

    model.showPreviousStep()
    assert events == []
    model.showNextStep()
    assert model.currentStep == 1
    assert root.bbox == BBox(10.0, 20.0, 30.0, 20.0)
    model.showNextStep()
    assert model.currentStep == 1
    model.showPreviousStep()
    assert model.currentStep == 0


def testPlayingFromLastStepRestartsExistingLayoutWithoutParsingAgain() -> None:
    model, root, _, parser, _ = buildModel()
    model.loadText("source")
    model.showStep(model.totalSteps - 1)

    model.setPlaying(True)

    assert model.isPlaying is True
    assert model.currentStep == 0
    assert root.bbox == BBox(1.0, 2.0, 30.0, 20.0)
    assert parser.sources == ["source"]


def testPlayingSingleStepTreeRebuildsAnimationSteps() -> None:
    root = Root("Root")
    initialStep = LayoutStep(0, {root: BBox(1.0, 2.0, 30.0, 20.0)})
    rebuiltSteps = [
        LayoutStep(0, {root: BBox(3.0, 4.0, 30.0, 20.0)}),
        LayoutStep(1, {root: BBox(5.0, 6.0, 30.0, 20.0)}),
    ]
    layout = LayoutCalculatorFake(initialSteps=[initialStep])
    model = Model(parser=ParserFake([root]), layoutCalculator=layout)
    model.loadText("source")
    layout.initialSteps = rebuiltSteps

    model.setPlaying(True)

    assert model.isPlaying is True
    assert model.totalSteps == 2
    assert model.currentStep == 0
    assert root.bbox == rebuiltSteps[0].positions[root]


def testPlayingFromMiddleKeepsCurrentStep() -> None:
    root = Root("root")
    steps = [
        LayoutStep(0, {root: BBox(1.0, 2.0, 30.0, 20.0)}),
        LayoutStep(1, {root: BBox(5.0, 6.0, 30.0, 20.0)}),
        LayoutStep(2, {root: BBox(10.0, 20.0, 30.0, 20.0)}),
    ]
    model, _, _, _, _ = buildModel(
        root,
        layoutCalculator=LayoutCalculatorFake(steps, steps),
    )
    model.loadText("source")
    model.showStep(1)

    model.setPlaying(True)

    assert model.isPlaying is True
    assert model.currentStep == 1
    assert root.bbox == BBox(5.0, 6.0, 30.0, 20.0)


def testRestartingPlaybackKeepsRenamedNodeText() -> None:
    model, root, layout, parser, _ = buildModel()
    model.loadText("source")
    model.selectNode(root, BBox(1.0, 2.0, 3.0, 4.0))
    model.renameSelectedNode("renamed")

    model.setPlaying(True)

    assert root.text == "renamed"
    assert model.nodes[0].text == "renamed"
    assert parser.sources == ["source"]
    assert len(layout.initialCalls) == 2
    assert model.totalSteps == 2
    assert model.currentStep == 0


@pytest.mark.parametrize("index", [-1, 2])
def testShowStepRejectsOutOfRangeIndex(index: int) -> None:
    model, _, _, _, _ = buildModel()
    model.loadText("source")
    with pytest.raises(IndexError):
        model.showStep(index)


def testModelRejectsInvalidInputTypes() -> None:
    model, root, _, _, _ = buildModel()
    model.loadText("source")

    with pytest.raises(TypeError):
        model.loadFile("forest.txt")  # ty: ignore[invalid-argument-type]
    with pytest.raises(TypeError):
        model.loadText(None)  # ty: ignore[invalid-argument-type]
    with pytest.raises(TypeError):
        model.selectNode(root, "bbox")  # ty: ignore[invalid-argument-type]
    with pytest.raises(TypeError):
        model.showStep(1.0)  # ty: ignore[invalid-argument-type]
    with pytest.raises(TypeError):
        model.setPlaying(1)  # ty: ignore[invalid-argument-type]
    with pytest.raises(TypeError):
        model.exportCanvas("canvas.png")  # ty: ignore[invalid-argument-type]


def testSelectionRenameRecalculatesAndClearsEditor() -> None:
    model, root, layout, _, _ = buildModel()
    model.loadText("source")
    events = recordEvents(model)
    popupBBox = BBox(5.0, 6.0, 7.0, 8.0)

    model.selectNode(root, popupBBox)
    assert model.nodeEditorState is not None
    assert model.nodeEditorState.selectedNode is root
    model.renameSelectedNode("renamed")

    assert root.text == "renamed"
    assert layout.recalculateCalls == [([root], root)]
    assert model.nodeEditorState is None
    assert events == [
        ModelEvent.SELECTION_CHANGED,
        ModelEvent.EDITOR_CHANGED,
        ModelEvent.LAYOUT_CHANGED,
        ModelEvent.NODES_CHANGED,
        ModelEvent.SELECTION_CHANGED,
        ModelEvent.EDITOR_CHANGED,
    ]


def testFailedRecalculationRestoresNodeNameAndSelection() -> None:
    root = Root("before")
    layout = LayoutCalculatorFake(
        [LayoutStep(0, {root: BBox(0.0, 0.0, 20.0, 20.0)})],
        error=RuntimeError("layout failed"),
    )
    model, _, _, _, _ = buildModel(root, layoutCalculator=layout)
    model.loadText("source")
    model.selectNode(root, BBox(0.0, 0.0, 1.0, 1.0))

    with pytest.raises(RuntimeError, match="layout failed"):
        model.renameSelectedNode("after")

    assert root.text == "before"
    assert model.nodeEditorState is not None
    assert model.nodeEditorState.selectedNode is root


def testSelectionRejectsForeignNodeAndRenameRequiresSelection() -> None:
    model, _, _, _, _ = buildModel()
    model.loadText("source")
    with pytest.raises(ValueError):
        model.selectNode(Leaf("foreign"), BBox(0.0, 0.0, 1.0, 1.0))
    with pytest.raises(RuntimeError):
        model.renameSelectedNode("name")


def testClearSelectionIsIdempotent() -> None:
    model, root, _, _, _ = buildModel()
    model.loadText("source")
    events = recordEvents(model)
    model.clearSelection()
    assert events == []
    model.selectNode(root, BBox(0.0, 0.0, 1.0, 1.0))
    model.clearSelection()
    assert model.nodeEditorState is None


def testPlayingOnlyNotifiesWhenValueChanges() -> None:
    model, _, _, _, _ = buildModel()
    events = recordEvents(model)

    model.setPlaying(True)
    model.setPlaying(True)
    model.setPlaying(False)

    assert events == [ModelEvent.PLAYBACK_CHANGED, ModelEvent.PLAYBACK_CHANGED]


def testExportOperationsDelegateAndRememberSuccessfulPath(tmp_path: Path) -> None:
    model, root, _, _, renderer = buildModel()
    model.loadText("source")
    canvasPath = tmp_path / "canvas.png"
    subgraphPath = tmp_path / "subgraph.png"

    model.exportCanvas(canvasPath)
    assert renderer.canvasCalls == [([root], canvasPath)]
    assert model.outputFile == canvasPath
    model.selectNode(root, BBox(0.0, 0.0, 1.0, 1.0))
    model.exportSelectedSubgraph(subgraphPath)
    assert renderer.subgraphCalls == [(root, subgraphPath)]
    assert model.outputFile == subgraphPath


def testSubgraphExportRequiresSelection(tmp_path: Path) -> None:
    model, _, _, _, _ = buildModel()
    with pytest.raises(RuntimeError):
        model.exportSelectedSubgraph(tmp_path / "subgraph.png")


def testDesktopChangesNotifySubscribedViews() -> None:
    model, _, _, _, _ = buildModel()
    firstViewCalls: list[str] = []
    secondViewCalls: list[str] = []
    model.events.subscribe(ModelEvent.DESKTOP_CHANGED, lambda: firstViewCalls.append("render"))
    model.events.subscribe(ModelEvent.DESKTOP_CHANGED, lambda: secondViewCalls.append("render"))

    model.resizeDesktop(640.0, 480.0)
    model.panDesktop(10.0, 20.0)
    model.zoomDesktopAt(Point(100.0, 100.0), 2.0)
    model.resetDesktopViewport()

    assert firstViewCalls == ["render", "render", "render"]
    assert secondViewCalls == ["render", "render", "render"]
    assert model.desktop.windowSizeBBox == BBox(0.0, 0.0, 640.0, 480.0)
    assert model.desktop.windowCanvasBBox == BBox(0.0, 0.0, 640.0, 480.0)
    assert model.desktop.zoomScale == 1.0


def testPanDesktopIsClampedToHundredPixelCanvasMargin() -> None:
    root = Root("root")
    largeBBox = BBox(0.0, 0.0, 300.0, 250.0)
    layout = LayoutCalculatorFake([LayoutStep(0, {root: largeBBox})])
    model, _, _, _, _ = buildModel(root, layoutCalculator=layout)
    model.resizeDesktop(100.0, 100.0)
    model.loadText("trees:\nroot")

    model.panDesktop(-1000.0, -1000.0)
    assert model.desktop.windowCanvasBBox == BBox(300.0, 250.0, 100.0, 100.0)

    model.panDesktop(1000.0, 1000.0)
    assert model.desktop.windowCanvasBBox == BBox(-100.0, -100.0, 100.0, 100.0)


def testPanDesktopDoesNotNotifyWhenAlreadyAtCanvasBoundary() -> None:
    model, _, _, _, _ = buildModel()
    model.loadText("trees:\nroot")
    model.resizeDesktop(100.0, 100.0)
    model.panDesktop(1000.0, 1000.0)
    events = recordEvents(model)

    model.panDesktop(10.0, 10.0)

    assert model.desktop.windowCanvasBBox == BBox(-99.0, -98.0, 100.0, 100.0)
    assert events == []


def testCanvasMarginRemainsHundredViewPixelsAtZoom() -> None:
    root = Root("root")
    largeBBox = BBox(0.0, 0.0, 300.0, 250.0)
    layout = LayoutCalculatorFake([LayoutStep(0, {root: largeBBox})])
    model, _, _, _, _ = buildModel(root, layoutCalculator=layout)
    model.resizeDesktop(100.0, 100.0)
    model.loadText("trees:\nroot")
    model.zoomDesktopAt(Point(0.0, 0.0), 2.0)

    model.panDesktop(1000.0, 1000.0)

    viewport = model.desktop.windowCanvasBBox
    assert viewport.x == -50.0
    assert viewport.y == -50.0
    assert abs(viewport.x * model.desktop.zoomScale) == Constants.CANVAS_VIEWPORT_MARGIN
    assert abs(viewport.y * model.desktop.zoomScale) == Constants.CANVAS_VIEWPORT_MARGIN


def testZoomedOutCanvasCanScrollBetweenBothHorizontalMargins() -> None:
    root = Root("root")
    canvasBBox = BBox(0.0, 0.0, 100.0, 80.0)
    layout = LayoutCalculatorFake([LayoutStep(0, {root: canvasBBox})])
    model, _, _, _, _ = buildModel(root, layoutCalculator=layout)
    model.resizeDesktop(400.0, 300.0)
    model.loadText("trees:\nroot")
    model.zoomDesktopAt(Point(200.0, 150.0), Constants.MIN_ZOOM_SCALE)

    model.panDesktop(10_000.0, 0.0)
    rightmostOrigin = model.desktop.windowCanvasBBox.x
    nodeRightInView = (canvasBBox.x + canvasBBox.width - rightmostOrigin) * model.desktop.zoomScale
    assert nodeRightInView == 400.0 - Constants.CANVAS_VIEWPORT_MARGIN

    model.panDesktop(-10_000.0, 0.0)
    leftmostOrigin = model.desktop.windowCanvasBBox.x
    nodeLeftInView = (canvasBBox.x - leftmostOrigin) * model.desktop.zoomScale
    assert nodeLeftInView == Constants.CANVAS_VIEWPORT_MARGIN
    assert leftmostOrigin > rightmostOrigin


def testPanDesktopWithoutNodesIsIgnored() -> None:
    model, _, _, _, _ = buildModel()
    events = recordEvents(model)

    model.panDesktop(-20.0, -20.0)

    assert model.desktop.windowCanvasBBox == BBox(0.0, 0.0, 800.0, 600.0)
    assert events == []


def testInvalidDesktopChangeDoesNotNotifyViews() -> None:
    model, _, _, _, _ = buildModel()
    events = recordEvents(model)

    with pytest.raises(ValueError):
        model.resizeDesktop(-1.0, 100.0)
    with pytest.raises(ValueError):
        model.zoomDesktopAt(Point(0.0, 0.0), 0.0)
    with pytest.raises(TypeError):
        model.zoomDesktopAt("anchor", 2.0)  # ty: ignore[invalid-argument-type]

    assert events == []


def testModelExposesImmutableCollectionViews() -> None:
    model, _, _, _, _ = buildModel()
    model.loadText("source")

    assert isinstance(model.nodes, tuple)
    assert isinstance(model.layoutSteps, tuple)
