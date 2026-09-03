/* Pixel-art office floor. Visual inspiration: MIT pixel-agents
   (https://github.com/pixel-agents-hq/pixel-agents). Original Varma renderer.
   Staff are Board Addendum F names (person · department). No sitcom names.
   Click never grants authority. Talk/voice stays disabled. LIVE stays blocked. */
(function (global) {
  const T = 16;
  const S = 2;
  const COLS = 32;
  const ROWS = 20;

  const MAP = [
    "################################",
    "#..............#......#........#",
    "#..............#......#........#",
    "#..............#......#........#",
    "#..............#......#........#",
    "#..............#......#........#",
    "#######.##########.#######.#####",
    "#..............#......#........#",
    "#..............#......#........#",
    "#..............#......#........#",
    "#..............#......#........#",
    "#..............#......#........#",
    "#######.##########.#######.#####",
    "#.......#......#...............#",
    "#.......#......#...............#",
    "#..............................#",
    "#.......#......#...............#",
    "#.......#......#...............#",
    "#.......#......#...............#",
    "################################",
  ];

  const PAL = {
    floorA: "#3aa8a8",
    floorB: "#2e9494",
    floorShadow: "#217878",
    wall: "#4a4a54",
    wallMid: "#5a5a66",
    wallTop: "#7a7a86",
    wallDark: "#2e2e36",
    wood: "#8a5a32",
    woodTop: "#c4a06a",
    woodMid: "#a07040",
    woodDark: "#5c3a1c",
    felt: "#2f7a3c",
    feltDark: "#1f5a2c",
    plant: "#3d8c48",
    plantLite: "#6cbc58",
    plantDark: "#245c30",
    pot: "#8b4030",
    potLite: "#b06040",
    chairRed: "#c43b3b",
    chairRedDark: "#8a2424",
    chairOffice: "#3a3a44",
    screen: "#7ec8e3",
    screenHi: "#c8f0ff",
    screenDark: "#1a3340",
    sofa: "#c4453c",
    sofaDark: "#8a2e28",
    paper: "#f4efe0",
    lamp: "#f0d878",
    metal: "#8a8a94",
    ink: "#0b1f1c",
    foam: "#f7f1e6",
    rug: "#6b4a2e",
    glass: "#8ec4d4",
  };

  const SEATS = {
    ceo: { c: 25, r: 3 },
    "market-intelligence-research": { c: 2, r: 10 },
    "quant-strategy": { c: 7, r: 10 },
    trader: { c: 12, r: 10 },
    technology: { c: 26, r: 9 },
    challenge: { c: 3, r: 16 },
    risk: { c: 22, r: 16 },
  };

  const LOOK = {
    ceo: { hair: "#1a1a1a", skin: "#e6c8a8", body: "#1d3557", pants: "#0d1b2a", accent: "#c4a06a" },
    "market-intelligence-research": { hair: "#2b2118", skin: "#d4a574", body: "#2f5d50", pants: "#1d3557", accent: "#c4a06a" },
    challenge: { hair: "#1a1210", skin: "#8d5a3a", body: "#6b3a2a", pants: "#2a1a14", accent: "#d8c39a" },
    risk: { hair: "#c4b48a", skin: "#f0d0b0", body: "#8b1e1e", pants: "#3a1010", accent: "#e8dcc8" },
    trader: { hair: "#1a1210", skin: "#6b4228", body: "#3d5a80", pants: "#1d2a3a", accent: "#7ec8e3" },
    "quant-strategy": { hair: "#2b2118", skin: "#e0b898", body: "#4a3f6b", pants: "#2a2438", accent: "#c8b8e8" },
    technology: { hair: "#3a3028", skin: "#e8c8a8", body: "#2c3e50", pants: "#1a242e", accent: "#8a8a94" },
  };

  function canvasSize() {
    return { w: COLS * T * S, h: ROWS * T * S };
  }

  function px(ctx, x, y, w, h, c) {
    ctx.fillStyle = c;
    ctx.fillRect(Math.round(x * S), Math.round(y * S), Math.round(w * S), Math.round(h * S));
  }

  function at(c, r) {
    if (r < 0 || r >= ROWS || c < 0 || c >= COLS) return "#";
    return MAP[r].charAt(c);
  }

  function isWall(c, r) {
    return at(c, r) === "#";
  }

  function isFloor(c, r) {
    return at(c, r) === ".";
  }

  function box(ctx, x, y, w, h, top, side) {
    px(ctx, x, y, w, Math.max(1, h - 3), top);
    px(ctx, x, y + h - 3, w, 3, side);
    px(ctx, x + w - 1, y + 1, 1, h - 2, side);
  }

  function plant(ctx, x, y) {
    px(ctx, x + 4, y + 11, 8, 5, PAL.pot);
    px(ctx, x + 3, y + 11, 10, 2, PAL.potLite);
    px(ctx, x + 6, y + 2, 5, 10, PAL.plantDark);
    px(ctx, x + 3, y + 4, 6, 6, PAL.plant);
    px(ctx, x + 8, y + 3, 6, 7, PAL.plantLite);
    px(ctx, x + 5, y + 1, 3, 3, PAL.plantLite);
  }

  function chair(ctx, x, y, red) {
    const back = red ? PAL.chairRed : PAL.chairOffice;
    const dark = red ? PAL.chairRedDark : PAL.wallDark;
    px(ctx, x + 2, y, 10, 8, back);
    px(ctx, x + 3, y + 1, 8, 4, dark);
    box(ctx, x, y + 7, 14, 7, back, dark);
    px(ctx, x + 1, y + 13, 3, 3, PAL.metal);
    px(ctx, x + 10, y + 13, 3, 3, PAL.metal);
  }

  function monitor(ctx, x, y) {
    px(ctx, x, y, 16, 12, PAL.wallDark);
    px(ctx, x + 2, y + 2, 12, 8, PAL.screen);
    px(ctx, x + 3, y + 3, 4, 2, PAL.screenHi);
    px(ctx, x + 7, y + 12, 3, 3, PAL.metal);
    px(ctx, x + 4, y + 14, 9, 2, PAL.wallDark);
  }

  function workstation(ctx, x, y) {
    box(ctx, x, y + 10, 44, 12, PAL.woodTop, PAL.woodDark);
    px(ctx, x + 2, y + 11, 40, 2, PAL.wood);
    monitor(ctx, x + 14, y);
    px(ctx, x + 8, y + 13, 16, 4, PAL.metal);
    px(ctx, x + 10, y + 14, 2, 2, PAL.ink);
    px(ctx, x + 13, y + 14, 2, 2, PAL.ink);
    px(ctx, x + 16, y + 14, 2, 2, PAL.ink);
    px(ctx, x + 28, y + 12, 8, 6, PAL.paper);
    px(ctx, x + 30, y + 13, 5, 1, PAL.ink);
  }

  function lDesk(ctx, x, y) {
    box(ctx, x, y + 16, 48, 14, PAL.woodTop, PAL.woodDark);
    box(ctx, x + 36, y, 16, 30, PAL.woodMid, PAL.woodDark);
    px(ctx, x + 2, y + 17, 32, 2, PAL.wood);
    monitor(ctx, x + 10, y + 6);
    px(ctx, x + 6, y + 20, 14, 4, PAL.metal);
    px(ctx, x + 38, y + 4, 10, 8, PAL.paper);
  }

  function conferenceTable(ctx, x, y) {
    box(ctx, x, y, 112, 36, PAL.woodTop, PAL.woodDark);
    px(ctx, x + 4, y + 3, 104, 2, PAL.wood);
    px(ctx, x + 8, y + 8, 18, 12, PAL.paper);
    px(ctx, x + 10, y + 10, 12, 1, PAL.ink);
    px(ctx, x + 10, y + 13, 10, 1, PAL.ink);
    px(ctx, x + 40, y + 6, 22, 14, PAL.wallDark);
    px(ctx, x + 42, y + 8, 18, 10, PAL.screen);
    px(ctx, x + 44, y + 9, 6, 3, PAL.screenHi);
    px(ctx, x + 72, y + 10, 16, 10, PAL.paper);
    px(ctx, x + 88, y + 8, 12, 8, PAL.paper);
    px(ctx, x + 6, y + 32, 6, 6, PAL.woodDark);
    px(ctx, x + 100, y + 32, 6, 6, PAL.woodDark);
  }

  function poolTable(ctx, x, y) {
    box(ctx, x, y, 72, 40, PAL.wood, PAL.woodDark);
    px(ctx, x + 6, y + 5, 60, 28, PAL.felt);
    px(ctx, x + 6, y + 5, 60, 3, PAL.feltDark);
    px(ctx, x + 6, y + 5, 5, 5, PAL.ink);
    px(ctx, x + 61, y + 5, 5, 5, PAL.ink);
    px(ctx, x + 6, y + 28, 5, 5, PAL.ink);
    px(ctx, x + 61, y + 28, 5, 5, PAL.ink);
    px(ctx, x + 33, y + 5, 5, 5, PAL.ink);
    px(ctx, x + 18, y + 14, 3, 3, "#f2e6c8");
    px(ctx, x + 28, y + 18, 3, 3, "#c43b3b");
    px(ctx, x + 36, y + 12, 3, 3, "#3d5a80");
    px(ctx, x + 44, y + 20, 3, 3, "#f0d878");
    px(ctx, x + 24, y + 22, 3, 3, "#4a3f6b");
  }

  function sofa(ctx, x, y) {
    box(ctx, x, y + 8, 48, 16, PAL.sofa, PAL.sofaDark);
    px(ctx, x, y, 10, 12, PAL.sofaDark);
    px(ctx, x + 38, y, 10, 12, PAL.sofaDark);
    px(ctx, x + 12, y + 10, 12, 6, PAL.chairRed);
    px(ctx, x + 26, y + 10, 12, 6, PAL.chairRed);
  }

  function coffeeTable(ctx, x, y) {
    box(ctx, x, y, 28, 14, PAL.woodTop, PAL.woodDark);
    px(ctx, x + 6, y + 4, 8, 6, PAL.paper);
    px(ctx, x + 18, y + 3, 6, 6, PAL.pot);
  }

  function cabinet(ctx, x, y) {
    box(ctx, x, y, 16, 24, PAL.metal, PAL.wallDark);
    px(ctx, x + 2, y + 3, 12, 6, PAL.wallMid);
    px(ctx, x + 2, y + 11, 12, 6, PAL.wallMid);
    px(ctx, x + 12, y + 5, 2, 2, PAL.lamp);
    px(ctx, x + 12, y + 13, 2, 2, PAL.lamp);
  }

  function bookshelf(ctx, x, y) {
    box(ctx, x, y, 16, 28, PAL.wood, PAL.woodDark);
    px(ctx, x + 2, y + 3, 4, 8, "#8b1e1e");
    px(ctx, x + 6, y + 3, 4, 8, "#1d3557");
    px(ctx, x + 10, y + 3, 4, 8, "#2f5d50");
    px(ctx, x + 2, y + 14, 4, 8, "#4a3f6b");
    px(ctx, x + 6, y + 14, 4, 8, "#8a5a32");
    px(ctx, x + 10, y + 14, 4, 8, "#3d5a80");
  }

  function lamp(ctx, x, y) {
    px(ctx, x + 5, y + 10, 3, 10, PAL.metal);
    px(ctx, x + 2, y + 18, 9, 3, PAL.wallDark);
    px(ctx, x + 3, y, 7, 10, PAL.lamp);
    px(ctx, x + 4, y + 2, 5, 4, "#fff6c8");
  }

  function tv(ctx, x, y) {
    px(ctx, x, y, 22, 14, PAL.wallDark);
    px(ctx, x + 2, y + 2, 18, 10, "#243a58");
    px(ctx, x + 4, y + 3, 6, 3, PAL.screen);
    px(ctx, x + 8, y + 14, 6, 3, PAL.metal);
  }

  function serverRack(ctx, x, y) {
    box(ctx, x, y, 18, 32, PAL.wallMid, PAL.wallDark);
    for (let i = 0; i < 5; i += 1) {
      px(ctx, x + 2, y + 3 + i * 5, 14, 4, PAL.ink);
      px(ctx, x + 4, y + 4 + i * 5, 2, 2, i % 2 ? PAL.plantLite : PAL.chairRed);
      px(ctx, x + 8, y + 4 + i * 5, 6, 2, PAL.screenDark);
    }
  }

  function cooler(ctx, x, y) {
    box(ctx, x, y + 10, 12, 18, PAL.foam, PAL.metal);
    px(ctx, x + 2, y, 8, 12, PAL.glass);
    px(ctx, x + 3, y + 2, 6, 4, "#b8dce8");
    px(ctx, x + 5, y + 20, 3, 3, PAL.screen);
  }

  function rug(ctx, x, y, w, h) {
    px(ctx, x, y, w, h, PAL.rug);
    px(ctx, x + 2, y + 2, w - 4, h - 4, "#7a5636");
  }

  function bin(ctx, x, y) {
    box(ctx, x, y, 8, 10, PAL.metal, PAL.wallDark);
  }

  function drawFloor(ctx) {
    for (let r = 0; r < ROWS; r += 1) {
      for (let c = 0; c < COLS; c += 1) {
        const x = c * T;
        const y = r * T;
        if (isWall(c, r)) {
          px(ctx, x, y, T, T, PAL.wall);
          px(ctx, x, y, T, 5, PAL.wallTop);
          px(ctx, x, y + 5, T, 1, PAL.wallMid);
          px(ctx, x, y + T - 3, T, 3, PAL.wallDark);
          if (isFloor(c, r + 1)) {
            px(ctx, x, y + T, T, 3, PAL.floorShadow);
          }
          if (r === 0 && c % 6 === 3) {
            px(ctx, x + 3, y + 4, 10, 8, PAL.glass);
            px(ctx, x + 4, y + 5, 3, 3, PAL.screenHi);
          }
        } else if (isFloor(c, r)) {
          const a = (c + r) % 2 === 0;
          px(ctx, x, y, T, T, a ? PAL.floorA : PAL.floorB);
        } else {
          px(ctx, x, y, T, T, PAL.wallDark);
        }
      }
    }
  }

  function drawFurniture(ctx) {
    conferenceTable(ctx, 40, 28);
    chair(ctx, 48, 14, true);
    chair(ctx, 88, 14, true);
    chair(ctx, 128, 14, true);
    chair(ctx, 48, 66, false);
    chair(ctx, 88, 66, false);
    chair(ctx, 128, 66, false);
    plant(ctx, 200, 18);
    plant(ctx, 16, 18);
    bin(ctx, 16, 70);

    box(ctx, 258, 18, 70, 12, PAL.woodMid, PAL.woodDark);
    px(ctx, 262, 20, 10, 8, PAL.metal);
    px(ctx, 276, 21, 8, 6, PAL.pot);
    sofa(ctx, 258, 40);
    coffeeTable(ctx, 268, 72);
    plant(ctx, 318, 18);

    rug(ctx, 376, 22, 96, 64);
    lDesk(ctx, 376, 20);
    chair(ctx, 392, 52, true);
    cabinet(ctx, 448, 18);
    lamp(ctx, 430, 18);
    tv(ctx, 456, 20);
    plant(ctx, 464, 70);

    workstation(ctx, 24, 128);
    chair(ctx, 36, 154, false);
    plant(ctx, 80, 114);
    workstation(ctx, 104, 128);
    chair(ctx, 116, 154, false);
    plant(ctx, 160, 114);
    workstation(ctx, 176, 128);
    chair(ctx, 188, 154, false);
    plant(ctx, 208, 168);

    poolTable(ctx, 258, 128);
    plant(ctx, 336, 114);
    cooler(ctx, 258, 176);

    serverRack(ctx, 372, 114);
    workstation(ctx, 400, 128);
    chair(ctx, 412, 154, false);
    lamp(ctx, 448, 114);
    plant(ctx, 464, 168);

    bookshelf(ctx, 18, 212);
    workstation(ctx, 36, 244);
    chair(ctx, 48, 270, false);
    plant(ctx, 96, 276);
    lamp(ctx, 18, 248);

    cooler(ctx, 160, 220);
    plant(ctx, 200, 276);
    bin(ctx, 148, 276);

    rug(ctx, 268, 220, 160, 72);
    lDesk(ctx, 288, 228);
    chair(ctx, 304, 260, true);
    cabinet(ctx, 256, 212);
    tv(ctx, 430, 212);
    plant(ctx, 464, 276);
    lamp(ctx, 400, 220);
  }

  function drawSprite(ctx, x, y, look, highlight, bob) {
    const gy = y + bob;
    if (highlight) {
      px(ctx, x - 3, gy - 3, 18, 26, "rgba(255,255,180,0.35)");
    }
    px(ctx, x + 4, gy, 8, 6, look.hair);
    px(ctx, x + 3, gy + 1, 10, 4, look.hair);
    px(ctx, x + 4, gy + 4, 8, 7, look.skin);
    px(ctx, x + 5, gy + 6, 2, 2, PAL.ink);
    px(ctx, x + 9, gy + 6, 2, 2, PAL.ink);
    px(ctx, x + 6, gy + 9, 4, 1, "#c47878");
    px(ctx, x + 3, gy + 11, 10, 8, look.body);
    px(ctx, x + 2, gy + 12, 2, 6, look.body);
    px(ctx, x + 12, gy + 12, 2, 6, look.body);
    px(ctx, x + 7, gy + 13, 2, 3, look.accent);
    px(ctx, x + 4, gy + 18, 3, 6, look.pants);
    px(ctx, x + 9, gy + 18, 3, 6, look.pants);
    px(ctx, x + 4, gy + 23, 3, 2, PAL.ink);
    px(ctx, x + 9, gy + 23, 3, 2, PAL.ink);
  }

  function nameplate(ctx, x, y, displayName) {
    const raw = String(displayName || "");
    const parts = raw.split(" · ");
    const person = parts[0] || raw;
    const dept = parts[1] ? "· " + parts[1] : "";
    ctx.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
    const pw = ctx.measureText(person).width / S;
    const dw = dept ? ctx.measureText(dept).width / S : 0;
    const bw = Math.max(pw, dw, 36) + 8;
    const bh = dept ? 18 : 11;
    const bx = x - bw / 2;
    px(ctx, bx, y, bw, bh, "rgba(12,22,20,0.82)");
    px(ctx, bx, y, bw, 1, PAL.ink);
    ctx.textAlign = "center";
    ctx.fillStyle = PAL.foam;
    ctx.fillText(person, x * S, (y + 8) * S);
    if (dept) ctx.fillText(dept, x * S, (y + 16) * S);
    ctx.textAlign = "left";
  }

  function drawBubble(ctx, x, y, text) {
    const label = String(text || "OK").slice(0, 14);
    const bw = Math.max(36, label.length * 5 + 8);
    const bx = x - 4;
    const by = y - 16;
    px(ctx, bx, by, bw, 12, PAL.foam);
    px(ctx, bx, by, bw, 1, PAL.ink);
    px(ctx, bx, by + 11, bw, 1, PAL.ink);
    px(ctx, bx, by, 1, 12, PAL.ink);
    px(ctx, bx + bw - 1, by, 1, 12, PAL.ink);
    px(ctx, bx + 6, by + 12, 3, 3, PAL.foam);
    ctx.fillStyle = PAL.ink;
    ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, monospace";
    ctx.fillText(label, (bx + 4) * S, (by + 9) * S);
  }

  function seatFor(emp) {
    const s = SEATS[emp.slug];
    if (s) return { x: s.c * T + 2, y: s.r * T - 8 };
    return { x: (emp.office_x || 96), y: (emp.office_y || 108) };
  }

  function draw(ctx, canvas, employees, selected, now) {
    const size = canvasSize();
    if (canvas.width !== size.w) canvas.width = size.w;
    if (canvas.height !== size.h) canvas.height = size.h;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = PAL.wallDark;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawFloor(ctx);
    drawFurniture(ctx);
    const t = now || 0;
    (employees || []).forEach((emp, i) => {
      const pos = seatFor(emp);
      const bob = Math.round(Math.sin(t / 380 + i) * 1);
      const look = LOOK[emp.slug] || LOOK["market-intelligence-research"];
      const on = selected && selected.slug === emp.slug;
      drawSprite(ctx, pos.x, pos.y, look, on, bob);
      drawBubble(ctx, pos.x + (i % 2 === 0 ? -6 : 4), pos.y + bob, emp.status_bubble || emp.status || "OK");
      nameplate(ctx, pos.x + 8, pos.y + 28, emp.display_name || emp.slug);
      emp._hit = {
        x: (pos.x - 16) * S,
        y: (pos.y - 18) * S,
        w: 40 * S,
        h: 52 * S,
      };
    });
  }

  global.VarmaOfficeFloor = {
    draw: draw,
    canvasSize: canvasSize,
    SEATS: SEATS,
    COLS: COLS,
    ROWS: ROWS,
    T: T,
    S: S,
    MAP: MAP,
  };
})(window);
