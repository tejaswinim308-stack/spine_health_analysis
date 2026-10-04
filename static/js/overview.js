(function () {
  const emptyEl = document.getElementById("overview-empty");
  const bodyEl = document.getElementById("overview-body");

  function renderOverview(data) {
    emptyEl.classList.add("hidden");
    bodyEl.classList.remove("hidden");
    bodyEl.classList.add("flex");

    document.getElementById("kpi-rows").textContent = data.preview.n_rows;
    document.getElementById("kpi-cols").textContent = data.preview.n_columns;
    document.getElementById("kpi-dupes").textContent = data.duplicates.duplicate_count;
    document.getElementById("kpi-missing-cols").textContent = data.missing.filter((m) => m.missing_count > 0).length;

    renderTable(
      document.getElementById("dtype-table"),
      ["column", "pandas_dtype", "semantic_type", "unique_values"],
      data.dtypes
    );
    renderTable(
      document.getElementById("missing-table"),
      ["column", "missing_count", "missing_pct"],
      data.missing.filter((m) => m.missing_count > 0).length ? data.missing.filter((m) => m.missing_count > 0) : data.missing.slice(0, 5)
    );
    renderTable(document.getElementById("dupe-table"), data.preview.columns, data.duplicates.sample_rows);
    renderTable(document.getElementById("preview-table"), data.preview.columns, data.preview.rows);
  }

  async function load() {
    try {
      const data = await apiGet("/api/overview");
      renderOverview(data);
      if (data.status.cleaned) {
        // fetch log separately isn't stored on overview; re-fetch not needed here
      }
    } catch (e) {
      emptyEl.classList.remove("hidden");
      bodyEl.classList.add("hidden");
    }
  }

  document.getElementById("clean-btn").addEventListener("click", async (ev) => {
    const btn = ev.currentTarget;
    btn.disabled = true;
    btn.classList.add("opacity-60");
    try {
      const data = await apiPost("/api/clean", {});
      const logCard = document.getElementById("cleaning-log-card");
      logCard.classList.remove("hidden");
      const logEl = document.getElementById("cleaning-log");
      logEl.innerHTML = data.log.map((l) => `<li>${escapeHtml(l)}</li>`).join("");
      await load();
      refreshStatusBar();
    } catch (e) {
      alert("Cleaning failed: " + e.message);
    } finally {
      btn.disabled = false;
      btn.classList.remove("opacity-60");
    }
  });

  load();
})();
