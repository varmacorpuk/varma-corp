/* 2D office canvas. Click employee → right-hand panel. Same kernel runtime for chat. */
(function () {
  const API = localStorage.getItem("varmaApi") || "http://127.0.0.1:8000";
  const TOKEN = localStorage.getItem("varmaToken") || "dev-board-member";
  const canvas = document.getElementById("office-floor");
  const ctx = canvas.getContext("2d");
  const rightPanel = document.getElementById("right-panel");
  const panelBody = document.getElementById("panel-body");
  const placeholder = document.getElementById("panel-placeholder");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const modeBanner = document.getElementById("mode-banner");

  let employees = [];
  let selected = null;
  const sprite = { w: 16, h: 24, scale: 4 };

  function headers(json) {
    const h = { Authorization: "Bearer " + TOKEN };
    if (json) h["Content-Type"] = "application/json";
    return h;
  }

  async function get(path) {
    const r = await fetch(API + path, { headers: headers() });
    if (!r.ok) throw new Error(path + " " + r.status);
    return r.json();
  }

  function draw() {
    const w = canvas.width;
    const h = canvas.height;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#6b8f71";
    ctx.fillRect(0, 0, w, h);
    for (let y = 0; y < h; y += 16) {
      for (let x = 0; x < w; x += 16) {
        ctx.fillStyle = ((x + y) / 16) % 2 === 0 ? "#7aa078" : "#628a68";
        ctx.fillRect(x, y, 16, 16);
      }
    }
    // research desk
    ctx.fillStyle = "#6b4a2e";
    ctx.fillRect(60, 150, 120, 40);
    ctx.fillStyle = "#d8c39a";
    ctx.fillRect(68, 142, 48, 12);
    ctx.fillStyle = "#111";
    ctx.font = "10px monospace";
    ctx.fillText("RESEARCH", 72, 136);
    // CEO desk
    ctx.fillStyle = "#3d2b1f";
    ctx.fillRect(400, 70, 120, 40);
    ctx.fillStyle = "#d8c39a";
    ctx.fillRect(408, 62, 48, 12);
    ctx.fillStyle = "#111";
    ctx.fillText("CEO", 412, 56);

    employees.forEach((e) => {
      const x = (e.office_x || 96) * 2;
      const y = (e.office_y || 108) * 1.4;
      const kind = e.slug === "ceo" ? "ceo" : "research";
      drawSprite(x, y, selected && selected.slug === e.slug, kind);
      drawBubble(x, y, e.status_bubble || e.status || "OK");
      drawName(x, y, e.display_name || e.slug);
      e._hit = { x: x - 8, y: y - 40, w: 80, h: 90 };
    });
  }

  function drawSprite(x, y, highlight, kind) {
    const s = sprite.scale;
    const px = (gx, gy, c, gw, gh) => {
      ctx.fillStyle = c;
      ctx.fillRect(x + gx * s, y + gy * s, (gw || 1) * s, (gh || 1) * s);
    };
    if (highlight) {
      ctx.fillStyle = "rgba(255,255,180,0.5)";
      ctx.fillRect(x - 6, y - 6, 16 * s + 12, 24 * s + 12);
    }
    if (kind === "ceo") {
      px(4, 2, "#1a1a1a", 8, 6);
      px(5, 4, "#d2b48c", 6, 6);
      px(3, 10, "#1d3557", 10, 8);
      px(4, 18, "#111", 3, 6);
      px(9, 18, "#111", 3, 6);
    } else {
      px(4, 2, "#2b2118", 8, 6);
      px(5, 4, "#e6c8a8", 6, 6);
      px(3, 10, "#2f5d50", 10, 8);
      px(4, 18, "#1d3557", 3, 6);
      px(9, 18, "#1d3557", 3, 6);
    }
  }

  function drawBubble(x, y, text) {
    const label = (text || "OK").slice(0, 14);
    ctx.fillStyle = "#fff";
    ctx.strokeStyle = "#111";
    const bw = Math.max(48, label.length * 7);
    const bx = x - 4;
    const by = y - 22;
    ctx.fillRect(bx, by, bw, 14);
    ctx.strokeRect(bx, by, bw, 14);
    ctx.fillStyle = "#111";
    ctx.font = "9px monospace";
    ctx.fillText(label, bx + 3, by + 10);
  }

  function drawName(x, y, name) {
    ctx.fillStyle = "#111";
    ctx.font = "10px monospace";
    ctx.fillText(String(name || "").slice(0, 16), x - 4, y + 28 * sprite.scale / 4 + 20);
  }

  canvas.addEventListener("click", (ev) => {
    const rect = canvas.getBoundingClientRect();
    const x = (ev.clientX - rect.left) * (canvas.width / rect.width);
    const y = (ev.clientY - rect.top) * (canvas.height / rect.height);
    const hit = employees.find((e) => {
      const h = e._hit;
      return h && x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h;
    });
    if (hit) selectEmployee(hit);
  });

  async function selectEmployee(emp) {
    selected = emp;
    draw();
    placeholder.hidden = true;
    panelBody.hidden = false;
    chatForm.hidden = false;
    chatInput.placeholder = emp.slug === "ceo" ? "Ask the CEO…" : "Ask the analyst…";
    const detail = await get("/employees/" + emp.slug);
    const latest = await get("/employees/" + emp.slug + "/brief/latest");
    const inbox = await get("/employees/" + emp.slug + "/inbox");
    const brief = latest.brief;
    const received = (inbox.items || []).find((it) => it.brief);
    panelBody.innerHTML = `
      <h3>${escapeHtml(detail.display_name)}</h3>
      <p class="meta">${escapeHtml(detail.role_title)} · ${escapeHtml(detail.department)}</p>
      <p class="bubble-note">Status bubble: ${escapeHtml(detail.status_bubble)} (short). Detail belongs here, not as an overlay.</p>
      <p class="meta">Click does not grant authority.</p>
      ${
        emp.slug === "ceo"
          ? "<p class=\"meta\"><strong>CEO does not approve live trading.</strong> Board Member is the human authority. A meeting pack is not LIVE approval.</p>"
          : ""
      }
      <h3>Latest produced brief</h3>
      ${brief ? renderBrief(brief) : "<p>No brief produced by this employee.</p>"}
      <h3>Meeting inbox</h3>
      ${received ? renderInboxItem(received) : "<p>No handoff artefacts in this inbox.</p>"}
    `;
  }

  function renderInboxItem(item) {
    return `<div class="brief">
      <p class="meta">Handoff ${escapeHtml(item.status || "")} · ${escapeHtml(item.purpose || "")}</p>
      <p class="meta">${escapeHtml(item.note || "")}</p>
      ${item.brief ? renderBrief(item.brief) : ""}
    </div>`;
  }

  function renderBrief(b) {
    const items = (b.items || [])
      .map(
        (it) =>
          `<li>${escapeHtml(it.claim || "")} <small>source: ${escapeHtml(it.source || "")} @ ${escapeHtml(it.published_at || "")}</small></li>`
      )
      .join("");
    return `<div class="brief">
      <strong>${escapeHtml(b.headline)}</strong>
      <p>${escapeHtml(b.summary)}</p>
      <p>Recipient: ${escapeHtml(b.intended_recipient || "")} · Freshness: ${escapeHtml(b.freshness_flag)} · verified: ${b.verification_passed} · cost_units: ${b.cost_units}</p>
      <p>${escapeHtml(b.watchlist_disclaimer || "")}</p>
      <ul>${items}</ul>
    </div>`;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  chatForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!selected) return;
    const message = chatInput.value.trim();
    if (!message) return;
    const r = await fetch(API + "/employees/" + selected.slug + "/chat", {
      method: "POST",
      headers: headers(true),
      body: JSON.stringify({ message }),
    });
    const data = await r.json();
    const p = document.createElement("p");
    p.className = "meta";
    p.textContent = (data.reply || JSON.stringify(data)).slice(0, 800);
    panelBody.appendChild(p);
    chatInput.value = "";
  });

  async function boot() {
    try {
      const health = await get("/health");
      modeBanner.textContent = "trading_mode: " + health.trading_mode;
      const state = await get("/office/state");
      employees = state.employees || [];
      draw();
    } catch (err) {
      modeBanner.textContent = "kernel unreachable — start the API";
      employees = [
        {
          slug: "market-intelligence-research",
          display_name: "Asha Patel",
          status_bubble: "OFFLINE",
          office_x: 96,
          office_y: 108,
        },
        {
          slug: "ceo",
          display_name: "CEO",
          status_bubble: "OFFLINE",
          office_x: 220,
          office_y: 70,
        },
      ];
      draw();
    }
  }

  boot();
})();
