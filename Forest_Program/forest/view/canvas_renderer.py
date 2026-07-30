"""Modelの状態をQt Graphics Sceneへ差分反映する。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from PySide6.QtCore import QLineF, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsPathItem, QGraphicsScene, QGraphicsSimpleTextItem

from forest.layout import GraphTraversal
from forest.model import NodeEditorState
from forest.shared import Constants, Desktop, Point
from forest.tree import BaseNode, Leaf, Root
from forest.view.theme import ViewTheme


class CanvasViewState(Protocol):
    @property
    def nodes(self) -> tuple[BaseNode, ...]: ...

    @property
    def desktop(self) -> Desktop: ...

    @property
    def nodeEditorState(self) -> NodeEditorState | None: ...


class NodeGraphicsItem(QGraphicsPathItem):
    """1ノードの背景、枠線、文字列を一体として保持するGraphics Item。"""

    def __init__(self, node: BaseNode) -> None:
        super().__init__()
        self.node = node
        self._label = QGraphicsSimpleTextItem(self)
        font = QFont(Constants.FONT_FAMILY)
        font.setPixelSize(Constants.FONT_SIZE)
        self._label.setFont(font)
        self._label.setBrush(QBrush(QColor(ViewTheme.TEXT_COLOR)))
        self.setZValue(1.0)

    def updateFromNode(self, isSelected: bool) -> None:
        bbox = self.node.bbox
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(0.0, 0.0, bbox.width, bbox.height),
            ViewTheme.NODE_CORNER_RADIUS,
            ViewTheme.NODE_CORNER_RADIUS,
        )
        fill, outline = CanvasRenderer.nodeColors(self.node, isSelected)
        self.setPath(path)
        self.setBrush(QBrush(QColor(fill)))
        self.setPen(QPen(QColor(outline), 1.0))
        self.setPos(bbox.x, bbox.y)
        self._label.setText(self.node.text)
        labelBounds = self._label.boundingRect()
        self._label.setPos(
            (bbox.width - labelBounds.width()) / 2,
            (bbox.height - labelBounds.height()) / 2,
        )


class CanvasRenderer:
    """QGraphicsSceneの要素をModelのノードと一対一に同期する。"""

    def __init__(self, scene: QGraphicsScene, model: CanvasViewState, view: object | None = None) -> None:
        self._scene = scene
        self._model = model
        self._view = view
        self._graphTraversal = GraphTraversal()
        self._nodeItems: dict[BaseNode, NodeGraphicsItem] = {}
        self._edgeItems: dict[tuple[BaseNode, BaseNode], QGraphicsLineItem] = {}
        self._promptItems: list[QGraphicsSimpleTextItem] = []

    @property
    def nodeItems(self) -> dict[BaseNode, NodeGraphicsItem]:
        return dict(self._nodeItems)

    @property
    def edgeItems(self) -> dict[tuple[BaseNode, BaseNode], QGraphicsLineItem]:
        return dict(self._edgeItems)

    def render(self, width: int, height: int) -> None:
        nodes = self._allNodes()
        self._syncNodeSet(nodes)
        self._syncEdgeSet(nodes)
        self._syncItems()
        self._syncPrompt(width, height, bool(nodes))
        self.syncViewport(width, height)

    def syncLayout(self, width: int, height: int) -> bool:
        nodes = self._allNodes()
        existingNodes = set(self._nodeItems)
        edges = set(self._graphTraversal.allEdges(nodes))
        reused = set(nodes) == existingNodes and edges == set(self._edgeItems)
        if not reused:
            self.render(width, height)
            return False
        self._syncItems()
        return True

    def syncViewport(self, width: int, height: int) -> bool:
        desktop = self._model.desktop
        origin = desktop.windowCanvasBBox
        transform = QTransform(
            desktop.zoomScale,
            0.0,
            0.0,
            desktop.zoomScale,
            -origin.x * desktop.zoomScale,
            -origin.y * desktop.zoomScale,
        )
        setTransform = getattr(self._view, "setTransform", None)
        if callable(setTransform):
            setTransform(transform)
        self._scene.setSceneRect(self._sceneBounds(width, height))
        if not self._nodeItems:
            self._syncPrompt(width, height, False)
        return True

    def nodeAt(self, viewPoint: Point) -> BaseNode | None:
        canvasPoint = self._model.desktop.viewToCanvas(viewPoint)
        for node in reversed(self._allNodes()):
            bbox = node.bbox
            if bbox.x <= canvasPoint.x <= bbox.x + bbox.width and bbox.y <= canvasPoint.y <= bbox.y + bbox.height:
                return node
        return None

    def _allNodes(self) -> list[BaseNode]:
        nodes: list[BaseNode] = []
        seen: set[int] = set()
        for root in self._model.nodes:
            for node in self._graphTraversal.reachableFrom(root):
                if id(node) not in seen:
                    seen.add(id(node))
                    nodes.append(node)
        return nodes

    def _syncNodeSet(self, nodes: Iterable[BaseNode]) -> None:
        nextNodes = set(nodes)
        for node in set(self._nodeItems) - nextNodes:
            self._scene.removeItem(self._nodeItems.pop(node))
        for node in nextNodes - set(self._nodeItems):
            item = NodeGraphicsItem(node)
            self._nodeItems[node] = item
            self._scene.addItem(item)

    def _syncEdgeSet(self, nodes: Iterable[BaseNode]) -> None:
        nextEdges = set(self._graphTraversal.allEdges(nodes))
        for edge in set(self._edgeItems) - nextEdges:
            self._scene.removeItem(self._edgeItems.pop(edge))
        for edge in nextEdges - set(self._edgeItems):
            item = QGraphicsLineItem()
            item.setPen(QPen(QColor(ViewTheme.EDGE_COLOR), 1.0))
            item.setZValue(0.0)
            self._edgeItems[edge] = item
            self._scene.addItem(item)

    def _syncItems(self) -> None:
        selected = self._model.nodeEditorState.selectedNode if self._model.nodeEditorState else None
        for node, item in self._nodeItems.items():
            item.updateFromNode(node is selected)
        for (parent, child), item in self._edgeItems.items():
            item.setLine(
                QLineF(
                    parent.bbox.x + parent.bbox.width,
                    parent.bbox.y + parent.bbox.height / 2,
                    child.bbox.x,
                    child.bbox.y + child.bbox.height / 2,
                )
            )

    def _syncPrompt(self, width: int, height: int, hasNodes: bool) -> None:
        for item in self._promptItems:
            self._scene.removeItem(item)
        self._promptItems.clear()
        if hasNodes:
            return
        desktop = self._model.desktop
        center = desktop.viewToCanvas(Point(width / 2, height / 2))
        for text, yOffset, size, color in (
            ("ファイルをドロップ", -14, 17, ViewTheme.TEXT_COLOR),
            ("またはクリックして開く", 18, 12, ViewTheme.SECONDARY_TEXT_COLOR),
        ):
            item = QGraphicsSimpleTextItem(text)
            font = QFont(Constants.FONT_FAMILY)
            font.setPixelSize(size)
            font.setBold(size == 17)
            item.setFont(font)
            item.setBrush(QBrush(QColor(color)))
            item.setFlag(QGraphicsSimpleTextItem.GraphicsItemFlag.ItemIgnoresTransformations)
            bounds = item.boundingRect()
            item.setPos(center.x - bounds.width() / 2, center.y + yOffset - bounds.height() / 2)
            self._scene.addItem(item)
            self._promptItems.append(item)

    def _sceneBounds(self, width: int, height: int) -> QRectF:
        desktop = self._model.desktop
        viewport = desktop.windowCanvasBBox
        nodes = self._allNodes()
        if not nodes:
            return QRectF(viewport.x, viewport.y, max(1.0, viewport.width), max(1.0, viewport.height))
        canvasMargin = Constants.CANVAS_VIEWPORT_MARGIN / desktop.zoomScale
        minimumX = min(0.0, *(node.bbox.x - canvasMargin for node in nodes))
        minimumY = min(0.0, *(node.bbox.y - canvasMargin for node in nodes))
        maximumX = max(
            width / desktop.zoomScale,
            *(node.bbox.x + node.bbox.width + canvasMargin for node in nodes),
        )
        maximumY = max(
            height / desktop.zoomScale,
            *(node.bbox.y + node.bbox.height + canvasMargin for node in nodes),
        )
        return QRectF(minimumX, minimumY, maximumX - minimumX, maximumY - minimumY)

    @staticmethod
    def nodeColors(node: BaseNode, isSelected: bool) -> tuple[str, str]:
        if isSelected:
            if isinstance(node, Root):
                return ViewTheme.ROOT_SELECTED_FILL_COLOR, ViewTheme.ROOT_SELECTED_BORDER_COLOR
            if isinstance(node, Leaf):
                return ViewTheme.LEAF_SELECTED_FILL_COLOR, ViewTheme.LEAF_SELECTED_BORDER_COLOR
            return ViewTheme.NODE_SELECTED_FILL_COLOR, ViewTheme.NODE_SELECTED_BORDER_COLOR
        if isinstance(node, Root):
            return ViewTheme.ROOT_FILL_COLOR, ViewTheme.ROOT_BORDER_COLOR
        if isinstance(node, Leaf):
            return ViewTheme.LEAF_FILL_COLOR, ViewTheme.LEAF_BORDER_COLOR
        return ViewTheme.NODE_FILL_COLOR, ViewTheme.NODE_BORDER_COLOR
