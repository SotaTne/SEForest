"""Modelの状態変更を複数のViewへ通知するイベント機構。"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto


class ModelEvent(Enum):
    """Viewが再読込する状態領域を表す。"""

    NODES_CHANGED = auto()
    LAYOUT_CHANGED = auto()
    SELECTION_CHANGED = auto()
    EDITOR_CHANGED = auto()
    PLAYBACK_CHANGED = auto()
    DESKTOP_CHANGED = auto()


class EventEmitter[E]:
    """イベントごとに登録された複数のcallbackを登録順に呼び出す。"""

    def __init__(self) -> None:
        self._callbacks: dict[E, list[Callable[[], None]]] = {}

    def subscribe(self, event: E, callback: Callable[[], None]) -> None:
        """callbackを登録する。同一イベントへの同一callbackは重複登録しない。"""

        if not callable(callback):
            raise TypeError("callback must be callable")
        callbacks = self._callbacks.setdefault(event, [])
        if callback not in callbacks:
            callbacks.append(callback)

    def notify(self, event: E) -> None:
        """通知開始時点で登録されていたcallbackを登録順に呼び出す。"""

        for callback in tuple(self._callbacks.get(event, ())):
            callback()
