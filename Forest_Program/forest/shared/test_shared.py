import sys
from pathlib import Path
from types import MappingProxyType

import pytest

from forest.shared import BBox, Constants, LayoutStep, Point
from forest.tree import Leaf


def testPointStoresCoordinates() -> None:
    assert Point(1.5, -2.0) == Point(1.5, -2.0)


def testBBoxRejectsNegativeSize() -> None:
    with pytest.raises(ValueError):
        BBox(0.0, 0.0, -1.0, 1.0)


def testLayoutStepCopiesAndProtectsPositions() -> None:
    node = Leaf("leaf")
    original = {node: BBox(1.0, 2.0, 3.0, 4.0)}
    step = LayoutStep(0, original)
    original.clear()

    assert step.positions[node] == BBox(1.0, 2.0, 3.0, 4.0)
    assert isinstance(step.positions, MappingProxyType)


def testLayoutStepRejectsNegativeIndex() -> None:
    with pytest.raises(ValueError):
        LayoutStep(-1, {})


def testConstantsMatchRequirements() -> None:
    assert Constants.FONT_FAMILY == "Noto Serif JP"
    assert Constants.FONT_SIZE == 12
    assert Constants.HORIZONTAL_SPACING == 25.0
    assert Constants.VERTICAL_SPACING == 2.0


def testConstantsCannotBeInstantiated() -> None:
    with pytest.raises(TypeError):
        Constants()


def testApplicationRootUsesProjectRootDuringNormalExecution() -> None:
    assert Constants.applicationRoot() == Path(__file__).parents[2]


def testApplicationRootUsesPyInstallerBundleRoot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert Constants.applicationRoot() == tmp_path


def testLoadSerifFontUsesRequiredPointSize() -> None:
    font = Constants.loadSerifFont()
    assert font.getbbox("Forest")[2] > 0
    assert font.getbbox("日本語")[2] > 0
    assert getattr(font, "path", None) == Path(__file__).parents[2] / Constants.FONT_PATH
    assert font.getname()[0] == "Noto Serif JP"
    assert getattr(font, "size", Constants.FONT_SIZE) == Constants.FONT_SIZE
