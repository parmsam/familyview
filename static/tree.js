// FamilyView tree page — two view modes:
//   "graph" = D3 force-directed (default)
//   "tree"  = family-chart library (purpose-built genealogy tree)

(function () {

  // -------------------------------------------------------------------------
  // Shared state
  // -------------------------------------------------------------------------
  const genderColor = {
    male: "#60a5fa", female: "#f472b6", other: "#a78bfa", unknown: "#9ca3af",
  };

  let currentMode = "graph";
  let graphCachedData = null;
  let fcInitialized = false;
  let d3Simulation = null;

  // -------------------------------------------------------------------------
  // Graph view — D3 force-directed
  // -------------------------------------------------------------------------
  const graphContainer = document.getElementById("tree-graph-container");

  if (graphContainer) {
    const width  = graphContainer.clientWidth  || 900;
    const height = graphContainer.clientHeight || 600;

    const svg = d3.select("#tree-graph-container")
      .append("svg")
      .attr("width", "100%").attr("height", "100%")
      .attr("viewBox", [0, 0, width, height]);

    svg.append("defs").append("marker")
      .attr("id", "arrow").attr("viewBox", "0 -5 10 10")
      .attr("refX", 22).attr("refY", 0)
      .attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto")
      .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#6b7280");

    const g = svg.append("g");

    const zoom = d3.zoom().scaleExtent([0.1, 4])
      .on("zoom", (e) => g.attr("transform", e.transform));
    svg.call(zoom);

    function renderGraph(data) {
      if (d3Simulation) d3Simulation.stop();
      g.selectAll("*").remove();

      const nodes = data.nodes.map((d) => ({ ...d }));
      const links = data.links.map((d) => ({ ...d }));
      const nodeById = new Map(nodes.map((n) => [n.id, n]));

      const safeLinks = links
        .filter((l) => nodeById.has(l.source) && nodeById.has(l.target))
        .map((l) => ({ ...l, source: nodeById.get(l.source), target: nodeById.get(l.target) }));

      const linkSel = g.append("g").selectAll("line").data(safeLinks).join("line")
        .attr("stroke", "#9ca3af").attr("stroke-width", 1.5)
        .attr("stroke-dasharray", (d) => d.type === "spouse" ? "5,4" : null)
        .attr("marker-end", (d) => d.type === "parent_child" ? "url(#arrow)" : null);

      const nodeSel = g.append("g").selectAll("circle").data(nodes).join("circle")
        .attr("r", 18)
        .attr("fill", (d) => genderColor[d.gender] || genderColor.unknown)
        .attr("stroke", "#fff").attr("stroke-width", 3)
        .style("cursor", "pointer")
        .on("click", (_, d) => { window.location.href = `/members/${d.id}`; })
        .call(d3.drag()
          .on("start", (e, d) => { if (!e.active) d3Simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
          .on("drag",  (e, d) => { d.fx = e.x; d.fy = e.y; })
          .on("end",   (e, d) => { if (!e.active) d3Simulation.alphaTarget(0); d.fx = null; d.fy = null; }));

      nodeSel.append("title").text((d) => {
        let t = d.name;
        if (d.birth_date) t += `\nb. ${d.birth_date}`;
        if (d.death_date) t += `\nd. ${d.death_date}`;
        return t;
      });

      const labelSel = g.append("g").selectAll("text").data(nodes).join("text")
        .text((d) => d.name)
        .attr("text-anchor", "middle").attr("dy", 32)
        .attr("font-size", "11px").attr("fill", "#374151")
        .style("pointer-events", "none").style("user-select", "none");

      d3Simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(safeLinks).id((d) => d.id)
          .distance((d) => d.type === "spouse" ? 60 : 100)
          .strength((d) => d.type === "spouse" ? 0.8 : 0.5))
        .force("charge", d3.forceManyBody().strength(-350))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide(40))
        .on("tick", () => {
          linkSel.attr("x1", (d) => d.source.x).attr("y1", (d) => d.source.y)
                 .attr("x2", (d) => d.target.x).attr("y2", (d) => d.target.y);
          nodeSel.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
          labelSel.attr("x", (d) => d.x).attr("y", (d) => d.y);
        });

      if (nodes.length === 0) {
        g.append("text")
          .attr("x", width / 2).attr("y", height / 2)
          .attr("text-anchor", "middle").attr("fill", "#9ca3af").attr("font-size", "16px")
          .text("No family members yet. Add members to see the tree.");
      }
    }

    function loadGraph() {
      fetch("/api/tree-data")
        .then((r) => r.json())
        .then((data) => { graphCachedData = data; renderGraph(data); })
        .catch((err) => console.error("Graph load error:", err));
    }

    loadGraph();
    document.body.addEventListener("htmx:afterSettle", () => {
      if (currentMode === "graph") loadGraph();
    });

    window._reloadGraph = loadGraph;
  }

  // -------------------------------------------------------------------------
  // Tree view — family-chart library
  // -------------------------------------------------------------------------
  function initFamilyChart() {
    if (fcInitialized) return;

    const fc = window.f3;
    if (!fc) {
      console.error("family-chart (f3) not loaded");
      return;
    }

    fetch("/api/family-chart-data")
      .then((r) => r.json())
      .then((data) => {
        if (data.length === 0) {
          document.getElementById("tree-fc-container").innerHTML =
            '<p style="text-align:center;color:#9ca3af;padding:4rem;font-size:1rem;">No family members yet.</p>';
          return;
        }

        const f3Chart = fc.createChart("#tree-fc-container", data);

        f3Chart.setSingleParentEmptyCard(false);

        f3Chart
          .setCardHtml()
          .setCardDisplay([
            ["first name", "last name"],
            ["birthday"],
          ]);

        f3Chart.updateTree({ initial: true });

        // Navigate to member detail on card click
        document.getElementById("tree-fc-container").addEventListener("click", (e) => {
          // Walk up from the clicked element looking for a D3-data-bound card node
          let el = e.target;
          while (el && el.id !== "tree-fc-container") {
            const datum = d3.select(el).datum();
            if (datum && datum.id) {
              window.location.href = `/members/${datum.id}`;
              return;
            }
            el = el.parentElement;
          }
        });

        fcInitialized = true;
      })
      .catch((err) => console.error("Family-chart load error:", err));
  }

  // -------------------------------------------------------------------------
  // Toggle between views
  // -------------------------------------------------------------------------
  window.setTreeViewMode = function (mode) {
    currentMode = mode;

    const graphCont = document.getElementById("tree-graph-container");
    const fcCont    = document.getElementById("tree-fc-container");

    if (mode === "tree") {
      if (graphCont) graphCont.style.display = "none";
      if (fcCont)    fcCont.style.display    = "block";
      initFamilyChart();
    } else {
      if (graphCont) graphCont.style.display = "block";
      if (fcCont)    fcCont.style.display    = "none";
      // Restart D3 if it was stopped
      if (d3Simulation) d3Simulation.restart();
    }

    document.querySelectorAll("[data-tree-mode]").forEach((btn) => {
      const active = btn.dataset.treeMode === mode;
      btn.classList.toggle("bg-white",       active);
      btn.classList.toggle("text-emerald-700", active);
      btn.classList.toggle("font-semibold",  active);
      btn.classList.toggle("shadow-sm",      active);
      btn.classList.toggle("text-white/60",  !active);
    });
  };

})();
