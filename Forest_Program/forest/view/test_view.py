from dataclasses import dataclass

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QGraphicsScene

from forest.model import NodeEditorState
from forest.shared import BBox, Constants, Desktop, Point
from forest.tree import BaseNode, Leaf, Node, Root
from forest.view import CanvasRenderer, ViewTheme, clampPopupPosition


@dataclass
class ViewStateFake:
    nodes: tuple[BaseNode, ...]
    desktop: Desktop
    nodeEditorState: NodeEditorState | None = None


class GraphicsViewFake:
    def __init__(self) -> None:
        self.transforms: list[QTransform] = []

    def setTransform(self, transform: QTransform) -> None:
        self.transforms.append(transform)


def buildRenderedState() -> tuple[ViewStateFake, Root, Node, Leaf]:
    root = Root("root", BBox(10.0, 20.0, 80.0, 30.0))
    node = Node("node", BBox(120.0, 20.0, 80.0, 30.0))
    leaf = Leaf("leaf", BBox(230.0, 20.0, 80.0, 30.0))
    root.addChild(node)
    node.addChild(leaf)
    return ViewStateFake((root,), Desktop(800.0, 600.0)), root, node, leaf


def testEmptySceneRendersFilePrompt() -> None:
    scene = QGraphicsScene()
    renderer = CanvasRenderer(scene, ViewStateFake((), Desktop(400.0, 300.0)))

    renderer.render(400, 300)

    assert sorted(item.text() for item in renderer._promptItems) == [
        "またはクリックして開く",
        "ファイルをドロップ",
    ]
    assert renderer.nodeItems == {}
    assert renderer.edgeItems == {}


def testEmptyPromptRecentersAfterViewportResize() -> None:
    state = ViewStateFake((), Desktop(100.0, 50.0))
    renderer = CanvasRenderer(QGraphicsScene(), state)
    renderer.render(100, 50)
    initialPositions = [item.pos() for item in renderer._promptItems]

    state.desktop.resize(800.0, 600.0)
    renderer.syncViewport(800, 600)

    assert all(
        item.pos().x() > initial.x() for item, initial in zip(renderer._promptItems, initialPositions, strict=True)
    )
    assert all(
        item.pos().y() > initial.y() for item, initial in zip(renderer._promptItems, initialPositions, strict=True)
    )


def testTreeRenderCreatesOneGraphicsItemPerNodeAndEdge() -> None:
    state, root, node, leaf = buildRenderedState()
    renderer = CanvasRenderer(QGraphicsScene(), state)

    renderer.render(800, 600)

    assert set(renderer.nodeItems) == {root, node, leaf}
    assert set(renderer.edgeItems) == {(root, node), (node, leaf)}
    assert renderer.nodeItems[root].brush().color().name() == ViewTheme.ROOT_FILL_COLOR.lower()
    assert renderer.nodeItems[node].brush().color().name() == ViewTheme.NODE_FILL_COLOR.lower()
    assert renderer.nodeItems[leaf].brush().color().name() == ViewTheme.LEAF_FILL_COLOR.lower()
    assert renderer.nodeItems[root]._label.font().family() == Constants.FONT_FAMILY
    assert renderer.nodeItems[root]._label.font().pixelSize() == Constants.FONT_SIZE


@pytest.mark.parametrize(
    ("selectedIndex", "expectedFill", "expectedBorder"),
    [
        (0, Constants.ROOT_SELECTED_FILL_COLOR, Constants.ROOT_SELECTED_BORDER_COLOR),
        (1, Constants.NODE_SELECTED_FILL_COLOR, Constants.NODE_SELECTED_BORDER_COLOR),
        (2, Constants.LEAF_SELECTED_FILL_COLOR, Constants.LEAF_SELECTED_BORDER_COLOR),
    ],
)
def testSelectedNodeUsesDarkerColorsForItsOriginalType(
    selectedIndex: int,
    expectedFill: str,
    expectedBorder: str,
) -> None:
    state, root, node, leaf = buildRenderedState()
    selectedNode = (root, node, leaf)[selectedIndex]
    editorState = NodeEditorState()
    editorState.begin(selectedNode, BBox(0.0, 0.0, 1.0, 1.0))
    state.nodeEditorState = editorState
    renderer = CanvasRenderer(QGraphicsScene(), state)

    renderer.render(800, 600)

    item = renderer.nodeItems[selectedNode]
    assert item.brush().color().name() == expectedFill.lower()
    assert item.pen().color().name() == expectedBorder.lower()


