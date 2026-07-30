"""View入力をModel更新メッセージへ変換するControllerを提供する。"""

from forest.controller.command_port import ModelCommandPort
from forest.controller.controller import Controller

__all__ = ["Controller", "ModelCommandPort"]
