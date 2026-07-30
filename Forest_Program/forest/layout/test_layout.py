from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import pytest

from forest.layout import BBoxCalculator, GraphTraversal, LayoutCalculator
from forest.parser import Parser
from forest.shared import BBox, Constants
from forest.tree import Leaf, Node, Root


REQUIREMENT_TEXTS = Path(__file__).parents[3] / "Forest_Document" / "Requirement" / "texts"


@dataclass
class DesktopStub:
    windowCanvasBBox: BBox


def buildSharedGraph() -> tuple[Root, Node, Node, Leaf]:
    root = Root("root")
    left = Node("left")
    right = Node("right")
    shared = Leaf("shared")
    root.addChild(left)
    root.addChild(right)
    left.addChild(shared)
    right.addChild(shared)
    return root, left, right, shared


def testTraversalVisitsSharedNodeOnce() -> None:
    root, _, _, _ = buildSharedGraph()
    traversal = GraphTraversal()
    assert [node.text for node in traversal.reachableFrom(root)] == ["root", "left", "right", "shared"]
    assert traversal.edgesFrom(root) == traversal.allEdges([root])
    assert len(traversal.allEdges([root])) == 4


def testTraversalTerminatesOnCycle() -> None:
    first = Root("first")
    second = Node("second")
    first.addChild(second)
    second.addChild(first)
    traversal = GraphTraversal()

    assert traversal.reachableFrom(first) == [first, second]
    assert traversal.rootNodes([first]) == [first]


def testLayoutTerminatesOnCycle() -> None:
    first = Root("first")
    second = Node("second")
    first.addChild(second)
    second.addChild(first)

    steps = LayoutCalculator().createInitialSteps([first], DesktopStub(BBox(0.0, 0.0, 800.0, 600.0)))
    assert set(steps[-1].positions) == {first, second}


def testBBoxCalculatorReturnsUnionAndEmptyBounds() -> None:
    root = Root("root", BBox(10.0, 20.0, 30.0, 10.0))
    leaf = Leaf("leaf", BBox(50.0, 5.0, 20.0, 40.0))
    root.addChild(leaf)
    calculator = BBoxCalculator()

    assert calculator.forNodes([root]) == BBox(10.0, 5.0, 60.0, 40.0)
    assert calculator.forSubgraph(leaf) == leaf.bbox
    assert calculator.forNodes([]) == BBox(0.0, 0.0, 0.0, 0.0)


def testInitialLayoutUsesRequiredSpacingAndProducesSteps() -> None:
    root, left, right, shared = buildSharedGraph()
    calculator = LayoutCalculator()
    steps = calculator.createInitialSteps([root], DesktopStub(BBox(0.0, 0.0, 800.0, 600.0)))
    final = steps[-1].positions

    assert len(steps) == 4
    assert final[left].x - (final[root].x + final[root].width) == Constants.HORIZONTAL_SPACING
    assert final[right].y - (final[left].y + final[left].height) == Constants.VERTICAL_SPACING
    assert list(final).count(shared) == 1


def testInitialLayoutWrapsNodesAtViewportHeight() -> None:
    root = Root("root")
    children = [Leaf(str(index)) for index in range(3)]
    for child in children:
        root.addChild(child)
    first = LayoutCalculator().createInitialSteps([root], DesktopStub(BBox(0.0, 0.0, 100.0, 25.0)))[0]
    assert len({box.x for box in first.positions.values()}) > 1


def testFinalLayoutCentersParentBetweenChildren() -> None:
    root = Root("root")
    first = Leaf("first")
    second = Leaf("second")
    root.addChild(first)
    root.addChild(second)
    final = (
        LayoutCalculator()
        .createInitialSteps(
            [root],
            DesktopStub(BBox(0.0, 0.0, 800.0, 600.0)),
        )[-1]
        .positions
    )

    rootCenter = final[root].y + final[root].height / 2
    firstCenter = final[first].y + final[first].height / 2
    secondCenter = final[second].y + final[second].height / 2
    assert rootCenter == (firstCenter + secondCenter) / 2


