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
  const boardObservabilityBtn = document.getElementById("board-observability-btn");

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

  if (boardObservabilityBtn) {
    boardObservabilityBtn.addEventListener("click", () => {
      showBoardObservability();
    });
  }

  function openPanel() {
    placeholder.hidden = true;
    panelBody.hidden = false;
  }

  async function showBoardObservability() {
    if (!rightPanel) return;
    selected = null;
    draw();
    openPanel();
    if (chatForm) chatForm.hidden = true;
    try {
      const data = await get("/observability");
      panelBody.innerHTML = renderObservability(data);
    } catch (err) {
      panelBody.innerHTML = `
        <h3>Board observability</h3>
        <p class="meta">Read-only. Cost ledger and evidence live in the database, not on this desktop.</p>
        <p class="meta">Kernel unreachable or Board identity missing. Start the API. This view does not write controls.</p>
      `;
    }
  }

  function renderObservability(data) {
    const costs = (data.costs && data.costs.entries) || [];
    const evidence = (data.evidence && data.evidence.entries) || [];
    const filter = data.nightly_filter || {};
    const run = filter.run;
    const titles = (data.organisation_memory && data.organisation_memory.titles) || [];
    const pack = data.meeting_pack || {};
    const artefacts = (data.meeting_artefacts && data.meeting_artefacts.items) || [];
    const thesis = pack.challenge_sample_thesis || {};
    const bubbles = data.status_bubbles || [];
    const routines = data.routines || {};
    const missing = data.missing_numeric_limits || {};
    const unsetKeys = missing.unset_keys || [];
    const controls = data.controls || {};
    const allowList = controls.allow_list || [];
    const paperGate = data.paper_gate || {};
    const executionPorts = data.execution_ports || {};
    const brokerPaper = executionPorts.broker_paper || {};
    const livePort = executionPorts.live || {};
    const companyMeeting = data.company_meeting || {};
    const meetingRun = companyMeeting.run;
    const costRows = costs.length
      ? costs
          .map(
            (row) =>
              `<div class="ledger-row">${escapeHtml(row.workflow || "")} · ${escapeHtml(row.kind || "")} · ${escapeHtml(String(row.units))} units · ${escapeHtml(row.created_at || "")}<br /><span class="meta">${escapeHtml(row.note || "")}</span></div>`
          )
          .join("")
      : "<p class=\"meta\">No cost entries in the database yet.</p>";
    const evidenceRows = evidence.length
      ? evidence
          .map(
            (row) =>
              `<div class="ledger-row">${escapeHtml(row.kind || "")} · actor: ${escapeHtml(row.actor || "")} · ${escapeHtml(row.created_at || "")}<br /><span class="meta">${escapeHtml(String(row.payload || "").slice(0, 280))}</span></div>`
          )
          .join("")
      : "<p class=\"meta\">No evidence rows in the database yet.</p>";
    const filterBlock = run
      ? `<div class="ledger-row">cadence: ${escapeHtml(run.cadence || filter.cadence || "nightly")} · timezone: ${escapeHtml(run.timezone || "Europe/London")} · archived: ${escapeHtml(String(run.archived_count))} · controls_written: ${run.controls_written} · daemon: ${run.daemon}<br /><span class="meta">${escapeHtml(run.ran_at || "")}</span></div>`
      : `<p class="meta">${escapeHtml(filter.note || "No nightly filter run stored yet.")}</p>`;
    const titleRows = titles.length
      ? titles
          .map((row) => `<div class="ledger-row">${escapeHtml(row.title || "")}</div>`)
          .join("")
      : "<p class=\"meta\">No organisation-memory titles in the database yet.</p>";
    const bubbleRows = bubbles.length
      ? bubbles
          .map(
            (row) =>
              `<button type="button" class="bubble-link" data-employee-slug="${escapeHtml(row.slug || "")}">${escapeHtml(row.display_name || row.slug || "")}: ${escapeHtml(row.status_bubble || row.status || "")}</button>`
          )
          .join("")
      : "<p class=\"meta\">No employee status bubbles.</p>";
    const artefactRows = artefacts.length
      ? artefacts
          .map((row) => {
            const kind = escapeHtml(row.kind || "");
            const extra =
              row.kind === "sample_thesis"
                ? " · SAMPLE not a live trade"
                : row.kind === "risk_decision"
                  ? " · " + escapeHtml(row.decision || "")
                  : row.kind === "handoff"
                    ? " · " + escapeHtml(row.status || "")
                    : row.kind === "challenge_review"
                      ? " · " + escapeHtml(row.verdict || "")
                      : "";
            return `<div class="ledger-row">${kind}${extra}<br /><span class="meta">${escapeHtml(row.label || row.purpose || row.id || "")}</span></div>`;
          })
          .join("")
      : "<p class=\"meta\">No 07:30 meeting artefacts stored yet.</p>";
    const documented = routines.documented || {};
    const briefSched = documented.brief || {};
    const filterSched = documented.nightly_filter || {};
    const meetingSched = documented.company_meeting || {};
    const dbRoutines = routines.items || [];
    const routineRows = `
      <div class="ledger-row">06:30 weekday brief · ${escapeHtml(briefSched.timezone || "Europe/London")} · daemon: ${briefSched.daemon === true} · ${escapeHtml(briefSched.cli || "python -m varma.routines.run_brief")}<br /><span class="meta">${escapeHtml(briefSched.description || "")}</span></div>
      <div class="ledger-row">07:30 company meeting · ${escapeHtml(meetingSched.timezone || "Europe/London")} · daemon: ${meetingSched.daemon === true} · is_trade: ${meetingSched.is_trade === true} · ${escapeHtml(meetingSched.cli || "python -m varma.routines.run_0730_meeting")}<br /><span class="meta">${escapeHtml(meetingSched.description || "")}</span></div>
      <div class="ledger-row">Nightly memory filter · ${escapeHtml(filterSched.timezone || "Europe/London")} · daemon: ${filterSched.daemon === true} · writes_controls: ${filterSched.writes_controls === true} · ${escapeHtml(filterSched.cli || "")}<br /><span class="meta">${escapeHtml(filterSched.description || "")}</span></div>
      ${
        dbRoutines.length
          ? dbRoutines
              .map(
                (row) =>
                  `<div class="ledger-row">${escapeHtml(row.name || "")} · ${escapeHtml(row.schedule || "")} · ${escapeHtml(row.timezone || "")}<br /><span class="meta">${escapeHtml(row.notes || "")}</span></div>`
              )
              .join("")
          : ""
      }
    `;
    const missingRows = unsetKeys.length
      ? unsetKeys
          .map(
            (key) =>
              `<div class="ledger-row">${escapeHtml(key)} — unset (OPEN BOARD DECISION)</div>`
          )
          .join("")
      : "<p class=\"meta\">No missing numeric-limit keys.</p>";
    const allowRows = allowList.length
      ? allowList
          .map((symbol) => `<div class="ledger-row">${escapeHtml(symbol)}</div>`)
          .join("")
      : "<p class=\"meta\">Allow-list is empty. Empty allow-list cannot execute.</p>";
    return `
      <h3>Board observability</h3>
      <p class="meta">Read-only. Source: ${escapeHtml(data.source || "database")}. This view does not write controls, trading_mode, allow-list, or permissions.</p>
      <h3>Control snapshot</h3>
      <p class="meta">trading_mode: ${escapeHtml(controls.trading_mode || data.trading_mode || "")} · allow-list empty: ${controls.allow_list_empty === undefined ? data.allow_list_empty : controls.allow_list_empty} · LIVE adapter: ${controls.live_adapter_loaded === undefined ? data.live_adapter_loaded : controls.live_adapter_loaded}</p>
      <p class="meta">Employees cannot write controls: ${controls.employees_cannot_write_controls !== false}. Board Member is the human authority. This view is read-only.</p>
      ${allowRows}
      <h3>Paper gate</h3>
      <p class="meta">PAPER: ${escapeHtml(paperGate.paper_status || "not started")} · trading_mode: ${escapeHtml(paperGate.trading_mode || data.trading_mode || "")} · execution: ${paperGate.execution === true} · paper execution implemented: ${paperGate.paper_execution_implemented === true}</p>
      <p class="meta">EVALUATION: ${escapeHtml(paperGate.evaluation_status || "not")} · LIVE-trading recommendation: ${escapeHtml(paperGate.live_trading_recommendation || "not")} · Board review: ${escapeHtml(paperGate.board_review || "not")} · explicit Board approval: ${escapeHtml(paperGate.explicit_board_approval || "not")}</p>
      <p class="meta">${escapeHtml(paperGate.gate || "PAPER → EVALUATION → LIVE-TRADING RECOMMENDATION → BOARD REVIEW → EXPLICIT BOARD APPROVAL → LIVE")}. Silence is not approval. Paper duration/success thresholds are OPEN BOARD DECISIONS and are not invented here.</p>
      <h3>Execution ports</h3>
      <p class="meta">Status only. No fills. BROKER_PAPER: ${escapeHtml(brokerPaper.status || "UNLOADED")} (loaded: ${brokerPaper.loaded === true}) · LIVE: ${escapeHtml(livePort.status || "UNLOADED")} (loaded: ${livePort.loaded === true})</p>
      <p class="meta">fills: ${executionPorts.fills === true} · paper fills: ${executionPorts.paper_fills === true} · live fills: ${executionPorts.live_fills === true}. Constructing or using BROKER_PAPER or LIVE is denied. This view does not load those ports.</p>
      <h3>Missing numeric limits</h3>
      <p class="meta">OPEN BOARD DECISIONS. Keys only — values are not invented here. Missing limits DENY execution.</p>
      ${missingRows}
      <p class="meta">${escapeHtml(data.cost_cap_label || "TEMPORARY DEVELOPMENT DEFAULT cost cap. Not a Board-approved budget.")}</p>
      <h3>07:30 meeting pack</h3>
      <p class="meta">${escapeHtml(pack.meeting || "07:30 Europe/London company meeting")} · MI brief: ${escapeHtml(pack.brief_headline || "not")} · CEO handoff: ${escapeHtml(pack.ceo_handoff_status || "not")} · Challenge SAMPLE thesis: ${escapeHtml(thesis.status || "not")} · Risk: ${escapeHtml(pack.risk_status || "not")}</p>
      <p class="meta">${escapeHtml(thesis.label || "SAMPLE — not a live trade")}. Not an order.</p>
      <h3>07:30 meeting artefacts</h3>
      ${artefactRows}
      <h3>07:30 company meeting record</h3>
      <p class="meta">${escapeHtml(companyMeeting.meeting || "07:30 Europe/London company meeting")} · on-demand · daemon: ${companyMeeting.daemon === true} · is_trade: ${companyMeeting.is_trade === true} · LIVE approval: ${companyMeeting.is_live_approval === true} · cannot start LIVE: ${companyMeeting.cannot_start_live !== false}</p>
      ${
        meetingRun
          ? `<div class="ledger-row">started_by: ${escapeHtml(meetingRun.started_by || "")} · CEO handoff: ${escapeHtml(meetingRun.ceo_handoff_status || "not")} · Challenge: ${escapeHtml(meetingRun.challenge_status || "not")} · Risk: ${escapeHtml(meetingRun.risk_status || "not")} · trading_mode: ${escapeHtml(meetingRun.trading_mode_at_run || "")}<br /><span class="meta">${escapeHtml(meetingRun.brief_headline || "no MI brief")} · ${escapeHtml(meetingRun.ran_at || "")} · live_started: ${meetingRun.live_started === true}</span></div>
      <p class="meta">Attendance (four existing employees only — not a 12-employee roster). Board Member is the human, not an employee attendee. None of these employees can start LIVE.</p>
      ${
        (meetingRun.attendees || [])
          .map(
            (row) =>
              `<div class="ledger-row">${escapeHtml(row.display_name || row.slug || "")} · ${escapeHtml(row.role_title || "")} · cannot approve LIVE: ${row.cannot_approve_live !== false}</div>`
          )
          .join("")
      }`
          : `<p class="meta">${escapeHtml(companyMeeting.note || "No 07:30 company meeting stored yet.")}</p>`
      }
      <h3>Documented routines</h3>
      <p class="meta">On-demand. Europe/London. No 24/7 daemon. Nightly filter has no invented clock hour. Does not write controls.</p>
      ${routineRows}
      <h3>Nightly memory filter</h3>
      <p class="meta">On-demand. Europe/London. Evidence append-only. Does not write controls.</p>
      ${filterBlock}
      <h3>Organisation memory titles</h3>
      ${titleRows}
      <h3>Employee status bubbles</h3>
      <p class="meta">Board-only read from the kernel. Click a name to open that person in this panel. Office stays visible.</p>
      ${bubbleRows}
      <h3>Cost ledger</h3>
      <p class="meta">Total units: ${escapeHtml(String((data.costs && data.costs.total_units) || 0))} · TEMPORARY cap ${escapeHtml(String(data.cost_cap_units || ""))} (not a Board budget)</p>
      ${costRows}
      <h3>Recent evidence</h3>
      <p class="meta">Append-only evidence store. Originals are not overwritten.</p>
      ${evidenceRows}
    `;
  }

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
    let history = [];
    try {
      history = await get("/employees/" + emp.slug + "/chat");
    } catch (err) {
      history = [];
    }
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
      ${renderChatHistory(history)}
    `;
  }

  function renderChatHistory(rows) {
    if (!rows || !rows.length) {
      return "<h3>Chat history</h3><p class=\"meta\">No chat stored in the database yet.</p>";
    }
    const items = rows
      .map(
        (row) =>
          `<div class="ledger-row">${escapeHtml(row.from_role || "")}: ${escapeHtml(String(row.body || "").slice(0, 400))}</div>`
      )
      .join("");
    return `<h3>Chat history</h3><p class="meta">From the database. Same employee runtime. Talk is disabled.</p>${items}`;
  }

  if (panelBody) {
    panelBody.addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-employee-slug]");
      if (!btn) return;
      const emp = employees.find((e) => e.slug === btn.getAttribute("data-employee-slug"));
      if (emp) selectEmployee(emp);
    });
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
      await showBoardObservability();
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
      showBoardObservability();
    }
  }

  boot();
})();
