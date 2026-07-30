"""Render graph nodes and edges to a headless Pillow canvas."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PIL import Image, ImageDraw

from forest.layout import BBoxCalculator, GraphTraversal
from forest.shared import BBox, Constants
from forest.tree import BaseNode, Leaf, Root


class ImageRenderer:
    """Render the complete canvas or a selected subgraph as PNG."""

    def __init__(
        self,
        graphTraversal: GraphTraversal | None = None,
        bboxCalculator: BBoxCalculator | None = None,
    ) -> None:
        self._graphTraversal = graphTraversal or GraphTraversal()
        self._bboxCalculator = bboxCalculator or BBoxCalculator(self._graphTraversal)
        self._targetCanvas: Image.Image | None = None

    def renderCanvas(self, nodes: list[BaseNode], outputPath: Path) -> None:
        allNodes: list[BaseNode] = []
        seen: set[int] = set()
        for start in nodes:
            for node in self._graphTraversal.reachableFrom(start):
                if id(node) not in seen:
                    seen.add(id(node))
                    allNodes.append(node)
        bounds = self._bboxCalculator.forNodes(allNodes)
        self._render(allNodes, bounds, self._createTargetCanvas(bounds), outputPath)

    def renderSubgraph(self, start: BaseNode, outputPath: Path) -> None:
        nodes = self._graphTraversal.reachableFrom(start)
        bounds = self._bboxCalculator.forSubgraph(start)
        self._render(nodes, bounds, self._createTargetCanvas(bounds), outputPath)

    def _createTargetCanvas(self, bounds: BBox) -> Image.Image:
        width = max(1, int(round(bounds.width)) + Constants.IMAGE_PADDING * 2)
        height = max(1, int(round(bounds.height)) + Constants.IMAGE_PADDING * 2)
        self._targetCanvas = Image.new("RGB", (width, height), Constants.IMAGE_BACKGROUND_COLOR)
        return self._targetCanvas

    def _render(
        self,
        nodes: Iterable[BaseNode],
        bounds: BBox,
        targetCanvas: Image.Image,
        outputPath: Path,
    ) -> None:
        nodeList = list(nodes)
        draw = ImageDraw.Draw(targetCanvas)
        offsetX = Constants.IMAGE_PADDING - bounds.x
        offsetY = Constants.IMAGE_PADDING - bounds.y
        self._drawEdges(nodeList, draw, offsetX, offsetY)
        self._drawNodes(nodeList, draw, offsetX, offsetY)
        outputPath.parent.mkdir(parents=True, exist_ok=True)
        targetCanvas.save(outputPath, format="PNG")

    def _drawEdges(
        self,
        nodes: list[BaseNode],
        draw: ImageDraw.ImageDraw,
        offsetX: float,
        offsetY: float,
    ) -> None:
        for parent, child in self._graphTraversal.allEdges(nodes):
            start = (
                parent.bbox.x + parent.bbox.width + offsetX,
                parent.bbox.y + parent.bbox.height / 2 + offsetY,
            )
            end = (child.bbox.x + offsetX, child.bbox.y + child.bbox.height / 2 + offsetY)
            draw.line((start, end), fill=Constants.EDGE_COLOR, width=1)

    def _drawNodes(
        self,
        nodes: list[BaseNode],
        draw: ImageDraw.ImageDraw,
        offsetX: float,
        offsetY: float,
    ) -> None:
        font = Constants.loadSerifFont()
        for node in nodes:
            box = node.bbox
            rectangle = (
                box.x + offsetX,
                box.y + offsetY,
                box.x + box.width + offsetX,
                box.y + box.height + offsetY,
            )
            if isinstance(node, Root):
                fill = Constants.ROOT_FILL_COLOR
            elif isinstance(node, Leaf):
                fill = Constants.LEAF_FILL_COLOR
            else:
                fill = Constants.NODE_FILL_COLOR
            draw.rectangle(rectangle, fill=fill, outline=Constants.BORDER_COLOR, width=1)
            draw.text(
                (rectangle[0] + Constants.NODE_HORIZONTAL_PADDING / 2, rectangle[1] + 3),
                node.text,
                fill=Constants.TEXT_COLOR,
                font=font,
            )