def testRecalculateMeasuresRenamedNodeAgain() -> None:
    root = Root("r")
    leaf = Leaf("x")
    root.addChild(leaf)
    calculator = LayoutCalculator()
    initial = calculator.createInitialSteps([root], DesktopStub(BBox(0.0, 0.0, 800.0, 600.0)))[-1]
    leaf.bbox = initial.positions[leaf]
    oldWidth = initial.positions[leaf].width
    leaf.rename("a much longer node name")

    recalculated = calculator.recalculate([root], leaf)[0]
    assert recalculated.positions[leaf].width > oldWidth


def testRecalculateUsesPartialUpdateWhenLayerWidthDoesNotChange() -> None:
    root = Root("root")
    short = Leaf("a")
    widest = Leaf("a very wide sibling")
    root.addChild(short)
    root.addChild(widest)
    calculator = LayoutCalculator()
    final = calculator.createInitialSteps([root], DesktopStub(BBox(0.0, 0.0, 800.0, 600.0)))[-1]
    for node, bbox in final.positions.items():
        node.bbox = bbox
    short.rename("medium")

    recalculated = calculator.recalculate([root], short)[0]
    assert set(recalculated.positions) == {short}
    assert recalculated.positions[short].width < widest.bbox.width


def testEmptyLayoutHasNoSteps() -> None:
    assert LayoutCalculator().createInitialSteps([], DesktopStub(BBox(0.0, 0.0, 1.0, 1.0))) == []


def testOneHundredNodesLayoutWithinThreeSeconds() -> None:
    root = Root("root")
    for index in range(99):
        root.addChild(Leaf(f"leaf-{index}"))
    start = perf_counter()
    LayoutCalculator().createInitialSteps([root], DesktopStub(BBox(0.0, 0.0, 1200.0, 800.0)))
    assert perf_counter() - start < 3.0


@pytest.mark.parametrize("filename", ["tree.txt", "forest.txt", "semilattice.txt"])
def testRequirementSamplesProduceForwardNonOverlappingLayout(filename: str) -> None:
    roots = Parser().parse((REQUIREMENT_TEXTS / filename).read_text(encoding="utf-8"))
    final = LayoutCalculator().createInitialSteps(roots, DesktopStub(BBox(0.0, 0.0, 1200.0, 800.0)))[-1]
    boxes = list(final.positions.values())

    for index, first in enumerate(boxes):
        for second in boxes[index + 1 :]:
            separated = (
                first.x + first.width <= second.x
                or second.x + second.width <= first.x
                or first.y + first.height <= second.y
                or second.y + second.height <= first.y
            )
            assert separated
    for parent, child in GraphTraversal().allEdges(roots):
        assert final.positions[parent].x < final.positions[child].x


def testTraversalInternalOperationsPreserveIdentity() -> None:
    root, left, right, shared = buildSharedGraph()
    traversal = GraphTraversal()
    assert traversal._unique([root, root]) == [root]
    assert traversal._allNodes([root]) == [root, left, right, shared]


def testBBoxInternalBoundsOperation() -> None:
    first = Leaf("first", BBox(-5.0, 3.0, 10.0, 7.0))
    second = Leaf("second", BBox(10.0, -2.0, 5.0, 4.0))
    assert BBoxCalculator()._bounds([first, second]) == BBox(-5.0, -2.0, 20.0, 12.0)


def testLayoutInternalOperationsProduceConsistentPositions() -> None:
    root, left, right, shared = buildSharedGraph()
    calculator = LayoutCalculator()
    viewport = BBox(0.0, 0.0, 800.0, 600.0)
    calculator._buildParentIndex([root])
    measured = calculator._measure(root)
    initial = calculator._initialPositions([root, left, right, shared], viewport)
    positions, depths = calculator._hierarchicalPositions([root], viewport)

    assert measured.width >= Constants.MIN_NODE_WIDTH
    assert calculator._allNodes([root]) == [root, left, right, shared]
    assert set(initial) == {root, left, right, shared}
    assert set(positions) == {root, left, right, shared}
    assert depths == {root: 0, left: 1, right: 1, shared: 2}
    assert calculator._depthsFor([root]) == depths
    assert set(calculator._placeRoots([root], viewport)[0].positions) == {root}
    assert len(calculator._placeDescendants(root)) == 3
    assert set(calculator._resolveSharedNodes([root])[0].positions) == {shared}
