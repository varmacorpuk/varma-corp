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
    desk(60, 150, "RESEARCH");
    desk(400, 70, "CEO");
    desk(30, 50, "CHALLENGE");
    desk(480, 250, "RISK");

    employees.forEach((e) => {
      const x = (e.office_x || 96) * 2;
      const y = (e.office_y || 108) * 1.4;
      drawSprite(x, y, selected && selected.slug === e.slug, e.slug);
      drawBubble(x, y, e.status_bubble || e.status || "OK");
      drawName(x, y, e.display_name || e.slug);
      e._hit = { x: x - 8, y: y - 40, w: 80, h: 90 };
    });
  }

  function desk(dx, dy, label) {
    ctx.fillStyle = "#6b4a2e";
    ctx.fillRect(dx, dy, 110, 36);
    ctx.fillStyle = "#d8c39a";
    ctx.fillRect(dx + 8, dy - 8, 48, 12);
    ctx.fillStyle = "#111";
    ctx.font = "10px monospace";
    ctx.fillText(label, dx + 10, dy - 14);
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
    const body =
      kind === "ceo" ? "#1d3557" : kind === "challenge" ? "#6b3a2a" : kind === "risk" ? "#8b1e1e" : "#2f5d50";
    const hair = kind === "ceo" ? "#1a1a1a" : "#2b2118";
    px(4, 2, hair, 8, 6);
    px(5, 4, "#e6c8a8", 6, 6);
    px(3, 10, body, 10, 8);
    px(4, 18, "#1d3557", 3, 6);
    px(9, 18, "#1d3557", 3, 6);
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

  function chatPlaceholder(slug) {
    if (slug === "ceo") return "Ask the CEO…";
    if (slug === "challenge") return "Ask Challenge…";
    if (slug === "risk") return "Ask Risk…";
    return "Ask the analyst…";
  }

  async function selectEmployee(emp) {
    if (!rightPanel) return;
    selected = emp;
    draw();
    placeholder.hidden = true;
    panelBody.hidden = false;
    chatForm.hidden = false;
    chatInput.placeholder = chatPlaceholder(emp.slug);
    const work = await get("/employees/" + emp.slug + "/work");
    const authorityNote = work.cannot_approve_live_trading
      ? `<p class="meta"><strong>${escapeHtml(work.display_name)} does not approve live trading.</strong> Board Member is the human authority.</p>`
      : "";
    panelBody.innerHTML = `
      <h3>${escapeHtml(work.display_name)}</h3>
      <p class="meta">${escapeHtml(work.role_title)} · ${escapeHtml(work.department)}</p>
      <p class="bubble-note">Status bubble: ${escapeHtml(work.status_bubble)} (short). Detail belongs here, not as an overlay.</p>
      <p class="meta">Click does not grant authority.</p>
      ${authorityNote}
      ${work.brief ? "<h3>Latest produced brief</h3>" + renderBrief(work.brief) : ""}
      ${work.received_brief && emp.slug === "ceo" ? "<h3>Meeting inbox</h3>" + renderBrief(work.received_brief) : ""}
      ${work.thesis ? "<h3>SAMPLE thesis (not a live trade)</h3>" + renderThesis(work.thesis) : ""}
      ${work.challenge_review ? "<h3>Challenge review</h3>" + renderChallenge(work.challenge_review) : ""}
      ${work.risk_decision ? "<h3>Risk decision</h3>" + renderRisk(work.risk_decision) : ""}
      <h3>Handoffs</h3>
      ${renderInboxList(work.inbox || [])}
    `;
  }

  function renderInboxList(items) {
    if (!items.length) return "<p>No handoff artefacts in this inbox.</p>";
    return items
      .map((item) => {
        return `<div class="brief">
          <p class="meta">Handoff ${escapeHtml(item.status || "")} · ${escapeHtml(item.purpose || "")}</p>
          <p class="meta">${escapeHtml(item.note || "")}</p>
          ${item.brief ? renderBrief(item.brief) : ""}
          ${item.thesis ? renderThesis(item.thesis) : ""}
          ${item.challenge_review ? renderChallenge(item.challenge_review) : ""}
          ${item.risk_decision ? renderRisk(item.risk_decision) : ""}
        </div>`;
      })
      .join("");
  }

  function renderThesis(t) {
    return `<div class="brief">
      <strong>${escapeHtml(t.title || "")}</strong>
      <p>${escapeHtml(t.statement || "")}</p>
      <p>Label: ${escapeHtml(t.label || "")} · symbol: ${escapeHtml(t.symbol || "")} · live_trade: ${t.is_live_trade}</p>
      <p>${escapeHtml(t.notes || "")}</p>
    </div>`;
  }

  function renderChallenge(c) {
    const objections = (c.objections || [])
      .map((o) => `<li>${escapeHtml(o.claim || o.id || "")}</li>`)
      .join("");
    return `<div class="brief">
      <p>Verdict: ${escapeHtml(c.verdict || "")} · ${escapeHtml(c.label || "")}</p>
      <p>${escapeHtml(c.summary || "")}</p>
      <ul>${objections}</ul>
    </div>`;
  }

  function renderRisk(d) {
    const reasons = (d.reasons || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("");
    return `<div class="brief">
      <p><strong>${escapeHtml(d.decision || "")}</strong> · ${escapeHtml(d.label || "")}</p>
      <p>${escapeHtml(d.summary || "")}</p>
      <p>Control engine: ${escapeHtml(d.control_engine_reason || "")}</p>
      <ul>${reasons}</ul>
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
        {
          slug: "challenge",
          display_name: "Challenge",
          status_bubble: "OFFLINE",
          office_x: 40,
          office_y: 48,
        },
        {
          slug: "risk",
          display_name: "Risk",
          status_bubble: "OFFLINE",
          office_x: 255,
          office_y: 175,
        },
      ];
      draw();
    }
  }

  boot();
})();
