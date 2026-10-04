(function () {
  const emptyEl = document.getElementById("eda-empty");
  const bodyEl = document.getElementById("eda-body");

  async function load() {
    let status;
    try {
      status = await apiGet("/api/status");
    } catch (e) { return; }
    if (!status.loaded) return;

    emptyEl.classList.add("hidden");
    bodyEl.classList.remove("hidden");
    bodyEl.classList.add("flex");

    const stats = await apiGet("/api/eda/stats");
    const statCols = stats.descriptive_statistics.length
      ? Object.keys(stats.descriptive_statistics[0])
      : [];
    renderTable(document.getElementById("stats-table"), statCols, stats.descriptive_statistics);
    renderTable(
      document.getElementById("outlier-table"),
      ["column", "q1", "q3", "iqr", "lower_bound", "upper_bound", "outlier_count", "outlier_pct"],
      stats.outliers
    );

    const numericCols = stats.descriptive_statistics.map((r) => r.column);
    const select = document.getElementById("hist-col-select");
    select.innerHTML = numericCols.map((c) => `<option value="${c}">${c}</option>`).join("");

    const corr = await apiGet("/api/eda/correlation");
    setImage(document.getElementById("corr-chart"), corr.heatmap_png);

    const charts = await apiGet("/api/eda/charts");
    if (charts.histogram) {
      select.value = charts.histogram.column;
      setImage(document.getElementById("hist-chart"), charts.histogram.image);
    }
    if (charts.scatter) setImage(document.getElementById("scatter-chart"), charts.scatter.image);
    if (charts.boxplot) setImage(document.getElementById("box-chart"), charts.boxplot.image);
    else if (charts.bar) setImage(document.getElementById("box-chart"), charts.bar.image);

    select.addEventListener("change", async () => {
      document.getElementById("hist-chart").innerHTML = `<div class="skel h-64 rounded"></div>`;
      try {
        const r = await apiGet(`/api/eda/chart?type=histogram&column=${encodeURIComponent(select.value)}`);
        setImage(document.getElementById("hist-chart"), r.image);
      } catch (e) { /* no-op */ }
    });
  }

  load();
})();
