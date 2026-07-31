"""GUIイベントから受け取る文字列や位置を正規化する。"""

from __future__ import annotations


def clampPopupPosition(
    x: float,
    y: float,
    popupWidth: int,
    popupHeight: int,
    containerWidth: int,
    containerHeight: int,
    margin: int = 10,
) -> tuple[int, int]:
    """ポップアップが表示領域からはみ出さない左上位置を返す。"""

    maximumX = max(margin, containerWidth - popupWidth - margin)
    maximumY = max(margin, containerHeight - popupHeight - margin)
    return (
        round(min(maximumX, max(margin, x))),
        round(min(maximumY, max(margin, y))),
    )
