// Shared Mermaid loader and UML relation styling.
const diagramElements = [...document.querySelectorAll("[data-mermaid-source]")];

try {
  const [{ default: mermaid }, { default: elkLayouts }] = await Promise.all([
    import("https://cdn.jsdelivr.net/npm/mermaid@11.16.0/dist/mermaid.esm.min.mjs"),
    import(
      "https://cdn.jsdelivr.net/npm/@mermaid-js/layout-elk@0.2.2/dist/mermaid-layout-elk.esm.min.mjs"
    )
  ]);

  mermaid.registerLayoutLoaders(elkLayouts);

  await Promise.all(diagramElements.map(async (element) => {
    const sourcePath = element.dataset.mermaidSource;
    const response = await fetch(sourcePath);

    if (!response.ok) {
      throw new Error(`${sourcePath}: ${response.status} ${response.statusText}`);
    }

    element.textContent = await response.text();
  }));

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: "default"
  });
  await mermaid.run({ nodes: diagramElements });

  const relationColors = {
    inheritance: "#c84655",
    composition: "#d97706",
    aggregation: "#2f855a",
    association: "#2563a6",
    realization: "#5b5fc7",
    dependency: "#8b51a5"
  };

  for (const element of diagramElements) {
    const svg = element.querySelector("svg");

    if (!svg) {
      continue;
    }

    const relationTypes = new Map();

    for (const relation of svg.querySelectorAll("path.relation[data-id]")) {
      const marker = [
        relation.getAttribute("marker-start"),
        relation.getAttribute("marker-end")
      ].join(" ");
      const isDashed = relation.classList.contains("edge-pattern-dashed");
      let relationType = isDashed ? "dependency" : "association";

      if (marker.includes("composition")) {
        relationType = "composition";
      } else if (marker.includes("aggregation")) {
        relationType = "aggregation";
      } else if (marker.includes("extension")) {
        relationType = isDashed ? "realization" : "inheritance";
      }

      const relationColor = relationColors[relationType];
      relation.style.setProperty("stroke", relationColor, "important");

      for (const markerAttribute of ["marker-start", "marker-end"]) {
        const markerReference = relation.getAttribute(markerAttribute);
        const originalMarkerId = markerReference?.match(/#([^)]+)/)?.[1];

        if (!originalMarkerId) {
          continue;
        }

        const coloredMarkerId = `${originalMarkerId}-${relationType}`;
        let coloredMarker = [...svg.querySelectorAll("marker")]
          .find((markerElement) => markerElement.id === coloredMarkerId);

        if (!coloredMarker) {
          const originalMarker = [...svg.querySelectorAll("marker")]
            .find((markerElement) => markerElement.id === originalMarkerId);

          if (!originalMarker) {
            continue;
          }

          coloredMarker = originalMarker.cloneNode(true);
          coloredMarker.id = coloredMarkerId;

          for (const shape of coloredMarker.querySelectorAll("path, polygon, circle")) {
            const markerFill = relationType === "aggregation" ? "#ffffff" : relationColor;
            shape.style.setProperty("fill", markerFill, "important");
            shape.style.setProperty("stroke", relationColor, "important");
          }

          originalMarker.parentNode.append(coloredMarker);
        }

        relation.setAttribute(markerAttribute, `url(#${coloredMarkerId})`);
      }

      relationTypes.set(relation.dataset.id, relationType);
    }

    for (const label of svg.querySelectorAll(".edgeLabels .label[data-id]")) {
      const relationType = relationTypes.get(label.dataset.id);

      if (relationType) {
        label.closest(".edgeLabel")?.classList.add(`relation-label-${relationType}`);
      }
    }
  }
} catch (error) {
  for (const element of diagramElements) {
    element.classList.add("mermaid-error");
    element.textContent = `UML図を表示できませんでした。\n${String(error)}`;
  }
}
