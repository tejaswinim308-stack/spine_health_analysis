(function () {
  const dropzone = document.getElementById("dropzone-box");
  const fileInput = document.getElementById("file-input");
  const statusEl = document.getElementById("upload-status");
  const sampleBtn = document.getElementById("load-sample-btn");

  function showResult(data) {
    document.getElementById("summary-rows").textContent = data.raw_rows ?? data.clean_rows ?? "-";
    document.getElementById("summary-cols").textContent = data.raw_columns ?? "-";
    if (data.preview) {
      renderTable(document.getElementById("preview-table"), data.preview.columns, data.preview.rows);
    }
    refreshStatusBar();
  }

  async function upload(file) {
    statusEl.textContent = `Uploading ${file.name}...`;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const data = await apiPost("/api/upload", fd, true);
      statusEl.innerHTML = `<span class="text-tertiary">&#10003;</span> Loaded ${data.raw_rows} rows / ${data.raw_columns} columns from ${file.name}.`;
      showResult(data);
    } catch (e) {
      statusEl.innerHTML = `<span class="text-error">Upload failed: ${escapeHtml(e.message)}</span>`;
    }
  }

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("dragover", (ev) => { ev.preventDefault(); dropzone.classList.add("ring-2", "ring-primary"); });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("ring-2", "ring-primary"));
  dropzone.addEventListener("drop", (ev) => {
    ev.preventDefault();
    dropzone.classList.remove("ring-2", "ring-primary");
    if (ev.dataTransfer.files.length) upload(ev.dataTransfer.files[0]);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) upload(fileInput.files[0]);
  });

  sampleBtn.addEventListener("click", async () => {
    statusEl.textContent = "Loading sample dataset...";
    try {
      const data = await apiPost("/api/load-sample", {});
      statusEl.innerHTML = `<span class="text-tertiary">&#10003;</span> Loaded sample dataset (${data.raw_rows} rows).`;
      showResult(data);
    } catch (e) {
      statusEl.innerHTML = `<span class="text-error">Failed: ${escapeHtml(e.message)}</span>`;
    }
  });

  // If data already loaded (nav back to this page), show current preview.
  (async () => {
    try {
      const s = await apiGet("/api/status");
      if (s.loaded) {
        const p = await apiGet("/api/preview");
        showResult({ raw_rows: s.raw_rows, raw_columns: s.raw_columns, preview: p });
      }
    } catch (e) { /* no-op */ }
  })();
})();
