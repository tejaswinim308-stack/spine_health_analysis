(function () {
  const emptyEl = document.getElementById("insights-empty");
  const needTargetEl = document.getElementById("insights-need-target");
  const loadingEl = document.getElementById("model-loading");
  const bodyEl = document.getElementById("model-body");

  function metricCard(name, m) {
    const rows = [
      ["Accuracy", m.accuracy],
      ["Precision", m.precision],
      ["Recall", m.recall],
      ["F1 Score", m.f1_score],
      ["ROC-AUC", m.roc_auc === null ? "n/a" : m.roc_auc],
    ];
    return `
      <div class="bg-surface-container-low rounded p-space-lg shadow-md flex flex-col gap-space-sm">
        <div class="font-label-md text-label-md font-semibold text-on-surface flex items-center gap-space-xs">
          <span class="material-symbols-outlined text-secondary text-[20px]">model_training</span>${escapeHtml(name)}
        </div>
        <div class="grid grid-cols-2 gap-space-sm">
          ${rows.map(([label, val]) => `
            <div class="bg-surface-container rounded p-space-sm">
              <div class="font-caption text-caption text-outline uppercase">${label}</div>
              <div class="font-headline-sm text-headline-sm font-mono text-on-surface">${val}</div>
            </div>`).join("")}
        </div>
      </div>`;
  }

  function confusionMatrixCard(name, m) {
    const classes = m.class_names;
    let html = `<div class="bg-surface-container-low rounded p-space-lg shadow-md">
      <div class="font-label-md text-label-md font-semibold text-on-surface mb-space-sm">${escapeHtml(name)} — Confusion Matrix</div>
      <div class="overflow-x-auto"><table class="border-collapse">
      <thead><tr><th class="p-1"></th>${classes.map((c) => `<th class="p-1 font-caption text-caption text-outline">Pred ${escapeHtml(c)}</th>`).join("")}</tr></thead><tbody>`;
    m.confusion_matrix.forEach((row, i) => {
      html += `<tr><td class="p-1 font-caption text-caption text-outline">Actual ${escapeHtml(classes[i])}</td>`;
      row.forEach((v, j) => {
        const strong = i === j;
        html += `<td class="p-2 text-center font-mono text-body-sm rounded ${strong ? "bg-tertiary/15 text-tertiary font-semibold" : "bg-surface-container text-on-surface-variant"}">${v}</td>`;
      });
      html += `</tr>`;
    });
    html += `</tbody></table></div></div>`;
    return html;
  }

  function renderResults(results) {
    document.getElementById("feature-notes").innerHTML =
      `Trained on <b>${results.n_train}</b> rows, validated on <b>${results.n_test}</b> held-out rows, using <b>${results.n_features}</b> engineered features. ` +
      (results.feature_engineering_notes.length
        ? `Engineered features: ${results.feature_engineering_notes.map(escapeHtml).join("; ")}.`
        : "");

    const cardsEl = document.getElementById("model-cards");
    cardsEl.innerHTML = Object.entries(results.models).map(([name, m]) => metricCard(name, m)).join("");

    const best = results.models[results.best_model];
    if (best.feature_importance) {
      renderTable(
        document.getElementById("importance-table"),
        ["feature", "importance"],
        best.feature_importance
      );
    }

    document.getElementById("confusion-matrices").innerHTML = Object.entries(results.models)
      .map(([name, m]) => confusionMatrixCard(name, m))
      .join("");
  }

  async function loadRecommendations() {
    try {
      const r = await apiGet("/api/risk/recommendations");
      document.getElementById("recommendations-list").innerHTML = r.recommendations
        .map((n) => `<li>${escapeHtml(n)}</li>`)
        .join("");
    } catch (e) { /* no-op */ }
  }

  async function train() {
    loadingEl.classList.remove("hidden");
    bodyEl.classList.add("hidden");
    try {
      const results = await apiPost("/api/model/train", {});
      loadingEl.classList.add("hidden");
      bodyEl.classList.remove("hidden");
      bodyEl.classList.add("flex");
      renderResults(results);
      await loadRecommendations();
    } catch (e) {
      loadingEl.classList.add("hidden");
      needTargetEl.classList.remove("hidden");
      needTargetEl.textContent = "Could not train model: " + e.message;
    }
  }

  document.getElementById("train-btn").addEventListener("click", train);

  async function load() {
    let status;
    try {
      status = await apiGet("/api/status");
    } catch (e) { return; }
    if (!status.loaded) return;
    emptyEl.classList.add("hidden");

    const existing = await apiGet("/api/model/results");
    if (existing.trained) {
      bodyEl.classList.remove("hidden");
      bodyEl.classList.add("flex");
      renderResults(existing);
      await loadRecommendations();
    }
  }

  load();
})();
