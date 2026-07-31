from pathlib import Path

import pytest

from forest.layout import GraphTraversal
from forest.parser import ParseError, Parser
from forest.tree import BaseNode, Leaf, Root

REQUIREMENT_TEXTS = Path(__file__).parents[3] / "Forest_Document" / "Requirement" / "texts"


@pytest.mark.parametrize(
    ("filename", "rootCount", "nodeCount"),
    [("tree.txt", 1, 70), ("forest.txt", 3, 72), ("semilattice.txt", 3, 69)],
)
def testParseRequirementSamples(filename: str, rootCount: int, nodeCount: int) -> None:
    roots = Parser().parse((REQUIREMENT_TEXTS / filename).read_text(encoding="utf-8"))
    traversal = GraphTraversal()
    nodes = {node for root in roots for node in traversal.reachableFrom(root)}

    assert len(roots) == rootCount
    assert len(nodes) == nodeCount


def testParsePreservesDistinctNodesWithSameName() -> None:
    roots = Parser().parse((REQUIREMENT_TEXTS / "forest.txt").read_text(encoding="utf-8"))
    assert [root.text for root in roots] == ["Object", "Object", "Object"]
    assert len({id(root) for root in roots}) == 3


def testParseSharesNodeReferencedByMultipleBranches() -> None:
    roots = Parser().parse((REQUIREMENT_TEXTS / "semilattice.txt").read_text(encoding="utf-8"))
    traversal = GraphTraversal()
    nodes = {node.text: node for root in roots for node in traversal.reachableFrom(root)}
    smallDouble = nodes["SmallDouble"]
    parents = {parent.text for parent, child in traversal.allEdges(roots) if child is smallDouble}
    assert parents == {"LimitedPrecisionReal", "Duration"}


def testParseEmptyTextReturnsNoRoots() -> None:
    assert Parser().parse("  \n") == []


def testParseTreesAndNodesWithoutBranchesSharesNames() -> None:
    sourceText = """trees:
RootA
|-- Shared
RootB
|-- Shared
nodes:
1, RootA
2, RootB
3, Shared
"""
    roots = Parser().parse(sourceText)

    assert [root.text for root in roots] == ["RootA", "RootB"]
    assert roots[0].children()[0] is roots[1].children()[0]


def testParseSingleRootWithoutBranches() -> None:
    roots = Parser().parse("trees:\nRoot\nnodes:\n1, Root\n")
    assert len(roots) == 1
    assert isinstance(roots[0], Root)


@pytest.mark.parametrize(
    "sourceText",
    [
        "nodes:\n1, Root\n",
        "trees:\nRoot\nnodes:\n1, Root\nbranches:\n1, 2\n",
        "trees:\nRoot\nnodes:\nnot-an-id, Root\nbranches:\n",
        "trees:\nRoot\nnodes:\n1, Root\n1, Other\nbranches:\n",
        "trees:\nUnknown\nnodes:\n1, Root\nbranches:\n",
    ],
)
def testParseRejectsMalformedText(sourceText: str) -> None:
    with pytest.raises(ParseError):
        Parser().parse(sourceText)


def testParseRejectsNonStringInput() -> None:
    with pytest.raises(TypeError):
        Parser().parse(None)  # ty: ignore[invalid-argument-type]


def testParserInternalSectionAndRegistryOperations() -> None:
    parser = Parser()
    sections = parser._splitSections("trees:\nRoot\nnodes:\n1, Root\n2, Leaf\nbranches:\n1, 2\n")
    branches = parser._parseBranches(sections["branches"])
    labels = parser._parseNodeLabels(sections["nodes"])
    registry = parser._parseNodeRegistry(sections["nodes"], branches)
    parser._connectBranches(branches, registry)

    assert parser._treeLine("|-- Leaf") == (1, "Leaf")
    assert labels == {1: "Root", 2: "Leaf"}
    assert isinstance(registry[1], Root)
    assert isinstance(registry[2], Leaf)
    assert registry[1].children() == (registry[2],)


def testParserInternalTreeAndNameLookupOperations() -> None:
    parser = Parser()
    registry: dict[int, BaseNode] = {1: Root("Root"), 2: Leaf("Leaf")}
    parser._parseTrees(["Root", "|-- Leaf"], registry)

    assert registry[1].children() == (registry[2],)
    assert parser._nodeFor("Leaf", {"Leaf": registry[2]}) is registry[2]


def testParserBuildsBranchesFromTreeStructure() -> None:
    parser = Parser()
    branches, rootIds = parser._branchesFromTrees(["Root", "|-- Leaf"], {1: "Root", 2: "Leaf"})
    assert branches == [(1, 2)]
    assert rootIds == {1}
