"""選択ノードに対する未確定の編集状態を保持する。"""

from __future__ import annotations

from forest.shared import BBox
from forest.tree import BaseNode


class NodeEditorState:
    """編集対象、下書き文字列、ポップアップ位置をまとめて管理する。"""

    def __init__(self) -> None:
        self._selectedNode: BaseNode | None = None
        self._editingText = ""
        self._popupBBox = BBox(0.0, 0.0, 0.0, 0.0)

    @property
    def selectedNode(self) -> BaseNode | None:
        return self._selectedNode

    @property
    def editingText(self) -> str:
        return self._editingText

    @property
    def popupBBox(self) -> BBox:
        return self._popupBBox

    @property
    def isEditing(self) -> bool:
        return self._selectedNode is not None

    def begin(self, node: BaseNode, popupBBox: BBox) -> None:
        """指定ノードの現在名を下書きとして編集を開始する。"""

        if not isinstance(node, BaseNode):
            raise TypeError("node must be a BaseNode")
        if not isinstance(popupBBox, BBox):
            raise TypeError("popupBBox must be a BBox")
        self._selectedNode = node
        self._editingText = node.text
        self._popupBBox = popupBBox

    def updateDraft(self, text: str) -> None:
        """編集中の下書きを更新する。"""

        self._requireEditing()
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        self._editingText = text

    def commit(self) -> str:
        """下書きを返して編集状態を終了する。"""

        self._requireEditing()
        text = self._editingText
        self.cancel()
        return text

    def cancel(self) -> None:
        """編集状態を初期化する。"""

        self._selectedNode = None
        self._editingText = ""
        self._popupBBox = BBox(0.0, 0.0, 0.0, 0.0)

    def _requireEditing(self) -> None:
        if self._selectedNode is None:
            raise RuntimeError("node editing has not started")
