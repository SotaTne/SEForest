// Shared Mermaid rendering, relation styling, and diagram controls.
const DIAGRAM_ELEMENTS = [...document.querySelectorAll("[data-mermaid-source]")];
const RELATION_STYLES = {
  inheritance: { color: "#c84655", background: "#f9e4e7" },
  composition: { color: "#d97706", background: "#ffebd1" },
  aggregation: { color: "#2f855a", background: "#e5f5f1" },
  association: { color: "#2563a6", background: "#e2effb" },
  realization: { color: "#5b5fc7", background: "#e8e8fa" },
  dependency: { color: "#8b51a5", background: "#f1e5f6" }
};
const CONTROL_BUTTONS = [
  ["out", "−", "UML図を縮小"],
  ["reset", "100%", "表示倍率を100%に戻す"],
  ["in", "＋", "UML図を拡大"],
  ["save", "保存", "UML図をSVG形式で保存"]
];
const MULTIPLICITY_RELATION_PATTERN =
  /^\s*([\w-]+)(\s+"[^"]+")?\s+(<\|--|--\*|\*--|--o|o--|-->|<--|\.\.>|<\.\.|--)\s+("[^"]+"\s+)?([\w-]+)/;

async function loadMermaid() {
  const [mermaidModule, elkModule] = await Promise.all([
    import("https://cdn.jsdelivr.net/npm/mermaid@11.16.0/dist/mermaid.esm.min.mjs"),
    import(
      "https://cdn.jsdelivr.net/npm/@mermaid-js/layout-elk@0.2.2/dist/mermaid-layout-elk.esm.min.mjs"
    )
  ]);

  mermaidModule.default.registerLayoutLoaders(elkModule.default);
  return mermaidModule.default;
}

function getRelationType(relation) {
  const markerNames = [
    relation.getAttribute("marker-start"),
    relation.getAttribute("marker-end")
  ].join(" ");
  const isDashed = relation.classList.contains("edge-pattern-dashed");

  if (markerNames.includes("composition")) {
    return "composition";
  }
  if (markerNames.includes("aggregation")) {
    return "aggregation";
  }
  if (markerNames.includes("extension")) {
    return isDashed ? "realization" : "inheritance";
  }
  return isDashed ? "dependency" : "association";
}

