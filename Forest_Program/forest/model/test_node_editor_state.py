import pytest

from forest.model import NodeEditorState
from forest.shared import BBox
from forest.tree import Leaf


def testEditorLifecycleKeepsDraftSeparateFromNodeUntilCommit() -> None:
    node = Leaf("before")
    popupBBox = BBox(1.0, 2.0, 3.0, 4.0)
    state = NodeEditorState()

    state.begin(node, popupBBox)
    state.updateDraft("after")

    assert state.selectedNode is node
    assert state.editingText == "after"
    assert state.popupBBox == popupBBox
    assert node.text == "before"
    assert state.commit() == "after"
    assert not state.isEditing
    assert state.selectedNode is None


def testCancelClearsAllEditorState() -> None:
    state = NodeEditorState()
    state.begin(Leaf("node"), BBox(1.0, 2.0, 3.0, 4.0))
    state.cancel()

    assert state.selectedNode is None
    assert state.editingText == ""
    assert state.popupBBox == BBox(0.0, 0.0, 0.0, 0.0)


@pytest.mark.parametrize("operation", ["update", "commit"])
def testEditingOperationsRequireSelection(operation: str) -> None:
    state = NodeEditorState()
    with pytest.raises(RuntimeError):
        if operation == "update":
            state.updateDraft("text")
        else:
            state.commit()


def testEditorRejectsInvalidArguments() -> None:
    state = NodeEditorState()
    with pytest.raises(TypeError):
        state.begin("node", BBox(0.0, 0.0, 1.0, 1.0))  # ty: ignore[invalid-argument-type]
    state.begin(Leaf("node"), BBox(0.0, 0.0, 1.0, 1.0))
    with pytest.raises(TypeError):
        state.updateDraft(1)  # ty: ignore[invalid-argument-type]
