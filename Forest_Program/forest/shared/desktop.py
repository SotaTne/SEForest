"""表示領域とキャンバス座標の変換状態を管理する。"""

from __future__ import annotations

from forest.shared.constants import Constants
from forest.shared.geometry import BBox, Point


class Desktop:
    """ウィンドウサイズ、パン位置、拡大率を保持する。"""

    def __init__(self, width: float = 0.0, height: float = 0.0) -> None:
        self._validateSize(width, height)
        self._windowSizeBBox = BBox(0.0, 0.0, width, height)
        self._windowCanvasBBox = BBox(0.0, 0.0, width, height)
        self._zoomScale = 1.0

    @property
    def windowSizeBBox(self) -> BBox:
        return self._windowSizeBBox

    @property
    def windowCanvasBBox(self) -> BBox:
        return self._windowCanvasBBox

    @property
    def zoomScale(self) -> float:
        return self._zoomScale

    def resize(self, width: float, height: float) -> None:
        """ウィンドウと、現在の拡大率で見えるキャンバス範囲を更新する。"""

        self._validateSize(width, height)
        self._windowSizeBBox = BBox(0.0, 0.0, width, height)
        self._windowCanvasBBox = BBox(
            self._windowCanvasBBox.x,
            self._windowCanvasBBox.y,
            width / self._zoomScale,
            height / self._zoomScale,
        )

    def pan(self, dx: float, dy: float) -> None:
        """View座標で指定された移動量だけ表示領域を移動する。"""

        self._windowCanvasBBox = BBox(
            self._windowCanvasBBox.x - dx / self._zoomScale,
            self._windowCanvasBBox.y - dy / self._zoomScale,
            self._windowCanvasBBox.width,
            self._windowCanvasBBox.height,
        )

    def zoomAt(self, anchor: Point, scaleDelta: float) -> None:
        """指定したView座標を固定したまま拡大率を変更する。"""

        if scaleDelta <= 0:
            raise ValueError("scaleDelta must be positive")
        canvasAnchor = self.viewToCanvas(anchor)
        newScale = min(
            Constants.MAX_ZOOM_SCALE,
            max(Constants.MIN_ZOOM_SCALE, self._zoomScale * scaleDelta),
        )
        self._zoomScale = newScale
        self._windowCanvasBBox = BBox(
            canvasAnchor.x - anchor.x / newScale,
            canvasAnchor.y - anchor.y / newScale,
            self._windowSizeBBox.width / newScale,
            self._windowSizeBBox.height / newScale,
        )

    def canvasToView(self, point: Point) -> Point:
        """キャンバス座標をView座標へ変換する。"""

        return Point(
            (point.x - self._windowCanvasBBox.x) * self._zoomScale,
            (point.y - self._windowCanvasBBox.y) * self._zoomScale,
        )

    def viewToCanvas(self, point: Point) -> Point:
        """View座標をキャンバス座標へ変換する。"""

        return Point(
            self._windowCanvasBBox.x + point.x / self._zoomScale,
            self._windowCanvasBBox.y + point.y / self._zoomScale,
        )

    def resetViewport(self) -> None:
        """パンと拡大率を初期状態へ戻す。"""

        self._zoomScale = 1.0
        self._windowCanvasBBox = BBox(
            0.0,
            0.0,
            self._windowSizeBBox.width,
            self._windowSizeBBox.height,
        )

    @staticmethod
    def _validateSize(width: float, height: float) -> None:
        if width < 0 or height < 0:
            raise ValueError("width and height must be non-negative")