function addDiagramControls(element, svg) {
  const container = element.closest(".mermaid-container");

  if (!container || container.dataset.umlZoomReady === "true") {
    return;
  }

  const controls = document.createElement("div");
  const buttons = {};
  controls.className = "uml-zoom-controls";
  controls.setAttribute("role", "group");
  controls.setAttribute("aria-label", "UML図の操作");

  for (const [name, label, title] of CONTROL_BUTTONS) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `uml-zoom-${name}`;
    button.textContent = label;
    button.title = title;
    button.setAttribute("aria-label", title);
    buttons[name] = button;
    controls.append(button);
  }

  container.before(controls);

  const minimumScale = Number(container.dataset.umlZoomMin ?? "0.25");
  const maximumScale = Number(container.dataset.umlZoomMax ?? "2");
  const scaleStep = Number(container.dataset.umlZoomStep ?? "0.25");
  const initialWidth = svg.getBoundingClientRect().width;
  const initialHeight = container.getBoundingClientRect().height;
  let scale = 1;
  let touchStartDistance = 0;
  let touchStartScale = 1;
  let gestureStartScale = 1;
  container.style.height = `${initialHeight}px`;

  const applyScale = (anchor = null) => {
    const previousBounds = svg.getBoundingClientRect();
    const hasAnchor = Number.isFinite(anchor?.clientX) && Number.isFinite(anchor?.clientY);
    const anchorRatio = hasAnchor && previousBounds.width > 0 && previousBounds.height > 0
      ? {
          x: Math.min(1, Math.max(0, (anchor.clientX - previousBounds.left) / previousBounds.width)),
          y: Math.min(1, Math.max(0, (anchor.clientY - previousBounds.top) / previousBounds.height))
        }
      : null;

    scale = Math.min(maximumScale, Math.max(minimumScale, scale));
    svg.style.width = `${initialWidth * scale}px`;
    svg.style.minWidth = "0px";
    svg.style.maxWidth = "none";
    container.style.overscrollBehavior = scale <= 1 ? "auto" : "contain";
    buttons.reset.textContent = `${Math.round(scale * 100)}%`;
    buttons.out.disabled = scale <= minimumScale;
    buttons.in.disabled = scale >= maximumScale;

    if (anchorRatio) {
      const currentBounds = svg.getBoundingClientRect();
      const previousX = previousBounds.left + previousBounds.width * anchorRatio.x;
      const previousY = previousBounds.top + previousBounds.height * anchorRatio.y;
      const currentX = currentBounds.left + currentBounds.width * anchorRatio.x;
      const currentY = currentBounds.top + currentBounds.height * anchorRatio.y;
      container.scrollLeft += currentX - previousX;
      container.scrollTop += currentY - previousY;
    }
  };

  buttons.out.addEventListener("click", () => {
    scale -= scaleStep;
    applyScale();
  });
  buttons.reset.addEventListener("click", () => {
    scale = 1;
    applyScale();
  });
  buttons.in.addEventListener("click", () => {
    scale += scaleStep;
    applyScale();
  });
  buttons.save.addEventListener("click", () => {
    const savedSvg = svg.cloneNode(true);
    const viewBox = svg.viewBox.baseVal;
    const sourcePath = element.dataset.mermaidSource ?? "uml.mmd";
    const sourceName = sourcePath.split("/").pop() ?? "uml.mmd";
    const fileName = sourceName.replace(/\.mmd$/i, ".svg");

    savedSvg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    savedSvg.setAttribute("width", String(viewBox.width));
    savedSvg.setAttribute("height", String(viewBox.height));
    savedSvg.style.removeProperty("width");
    savedSvg.style.removeProperty("min-width");
    savedSvg.style.removeProperty("max-width");

    const svgText = new XMLSerializer().serializeToString(savedSvg);
    const svgFile = new Blob([svgText], { type: "image/svg+xml;charset=utf-8" });
    const downloadUrl = URL.createObjectURL(svgFile);
    const downloadLink = document.createElement("a");
    downloadLink.href = downloadUrl;
    downloadLink.download = fileName;
    downloadLink.click();
    setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
  });
  container.addEventListener("wheel", (event) => {
    if (!event.ctrlKey && !event.metaKey) {
      return;
    }

    event.preventDefault();
    scale *= Math.exp(-event.deltaY * 0.002);
    applyScale(event);
  }, { passive: false });
  container.addEventListener("touchstart", (event) => {
    if (event.touches.length === 2) {
      const [firstTouch, secondTouch] = event.touches;
      touchStartDistance = Math.hypot(
        secondTouch.clientX - firstTouch.clientX,
        secondTouch.clientY - firstTouch.clientY
      );
      touchStartScale = scale;
    }
  }, { passive: true });
  container.addEventListener("touchmove", (event) => {
    if (event.touches.length !== 2 || touchStartDistance === 0) {
      return;
    }

    event.preventDefault();
    const [firstTouch, secondTouch] = event.touches;
    const currentDistance = Math.hypot(
      secondTouch.clientX - firstTouch.clientX,
      secondTouch.clientY - firstTouch.clientY
    );
    scale = touchStartScale * (currentDistance / touchStartDistance);
    applyScale({
      clientX: (firstTouch.clientX + secondTouch.clientX) / 2,
      clientY: (firstTouch.clientY + secondTouch.clientY) / 2
    });
  }, { passive: false });
  container.addEventListener("touchend", (event) => {
    if (event.touches.length < 2) {
      touchStartDistance = 0;
    }
  }, { passive: true });
  container.addEventListener("gesturestart", (event) => {
    event.preventDefault();
    gestureStartScale = scale;
  }, { passive: false });
  container.addEventListener("gesturechange", (event) => {
    event.preventDefault();
    scale = gestureStartScale * event.scale;
    applyScale(event);
  }, { passive: false });

  container.dataset.umlZoomReady = "true";
  applyScale();
}

