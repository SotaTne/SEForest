"""森構造の配置ロジックで使用するノード型を定義する。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from forest.shared.geometry import BBox


class BaseNode(ABC):
    """すべてのノードに共通する表示情報と操作を定義する基底クラス。"""

    def __init__(self, text: str, bbox: BBox | None = None) -> None:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        self._text = text
        self._bbox = bbox if bbox is not None else BBox(0.0, 0.0, 0.0, 0.0)

    @property
    def text(self) -> str:
        """ノードに表示する文字列を返す。"""

        return self._text

    @property
    def bbox(self) -> BBox:
        """ノードの現在位置と大きさを返す。"""

        return self._bbox

    @bbox.setter
    def bbox(self, bbox: BBox) -> None:
        """ノードの現在位置と大きさを更新する。"""

        if not isinstance(bbox, BBox):
            raise TypeError("bbox must be a BBox")
        self._bbox = bbox

    def rename(self, text: str) -> None:
        """ノードの表示文字列を変更する。"""

        if not isinstance(text, str):
            raise TypeError("text must be a string")
        self._text = text

    @abstractmethod
    def children(self) -> tuple[BaseNode, ...]:
        """内部の可変コレクションを公開せず、子ノードをタプルで返す。"""


class _ParentNode(BaseNode):
    """子ノードを保持できるノードに共通する内部実装。"""

    def __init__(self, text: str, bbox: BBox | None = None) -> None:
        super().__init__(text, bbox)
        self._childNodes: list[BaseNode] = []

    def addChild(self, child: BaseNode) -> None:
        """子ノードを追加する。同じインスタンスが登録済みの場合は追加しない。"""

        if not isinstance(child, BaseNode):
            raise TypeError("child must be a BaseNode")
        if child not in self._childNodes:
            self._childNodes.append(child)

    def children(self) -> tuple[BaseNode, ...]:
        """登録順を維持した子ノードのタプルを返す。"""

        return tuple(self._childNodes)


class Node(_ParentNode):
    """子ノードを持つ中間ノード。"""


class Root(_ParentNode):
    """木構造の表示開始点となるルートノード。"""


class Leaf(BaseNode):
    """子ノードを持たない末端ノード。"""

    def children(self) -> tuple[BaseNode, ...]:
        """末端ノードのため空のタプルを返す。"""

        return ()
