import pytest

from forest.shared import BBox, Constants, Desktop, Point


def testDesktopResizeAndCoordinateRoundTrip() -> None:
    desktop = Desktop()
    desktop.resize(800.0, 600.0)
    point = Point(125.0, 75.0)

    assert desktop.windowSizeBBox == BBox(0.0, 0.0, 800.0, 600.0)
    assert desktop.windowCanvasBBox == BBox(0.0, 0.0, 800.0, 600.0)
    assert desktop.canvasToView(desktop.viewToCanvas(point)) == point


def testPanUsesViewDistanceAtCurrentZoom() -> None:
    desktop = Desktop(800.0, 600.0)
    desktop.zoomAt(Point(0.0, 0.0), 2.0)
    desktop.pan(20.0, -10.0)

    assert desktop.windowCanvasBBox == BBox(-10.0, 5.0, 400.0, 300.0)


def testZoomKeepsAnchorAtSameViewPosition() -> None:
    desktop = Desktop(800.0, 600.0)
    anchor = Point(200.0, 150.0)
    canvasPoint = desktop.viewToCanvas(anchor)

    desktop.zoomAt(anchor, 2.0)

    assert desktop.zoomScale == 2.0
    assert desktop.canvasToView(canvasPoint) == anchor


def testZoomIsClampedAndRejectsNonPositiveDelta() -> None:
    desktop = Desktop(100.0, 100.0)
    desktop.zoomAt(Point(0.0, 0.0), 1000.0)
    assert desktop.zoomScale == Constants.MAX_ZOOM_SCALE
    desktop.zoomAt(Point(0.0, 0.0), 0.000001)
    assert desktop.zoomScale == Constants.MIN_ZOOM_SCALE
    with pytest.raises(ValueError):
        desktop.zoomAt(Point(0.0, 0.0), 0.0)


def testResetViewportPreservesWindowSize() -> None:
    desktop = Desktop(320.0, 240.0)
    desktop.zoomAt(Point(100.0, 100.0), 2.0)
    desktop.pan(10.0, 10.0)
    desktop.resetViewport()

    assert desktop.zoomScale == 1.0
    assert desktop.windowCanvasBBox == BBox(0.0, 0.0, 320.0, 240.0)


@pytest.mark.parametrize(("width", "height"), [(-1.0, 0.0), (0.0, -1.0)])
def testDesktopRejectsNegativeSize(width: float, height: float) -> None:
    with pytest.raises(ValueError):
        Desktop(width, height)
