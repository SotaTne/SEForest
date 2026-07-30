"""trees、nodes、branchesの各セクションから共有ノードを含むグラフを生成する。"""

from __future__ import annotations

from collections.abc import Iterable

from forest.tree import BaseNode, Leaf, Node, Root


class ParseError(ValueError):
    """Forestテキストの構造が不正な場合に送出する例外。"""


class Parser:
    """要求仕様書のサンプルで使用されるForestテキスト形式を解析する。"""

    def parse(self, sourceText: str) -> list[BaseNode]:
        """Forestテキストを解析し、木構造ごとの開始ノードを返す。

        branchesセクションが省略された場合は、treesセクションのインデント表現から
        親子関係を復元する。同じノードIDへの参照には同一インスタンスを使用するため、
        複数の親を持つ共有ノードも保持できる。

        Args:
            sourceText: 解析対象のForestテキスト。

        Returns:
            解析された木構造の開始ノード一覧。空文字列の場合は空の一覧。

        Raises:
            TypeError: ``sourceText`` が文字列ではない場合。
            ParseError: 必須セクションの不足や定義形式の誤りがある場合。
        """

        if not isinstance(sourceText, str):
            raise TypeError("sourceText must be a string")
        if not sourceText.strip():
            return []

        sections = self._splitSections(sourceText)
        if "trees" not in sections or "nodes" not in sections:
            raise ParseError("trees and nodes sections are required")

        labels = self._parseNodeLabels(sections["nodes"])
        branches = self._parseBranches(sections.get("branches", []))
        rootIds: set[int] | None = None
        if not branches:
            branches, rootIds = self._branchesFromTrees(sections["trees"], labels)
        registry = self._parseNodeRegistry(sections["nodes"], branches, rootIds)
        if branches:
            self._connectBranches(branches, registry)
        self._parseTrees(sections["trees"], registry)

        roots: list[BaseNode] = [node for node in registry.values() if isinstance(node, Root)]
        if not roots and registry:
            roots = [next(iter(registry.values()))]
        return roots

    def _splitSections(self, sourceText: str) -> dict[str, list[str]]:
        """入力テキストをセクション名ごとの行一覧へ分割する。"""

        sections: dict[str, list[str]] = {}
        currentSection: str | None = None
        for rawLine in sourceText.splitlines():
            line = rawLine.rstrip()
            if line.endswith(":") and line[:-1].strip().isidentifier():
                currentSection = line[:-1].strip().lower()
                if currentSection in sections:
                    raise ParseError(f"duplicate section: {currentSection}")
                sections[currentSection] = []
            elif currentSection is not None and line.strip():
                sections[currentSection].append(line)
            elif line.strip():
                raise ParseError("content appears before the first section")
        return sections

    def _parseNodeRegistry(
        self,
        lines: Iterable[str],
        branches: list[tuple[int, int]],
        rootIds: set[int] | None = None,
    ) -> dict[int, BaseNode]:
        """接続関係を基に各IDのノード種別を判定し、ノードを生成する。"""

        labels = self._parseNodeLabels(lines)
        outgoing = {parentId for parentId, _ in branches}
        incoming = {childId for _, childId in branches}
        resolvedRootIds = rootIds if rootIds is not None else outgoing - incoming
        registry: dict[int, BaseNode] = {}
        for nodeId, label in labels.items():
            if nodeId in resolvedRootIds:
                registry[nodeId] = Root(label)
            elif nodeId in outgoing:
                registry[nodeId] = Node(label)
            else:
                registry[nodeId] = Leaf(label)
        return registry

    def _parseNodeLabels(self, lines: Iterable[str]) -> dict[int, str]:
        """nodesセクションからノードIDと表示名の対応を読み取る。"""

        labels: dict[int, str] = {}
        for line in lines:
            parts = [part.strip() for part in line.split(",", maxsplit=1)]
            if len(parts) != 2 or not parts[1]:
                raise ParseError(f"invalid node definition: {line}")
            try:
                nodeId = int(parts[0])
            except ValueError as error:
                raise ParseError(f"invalid node id: {parts[0]}") from error
            if nodeId in labels:
                raise ParseError(f"duplicate node id: {nodeId}")
            labels[nodeId] = parts[1]
        return labels

    def _branchesFromTrees(
        self,
        lines: Iterable[str],
        labels: dict[int, str],
    ) -> tuple[list[tuple[int, int]], set[int]]:
        """treesセクションの階層表現から接続関係とルートIDを復元する。"""

        nodeIdsByName: dict[str, list[int]] = {}
        for nodeId, label in labels.items():
            nodeIdsByName.setdefault(label, []).append(nodeId)

        branches: list[tuple[int, int]] = []
        rootIds: set[int] = set()
        rootOccurrences: dict[str, int] = {}
        stack: list[int] = []
        for line in lines:
            depth, name = self._treeLine(line)
            candidates = nodeIdsByName.get(name)
            if not candidates:
                raise ParseError(f"tree references unknown node: {name}")
            if depth == 0:
                index = rootOccurrences.get(name, 0)
                nodeId = candidates[min(index, len(candidates) - 1)]
                rootOccurrences[name] = index + 1
                rootIds.add(nodeId)
            else:
                nodeId = candidates[0]
            if depth > len(stack):
                raise ParseError(f"tree depth jumps unexpectedly: {line}")
            if depth > 0:
                edge = (stack[depth - 1], nodeId)
                if edge not in branches:
                    branches.append(edge)
            stack[depth:] = [nodeId]
        return branches, rootIds

    def _parseBranches(self, lines: Iterable[str]) -> list[tuple[int, int]]:
        """branchesセクションから親IDと子IDの組を読み取る。"""

        branches: list[tuple[int, int]] = []
        for line in lines:
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 2:
                raise ParseError(f"invalid branch definition: {line}")
            try:
                branches.append((int(parts[0]), int(parts[1])))
            except ValueError as error:
                raise ParseError(f"invalid branch definition: {line}") from error
        return branches

    def _connectBranches(
        self,
        branches: Iterable[tuple[int, int]],
        registry: dict[int, BaseNode],
    ) -> None:
        """IDで表された接続関係をノードインスタンスへ反映する。"""

        for parentId, childId in branches:
            try:
                parent = registry[parentId]
                child = registry[childId]
            except KeyError as error:
                raise ParseError(f"branch references unknown node id: {error.args[0]}") from error
            if not isinstance(parent, (Node, Root)):
                raise ParseError(f"node {parentId} is declared as a leaf but has children")
            parent.addChild(child)

    def _parseTrees(self, lines: Iterable[str], registry: dict[int, BaseNode]) -> None:
        """treesセクションの階層表現をノードインスタンスへ反映する。"""

        nodesByName: dict[str, list[BaseNode]] = {}
        for node in registry.values():
            nodesByName.setdefault(node.text, []).append(node)

        stack: list[BaseNode] = []
        rootOccurrences: dict[str, int] = {}
        for line in lines:
            depth, name = self._treeLine(line)
            candidates = nodesByName.get(name)
            if not candidates:
                raise ParseError(f"tree references unknown node: {name}")
            if depth == 0:
                index = rootOccurrences.get(name, 0)
                node = candidates[min(index, len(candidates) - 1)]
                rootOccurrences[name] = index + 1
            else:
                node = candidates[0]
            if depth > len(stack):
                raise ParseError(f"tree depth jumps unexpectedly: {line}")
            if depth > 0:
                parent = stack[depth - 1]
                if not isinstance(parent, (Node, Root)):
                    raise ParseError(f"leaf cannot have children: {parent.text}")
                parent.addChild(node)
            stack[depth:] = [node]

    def _nodeFor(self, name: str, registry: dict[str, BaseNode]) -> BaseNode:
        """表示名に対応するノードを返し、未定義の場合は解析エラーにする。"""

        try:
            return registry[name]
        except KeyError as error:
            raise ParseError(f"tree references unknown node: {name}") from error

    def _treeLine(self, line: str) -> tuple[int, str]:
        """木構造の1行から深さとノード名を取り出す。"""

        depth = line.count("|--")
        name = line.split("|--")[-1].strip()
        if not name:
            raise ParseError(f"invalid tree line: {line}")
        return depth, name
