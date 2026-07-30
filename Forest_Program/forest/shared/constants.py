"""Defaults shared by layout and rendering logic."""

from PIL import ImageFont


class Constants:
    """Constants defined by the requirements and detailed design."""

    FONT_FAMILY = "Serif"
    FONT_SIZE = 12
    SERIF_FONT_CANDIDATES = (
        "/System/Library/Fonts/Times.ttc",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "DejaVuSerif.ttf",
        "LiberationSerif-Regular.ttf",
        "C:/Windows/Fonts/times.ttf",
    )
    HORIZONTAL_SPACING = 25.0
    VERTICAL_SPACING = 2.0
    MIN_ZOOM_SCALE = 0.1
    MAX_ZOOM_SCALE = 8.0
    DRAG_THRESHOLD = 4.0
    PLAYBACK_INTERVAL_MS = 100
    MIN_NODE_WIDTH = 24.0
    NODE_HORIZONTAL_PADDING = 12.0
    NODE_VERTICAL_PADDING = 8.0
    IMAGE_PADDING = 10
    IMAGE_BACKGROUND_COLOR = "white"
    ROOT_FILL_COLOR = "#ead8bd"
    NODE_FILL_COLOR = "#f4ead3"
    LEAF_FILL_COLOR = "#e8f1cf"
    EDGE_COLOR = "#5f6b7a"
    BORDER_COLOR = "#5d5348"
    TEXT_COLOR = "#202020"

    @staticmethod
    def loadSerifFont() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """Load the required Serif font at the configured point size."""

        for fontCandidate in Constants.SERIF_FONT_CANDIDATES:
            try:
                return ImageFont.truetype(fontCandidate, Constants.FONT_SIZE)
            except OSError:
                continue
        return ImageFont.load_default(size=Constants.FONT_SIZE)

    def __new__(cls) -> "Constants":
        raise TypeError("Constants cannot be instantiated")
