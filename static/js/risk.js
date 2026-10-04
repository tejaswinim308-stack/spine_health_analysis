(function () {
  const emptyEl = document.getElementById("risk-empty");
  const bodyEl = document.getElementById("risk-body");

  const RISK_COLORS = { Low: "text-tertiary", Moderate: "text-secondary", High: "text-error" };

  function renderDistribution(dist) {
    const container = document.getElementById("risk-dist-cards");
    if (!dist.available) {
      container.innerHTML = `<div class="bg-surface-container-low rounded p-space-lg text-on-surface-variant font-body-sm text-body-sm col-span-3">${escapeHtml(dist.reason)}</div>`;
      return;
    }
    container.innerHTML = dist.categories
      .map((cat, i) => `
        <div class="bg-surface-container-low rounded p-space-lg shadow-md flex flex-col gap-1">
          <div class="flex items-center justify-between">
            <span class="font-label-md text-label-md text-on-surface-variant">${escapeHtml(cat)} Risk</span>
            ${riskBadge(cat)}
          </div>
          <span class="font-display-lg text-display-lg font-mono ${RISK_COLORS[cat] || "text-on-surface"}">${dist.counts[i]}</span>
          <span class="font-body-sm text-body-sm text-on-surface-variant">${dist.pct[i]}% of ${dist.total} patients</span>
        </div>`)
      .join("");
  }

  async function loadAggregate() {
    const groupCol = document.getElementById("group-select").value;
    const aggCol = document.getElementById("agg-select").value;
    const q = new URLSearchParams({ group_col: groupCol });
    if (aggCol) q.set("agg_col", aggCol);
    const data = await apiGet(`/api/risk/aggregate?${q.toString()}`);
    if (!data.available) {
      document.getElementById("aggregate-table").innerHTML = `<div class="text-on-surface-variant font-body-sm text-body-sm">${escapeHtml(data.reason)}</div>`;
      document.getElementById("crosstab-table").innerHTML = "";
      return;
    }
    const cols = data.rows.length ? Object.keys(data.rows[0]) : [];
    renderTable(document.getElementById("aggregate-table"), cols, data.rows);

    if (data.crosstab) {
      const ctCols = ["group", ...data.crosstab.columns];
      const ctRows = data.crosstab.index.map((idx, i) => {
        const row = { group: idx };
        data.crosstab.columns.forEach((c, j) => (row[c] = data.crosstab.matrix[i][j]));
        return row;
      });
      renderTable(document.getElementById("crosstab-table"), ctCols, ctRows);
    } else {
      document.getElementById("crosstab-table").innerHTML = "";
    }
  }

  async function load() {
    let status;
    try {
      status = await apiGet("/api/status");
    } catch (e) { return; }
    if (!status.loaded) return;
    emptyEl.classList.add("hidden");
    bodyEl.classList.remove("hidden");
    bodyEl.classList.add("flex");

    const dist = await apiGet("/api/risk/distribution");
    renderDistribution(dist);

    const overview = await apiGet("/api/overview");
    const catCols = overview.dtypes.filter((d) => d.semantic_type === "categorical").map((d) => d.column);
    const numCols = overview.dtypes.filter((d) => d.semantic_type === "numeric").map((d) => d.column);

    const groupSelect = document.getElementById("group-select");
    groupSelect.innerHTML = catCols.map((c) => `<option value="${c}">${c}</option>`).join("");
    const aggSelect = document.getElementById("agg-select");
    aggSelect.innerHTML = `<option value="">(row count)</option>` + numCols.map((c) => `<option value="${c}">avg ${c}</option>`).join("");

    groupSelect.addEventListener("change", loadAggregate);
    aggSelect.addEventListener("change", loadAggregate);
    if (catCols.length) await loadAggregate();
  }

  load();
})();
