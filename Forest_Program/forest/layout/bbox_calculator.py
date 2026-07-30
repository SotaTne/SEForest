"""グラフ全体または部分グラフの描画範囲を計算する。"""

from collections.abc import Iterable

from forest.layout.graph_traversal import GraphTraversal
from forest.shared import BBox
from forest.tree import BaseNode


class BBoxCalculator:
    """複数ノードの境界矩形を包含する最小の矩形を計算する。"""

    def __init__(self, graphTraversal: GraphTraversal | None = None) -> None:
        self._graphTraversal = graphTraversal or GraphTraversal()

    def forNodes(self, nodes: Iterable[BaseNode]) -> BBox:
        """指定されたノードと、その子孫すべてを含む描画範囲を返す。"""

        allNodes: list[BaseNode] = []
        seen: set[int] = set()
        for node in nodes:
            for reachable in self._graphTraversal.reachableFrom(node):
                if id(reachable) not in seen:
                    seen.add(id(reachable))
                    allNodes.append(reachable)
        return self._bounds(allNodes)

    def forSubgraph(self, start: BaseNode) -> BBox:
        """開始ノードから到達できる部分グラフの描画範囲を返す。"""

        return self._bounds(self._graphTraversal.reachableFrom(start))

    def _bounds(self, nodes: Iterable[BaseNode]) -> BBox:
        """指定ノードの境界矩形を結合する。ノードがなければ空の矩形を返す。"""

        boxes = [node.bbox for node in nodes]
        if not boxes:
            return BBox(0.0, 0.0, 0.0, 0.0)
        left = min(box.x for box in boxes)
        top = min(box.y for box in boxes)
        right = max(box.x + box.width for box in boxes)
        bottom = max(box.y + box.height for box in boxes)
        return BBox(left, top, right - left, bottom - top)
