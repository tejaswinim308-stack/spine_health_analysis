(function () {
  async function load() {
    let status;
    try {
      status = await apiGet("/api/status");
    } catch (e) { return; }
    if (!status.loaded) return;

    document.getElementById("export-empty").classList.add("hidden");
    const body = document.getElementById("export-body");
    body.classList.remove("hidden");
    body.classList.add("grid");

    const summarySection = document.getElementById("summary-section");
    summarySection.classList.remove("hidden");
    summarySection.classList.add("flex");

    const summary = await apiGet("/api/export/summary");
    const json = JSON.stringify(summary, null, 2);
    document.getElementById("summary-json").textContent = json;

    const blob = new Blob([json], { type: "application/json" });
    document.getElementById("download-summary").href = URL.createObjectURL(blob);
  }

  load();
})();
