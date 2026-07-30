import pytest

from forest.shared import BBox
from forest.tree import Leaf, Node, Root


def testBaseNodeStoresAndRenamesText() -> None:
    leaf = Leaf("before")
    leaf.rename("after")
    assert leaf.text == "after"


def testRenameRejectsNonStringText() -> None:
    leaf = Leaf("leaf")
    with pytest.raises(TypeError):
        leaf.rename(1)  # ty: ignore[invalid-argument-type]


def testBaseNodeRejectsNonStringText() -> None:
    with pytest.raises(TypeError):
        Leaf(1)  # ty: ignore[invalid-argument-type]


def testBBoxCanBeAppliedByModel() -> None:
    leaf = Leaf("leaf")
    leaf.bbox = BBox(1.0, 2.0, 3.0, 4.0)
    assert leaf.bbox == BBox(1.0, 2.0, 3.0, 4.0)


def testNodeAndRootExposeImmutableChildren() -> None:
    child = Leaf("child")
    node = Node("node")
    root = Root("root")
    node.addChild(child)
    root.addChild(node)

    assert node.children() == (child,)
    assert root.children() == (node,)


def testSharedChildRetainsIdentity() -> None:
    shared = Leaf("shared")
    left = Node("left")
    right = Node("right")
    left.addChild(shared)
    right.addChild(shared)

    assert left.children()[0] is right.children()[0]


def testDuplicateChildIsIgnored() -> None:
    child = Leaf("child")
    node = Node("node")
    node.addChild(child)
    node.addChild(child)
    assert node.children() == (child,)


def testLeafHasNoChildren() -> None:
    assert Leaf("leaf").children() == ()