function enhanceDiagram(element) {
  const svg = element.querySelector("svg");

  if (!svg) {
    return;
  }

  const relationTypes = new Map();
  const relations = [...svg.querySelectorAll("path.relation[data-id]")];
  const markers = [...svg.querySelectorAll("marker")];

  // Apply one color scheme to each relation line, marker, and label.
  for (const relation of relations) {
    const relationType = getRelationType(relation);
    const relationStyle = RELATION_STYLES[relationType];
    relation.style.setProperty("stroke", relationStyle.color, "important");
    relationTypes.set(relation.dataset.id, relationType);

    for (const markerAttribute of ["marker-start", "marker-end"]) {
      const markerReference = relation.getAttribute(markerAttribute);
      const originalMarkerId = markerReference?.match(/#([^)]+)/)?.[1];

      if (!originalMarkerId) {
        continue;
      }

      const coloredMarkerId = `${originalMarkerId}-${relationType}`;
      let coloredMarker = markers.find((marker) => marker.id === coloredMarkerId);

      if (!coloredMarker) {
        const originalMarker = markers.find((marker) => marker.id === originalMarkerId);

        if (!originalMarker) {
          continue;
        }

        coloredMarker = originalMarker.cloneNode(true);
        coloredMarker.id = coloredMarkerId;
        const markerFill = relationType === "aggregation" ? "#ffffff" : relationStyle.color;

        for (const shape of coloredMarker.querySelectorAll("path, polygon, circle")) {
          shape.style.setProperty("fill", markerFill, "important");
          shape.style.setProperty("stroke", relationStyle.color, "important");
        }

        originalMarker.parentNode.append(coloredMarker);
        markers.push(coloredMarker);
      }

      relation.setAttribute(markerAttribute, `url(#${coloredMarker.id})`);
    }
  }

  for (const label of svg.querySelectorAll(".edgeLabels .label[data-id]")) {
    const relationType = relationTypes.get(label.dataset.id);

    if (relationType) {
      label.closest(".edgeLabel")?.classList.add(`relation-label-${relationType}`);
    }
  }

  // Mermaid does not link multiplicity labels to their relation paths.
  // Match them with the source definition, then center and color each label.
  const multiplicityRelations = (element.umlSourceText ?? "")
    .split("\n")
    .map((line) => line.match(MULTIPLICITY_RELATION_PATTERN))
    .filter((match) => match && (match[2] || match[4]))
    .map((match) => {
      const [, source, sourceMultiplicity, arrow, targetMultiplicity, target] = match;
      const relationType = arrow.includes("*")
        ? "composition"
        : arrow.includes("o") ? "aggregation" : "association";
      const relation = relations.find((path) => (
        path.dataset.id.startsWith(`id_${source}_${target}_`)
        && relationTypes.get(path.dataset.id) === relationType
      ));
      return {
        relation,
        relationType,
        terminalAtStart: Boolean(sourceMultiplicity && !targetMultiplicity)
      };
    });

  const terminals = [...svg.querySelectorAll(".edgeTerminals")];

  for (const [index, terminal] of terminals.entries()) {
    const multiplicityRelation = multiplicityRelations[index];
    const labelBox = terminal.querySelector("foreignObject > div");

    if (!multiplicityRelation?.relation || !labelBox) {
      continue;
    }

    const { relation, relationType, terminalAtStart } = multiplicityRelation;
    const relationStyle = RELATION_STYLES[relationType];
    const endpoint = relation.getPointAtLength(
      terminalAtStart ? 0 : relation.getTotalLength()
    );
    const currentTransform = terminal.getAttribute("transform") ?? "";
    const currentY = currentTransform.match(/translate\([^, ]+[, ]+([^\)]+)\)/)?.[1];

    if (currentY) {
      terminal.setAttribute("transform", `translate(${endpoint.x}, ${currentY})`);
    }

    const foreignObject = labelBox.closest("foreignObject");

    if (foreignObject?.parentElement === terminal) {
      const labelWidth = Number(foreignObject.getAttribute("width"));

      if (Number.isFinite(labelWidth) && labelWidth > 0) {
        foreignObject.setAttribute("x", String(-labelWidth / 2));
      }
    }

    labelBox.style.setProperty("background-color", relationStyle.background, "important");
    labelBox.style.setProperty("color", relationStyle.color, "important");
  }

  addDiagramControls(element, svg);
}

async function renderDiagrams(elements) {
  const mermaid = await loadMermaid();
  await Promise.all(elements.map(async (element) => {
    const sourcePath = element.dataset.mermaidSource;
    const response = await fetch(sourcePath);

    if (!response.ok) {
      throw new Error(`${sourcePath}: ${response.status} ${response.statusText}`);
    }

    element.umlSourceText = await response.text();
    element.textContent = element.umlSourceText;
  }));
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: "default"
  });
  await mermaid.run({ nodes: elements });
  elements.forEach(enhanceDiagram);
}

try {
  await renderDiagrams(DIAGRAM_ELEMENTS);
} catch (error) {
  for (const element of DIAGRAM_ELEMENTS) {
    element.classList.add("mermaid-error");
    element.textContent = `UML図を表示できませんでした。\n${String(error)}`;
  }
}
