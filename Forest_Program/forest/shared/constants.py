"""配置計算と画像描画で共有する既定値を定義する。"""

import sys
from pathlib import Path
from typing import Self

from PIL import ImageFont


class Constants:
    """要求仕様書および詳細設計書に基づく定数をまとめたクラス。"""

    FONT_FAMILY = "Noto Serif JP"
    FONT_SIZE = 12
    FONT_PATH = Path("assets/fonts/NotoSerifJP-Regular.otf")
    HORIZONTAL_SPACING = 25.0
    VERTICAL_SPACING = 2.0
    MIN_ZOOM_SCALE = 0.1
    MAX_ZOOM_SCALE = 8.0
    DRAG_THRESHOLD = 4.0
    CANVAS_VIEWPORT_MARGIN = 100.0
    PLAYBACK_STEP_INTERVAL_MS = 50
    MIN_NODE_WIDTH = 24.0
    NODE_HORIZONTAL_PADDING = 12.0
    NODE_VERTICAL_PADDING = 8.0
    IMAGE_PADDING = 10
    IMAGE_BACKGROUND_COLOR = "white"
    ROOT_FILL_COLOR = "#ead8bd"
    NODE_FILL_COLOR = "#f4ead3"
    LEAF_FILL_COLOR = "#e8f1cf"
    ROOT_SELECTED_FILL_COLOR = "#f1e4d8"
    ROOT_SELECTED_BORDER_COLOR = "#d5bfae"
    NODE_SELECTED_FILL_COLOR = "#f0eeea"
    NODE_SELECTED_BORDER_COLOR = "#cfc9c1"
    LEAF_SELECTED_FILL_COLOR = "#e7f1e2"
    LEAF_SELECTED_BORDER_COLOR = "#bfd3b7"
    EDGE_COLOR = "#5f6b7a"
    BORDER_COLOR = "#5d5348"
    TEXT_COLOR = "#202020"

    @staticmethod
    def applicationRoot() -> Path:
        """フォントなどの同梱ファイルを探す基準ディレクトリを返す。"""

        bundledRoot = getattr(sys, "_MEIPASS", None)
        if bundledRoot is not None:
            return Path(bundledRoot)
        return Path(__file__).resolve().parents[2]

    @staticmethod
    def loadSerifFont() -> ImageFont.FreeTypeFont:
        """同梱された日本語対応Serifフォントを読み込む。"""

        return ImageFont.truetype(Constants.applicationRoot() / Constants.FONT_PATH, Constants.FONT_SIZE)

    def __new__(cls) -> Self:
        raise TypeError("Constants cannot be instantiated")
