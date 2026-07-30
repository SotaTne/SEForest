"""Cycle-safe traversal for graphs containing shared nodes."""

from collections import deque
from collections.abc import Iterable

from forest.tree import BaseNode


class GraphTraversal:
    """Traverse a graph by node identity without visiting a node twice."""

    def rootNodes(self, nodes: Iterable[BaseNode]) -> list[BaseNode]:
        starts = self._unique(nodes)
        allNodes = self._allNodes(starts)
        children = {child for node in allNodes for child in node.children()}
        roots = [node for node in allNodes if node not in children]
        return roots if roots else starts

    def reachableFrom(self, start: BaseNode) -> list[BaseNode]:
        return self._allNodes([start])

    def edgesFrom(self, start: BaseNode) -> list[tuple[BaseNode, BaseNode]]:
        return self.allEdges([start])

    def allEdges(self, nodes: Iterable[BaseNode]) -> list[tuple[BaseNode, BaseNode]]:
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
        result: list[BaseNode] = []
        seen: set[int] = set()
        for node in nodes:
            if id(node) not in seen:
                seen.add(id(node))
                result.append(node)
        return result