def testLayoutChangeReusesItemsAndUpdatesNodeAndEdgeGeometry() -> None:
    state, root, node, _ = buildRenderedState()
    renderer = CanvasRenderer(QGraphicsScene(), state)
    renderer.render(800, 600)
    rootItem = renderer.nodeItems[root]
    edgeItem = renderer.edgeItems[(root, node)]

    root.bbox = BBox(30.0, 45.0, 80.0, 30.0)
    reused = renderer.syncLayout(800, 600)

    assert reused is True
    assert renderer.nodeItems[root] is rootItem
    assert renderer.edgeItems[(root, node)] is edgeItem
    assert rootItem.pos() == QPointF(30.0, 45.0)
    assert edgeItem.line().p1() == QPointF(110.0, 60.0)
    assert edgeItem.line().p2() == QPointF(120.0, 35.0)


def testStructureChangeFallsBackAndAddsNewItems() -> None:
    state, _, node, _ = buildRenderedState()
    renderer = CanvasRenderer(QGraphicsScene(), state)
    renderer.render(800, 600)
    added = Leaf("added", BBox(340.0, 20.0, 80.0, 30.0))
    node.addChild(added)

    reused = renderer.syncLayout(800, 600)

    assert reused is False
    assert added in renderer.nodeItems
    assert (node, added) in renderer.edgeItems


def testViewportTransformUsesModelPanAndZoom() -> None:
    state, _, _, _ = buildRenderedState()
    view = GraphicsViewFake()
    renderer = CanvasRenderer(QGraphicsScene(), state, view)
    renderer.render(800, 600)

    state.desktop.zoomAt(Point(0.0, 0.0), 2.0)
    state.desktop.pan(-20.0, -10.0)
    renderer.syncViewport(800, 600)

    transform = view.transforms[-1]
    assert transform.m11() == 2.0
    assert transform.m22() == 2.0
    assert transform.dx() == -20.0
    assert transform.dy() == -10.0


@pytest.mark.parametrize(
    ("point", "expectedText"),
    [
        (Point(10.0, 20.0), "root"),
        (Point(160.0, 35.0), "node"),
        (Point(310.0, 50.0), "leaf"),
    ],
)
def testNodeAtIncludesBBoxBoundaries(point: Point, expectedText: str) -> None:
    state, _, _, _ = buildRenderedState()
    node = CanvasRenderer(QGraphicsScene(), state).nodeAt(point)
    assert node is not None
    assert node.text == expectedText


def testNodeAtAccountsForPanAndZoom() -> None:
    state, root, _, _ = buildRenderedState()
    state.desktop.zoomAt(Point(0.0, 0.0), 2.0)
    state.desktop.pan(-20.0, -10.0)
    viewPoint = state.desktop.canvasToView(Point(root.bbox.x + 1.0, root.bbox.y + 1.0))

    assert CanvasRenderer(QGraphicsScene(), state).nodeAt(viewPoint) is root


def testNodeAtReturnsNoneOutsideNodes() -> None:
    state, _, _, _ = buildRenderedState()
    assert CanvasRenderer(QGraphicsScene(), state).nodeAt(Point(500.0, 500.0)) is None


@pytest.mark.parametrize(
    ("position", "expected"),
    [
        ((-20.0, -10.0), (10, 10)),
        ((100.0, 80.0), (100, 80)),
        ((900.0, 700.0), (544, 436)),
    ],
)
def testPopupPositionIsClamped(position: tuple[float, float], expected: tuple[int, int]) -> None:
    assert clampPopupPosition(*position, 246, 154, 800, 600) == expected


def testViewThemeCannotBeInstantiated() -> None:
    with pytest.raises(TypeError):
        ViewTheme()
