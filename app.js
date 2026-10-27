// Frontend for the Application Tracker. Talks only to this server's /api.
const form = document.getElementById("add-form");
const list = document.getElementById("list");
const emptyMsg = document.getElementById("empty");
const statsEl = document.getElementById("stats");
const messageEl = document.getElementById("form-message");
const searchEl = document.getElementById("search");
const statusFilter = document.getElementById("filter-status");
const typeFilter = document.getElementById("filter-type");

function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function load() {
  const params = new URLSearchParams();
  if (searchEl.value.trim()) params.set("search", searchEl.value.trim());
  if (statusFilter.value) params.set("status", statusFilter.value);
  if (typeFilter.value) params.set("type", typeFilter.value);

  const [apps, stats] = await Promise.all([
    fetch(`/api/applications?${params}`).then((r) => r.json()),
    fetch("/api/stats").then((r) => r.json()),
  ]);

  statsEl.textContent = apps.length === 0
    ? `${stats.total} application(s) in total.`
    : `Showing ${apps.length} of ${stats.total} application(s).`;

  emptyMsg.hidden = apps.length !== 0;
  list.innerHTML = apps.map((app) => `
    <li class="app-card">
      <div>
        <strong>${escapeHtml(app.role)}</strong> at ${escapeHtml(app.company)}
        <span class="tag">${escapeHtml(app.type)}</span>
        <span class="tag">${escapeHtml(app.status)}</span>
      </div>
      <div class="meta">
        ${escapeHtml(app.location)}${app.location && app.date_applied ? " · " : ""}${escapeHtml(app.date_applied)}
        ${app.link ? ` · <a href="${escapeHtml(app.link)}" target="_blank" rel="noreferrer">Posting</a>` : ""}
      </div>
      ${app.notes ? `<p>${escapeHtml(app.notes)}</p>` : ""}
      <div class="row-actions">
        <label>Status
          <select data-action="status" data-id="${app.id}">
            ${["Saved", "Applied", "Interview", "Offer", "Rejected"].map(
              (s) => `<option ${s === app.status ? "selected" : ""}>${s}</option>`).join("")}
          </select>
        </label>
        <button type="button" data-action="delete" data-id="${app.id}">Delete</button>
      </div>
    </li>`).join("");
}

list.addEventListener("change", async (event) => {
  const el = event.target;
  if (el.dataset.action !== "status") return;
  await fetch(`/api/applications/${el.dataset.id}`, {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({status: el.value}),
  });
  load();
});

list.addEventListener("click", async (event) => {
  const btn = event.target.closest("[data-action='delete']");
  if (!btn) return;
  if (!confirm("Delete this application?")) return;
  await fetch(`/api/applications/${btn.dataset.id}`, {method: "DELETE"});
  load();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(form).entries());
  const res = await fetch("/api/applications", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    messageEl.textContent = err.error || "Could not save. Check company and role.";
    return;
  }
  form.reset();
  messageEl.textContent = "Saved.";
  load();
});

document.getElementById("clear-filters").addEventListener("click", () => {
  searchEl.value = "";
  statusFilter.value = "";
  typeFilter.value = "";
  load();
});

let debounce;
for (const el of [searchEl, statusFilter, typeFilter]) {
  el.addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(load, 200);
  });
}

load();
