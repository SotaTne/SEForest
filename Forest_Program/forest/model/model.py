"""アプリケーション状態とForestのユースケースを集約する。"""

from __future__ import annotations

from pathlib import Path

from forest.controller.command_port import ModelCommandPort
from forest.image_output import ImageRenderer
from forest.layout import BBoxCalculator, LayoutCalculator
from forest.model.events import EventEmitter, ModelEvent
from forest.model.node_editor_state import NodeEditorState
from forest.parser import Parser
from forest.shared import BBox, Constants, Desktop, LayoutStep, Point
from forest.tree import BaseNode


class Model(ModelCommandPort):
    """MVCのViewから独立した状態遷移とユースケースを提供する。"""

    def __init__(
        self,
        desktop: Desktop | None = None,
        parser: Parser | None = None,
        layoutCalculator: LayoutCalculator | None = None,
        bboxCalculator: BBoxCalculator | None = None,
        imageRenderer: ImageRenderer | None = None,
    ) -> None:
        self.events = EventEmitter[ModelEvent]()
        self._sourceText = ""
        self._nodes: list[BaseNode] = []
        self._canvasBBox = BBox(0.0, 0.0, 0.0, 0.0)
        self._outputFile: Path | None = None
        self._desktop = desktop or Desktop()
        self._nodeEditorState: NodeEditorState | None = None
        self._currentStep = 0
        self._totalSteps = 0
        self._isPlaying = False
        self._layoutSteps: list[LayoutStep] = []
        self._parser = parser or Parser()
        self._layoutCalculator = layoutCalculator or LayoutCalculator()
        self._bboxCalculator = bboxCalculator or BBoxCalculator()
        self._imageRenderer = imageRenderer or ImageRenderer()

    @property
    def sourceText(self) -> str:
        return self._sourceText

    @property
    def nodes(self) -> tuple[BaseNode, ...]:
        return tuple(self._nodes)

    @property
    def canvasBBox(self) -> BBox:
        return self._canvasBBox

    @property
    def outputFile(self) -> Path | None:
        return self._outputFile

    @property
    def desktop(self) -> Desktop:
        return self._desktop

    @property
    def nodeEditorState(self) -> NodeEditorState | None:
        return self._nodeEditorState

    @property
    def currentStep(self) -> int:
        return self._currentStep

    @property
    def totalSteps(self) -> int:
        return self._totalSteps

    @property
    def isPlaying(self) -> bool:
        return self._isPlaying

    @property
    def layoutSteps(self) -> tuple[LayoutStep, ...]:
        return tuple(self._layoutSteps)

    def loadFile(self, inputPath: Path) -> None:
        """UTF-8のForestファイルを読み込み、解析と配置を行う。"""

        if not isinstance(inputPath, Path):
            raise TypeError("inputPath must be a Path")
        self.loadText(inputPath.read_text(encoding="utf-8"))

    def loadText(self, sourceText: str) -> None:
        """Forestテキストを解析し、初期配置段階へ置き換える。"""

        if not isinstance(sourceText, str):
            raise TypeError("sourceText must be a string")
        nodes = self._parser.parse(sourceText)
        steps = self._layoutCalculator.createInitialSteps(nodes, self._desktop)
        self._sourceText = sourceText
        self._nodes = nodes
        self._nodeEditorState = None
        self._isPlaying = False
        self._replaceLayoutSteps(steps)
        self._notify(ModelEvent.NODES_CHANGED)
        self._notify(ModelEvent.SELECTION_CHANGED)
        self._notify(ModelEvent.PLAYBACK_CHANGED)

    def selectNode(self, node: BaseNode, popupBBox: BBox) -> None:
        """表示中のノードを選択し、編集状態を開始する。"""

        if node not in self._nodes and all(node not in step.positions for step in self._layoutSteps):
            raise ValueError("node is not part of the model")
        state = NodeEditorState()
        state.begin(node, popupBBox)
        self._nodeEditorState = state
        self._notify(ModelEvent.SELECTION_CHANGED)
        self._notify(ModelEvent.EDITOR_CHANGED)

    def clearSelection(self) -> None:
        """選択と編集中の下書きを破棄する。"""

        if self._nodeEditorState is None:
            return
        self._nodeEditorState.cancel()
        self._nodeEditorState = None
        self._notify(ModelEvent.SELECTION_CHANGED)
        self._notify(ModelEvent.EDITOR_CHANGED)

    def clearTree(self) -> None:
        """読み込んだツリーと派生状態を破棄し、ファイル選択前へ戻す。"""

        if not self._nodes and not self._sourceText:
            return
        self._sourceText = ""
        self._nodes = []
        self._canvasBBox = BBox(0.0, 0.0, 0.0, 0.0)
        self._outputFile = None
        self._nodeEditorState = None
        self._currentStep = 0
        self._totalSteps = 0
        self._isPlaying = False
        self._layoutSteps = []
        self._desktop.resetViewport()
        self._notify(ModelEvent.NODES_CHANGED)
        self._notify(ModelEvent.SELECTION_CHANGED)
        self._notify(ModelEvent.EDITOR_CHANGED)
        self._notify(ModelEvent.PLAYBACK_CHANGED)
        self._notify(ModelEvent.DESKTOP_CHANGED)

    def renameSelectedNode(self, text: str) -> None:
        """選択ノードを改名し、必要な配置を再計算する。"""

        if self._nodeEditorState is None or self._nodeEditorState.selectedNode is None:
            raise RuntimeError("no node is selected")
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        selectedNode = self._nodeEditorState.selectedNode
        oldText = selectedNode.text
        selectedNode.rename(text)
        try:
            steps = self._layoutCalculator.recalculate(self._nodes, selectedNode)
        except Exception:
            selectedNode.rename(oldText)
            raise
        self._nodeEditorState.cancel()
        self._nodeEditorState = None
        self._replaceLayoutSteps(steps)
        self._notify(ModelEvent.NODES_CHANGED)
        self._notify(ModelEvent.SELECTION_CHANGED)
        self._notify(ModelEvent.EDITOR_CHANGED)

    def showStep(self, index: int) -> None:
        """指定された配置段階を適用する。"""

        if not isinstance(index, int):
            raise TypeError("index must be an integer")
        if index < 0 or index >= self._totalSteps:
            raise IndexError("layout step index is out of range")
        self._currentStep = index
        self._applyLayoutStep(self._layoutSteps[index])
        self._notify(ModelEvent.LAYOUT_CHANGED)
        self._notify(ModelEvent.PLAYBACK_CHANGED)

    def showPreviousStep(self) -> None:
        """前の配置段階があれば表示する。"""

        if self._totalSteps and self._currentStep > 0:
            self.showStep(self._currentStep - 1)

    def showNextStep(self) -> None:
        """次の配置段階があれば表示する。"""

        if self._totalSteps and self._currentStep + 1 < self._totalSteps:
            self.showStep(self._currentStep + 1)

    def setPlaying(self, isPlaying: bool) -> None:
        """配置アニメーションの再生状態を設定する。"""

        if not isinstance(isPlaying, bool):
            raise TypeError("isPlaying must be a boolean")
        if self._isPlaying == isPlaying:
            return
        if isPlaying and self._totalSteps and self._currentStep == self._totalSteps - 1:
            if self._totalSteps == 1 and self._nodes:
                steps = self._layoutCalculator.createInitialSteps(self._nodes, self._desktop)
                self._replaceLayoutSteps(steps)
            else:
                self.showStep(0)
        self._isPlaying = isPlaying
        self._notify(ModelEvent.PLAYBACK_CHANGED)

    def exportCanvas(self, outputPath: Path) -> None:
        """配置済みのCanvas全体をPNGへ出力する。"""

        self._validateOutputPath(outputPath)
        self._imageRenderer.renderCanvas(self._nodes, outputPath)
        self._outputFile = outputPath

    def exportSelectedSubgraph(self, outputPath: Path) -> None:
        """選択ノードを起点とする部分グラフをPNGへ出力する。"""

        self._validateOutputPath(outputPath)
        if self._nodeEditorState is None or self._nodeEditorState.selectedNode is None:
            raise RuntimeError("no node is selected")
        self._imageRenderer.renderSubgraph(self._nodeEditorState.selectedNode, outputPath)
        self._outputFile = outputPath

    def resizeDesktop(self, width: float, height: float) -> None:
        self._desktop.resize(width, height)
        self._notify(ModelEvent.DESKTOP_CHANGED)

    def panDesktop(self, dx: float, dy: float) -> None:
        """View座標の移動量で表示領域をパンする。"""

        if not self._nodes:
            return
        viewport = self._desktop.windowCanvasBBox
        scale = self._desktop.zoomScale
        requestedX = viewport.x - dx / scale
        requestedY = viewport.y - dy / scale
        minimumX, maximumX, minimumY, maximumY = self._viewportLimits()
        boundedX = min(maximumX, max(minimumX, requestedX))
        boundedY = min(maximumY, max(minimumY, requestedY))
        if boundedX == viewport.x and boundedY == viewport.y:
            return
        self._moveDesktopOriginTo(boundedX, boundedY)
        self._notify(ModelEvent.DESKTOP_CHANGED)

    def zoomDesktopAt(self, anchor: Point, scaleDelta: float) -> None:
        """指定したView座標を中心に表示領域を拡大または縮小する。"""

        if not isinstance(anchor, Point):
            raise TypeError("anchor must be a Point")
        self._desktop.zoomAt(anchor, scaleDelta)
        if self._nodes:
            self._clampDesktopViewport()
        self._notify(ModelEvent.DESKTOP_CHANGED)

    def resetDesktopViewport(self) -> None:
        """パン位置と拡大率を初期状態へ戻す。"""

        self._desktop.resetViewport()
        self._notify(ModelEvent.DESKTOP_CHANGED)

    def _replaceLayoutSteps(self, steps: list[LayoutStep]) -> None:
        self._layoutSteps = list(steps)
        self._totalSteps = len(steps)
        self._currentStep = 0
        if steps:
            self._applyLayoutStep(steps[0])
        else:
            self._updateCanvasBBox()
        self._notify(ModelEvent.LAYOUT_CHANGED)

    def _applyLayoutStep(self, step: LayoutStep) -> None:
        for node, bbox in step.positions.items():
            node.bbox = bbox
        self._updateCanvasBBox()

    def _updateCanvasBBox(self) -> None:
        self._canvasBBox = self._bboxCalculator.forNodes(self._nodes)

    def _viewportLimits(self) -> tuple[float, float, float, float]:
        viewport = self._desktop.windowCanvasBBox
        canvasMargin = Constants.CANVAS_VIEWPORT_MARGIN / self._desktop.zoomScale
        leftAlignedX = self._canvasBBox.x - canvasMargin
        rightAlignedX = self._canvasBBox.x + self._canvasBBox.width + canvasMargin - viewport.width
        topAlignedY = self._canvasBBox.y - canvasMargin
        bottomAlignedY = self._canvasBBox.y + self._canvasBBox.height + canvasMargin - viewport.height
        return (
            min(leftAlignedX, rightAlignedX),
            max(leftAlignedX, rightAlignedX),
            min(topAlignedY, bottomAlignedY),
            max(topAlignedY, bottomAlignedY),
        )

    def _clampDesktopViewport(self) -> None:
        viewport = self._desktop.windowCanvasBBox
        minimumX, maximumX, minimumY, maximumY = self._viewportLimits()
        boundedX = min(maximumX, max(minimumX, viewport.x))
        boundedY = min(maximumY, max(minimumY, viewport.y))
        self._moveDesktopOriginTo(boundedX, boundedY)

    def _moveDesktopOriginTo(self, x: float, y: float) -> None:
        viewport = self._desktop.windowCanvasBBox
        scale = self._desktop.zoomScale
        self._desktop.pan((viewport.x - x) * scale, (viewport.y - y) * scale)

    def _notify(self, event: ModelEvent) -> None:
        self.events.notify(event)

    @staticmethod
    def _validateOutputPath(outputPath: Path) -> None:
        if not isinstance(outputPath, Path):
            raise TypeError("outputPath must be a Path")
