/* W17ant/Claude-Office DOM camera. Uses their room PNG, furniture sprites,
   character sprites, and % layout from rooms.ts / FurnitureRenderer / Character.
   File: vendor/claude-office/rooms/office-day.png
   Do not fillRect a lookalike. Do not blit a third-party tileset as the floor.
   Staff are Board Addendum F names (person · department). No sitcom names.
   Click a person opens chat/work. Click never grants authority.
   Talk/voice stays disabled. LIVE stays blocked. */
(function (global) {
  const LAYOUT = global.CLAUDE_OFFICE_LAYOUT;
  const CHAR_DIR = "vendor/claude-office/sprites/characters/";
  const VENDOR = "vendor/claude-office/";

  /* Desk spots from Claude-Office src/rooms.ts agentSpots (main-office). */
  const STAFF = {
    ceo: { spot: "spot-1", base: "Me-1", color: "#ff4444", boss: true },
    "market-intelligence-research": { spot: "spot-2", base: "Claude-1", color: "#4a9eff" },
    challenge: { spot: "spot-3", base: "employee-1", color: "#f0c040" },
    risk: { spot: "spot-4", base: "security-audit-1", color: "#e07050" },
    trader: { spot: "spot-5", base: "employee-2", color: "#50c878" },
    "quant-strategy": { spot: "spot-7", base: "Frontend-dev-1", color: "#c060e0" },
    technology: { spot: "spot-8", base: "dev-1", color: "#60c0e0" },
  };

  const SEATS = {};
  const spotsById = {};
  (LAYOUT.agentSpots || []).forEach((spot) => {
    spotsById[spot.id] = spot;
  });
  Object.keys(STAFF).forEach((slug) => {
    const spot = spotsById[STAFF[slug].spot];
    SEATS[slug] = { x: spot.x, y: spot.y, facing: spot.spriteFacing, zIndex: spot.zIndex };
  });

  function asset(sprite) {
    return LAYOUT.assets[sprite] || null;
  }

  function spriteUrl(base, facing) {
    return CHAR_DIR + base + "-" + facing + ".png";
  }

  function portraitUrl(slug) {
    const spec = STAFF[slug] || STAFF.ceo;
    return spriteUrl(spec.base, "front-right");
  }

  function ensureMounted(root) {
    if (!root || root.dataset.claudeOfficeMounted === "1") return;
    if (!LAYOUT) throw new Error("CLAUDE_OFFICE_LAYOUT missing");

    root.classList.add("room-container");
    root.style.aspectRatio = LAYOUT.room.aspectRatio;
    root.style.width = "100%";
    root.style.maxHeight = "100%";
    root.style.position = "relative";
    root.innerHTML = "";

    const bg = document.createElement("div");
    bg.className = "room-background";
    bg.style.backgroundImage = "url(" + LAYOUT.room.background + ")";
    root.appendChild(bg);

    const furnLayer = document.createElement("div");
    furnLayer.className = "furniture-layer";
    LAYOUT.furniture.forEach((item) => {
      if (item.type === "hotspot") return;
      const meta = asset(item.sprite);
      if (!meta) return;
      const wrap = document.createElement("div");
      wrap.className = "furniture-item";
      wrap.style.position = "absolute";
      wrap.style.left = item.x + "%";
      wrap.style.top = item.y + "%";
      wrap.style.transform = "translate(-50%, -100%)";
      wrap.style.zIndex = String(item.zIndex != null ? item.zIndex : Math.round(item.y));
      wrap.style.pointerEvents = "none";
      if (item.label) wrap.title = item.label;
      const img = document.createElement("img");
      img.src = meta.path;
      img.alt = item.label || item.type;
      img.draggable = false;
      img.style.height = (meta.height || 64) + "px";
      img.style.width = "auto";
      img.style.imageRendering = "pixelated";
      img.style.display = "block";
      img.style.filter = "drop-shadow(0 0 0.5px #000) drop-shadow(0 0 0.5px #000)";
      wrap.appendChild(img);
      furnLayer.appendChild(wrap);
    });
    root.appendChild(furnLayer);

    const charLayer = document.createElement("div");
    charLayer.className = "character-layer";
    root.appendChild(charLayer);

    const overlay = document.createElement("div");
    overlay.className = "day-overlay afternoon";
    root.appendChild(overlay);

    root.dataset.claudeOfficeMounted = "1";
  }

  function draw(root, employees, selected) {
    if (!root) return;
    ensureMounted(root);
    const layer = root.querySelector(".character-layer");
    if (!layer) return;

    const seen = new Set();
    (employees || []).forEach((emp) => {
      const spec = STAFF[emp.slug];
      if (!spec) return;
      const seat = SEATS[emp.slug];
      seen.add(emp.slug);
      let wrap = layer.querySelector('[data-employee-slug="' + emp.slug + '"]');
      if (!wrap) {
        wrap = document.createElement("div");
        wrap.className = "character-wrapper state-working clickable-staff";
        wrap.setAttribute("data-employee-slug", emp.slug);
        wrap.setAttribute("role", "button");
        wrap.setAttribute("tabindex", "0");
        wrap.title = emp.display_name || emp.slug;
        wrap.style.left = seat.x + "%";
        wrap.style.top = seat.y + "%";
        wrap.style.transform = "translate(-50%, -100%)";
        wrap.style.zIndex = String(seat.zIndex != null ? seat.zIndex : Math.round(seat.y));

        const bubble = document.createElement("div");
        bubble.className = "speech-bubble";
        bubble.hidden = true;
        wrap.appendChild(bubble);

        const body = document.createElement("div");
        body.className = "char-body-group";
        const shadow = document.createElement("div");
        shadow.className = "char-shadow";
        const img = document.createElement("img");
        img.className = "char-sprite";
        img.alt = emp.display_name || emp.slug;
        img.draggable = false;
        img.src = spriteUrl(spec.base, seat.facing || "rear-left");
        img.style.height = spec.boss ? "85px" : "78px";
        img.style.width = "auto";
        img.style.filter =
          "drop-shadow(0 0 1px " + spec.color + ") drop-shadow(0 0 0.5px #000)";
        body.appendChild(shadow);
        body.appendChild(img);
        wrap.appendChild(body);
        layer.appendChild(wrap);
      }

      const on = selected && selected.slug === emp.slug;
      wrap.classList.toggle("selected-staff", Boolean(on));
      wrap.setAttribute("aria-pressed", on ? "true" : "false");
      const bubble = wrap.querySelector(".speech-bubble");
      const text = emp.status_bubble || "";
      if (text) {
        bubble.hidden = false;
        bubble.textContent = text;
      } else {
        bubble.hidden = true;
      }
      emp._hit = { slug: emp.slug };
    });

    layer.querySelectorAll("[data-employee-slug]").forEach((el) => {
      if (!seen.has(el.getAttribute("data-employee-slug"))) el.remove();
    });
  }

  function drawPortrait(ctx, canvas, slug) {
    /* Kept for tests; portraits are <img> in the staff bar. */
    const url = portraitUrl(slug);
    if (canvas && canvas.tagName === "IMG") {
      canvas.src = url;
      return;
    }
    if (!ctx || !canvas) return;
    const img = new Image();
    img.onload = function () {
      ctx.imageSmoothingEnabled = false;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    };
    img.src = url;
  }

  global.VarmaOfficeFloor = {
    draw: draw,
    drawPortrait: drawPortrait,
    portraitUrl: portraitUrl,
    SEATS: SEATS,
    STAFF: STAFF,
    CHAR_DIR: CHAR_DIR,
    VENDOR: VENDOR,
    ROOM_URL: LAYOUT.room.background,
  };
})(window);
