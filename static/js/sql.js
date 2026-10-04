(function () {
  const emptyEl = document.getElementById("sql-empty");
  const bodyEl = document.getElementById("sql-body");

  function renderExample(ex) {
    const wrap = document.createElement("div");
    wrap.className = "bg-surface-container-low rounded p-space-lg shadow-md";
    const resultId = "ex-result-" + Math.random().toString(36).slice(2);
    wrap.innerHTML = `
      <div class="flex items-center justify-between mb-1">
        <div class="font-label-md text-label-md font-semibold text-on-surface">${escapeHtml(ex.title)}</div>
        <span class="font-caption text-caption text-secondary bg-secondary/10 px-2 py-0.5 rounded">${escapeHtml(ex.description)}</span>
      </div>
      <pre class="font-mono text-body-sm text-on-surface-variant bg-surface-container-lowest rounded p-space-sm overflow-x-auto mb-space-sm">${escapeHtml(ex.sql)}</pre>
      <div id="${resultId}"></div>
    `;
    const resultEl = wrap.querySelector(`#${resultId}`);
    if (ex.error) {
      resultEl.innerHTML = `<div class="text-body-sm text-on-surface-variant font-body-sm">Not applicable to this dataset's schema: ${escapeHtml(ex.error)}</div>`;
    } else if (ex.result) {
      renderTable(resultEl, ex.result.columns, ex.result.rows);
    }
    return wrap;
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

    const data = await apiGet("/api/sql/examples");
    const container = document.getElementById("examples-container");
    container.innerHTML = "";
    data.examples.forEach((ex) => container.appendChild(renderExample(ex)));
  }

  document.getElementById("run-sql-btn").addEventListener("click", async () => {
    const sql = document.getElementById("sql-input").value.trim();
    const errEl = document.getElementById("sql-error");
    errEl.textContent = "";
    if (!sql) return;
    try {
      const result = await apiPost("/api/sql/query", { sql });
      renderTable(document.getElementById("sql-result"), result.columns, result.rows);
    } catch (e) {
      errEl.textContent = e.message;
      document.getElementById("sql-result").innerHTML = "";
    }
  });

  load();
})();
