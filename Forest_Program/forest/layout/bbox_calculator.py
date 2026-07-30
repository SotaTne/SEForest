"""Calculate drawing bounds for complete and partial graphs."""

from collections.abc import Iterable

from forest.layout.graph_traversal import GraphTraversal
from forest.shared import BBox
from forest.tree import BaseNode


class BBoxCalculator:
    """Calculate the union of node bounding boxes."""

    def __init__(self, graphTraversal: GraphTraversal | None = None) -> None:
        self._graphTraversal = graphTraversal or GraphTraversal()

    def forNodes(self, nodes: Iterable[BaseNode]) -> BBox:
        allNodes: list[BaseNode] = []
        seen: set[int] = set()
        for node in nodes:
            for reachable in self._graphTraversal.reachableFrom(node):
                if id(reachable) not in seen:
                    seen.add(id(reachable))
                    allNodes.append(reachable)
        return self._bounds(allNodes)

    def forSubgraph(self, start: BaseNode) -> BBox:
        return self._bounds(self._graphTraversal.reachableFrom(start))

    def _bounds(self, nodes: Iterable[BaseNode]) -> BBox:
        boxes = [node.bbox for node in nodes]
        if not boxes:
            return BBox(0.0, 0.0, 0.0, 0.0)
        left = min(box.x for box in boxes)
        top = min(box.y for box in boxes)
        right = max(box.x + box.width for box in boxes)
        bottom = max(box.y + box.height for box in boxes)
        return BBox(left, top, right - left, bottom - top)
