"""Value objects for coordinates, bounds, and layout animation steps."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from forest.tree.nodes import BaseNode


@dataclass(frozen=True, slots=True)
class Point:
    """A coordinate on the canvas."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class BBox:
    """A rectangular area containing only position and size."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("width and height must be non-negative")


@dataclass(frozen=True, slots=True)
class LayoutStep:
    """Node positions for one layout animation step."""

    index: int
    positions: Mapping[BaseNode, BBox]

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("index must be non-negative")
        object.__setattr__(self, "positions", MappingProxyType(dict(self.positions)))
