"""共有ノードや循環を含むグラフを安全に探索する。"""

from collections import deque
from collections.abc import Iterable

from forest.tree import BaseNode


class GraphTraversal:
    """ノードの同一性に基づき、同じノードを二度訪問せずにグラフを探索する。"""

    def rootNodes(self, nodes: Iterable[BaseNode]) -> list[BaseNode]:
        """親から参照されていないルートノードを抽出する。

        循環によりルートを判定できない場合は、入力された開始ノードを返す。
        """

        starts = self._unique(nodes)
        allNodes = self._allNodes(starts)
        children = {child for node in allNodes for child in node.children()}
        roots = [node for node in allNodes if node not in children]
        return roots if roots else starts

    def reachableFrom(self, start: BaseNode) -> list[BaseNode]:
        """開始ノードから到達できるノードを幅優先順で返す。"""

        return self._allNodes([start])

    def edgesFrom(self, start: BaseNode) -> list[tuple[BaseNode, BaseNode]]:
        """開始ノードから到達できる重複のない辺を返す。"""

        return self.allEdges([start])

    def allEdges(self, nodes: Iterable[BaseNode]) -> list[tuple[BaseNode, BaseNode]]:
        """複数の開始ノードから到達できる重複のない辺を返す。"""

        edges: list[tuple[BaseNode, BaseNode]] = []
        seenEdges: set[tuple[int, int]] = set()
        for parent in self._allNodes(self._unique(nodes)):
            for child in parent.children():
                identity = (id(parent), id(child))
                if identity not in seenEdges:
                    seenEdges.add(identity)
                    edges.append((parent, child))
        return edges

    def _allNodes(self, starts: list[BaseNode]) -> list[BaseNode]:
        """複数の開始ノードを幅優先探索し、各インスタンスを一度だけ返す。"""

        result: list[BaseNode] = []
        seen: set[int] = set()
        queue = deque(starts)
        while queue:
            node = queue.popleft()
            if id(node) in seen:
                continue
            seen.add(id(node))
            result.append(node)
            queue.extend(node.children())
        return result

    def _unique(self, nodes: Iterable[BaseNode]) -> list[BaseNode]:
        """入力順を維持したまま、同一インスタンスの重複を除く。"""

        result: list[BaseNode] = []
        seen: set[int] = set()
        for node in nodes:
            if id(node) not in seen:
                seen.add(id(node))
                result.append(node)
        return result
