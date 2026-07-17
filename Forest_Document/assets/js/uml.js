// Shared Mermaid loader, UML styling, and zoom controls.
const diagramElements = [...document.querySelectorAll("[data-mermaid-source]")];
const relationColors = {
  inheritance: "#c84655",
  composition: "#d97706",
  aggregation: "#2f855a",
  association: "#2563a6",
  realization: "#5b5fc7",
  dependency: "#8b51a5"
};

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

async function loadDiagramSources(elements) {
  await Promise.all(elements.map(async (element) => {
    const sourcePath = element.dataset.mermaidSource;
    const response = await fetch(sourcePath);

    if (!response.ok) {
      throw new Error(`${sourcePath}: ${response.status} ${response.statusText}`);
    }

    element.textContent = await response.text();
  }));
}

function addZoomControls(element, svg) {
  const container = element.closest(".mermaid-container");

  if (!container || container.dataset.umlZoomReady === "true") {
    return;
  }

  const controls = document.createElement("div");
  const buttonSettings = [
    ["out", "−", "UML図を縮小"],
    ["reset", "100%", "表示倍率を100%に戻す"],
    ["in", "＋", "UML図を拡大"]
  ];
  const buttons = {};
  controls.className = "uml-zoom-controls";
  controls.setAttribute("role", "group");
  controls.setAttribute("aria-label", "UML図の表示倍率");

  for (const [name, label, title] of buttonSettings) {
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

  const minimumScale = Number(container.dataset.umlZoomMin ?? "0.5");
  const maximumScale = Number(container.dataset.umlZoomMax ?? "2");
  const scaleStep = Number(container.dataset.umlZoomStep ?? "0.25");
  const initialWidth = svg.getBoundingClientRect().width;
  let scale = 1;
  let touchStartDistance = 0;
  let touchStartScale = 1;
  let gestureStartScale = 1;

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
  const markers = [...svg.querySelectorAll("marker")];

  for (const relation of svg.querySelectorAll("path.relation[data-id]")) {
    const markerNames = [
      relation.getAttribute("marker-start"),
      relation.getAttribute("marker-end")
    ].join(" ");
    const isDashed = relation.classList.contains("edge-pattern-dashed");
    let relationType = isDashed ? "dependency" : "association";

    if (markerNames.includes("composition")) {
      relationType = "composition";
    } else if (markerNames.includes("aggregation")) {
      relationType = "aggregation";
    } else if (markerNames.includes("extension")) {
      relationType = isDashed ? "realization" : "inheritance";
    }

    const relationColor = relationColors[relationType];
    relation.style.setProperty("stroke", relationColor, "important");
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
        const markerFill = relationType === "aggregation" ? "#ffffff" : relationColor;

        for (const shape of coloredMarker.querySelectorAll("path, polygon, circle")) {
          shape.style.setProperty("fill", markerFill, "important");
          shape.style.setProperty("stroke", relationColor, "important");
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

  addZoomControls(element, svg);
}

async function renderDiagrams(elements) {
  const mermaid = await loadMermaid();
  await loadDiagramSources(elements);
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: "default"
  });
  await mermaid.run({ nodes: elements });
  elements.forEach(enhanceDiagram);
}

try {
  await renderDiagrams(diagramElements);
} catch (error) {
  for (const element of diagramElements) {
    element.classList.add("mermaid-error");
    element.textContent = `UML図を表示できませんでした。\n${String(error)}`;
  }
}
