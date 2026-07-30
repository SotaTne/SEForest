"""全ノードの初期配置から階層的な樹状配置までのアニメーション段階を生成する。"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from typing import Protocol

from forest.layout.graph_traversal import GraphTraversal
from forest.shared import BBox, Constants, LayoutStep
from forest.tree import BaseNode


class DesktopState(Protocol):
    """別途実装されるMVCの状態から受け取る表示領域情報のインターフェース。"""

    @property
    def windowCanvasBBox(self) -> BBox:
        """ウィンドウ内でノードを配置できるキャンバス領域を返す。"""

        ...


class LayoutCalculator:
    """循環と共有ノードを考慮し、再現可能な配置段階を生成する。"""

    def __init__(self) -> None:
        self._measuredSizeCache: dict[BaseNode, BBox] = {}
        self._parentsByNode: dict[BaseNode, list[BaseNode]] = {}
        self._layoutVersion = 0

    def createInitialSteps(self, nodes: list[BaseNode], desktop: DesktopState) -> list[LayoutStep]:
        """初期表示から樹状整列までの配置段階を生成する。

        最初の段階には全ノードを表示領域へ順番に並べた位置を格納し、その後は
        深さの浅い層から最終位置へ移動させた状態を追加する。Controllerは返された
        段階を順番にViewへ反映することで、樹状に整列するアニメーションを実現できる。

        Args:
            nodes: 配置対象となる木構造の開始ノード一覧。
            desktop: 配置可能なキャンバス領域を提供するMVC側の状態。

        Returns:
            時系列順の配置段階。対象ノードがない場合は空の一覧。
        """

        allNodes = self._allNodes(nodes)
        if not allNodes:
            return []
        self._buildParentIndex(nodes)
        viewport = desktop.windowCanvasBBox
        initialPositions = self._initialPositions(allNodes, viewport)
        finalPositions, depths = self._hierarchicalPositions(nodes, viewport)

        steps = [LayoutStep(0, initialPositions)]
        currentPositions = dict(initialPositions)
        for depth in sorted(set(depths.values())):
            for node in allNodes:
                if depths[node] == depth:
                    currentPositions[node] = finalPositions[node]
            steps.append(LayoutStep(len(steps), currentPositions))
        self._layoutVersion += 1
        return steps

    def recalculate(self, nodes: list[BaseNode], changedNode: BaseNode) -> list[LayoutStep]:
        """表示名が変更されたノードの大きさと配置を再計算する。

        変更後も同じ層の最大幅が変わらない場合は対象ノードだけを更新し、層幅が
        変わる場合は全体を再配置する。
        """

        self._buildParentIndex(nodes)
        allNodes = self._allNodes(nodes)
        if not allNodes:
            return []
        oldPositions, depths = self._hierarchicalPositions(nodes, BBox(0.0, 0.0, 0.0, 0.0))
        oldSize = self._measure(changedNode)
        otherWidths = [
            self._measure(node).width
            for node in allNodes
            if node is not changedNode and depths[node] == depths[changedNode]
        ]
        otherMaximumWidth = max(otherWidths, default=0.0)
        self._measuredSizeCache.pop(changedNode, None)
        newSize = self._measure(changedNode)
        if (
            oldSize.width <= otherMaximumWidth
            and newSize.width <= otherMaximumWidth
            and oldSize.height == newSize.height
        ):
            currentBox = changedNode.bbox if changedNode.bbox.width > 0 else oldPositions[changedNode]
            self._layoutVersion += 1
            return [
                LayoutStep(
                    self._layoutVersion,
                    {changedNode: BBox(currentBox.x, currentBox.y, newSize.width, newSize.height)},
                )
            ]
        viewport = BBox(
            min(node.bbox.x for node in allNodes),
            min(node.bbox.y for node in allNodes),
            0.0,
            0.0,
        )
        positions, _ = self._hierarchicalPositions(nodes, viewport)
        self._layoutVersion += 1
        return [LayoutStep(self._layoutVersion, positions)]

    def _measure(self, node: BaseNode) -> BBox:
        """フォントの描画範囲と余白からノードの表示サイズを求める。"""

        cached = self._measuredSizeCache.get(node)
        if cached is not None:
            return cached
        textBounds = Constants.loadSerifFont().getbbox(node.text)
        textWidth = float(textBounds[2] - textBounds[0])
        textHeight = float(textBounds[3] - textBounds[1])
        width = max(Constants.MIN_NODE_WIDTH, textWidth + Constants.NODE_HORIZONTAL_PADDING)
        height = max(float(Constants.FONT_SIZE), textHeight) + Constants.NODE_VERTICAL_PADDING
        measured = BBox(0.0, 0.0, width, height)
        self._measuredSizeCache[node] = measured
        return measured

    def _buildParentIndex(self, nodes: list[BaseNode]) -> None:
        """共有ノードを判定できるよう、子ノードから親ノードへの索引を構築する。"""

        parents: dict[BaseNode, list[BaseNode]] = defaultdict(list)
        for parent, child in GraphTraversal().allEdges(nodes):
            parents[child].append(parent)
        self._parentsByNode = dict(parents)

    def _placeRoots(self, nodes: list[BaseNode], viewport: BBox) -> list[LayoutStep]:
        """最終配置のうちルート層だけを配置段階として返す。"""

        positions, depths = self._hierarchicalPositions(nodes, viewport)
        rootPositions = {node: box for node, box in positions.items() if depths[node] == 0}
        return [LayoutStep(self._layoutVersion, rootPositions)]

    def _placeDescendants(self, root: BaseNode) -> list[LayoutStep]:
        """指定ルートの子孫を深さごとの配置段階として返す。"""

        positions, depths = self._hierarchicalPositions([root], root.bbox)
        return [
            LayoutStep(
                self._layoutVersion + depth,
                {node: positions[node] for node in positions if depths[node] == depth},
            )
            for depth in sorted(set(depths.values()))
        ]

    def _resolveSharedNodes(self, nodes: list[BaseNode]) -> list[LayoutStep]:
        """複数の親を持つ共有ノードの現在位置を配置段階として返す。"""

        del nodes
        sharedNodes = {node for node, parents in self._parentsByNode.items() if len(parents) > 1}
        return [LayoutStep(self._layoutVersion, {node: node.bbox for node in sharedNodes})]

    def _allNodes(self, nodes: Iterable[BaseNode]) -> list[BaseNode]:
        """複数の開始ノードから到達可能な全ノードを重複なく返す。"""

        result: list[BaseNode] = []
        seen: set[int] = set()
        for start in nodes:
            for node in GraphTraversal().reachableFrom(start):
                if id(node) not in seen:
                    seen.add(id(node))
                    result.append(node)
        return result

    def _initialPositions(self, nodes: list[BaseNode], viewport: BBox) -> dict[BaseNode, BBox]:
        """全ノードの初期位置を縦方向へ並べ、表示領域を超える場合は次の列へ送る。"""

        positions: dict[BaseNode, BBox] = {}
        x = viewport.x
        y = viewport.y
        columnWidth = 0.0
        bottom = viewport.y + viewport.height if viewport.height > 0 else float("inf")
        for node in nodes:
            size = self._measure(node)
            if y > viewport.y and y + size.height > bottom:
                x += columnWidth + Constants.HORIZONTAL_SPACING
                y = viewport.y
                columnWidth = 0.0
            positions[node] = BBox(x, y, size.width, size.height)
            y += size.height + Constants.VERTICAL_SPACING
            columnWidth = max(columnWidth, size.width)
        return positions

    def _hierarchicalPositions(
        self,
        nodes: list[BaseNode],
        viewport: BBox,
    ) -> tuple[dict[BaseNode, BBox], dict[BaseNode, int]]:
        """親子関係に基づく階層配置と各ノードの深さを計算する。

        親は可能な限り最初と最後の子の中央へ配置する。循環を検出した場合は
        探索中のノードを現在層の空き位置へ置き、再帰が終了しない状態を防ぐ。
        """

        allNodes = self._allNodes(nodes)
        depths = self._depthsFor(nodes)

        layers: dict[int, list[BaseNode]] = defaultdict(list)
        for node in allNodes:
            layers[depths[node]].append(node)
        layerWidths = {depth: max(self._measure(node).width for node in layer) for depth, layer in layers.items()}
        layerX: dict[int, float] = {}
        currentX = viewport.x
        for depth in sorted(layers):
            layerX[depth] = currentX
            currentX += layerWidths[depth] + Constants.HORIZONTAL_SPACING

        positions: dict[BaseNode, BBox] = {}
        nextYByDepth: dict[int, float] = defaultdict(lambda: viewport.y)
        nextLeafY = viewport.y
        inProgress: set[BaseNode] = set()

        def placeNode(node: BaseNode) -> float:
            """ノードと未配置の子孫を配置し、ノードの垂直方向の中心座標を返す。"""

            nonlocal nextLeafY
            if node in positions:
                box = positions[node]
                return box.y + box.height / 2

            depth = depths[node]
            size = self._measure(node)
            if node in inProgress:
                y = max(nextLeafY, nextYByDepth[depth])
                positions[node] = BBox(layerX[depth], y, size.width, size.height)
                nextYByDepth[depth] = y + size.height + Constants.VERTICAL_SPACING
                nextLeafY = nextYByDepth[depth]
                return y + size.height / 2

            inProgress.add(node)
            childCenters = [placeNode(child) for child in node.children()]
            inProgress.remove(node)
            if childCenters:
                desiredY = (childCenters[0] + childCenters[-1]) / 2 - size.height / 2
                y = max(desiredY, nextYByDepth[depth])
            else:
                y = max(nextLeafY, nextYByDepth[depth])
                nextLeafY = y + size.height + Constants.VERTICAL_SPACING
            positions[node] = BBox(layerX[depth], y, size.width, size.height)
            nextYByDepth[depth] = y + size.height + Constants.VERTICAL_SPACING
            return y + size.height / 2

        for root in GraphTraversal().rootNodes(nodes):
            placeNode(root)
            nextLeafY = max(
                nextLeafY, max(box.y + box.height for box in positions.values()) + Constants.HORIZONTAL_SPACING
            )
        for node in allNodes:
            placeNode(node)
        return positions, depths

    def _depthsFor(self, nodes: list[BaseNode]) -> dict[BaseNode, int]:
        """トポロジカルな探索で各ノードの深さを求める。

        循環に含まれて通常の探索で処理できないノードには、判明済みの親の深さを
        基準として深さを割り当てる。
        """

        allNodes = self._allNodes(nodes)
        edges = GraphTraversal().allEdges(nodes)
        incomingCount = {node: 0 for node in allNodes}
        for _, child in edges:
            incomingCount[child] += 1

        depths = {node: 0 for node in allNodes if incomingCount[node] == 0}
        queue = deque(node for node in allNodes if incomingCount[node] == 0)
        processed: set[BaseNode] = set()
        while queue:
            parent = queue.popleft()
            processed.add(parent)
            for child in parent.children():
                depths[child] = max(depths.get(child, 0), depths[parent] + 1)
                incomingCount[child] -= 1
                if incomingCount[child] == 0:
                    queue.append(child)

        for node in allNodes:
            if node in processed:
                continue
            knownParentDepths = [depths[parent] for parent, child in edges if child is node and parent in depths]
            depths[node] = max(knownParentDepths, default=-1) + 1
        return depths
