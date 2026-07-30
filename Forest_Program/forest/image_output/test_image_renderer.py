from pathlib import Path

from PIL import Image, ImageColor, ImageDraw

from forest.image_output import ImageRenderer
from forest.shared import BBox, Constants
from forest.tree import Leaf, Root


def buildRenderedTree() -> tuple[Root, Leaf]:
    root = Root("root", BBox(0.0, 0.0, 50.0, 20.0))
    leaf = Leaf("leaf", BBox(75.0, 0.0, 50.0, 20.0))
    root.addChild(leaf)
    return root, leaf


def assertPng(path: Path, expectedSize: tuple[int, int]) -> None:
    with Image.open(path) as image:
        assert image.format == "PNG"
        assert image.mode == "RGB"
        assert image.size == expectedSize


def testRenderCanvasWritesCompleteGraphPng(tmp_path: Path) -> None:
    root, _ = buildRenderedTree()
    outputPath = tmp_path / "nested" / "canvas.png"
    ImageRenderer().renderCanvas([root], outputPath)
    assertPng(outputPath, (145, 40))
    with Image.open(outputPath) as image:
        assert image.getpixel((130, 25)) == ImageColor.getrgb(Constants.LEAF_FILL_COLOR)


def testRenderSubgraphUsesSelectedBounds(tmp_path: Path) -> None:
    _, leaf = buildRenderedTree()
    outputPath = tmp_path / "subgraph.png"
    ImageRenderer().renderSubgraph(leaf, outputPath)
    assertPng(outputPath, (70, 40))


def testRenderEmptyCanvasWritesMinimalPng(tmp_path: Path) -> None:
    outputPath = tmp_path / "empty.png"
    ImageRenderer().renderCanvas([], outputPath)
    assertPng(outputPath, (20, 20))


def testImageRendererInternalOperationsDrawAndSave(tmp_path: Path) -> None:
    root, leaf = buildRenderedTree()
    renderer = ImageRenderer()
    bounds = BBox(0.0, 0.0, 125.0, 20.0)
    targetCanvas = renderer._createTargetCanvas(bounds)
    draw = ImageDraw.Draw(targetCanvas)
    renderer._drawEdges([root], draw, 10.0, 10.0)
    renderer._drawNodes([root, leaf], draw, 10.0, 10.0)
    assert targetCanvas.getbbox() is not None

    outputPath = tmp_path / "internal.png"
    renderer._render([root, leaf], bounds, targetCanvas, outputPath)
    assertPng(outputPath, (145, 40))
