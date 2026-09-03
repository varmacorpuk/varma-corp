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
  let lastJobNote = "";
  let jobRunning = false;
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
    desk(280, 250, "TRADER");
    desk(200, 40, "QUANT");
    desk(500, 140, "TECH");

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
      kind === "ceo"
        ? "#1d3557"
        : kind === "challenge"
          ? "#6b3a2a"
          : kind === "risk"
            ? "#8b1e1e"
            : kind === "trader"
              ? "#3d5a80"
              : kind === "quant-strategy"
                ? "#4a3f6b"
                : kind === "technology"
                  ? "#2c3e50"
                  : "#2f5d50";
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
    ctx.fillText(String(name || "").slice(0, 28), x - 4, y + 28 * sprite.scale / 4 + 20);
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
    const numericLimits = data.numeric_limits || {};
    const limitItems = numericLimits.items || [];
    const killSwitch = data.kill_switch || {};
    const evaluation = data.evaluation || {};
    const paperLedger = data.paper_ledger || {};
    const paperSession = data.paper_session || {};
    const paperFlatten = data.paper_flatten || {};
    const flattenRun = paperFlatten.run;
    const addendumC = data.addendum_c || {};
    const addendumJ = data.addendum_j || {};
    const addendumK = data.addendum_k || {};
    const backup = data.backup || {};
    const assumptions = paperLedger.assumptions || {};
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
    const flattenSched = documented.flatten_us_close || {};
    const flattenLondonSched = documented.flatten_london_close || {};
    const backupSched = documented.backup || {};
    const dbRoutines = routines.items || [];
    const routineRows = `
      <div class="ledger-row">06:30 weekday brief · ${escapeHtml(briefSched.timezone || "Europe/London")} · daemon: ${briefSched.daemon === true} · ${escapeHtml(briefSched.cli || "python -m varma.routines.run_brief")}<br /><span class="meta">${escapeHtml(briefSched.description || "")}</span></div>
      <div class="ledger-row">07:30 company meeting · ${escapeHtml(meetingSched.timezone || "Europe/London")} · daemon: ${meetingSched.daemon === true} · is_trade: ${meetingSched.is_trade === true} · ${escapeHtml(meetingSched.cli || "python -m varma.routines.run_0730_meeting")}<br /><span class="meta">${escapeHtml(meetingSched.description || "")}</span></div>
      <div class="ledger-row">Flatten US names before US cash close · ${escapeHtml(flattenSched.timezone || "Europe/London")} · daemon: ${flattenSched.daemon === true} · flatten_at: ${escapeHtml(flattenSched.flatten_at || "US_REGULAR_CASH_CLOSE")} · split_flatten_clocks true · ${escapeHtml(flattenSched.cli || "python -m varma.routines.run_flatten_us_close")}<br /><span class="meta">${escapeHtml(flattenSched.description || "")}</span></div>
      <div class="ledger-row">Flatten LSE names in London closing auction 16:30–16:35 · ${escapeHtml(flattenLondonSched.timezone || "Europe/London")} · daemon: ${flattenLondonSched.daemon === true} · flatten_at: ${escapeHtml(flattenLondonSched.flatten_at || "LONDON_CLOSING_AUCTION")} · 02F bound · ${escapeHtml(flattenLondonSched.cli || "python -m varma.routines.run_flatten_london_close")}<br /><span class="meta">${escapeHtml(flattenLondonSched.description || "")}</span></div>
      <div class="ledger-row">Nightly memory filter · ${escapeHtml(filterSched.timezone || "Europe/London")} · daemon: ${filterSched.daemon === true} · writes_controls: ${filterSched.writes_controls === true} · ${escapeHtml(filterSched.cli || "")}<br /><span class="meta">${escapeHtml(filterSched.description || "")}</span></div>
      <div class="ledger-row">Company backup · ${escapeHtml(backupSched.timezone || "Europe/London")} · daemon: ${backupSched.daemon === true} · after US close / end of London evening · owner: ${escapeHtml(backupSched.owner_display_name || "Owen Blake · Technology")} · ${escapeHtml(backupSched.cli || "python -m varma.routines.run_backup")}<br /><span class="meta">${escapeHtml(backupSched.description || "")}</span></div>
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
              `<div class="ledger-row">${escapeHtml(key)} — unset (still DENY)</div>`
          )
          .join("")
      : "<p class=\"meta\">No missing numeric-limit keys. Board Addendum A values are set.</p>";
    const limitRows = limitItems.length
      ? limitItems
          .map(
            (row) =>
              `<div class="ledger-row">${escapeHtml(row.key || "")}: ${escapeHtml(String(row.value))} ${escapeHtml(row.unit || "")} · ${escapeHtml(row.source || "Board Addendum A 2026-08-27")}</div>`
          )
          .join("")
      : missingRows;
    const allowRows = allowList.length
      ? allowList
          .map((symbol) => `<div class="ledger-row">${escapeHtml(symbol)}</div>`)
          .join("")
      : "<p class=\"meta\">Allow-list is Board Addendum E (PAPER membership). LIVE still denied.</p>";
    return `
      <h3>Board observability</h3>
      <p class="meta">Read-only. Source: ${escapeHtml(data.source || "database")}. This view does not write controls, trading_mode, allow-list, or permissions. GET /observability does not run jobs.</p>
      <h3>On-demand jobs</h3>
      <p class="meta">Board Member only. POST, not GET /observability. Employees are denied. Does not load broker ports, change trading_mode, or fill paper/live orders. CLI still works. After a run this panel refreshes from the database.</p>
      ${renderJobButtons(data)}
      ${lastJobNote ? `<p class="meta" id="job-run-status">${escapeHtml(lastJobNote)}</p>` : '<p class="meta" id="job-run-status"></p>'}
      <h3>Control snapshot</h3>
      <p class="meta">trading_mode: ${escapeHtml(controls.trading_mode || data.trading_mode || "")} · allow-list empty: ${controls.allow_list_empty === undefined ? data.allow_list_empty : controls.allow_list_empty} · LIVE adapter: ${controls.live_adapter_loaded === undefined ? data.live_adapter_loaded : controls.live_adapter_loaded} · kill switch halted: ${killSwitch.halted === true}</p>
      <p class="meta">Employees cannot write controls: ${controls.employees_cannot_write_controls !== false}. Board Member is the human authority. This view is read-only except Board-only job runs and the kill switch.</p>
      ${allowRows}
      <h3>Board Addendum A 2026-08-27 (Board-set)</h3>
      <p class="meta">Currency: GBP · Timezone: Europe/London. These VALUES are Board-set, not invented silent defaults. Employees cannot write limits. Unknown tickers deny. trading_mode stays LIVE_BLOCKED.</p>
      ${limitRows}
      <h3>Board Addendum C 2026-08-27 (paper session)</h3>
      <p class="meta">Desk open: UK cash open 08:00 Europe/London through US regular cash close 16:00 America/New_York converted onto the Europe/London clock (not hardcoded 21:00). split_flatten_clocks true. LSE names (SHEL.L, AZN.L, ULVR.L) flatten in the London closing auction 16:30–16:35 (02F bound; cannot drop independently of the opening buy). US names flatten at US close. Overnight: ${paperSession.overnight_holds === true}. US after-hours: ${paperSession.us_after_hours === true}. Extended hours: ${paperSession.extended_hours === true}. Daemon: ${paperSession.daemon === true}.</p>
      <p class="meta">GET /observability does not flatten. Flatten uses the internal simulator, not a broker. Empty allow-list still denies new orders. ${escapeHtml(addendumC.label || "Board Addendum C 2026-08-27")}</p>
      ${
        flattenRun
          ? `<div class="ledger-row">Last flatten: cancelled ${escapeHtml(String(flattenRun.cancelled_open_paper_orders ?? 0))} open orders · closed ${escapeHtml(String(flattenRun.closed_positions ?? 0))} positions · remaining ${escapeHtml(String(flattenRun.positions_remaining ?? 0))} · ${escapeHtml(flattenRun.ran_at || "")}</div>`
          : `<p class="meta">${escapeHtml(paperFlatten.note || "No flatten-before-US-close run stored yet.")}</p>`
      }
      <h3>Kill switch</h3>
      <p class="meta">Halted: ${killSwitch.halted === true} · paper equity: ${escapeHtml(String(killSwitch.paper_equity_gbp ?? paperLedger.equity_gbp ?? ""))} GBP · London-day P&amp;L: ${escapeHtml(String(killSwitch.london_day_pnl_gbp ?? paperLedger.london_day_pnl_gbp ?? ""))} GBP</p>
      <p class="meta">${escapeHtml(killSwitch.halt_if || "halt if paper equity &lt;= 800 GBP OR London-day P&amp;L &lt;= -50 GBP")}. Board Member can halt without an AI employee. On halt: cancel open PAPER orders only; never load LIVE; never flatten live.</p>
      <div class="kill-switch-actions">
        <button type="button" class="kill-halt" data-kill-action="halt">Halt paper</button>
        <button type="button" class="kill-reset" data-kill-action="reset">Reset kill switch</button>
      </div>
      <p class="meta">Employees cannot reset the kill switch.</p>
      <h3>Board Addendum I 2026-08-27 (two-opening rule)</h3>
      <p class="meta">Addendum I still exists as the two-opening rule. Grand Opening PAPER happened (Hari explicit yes, 3 Sep 2026, word: Open). Practice / paper only. The first paper-trade PATH exists (Trader proposal → ControlEngine → internal simulator). PAPER execution: ${escapeHtml(paperGate.paper_execution || (paperGate.paper_execution_closed === false ? "OPEN" : "CLOSED"))}. £1000 is the paper starting book. Addendum A limits apply. LIVE still blocked. Never auto-switch. Silence is not approval. Employees cannot open or close the firm. Deny reason if the Board closes paper again: PAPER_EXECUTION_CLOSED. Next human step is paper operation. LIVE later only if the Board says so.</p>
      <h3>Board Addendum K 2026-09-03 (LSE after London cash close)</h3>
      <p class="meta">${escapeHtml(addendumK.label || "Board Addendum K 2026-09-03")}. Hari explicit yes. After London cash shuts, deny paper orders in SHEL.L, AZN.L, ULVR.L only. CEO desk 02F: those three flatten in the London closing auction 16:30–16:35; US seven wait until US flatten. Desk still UK cash open through US cash close. split_flatten_clocks true. Dual-listed US lines SHEL/AZN/ULVR are not on the allow-list. LIVE_BLOCKED. Employees cannot write this lock.</p>
      <h3>Board Addendum J 2026-08-27 (company backup)</h3>
      <p class="meta">Company records are not on the Board Member laptop and not in GitHub. GitHub is code only. System of record: ${escapeHtml(backup.system_of_record || "database")}. Encrypted at rest: ${backup.encrypted_at_rest !== false}. Owner: ${escapeHtml(backup.owner_display_name || addendumJ.owner_display_name || "Owen Blake · Technology")}. Owen cannot write trading_mode, allow-list, or open the firm. Schedule: ${escapeHtml(backup.schedule || "daily after US close / end of London evening")} · daemon: ${backup.daemon === true}.</p>
      <p class="meta">Included: paper ledger, evidence, organisational memory, control snapshots. Excluded: secrets, live broker credentials (must not exist yet). Employees including the CEO cannot download secrets. Last successful backup: ${escapeHtml(backup.last_successful_backup_at || "none")}. Last failure: ${escapeHtml(backup.last_failure_at || "none")}${backup.last_failure_reason ? " · " + escapeHtml(backup.last_failure_reason) : ""}.</p>
      <h3>Paper gate</h3>
      <p class="meta">PAPER: ${escapeHtml(paperGate.paper_status || "not started")} · trading_mode: ${escapeHtml(paperGate.trading_mode || data.trading_mode || "")} · execution: ${paperGate.execution === true} · paper_execution_closed: ${paperGate.paper_execution_closed === true} · internal simulator: ${paperGate.internal_simulator === true}</p>
      <p class="meta">EVALUATION: ${escapeHtml(paperGate.evaluation_status || "not")} · LIVE-trading recommendation: ${escapeHtml(paperGate.live_trading_recommendation || "not")} · Board review: ${escapeHtml(paperGate.board_review || "not")} · explicit Board approval: ${escapeHtml(paperGate.explicit_board_approval || "not")}</p>
      <p class="meta">Success: ${escapeHtml(paperGate.successful_trade_definition || evaluation.successful_trade_definition || "CLOSED paper trade with profit &gt; 0")}. Trigger: win rate &gt; 50% AND book profitable. Auto-switch LIVE: ${paperGate.evaluation_auto_switch_live === true}. Paper duration remains an OPEN BOARD DECISION. Silence is not approval.</p>
      <h3>Paper ledger (internal simulator)</h3>
      <p class="meta">Not a broker. BROKER_PAPER and LIVE remain UNLOADED. PAPER allow-list is Board Addendum E. Simulated capital: ${escapeHtml(String(paperLedger.simulated_capital_gbp ?? "1000"))} GBP (paper starting book) · cash: ${escapeHtml(String(paperLedger.cash_gbp ?? ""))} · equity: ${escapeHtml(String(paperLedger.equity_gbp ?? ""))} · fills: ${escapeHtml(String(paperLedger.fills ?? 0))}</p>
      <p class="meta">Assumptions: spread ${escapeHtml(String(assumptions.spread_bps ?? 10))} bps · slippage ${escapeHtml(String(assumptions.slippage_bps ?? 5))} bps · commission ${escapeHtml(String(assumptions.commission_bps ?? 5))} bps. Fake delayed last treated as GBP (INTERNAL ASSUMPTION, no FX vendor).</p>
      <h3>Evaluation ledger</h3>
      <p class="meta">Closed trades: ${escapeHtml(String(evaluation.closed_trades ?? 0))} · profitable closes: ${escapeHtml(String(evaluation.profitable_closes ?? 0))} · win rate: ${escapeHtml(String(evaluation.win_rate ?? 0))} · book P&amp;L: ${escapeHtml(String(evaluation.book_pnl_gbp ?? 0))} GBP · trigger met: ${evaluation.evaluation_trigger_met === true} · auto-switch LIVE: ${evaluation.evaluation_auto_switch_live === true}</p>
      <p class="meta">Zero fills is valid while the allow-list is empty. Paper continues until the Board explicitly approves moving on.</p>
      <h3>Execution ports</h3>
      <p class="meta">Status only. No fills. BROKER_PAPER: ${escapeHtml(brokerPaper.status || "UNLOADED")} (loaded: ${brokerPaper.loaded === true}) · LIVE: ${escapeHtml(livePort.status || "UNLOADED")} (loaded: ${livePort.loaded === true})</p>
      <p class="meta">fills: ${executionPorts.fills === true} · paper fills: ${executionPorts.paper_fills === true} · live fills: ${executionPorts.live_fills === true}. Constructing or using BROKER_PAPER or LIVE is denied. This view does not load those ports.</p>
      <h3>Missing numeric limits</h3>
      <p class="meta">Board Addendum A 2026-08-27 set the required keys. Missing keys (if any) still DENY execution. Values are shown above.</p>
      ${missingRows}
      <p class="meta">${escapeHtml(data.cost_cap_label || "TEMPORARY DEVELOPMENT DEFAULT cost cap. Not a Board-approved budget.")}</p>
      <h3>07:30 meeting pack</h3>
      <p class="meta">${escapeHtml(pack.meeting || "07:30 Europe/London company meeting")} · MI brief: ${escapeHtml(pack.brief_headline || "not")} · CEO handoff: ${escapeHtml(pack.ceo_handoff_status || "not")} · Challenge SAMPLE thesis: ${escapeHtml(thesis.status || "not")} · Risk: ${escapeHtml(pack.risk_status || "not")}</p>
      <p class="meta">${escapeHtml(thesis.label || "SAMPLE — not a live trade")}. Not an order.</p>
      <h3>07:30 meeting artefacts</h3>
      ${artefactRows}
      <h3>07:30 company meeting record</h3>
      <p class="meta">${escapeHtml(companyMeeting.meeting || "07:30 Europe/London company meeting")} · on-demand · daemon: ${companyMeeting.daemon === true} · is_trade: ${companyMeeting.is_trade === true} · LIVE approval: ${companyMeeting.is_live_approval === true} · cannot start LIVE: ${companyMeeting.cannot_start_live !== false} · no Board Member diary invite · no calendar invite · no approval email</p>
      ${
        meetingRun
          ? `<div class="ledger-row">started_by: ${escapeHtml(meetingRun.started_by || "")} · CEO handoff: ${escapeHtml(meetingRun.ceo_handoff_status || "not")} · Challenge: ${escapeHtml(meetingRun.challenge_status || "not")} · Risk: ${escapeHtml(meetingRun.risk_status || "not")} · trading_mode: ${escapeHtml(meetingRun.trading_mode_at_run || "")}<br /><span class="meta">${escapeHtml(meetingRun.brief_headline || "no MI brief")} · ${escapeHtml(meetingRun.ran_at || "")} · live_started: ${meetingRun.live_started === true}</span></div>
      <p class="meta">Attendance (original four for 07:30 — not a 12-employee roster). Names are person · department. Board Member is the human, not an employee attendee. None of these employees can start LIVE.</p>
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

  function renderJobButtons(data) {
    const jobs = (data && data.runnable_jobs && data.runnable_jobs.items) || [
      { id: "run-brief", label: "Run morning intelligence brief", path: "/routines/run-brief" },
      { id: "run-challenge", label: "Run SAMPLE challenge", path: "/routines/run-challenge" },
      { id: "run-risk-deny", label: "Run Risk deny-path", path: "/routines/run-risk-deny" },
      { id: "run-0730-meeting", label: "Run 07:30 meeting record", path: "/routines/run-0730-meeting" },
      { id: "run-nightly-filter", label: "Run nightly memory filter", path: "/routines/run-nightly-filter" },
      { id: "run-flatten-us-close", label: "Flatten paper before US cash close", path: "/routines/run-flatten-us-close" },
      { id: "run-flatten-london-close", label: "Flatten LSE paper in London closing auction", path: "/routines/run-flatten-london-close" },
      { id: "run-backup", label: "Run company backup now", path: "/routines/run-backup" },
      { id: "run-paper-trade-path", label: "Run Trader paper-ticket proposal", path: "/routines/run-paper-trade-path" },
    ];
    return (
      '<div class="job-runs">' +
      jobs
        .map(
          (job) =>
            `<button type="button" class="job-run" data-job-path="${escapeHtml(job.path || "")}" data-job-id="${escapeHtml(job.id || "")}" ${jobRunning ? "disabled" : ""}>${escapeHtml(job.label || job.id || "")}</button>`
        )
        .join("") +
      "</div>"
    );
  }

  function chatPlaceholder(emp) {
    const label = (emp && emp.display_name) || "";
    if (label) return "Ask " + label + "…";
    const slug = emp && emp.slug;
    if (slug === "ceo") return "Ask Jordan Hale · CEO…";
    if (slug === "challenge") return "Ask Sam Okeke · Challenge…";
    if (slug === "risk") return "Ask Elena Voss · Risk…";
    if (slug === "trader") return "Ask Chris Adeyemi · Trader…";
    if (slug === "quant-strategy") return "Ask Nina Kapoor · Quant…";
    if (slug === "technology") return "Ask Owen Blake · Technology…";
    return "Ask Asha Patel · Research…";
  }

  async function selectEmployee(emp) {
    if (!rightPanel) return;
    selected = emp;
    draw();
    placeholder.hidden = true;
    panelBody.hidden = false;
    chatForm.hidden = false;
    chatInput.placeholder = chatPlaceholder(emp);
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
      const jobBtn = ev.target.closest("[data-job-path]");
      if (jobBtn) {
        const path = jobBtn.getAttribute("data-job-path") || "";
        if (path.indexOf("/routines/") === 0) {
          runBoardJob(path, jobBtn.textContent || path);
        }
        return;
      }
      const killBtn = ev.target.closest("[data-kill-action]");
      if (killBtn) {
        runKillSwitch(killBtn.getAttribute("data-kill-action") || "");
        return;
      }
      const btn = ev.target.closest("[data-employee-slug]");
      if (!btn) return;
      const emp = employees.find((e) => e.slug === btn.getAttribute("data-employee-slug"));
      if (emp) selectEmployee(emp);
    });
  }

  async function runKillSwitch(action) {
    if (jobRunning) return;
    jobRunning = true;
    const halt = action === "halt";
    const path = halt ? "/controls/kill-switch" : "/controls/kill-switch/reset";
    lastJobNote = halt ? "Halting paper…" : "Resetting kill switch…";
    const status = document.getElementById("job-run-status");
    if (status) status.textContent = lastJobNote;
    try {
      const r = await fetch(API + path, {
        method: "POST",
        headers: headers(true),
        body: halt ? JSON.stringify({ halt: true }) : undefined,
      });
      if (!r.ok) {
        lastJobNote =
          (halt ? "Halt" : "Reset") +
          " denied (" +
          r.status +
          "). Board Member only. Employees cannot reset the kill switch. LIVE was not loaded.";
        jobRunning = false;
        await showBoardObservability();
        return;
      }
      lastJobNote = halt
        ? "Kill switch halted. Open PAPER orders cancelled only. LIVE not loaded. No live flatten."
        : "Kill switch reset by Board Member. trading_mode still LIVE_BLOCKED.";
      jobRunning = false;
      await showBoardObservability();
    } catch (err) {
      lastJobNote = "Kill switch request failed. Kernel unreachable or Board identity missing.";
      jobRunning = false;
      await showBoardObservability();
    }
  }

  async function runBoardJob(path, label) {
    if (jobRunning) return;
    jobRunning = true;
    lastJobNote = "Running " + label + "…";
    const status = document.getElementById("job-run-status");
    if (status) status.textContent = lastJobNote;
    document.querySelectorAll(".job-run").forEach((b) => {
      b.disabled = true;
    });
    try {
      const r = await fetch(API + path, { method: "POST", headers: headers() });
      if (!r.ok) {
        lastJobNote = label + " denied (" + r.status + "). Board Member only. Employees cannot run jobs.";
        jobRunning = false;
        await showBoardObservability();
        return;
      }
      const body = await r.json().catch(() => ({}));
      lastJobNote =
        path.indexOf("paper-trade-path") !== -1
          ? label +
            " finished. Chris Adeyemi proposed a paper ticket. ControlEngine " +
            (body.allowed
              ? "ALLOW " + (body.reason || "PAPER_FILL_SIMULATED") + ". Simulator fill on the £1000 paper book. LIVE still off. Panel refreshed from the database."
              : "DENY " + (body.reason || "PAPER_EXECUTION_CLOSED") + ". No live fill. LIVE still off. Panel refreshed from the database.")
          : path.indexOf("flatten") !== -1
          ? label +
            " finished. Internal simulator flatten only. Panel refreshed from the database. trading_mode unchanged. BROKER_PAPER and LIVE remain UNLOADED. No broker fills."
          : label +
            " finished. Panel refreshed from the database. trading_mode unchanged. BROKER_PAPER and LIVE remain UNLOADED. No fills.";
      jobRunning = false;
      await showBoardObservability();
    } catch (err) {
      lastJobNote = "Job failed. Kernel unreachable or Board identity missing. This panel does not write controls.";
      jobRunning = false;
      await showBoardObservability();
    }
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
          display_name: "Asha Patel · Research",
          status_bubble: "OFFLINE",
          office_x: 96,
          office_y: 108,
        },
        {
          slug: "ceo",
          display_name: "Jordan Hale · CEO",
          status_bubble: "OFFLINE",
          office_x: 220,
          office_y: 70,
        },
        {
          slug: "challenge",
          display_name: "Sam Okeke · Challenge",
          status_bubble: "OFFLINE",
          office_x: 40,
          office_y: 48,
        },
        {
          slug: "risk",
          display_name: "Elena Voss · Risk",
          status_bubble: "OFFLINE",
          office_x: 255,
          office_y: 175,
        },
        {
          slug: "trader",
          display_name: "Chris Adeyemi · Trader",
          status_bubble: "OFFLINE",
          office_x: 160,
          office_y: 160,
        },
        {
          slug: "quant-strategy",
          display_name: "Nina Kapoor · Quant",
          status_bubble: "OFFLINE",
          office_x: 120,
          office_y: 40,
        },
        {
          slug: "technology",
          display_name: "Owen Blake · Technology",
          status_bubble: "OFFLINE",
          office_x: 250,
          office_y: 120,
        },
      ];
      draw();
      showBoardObservability();
    }
  }

  boot();
})();
