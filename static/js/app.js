// Shared helpers used by every dashboard page.

async function apiGet(url) {
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function apiPost(url, body, isForm) {
  const opts = { method: "POST" };
  if (isForm) {
    opts.body = body;
  } else {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body || {});
  }
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function escapeHtml(v) {
  if (v === null || v === undefined) return "";
  return String(v)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderTable(el, columns, rows, opts) {
  opts = opts || {};
  if (!rows || rows.length === 0) {
    el.innerHTML = `<div class="p-space-md text-on-surface-variant font-body-sm text-body-sm">No rows to display.</div>`;
    return;
  }
  const numericCols = new Set(
    columns.filter((c) => rows.every((r) => r[c] === null || typeof r[c] === "number"))
  );
  let html = `<div class="overflow-x-auto rounded border border-outline-variant/30">
    <table class="data-table w-full text-left border-collapse">
      <thead><tr class="bg-surface-container-lowest">`;
  columns.forEach((c) => {
    html += `<th class="px-3 py-2 font-caption text-caption uppercase tracking-wider text-outline border-b border-outline-variant/30 ${numericCols.has(c) ? "text-right" : ""}">${escapeHtml(c)}</th>`;
  });
  html += `</tr></thead><tbody>`;
  rows.forEach((r) => {
    html += `<tr class="hover:bg-surface-container-high/50 transition-colors">`;
    columns.forEach((c) => {
      let v = r[c];
      if (typeof v === "number" && !Number.isInteger(v)) v = v.toFixed(3);
      html += `<td class="px-3 py-2 border-b border-outline-variant/10 font-body-sm text-body-sm ${numericCols.has(c) ? "text-right font-mono text-on-surface" : "text-on-surface-variant"}">${escapeHtml(v)}</td>`;
    });
    html += `</tr>`;
  });
  html += `</tbody></table></div>`;
  el.innerHTML = html;
}

function riskBadge(category) {
  const map = {
    Low: "bg-tertiary/12 text-tertiary border-tertiary/25",
    Moderate: "bg-secondary/12 text-secondary border-secondary/25",
    High: "bg-error/15 text-error border-error/30",
  };
  const cls = map[category] || "bg-surface-container-high text-on-surface-variant border-outline-variant/30";
  return `<span class="px-2 py-0.5 rounded-full text-caption font-caption font-semibold border ${cls}">${escapeHtml(category)}</span>`;
}

function setImage(el, base64) {
  if (!base64) {
    el.innerHTML = `<div class="flex items-center justify-center h-48 text-on-surface-variant font-body-sm text-body-sm">Chart unavailable for this dataset.</div>`;
    return;
  }
  el.innerHTML = `<img src="data:image/png;base64,${base64}" class="w-full h-auto rounded" />`;
}

// -------------------------------------------------------------- header ---
async function refreshStatusBar() {
  try {
    const s = await apiGet("/api/status");
    const dot = document.getElementById("status-dot");
    const text = document.getElementById("status-text");
    const rowcount = document.getElementById("sidebar-rowcount");
    if (!s.loaded) {
      if (dot) dot.className = "w-1.5 h-1.5 rounded-full bg-outline";
      if (text) text.textContent = "No dataset loaded";
      if (rowcount) rowcount.textContent = "0";
      return s;
    }
    if (dot) dot.className = "w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse";
    if (text) {
      const rows = s.cleaned ? s.clean_rows : s.raw_rows;
      text.textContent = `${s.source_name} (${rows} rows)${s.cleaned ? " \u00b7 cleaned" : " \u00b7 raw"}`;
    }
    if (rowcount) rowcount.textContent = s.cleaned ? s.clean_rows : s.raw_rows;
    return s;
  } catch (e) {
    console.error(e);
  }
}

document.addEventListener("DOMContentLoaded", refreshStatusBar);
