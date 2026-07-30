"""Node types used by forest layout logic."""

from __future__ import annotations

from abc import ABC, abstractmethod

from forest.shared.geometry import BBox


class BaseNode(ABC):
    """Display information and operations common to every node."""

    def __init__(self, text: str, bbox: BBox | None = None) -> None:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        self._text = text
        self._bbox = bbox if bbox is not None else BBox(0.0, 0.0, 0.0, 0.0)

    @property
    def text(self) -> str:
        return self._text

    @property
    def bbox(self) -> BBox:
        return self._bbox

    @bbox.setter
    def bbox(self, bbox: BBox) -> None:
        if not isinstance(bbox, BBox):
            raise TypeError("bbox must be a BBox")
        self._bbox = bbox

    def rename(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        self._text = text

    @abstractmethod
    def children(self) -> tuple[BaseNode, ...]:
        """Return children without exposing the mutable collection."""


class _ParentNode(BaseNode):
    def __init__(self, text: str, bbox: BBox | None = None) -> None:
        super().__init__(text, bbox)
        self._childNodes: list[BaseNode] = []

    def addChild(self, child: BaseNode) -> None:
        if not isinstance(child, BaseNode):
            raise TypeError("child must be a BaseNode")
        if child not in self._childNodes:
            self._childNodes.append(child)

    def children(self) -> tuple[BaseNode, ...]:
        return tuple(self._childNodes)


class Node(_ParentNode):
    """An intermediate node with children."""


class Root(_ParentNode):
    """The display starting point of a tree."""


class Leaf(BaseNode):
    """A terminal node without children."""

    def children(self) -> tuple[BaseNode, ...]:
        return ()
