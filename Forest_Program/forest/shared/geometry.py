"""座標、境界矩形、配置アニメーションの各段階を表す値オブジェクト。"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from forest.tree.nodes import BaseNode


@dataclass(frozen=True, slots=True)
class Point:
    """キャンバス上の座標を表す。"""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class BBox:
    """位置と大きさだけを持つ矩形領域を表す。

    幅と高さは0以上でなければならない。座標には負の値も指定できる。
    """

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("width and height must be non-negative")


@dataclass(frozen=True, slots=True)
class LayoutStep:
    """配置アニメーションの1段階におけるノード位置を表す。

    ``positions`` は生成後に変更されない読み取り専用のマッピングとして保持する。
    """

    index: int
    positions: Mapping[BaseNode, BBox]

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("index must be non-negative")
        object.__setattr__(self, "positions", MappingProxyType(dict(self.positions)))
