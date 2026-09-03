/* 16-bit office floor. Visual look inspired by MIT pixel-agents
   (https://github.com/pixel-agents-hq/pixel-agents) and the framed office
   window of W17ant/Claude-Office (MIT). Original Varma renderer — no sitcom
   names, no copyrighted character likenesses.
   Staff are Board Addendum F names (person · department).
   Click never grants authority. Talk/voice stays disabled. LIVE stays blocked. */
(function (global) {
  const T = 16;
  const S = 2;
  const COLS = 32;
  const ROWS = 20;
  const WALL_H = 10;

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
    floorA: "#4a908f",
    floorB: "#3a7a79",
    floorShadow: "#2a5e5e",
    floorLite: "#6bb0ae",
    wall: "#c4b496",
    wallMid: "#b09c7e",
    wallTop: "#d8ccb4",
    wallDark: "#6a5a44",
    wallEdge: "#8a7860",
    trim: "#5a4a38",
    wood: "#8a5a32",
    woodTop: "#c4a06a",
    woodMid: "#a07040",
    woodDark: "#5c3a1c",
    woodGrain: "#b88850",
    felt: "#2f7a3c",
    feltDark: "#1f5a2c",
    plant: "#3d8c48",
    plantLite: "#6cbc58",
    plantDark: "#245c30",
    pot: "#8b4030",
    potLite: "#b06040",
    chairRed: "#c43b3b",
    chairRedDark: "#8a2424",
    chairOffice: "#5a6578",
    chairOfficeLite: "#7a8598",
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
    cubicle: "#3a4560",
    cubicleHi: "#5a6578",
    cubicleLo: "#242c40",
    cabinet: "#c43b3b",
    cabinetDark: "#8a2424",
    cabinetHi: "#e06060",
    door: "#6a4a28",
    doorHi: "#8a6a40",
  };

  const SEATS = {
    ceo: { c: 25, r: 3 },
    "market-intelligence-research": { c: 3, r: 9 },
    "quant-strategy": { c: 8, r: 9 },
    trader: { c: 13, r: 9 },
    technology: { c: 26, r: 9 },
    challenge: { c: 3, r: 16 },
    risk: { c: 22, r: 16 },
  };

  const PATHS = {
    ceo: [
      { c: 25, r: 3 },
      { c: 22, r: 4 },
      { c: 18, r: 6 },
      { c: 18, r: 8 },
      { c: 22, r: 4 },
      { c: 25, r: 3 },
    ],
    "market-intelligence-research": [
      { c: 3, r: 9 },
      { c: 5, r: 11 },
      { c: 7, r: 12 },
      { c: 11, r: 15 },
      { c: 7, r: 12 },
      { c: 3, r: 9 },
    ],
    "quant-strategy": [
      { c: 8, r: 9 },
      { c: 10, r: 11 },
      { c: 15, r: 12 },
      { c: 18, r: 8 },
      { c: 10, r: 11 },
      { c: 8, r: 9 },
    ],
    trader: [
      { c: 13, r: 9 },
      { c: 15, r: 12 },
      { c: 18, r: 15 },
      { c: 21, r: 9 },
      { c: 15, r: 12 },
      { c: 13, r: 9 },
    ],
    technology: [
      { c: 26, r: 9 },
      { c: 24, r: 11 },
      { c: 21, r: 9 },
      { c: 24, r: 8 },
      { c: 26, r: 9 },
    ],
    challenge: [
      { c: 3, r: 16 },
      { c: 7, r: 15 },
      { c: 11, r: 15 },
      { c: 7, r: 15 },
      { c: 3, r: 16 },
    ],
    risk: [
      { c: 22, r: 16 },
      { c: 18, r: 15 },
      { c: 21, r: 13 },
      { c: 24, r: 16 },
      { c: 22, r: 16 },
    ],
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

  function isWood(c, r) {
    return isFloor(c, r) && c >= 1 && c <= 14 && r >= 1 && r <= 5;
  }

  function box(ctx, x, y, w, h, top, side) {
    px(ctx, x, y, w, Math.max(1, h - 3), top);
    px(ctx, x, y + h - 3, w, 3, side);
    px(ctx, x + w - 1, y + 1, 1, h - 2, side);
  }

  function isoBox(ctx, x, y, w, depth, height, top, south, east) {
    px(ctx, x + 2, y + depth - height, w, height, top);
    px(ctx, x, y + depth, w + 2, 3, south);
    px(ctx, x + w + 1, y + depth - height + 1, 2, height + 2, east);
    px(ctx, x + 3, y + depth - height + 1, w - 2, 1, "rgba(255,255,255,0.12)");
  }

  function plant(ctx, x, y) {
    px(ctx, x + 5, y + 14, 8, 3, "rgba(0,0,0,0.25)");
    px(ctx, x + 4, y + 11, 8, 5, PAL.pot);
    px(ctx, x + 3, y + 11, 10, 2, PAL.potLite);
    px(ctx, x + 6, y + 2, 5, 10, PAL.plantDark);
    px(ctx, x + 3, y + 4, 6, 6, PAL.plant);
    px(ctx, x + 8, y + 3, 6, 7, PAL.plantLite);
    px(ctx, x + 5, y + 1, 3, 3, PAL.plantLite);
  }

  function chair(ctx, x, y, red) {
    const back = red ? PAL.chairRed : PAL.chairOffice;
    const dark = red ? PAL.chairRedDark : PAL.cubicleLo;
    const lite = red ? "#e06060" : PAL.chairOfficeLite;
    px(ctx, x + 3, y + 14, 10, 3, "rgba(0,0,0,0.22)");
    px(ctx, x + 2, y, 10, 8, back);
    px(ctx, x + 3, y + 1, 8, 3, lite);
    px(ctx, x + 3, y + 1, 8, 4, dark);
    box(ctx, x, y + 7, 14, 7, back, dark);
    px(ctx, x + 1, y + 13, 3, 3, PAL.metal);
    px(ctx, x + 10, y + 13, 3, 3, PAL.metal);
  }

  function monitor(ctx, x, y) {
    px(ctx, x, y, 16, 12, PAL.wallDark);
    px(ctx, x + 1, y + 1, 14, 10, PAL.screenDark);
    px(ctx, x + 2, y + 2, 12, 8, PAL.screen);
    px(ctx, x + 3, y + 3, 4, 2, PAL.screenHi);
    px(ctx, x + 7, y + 12, 3, 3, PAL.metal);
    px(ctx, x + 4, y + 14, 9, 2, PAL.wallDark);
  }

  function workstation(ctx, x, y) {
    isoBox(ctx, x, y + 8, 44, 12, 10, PAL.woodTop, PAL.woodDark, PAL.wood);
    px(ctx, x + 4, y + 11, 40, 2, PAL.woodGrain);
    monitor(ctx, x + 14, y);
    px(ctx, x + 8, y + 13, 16, 4, PAL.metal);
    px(ctx, x + 10, y + 14, 2, 2, PAL.ink);
    px(ctx, x + 13, y + 14, 2, 2, PAL.ink);
    px(ctx, x + 16, y + 14, 2, 2, PAL.ink);
    px(ctx, x + 28, y + 12, 8, 6, PAL.paper);
    px(ctx, x + 30, y + 13, 5, 1, PAL.ink);
    px(ctx, x + 34, y + 12, 4, 4, PAL.potLite);
  }

  function lDesk(ctx, x, y) {
    isoBox(ctx, x, y + 16, 48, 14, 12, PAL.woodTop, PAL.woodDark, PAL.wood);
    isoBox(ctx, x + 36, y, 16, 30, 12, PAL.woodMid, PAL.woodDark, PAL.wood);
    px(ctx, x + 2, y + 17, 32, 2, PAL.wood);
    monitor(ctx, x + 10, y + 6);
    px(ctx, x + 6, y + 20, 14, 4, PAL.metal);
    px(ctx, x + 38, y + 4, 10, 8, PAL.paper);
  }

  function conferenceTable(ctx, x, y) {
    isoBox(ctx, x, y, 112, 36, 8, PAL.woodTop, PAL.woodDark, PAL.wood);
    px(ctx, x + 6, y + 6, 104, 2, PAL.woodGrain);
    px(ctx, x + 8, y + 10, 18, 12, PAL.paper);
    px(ctx, x + 10, y + 12, 12, 1, PAL.ink);
    px(ctx, x + 10, y + 15, 10, 1, PAL.ink);
    px(ctx, x + 40, y + 8, 22, 14, PAL.wallDark);
    px(ctx, x + 42, y + 10, 18, 10, PAL.screen);
    px(ctx, x + 44, y + 11, 6, 3, PAL.screenHi);
    px(ctx, x + 72, y + 12, 16, 10, PAL.paper);
    px(ctx, x + 88, y + 10, 12, 8, PAL.paper);
    px(ctx, x + 8, y + 34, 6, 6, PAL.woodDark);
    px(ctx, x + 100, y + 34, 6, 6, PAL.woodDark);
  }

  function poolTable(ctx, x, y) {
    isoBox(ctx, x, y, 72, 40, 8, PAL.wood, PAL.woodDark, PAL.woodMid);
    px(ctx, x + 8, y + 8, 60, 28, PAL.felt);
    px(ctx, x + 8, y + 8, 60, 3, PAL.feltDark);
    px(ctx, x + 8, y + 8, 5, 5, PAL.ink);
    px(ctx, x + 63, y + 8, 5, 5, PAL.ink);
    px(ctx, x + 8, y + 31, 5, 5, PAL.ink);
    px(ctx, x + 63, y + 31, 5, 5, PAL.ink);
    px(ctx, x + 35, y + 8, 5, 5, PAL.ink);
    px(ctx, x + 20, y + 16, 3, 3, "#f2e6c8");
    px(ctx, x + 30, y + 20, 3, 3, "#c43b3b");
    px(ctx, x + 38, y + 14, 3, 3, "#3d5a80");
    px(ctx, x + 46, y + 22, 3, 3, "#f0d878");
    px(ctx, x + 26, y + 24, 3, 3, "#4a3f6b");
  }

  function sofa(ctx, x, y) {
    isoBox(ctx, x, y + 8, 48, 16, 10, PAL.sofa, PAL.sofaDark, PAL.chairRedDark);
    px(ctx, x, y, 10, 12, PAL.sofaDark);
    px(ctx, x + 38, y, 10, 12, PAL.sofaDark);
    px(ctx, x + 12, y + 10, 12, 6, PAL.chairRed);
    px(ctx, x + 26, y + 10, 12, 6, PAL.chairRed);
  }

  function coffeeTable(ctx, x, y) {
    isoBox(ctx, x, y, 28, 14, 6, PAL.woodTop, PAL.woodDark, PAL.wood);
    px(ctx, x + 6, y + 4, 8, 6, PAL.paper);
    px(ctx, x + 18, y + 3, 6, 6, PAL.pot);
  }

  function cabinet(ctx, x, y) {
    isoBox(ctx, x, y, 16, 24, 18, PAL.metal, PAL.wallDark, PAL.cubicle);
    px(ctx, x + 2, y + 6, 12, 6, PAL.wallMid);
    px(ctx, x + 2, y + 14, 12, 6, PAL.wallMid);
    px(ctx, x + 12, y + 8, 2, 2, PAL.lamp);
    px(ctx, x + 12, y + 16, 2, 2, PAL.lamp);
  }

  function redCabinet(ctx, x, y) {
    isoBox(ctx, x, y, 28, 36, 28, PAL.cabinetHi, PAL.cabinetDark, PAL.cabinet);
    px(ctx, x + 4, y + 10, 20, 8, PAL.cabinetDark);
    px(ctx, x + 4, y + 20, 20, 8, PAL.cabinetDark);
    px(ctx, x + 22, y + 13, 3, 3, PAL.lamp);
    px(ctx, x + 22, y + 23, 3, 3, PAL.lamp);
    px(ctx, x + 10, y + 4, 8, 3, PAL.metal);
  }

  function bookshelf(ctx, x, y) {
    isoBox(ctx, x, y, 16, 28, 22, PAL.wood, PAL.woodDark, PAL.woodMid);
    px(ctx, x + 2, y + 6, 4, 8, "#8b1e1e");
    px(ctx, x + 6, y + 6, 4, 8, "#1d3557");
    px(ctx, x + 10, y + 6, 4, 8, "#2f5d50");
    px(ctx, x + 2, y + 16, 4, 8, "#4a3f6b");
    px(ctx, x + 6, y + 16, 4, 8, "#8a5a32");
    px(ctx, x + 10, y + 16, 4, 8, "#3d5a80");
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
    isoBox(ctx, x, y, 18, 32, 26, PAL.cubicleHi, PAL.cubicleLo, PAL.cubicle);
    for (let i = 0; i < 5; i += 1) {
      px(ctx, x + 2, y + 6 + i * 5, 14, 4, PAL.ink);
      px(ctx, x + 4, y + 7 + i * 5, 2, 2, i % 2 ? PAL.plantLite : PAL.chairRed);
      px(ctx, x + 8, y + 7 + i * 5, 6, 2, PAL.screenDark);
    }
  }

  function cooler(ctx, x, y) {
    isoBox(ctx, x, y + 10, 12, 18, 14, PAL.foam, PAL.metal, PAL.cubicleHi);
    px(ctx, x + 2, y, 8, 12, PAL.glass);
    px(ctx, x + 3, y + 2, 6, 4, "#b8dce8");
    px(ctx, x + 3, y + 7, 6, 2, "#7ec8e3");
    px(ctx, x + 5, y + 20, 3, 3, PAL.screen);
  }

  function rug(ctx, x, y, w, h) {
    px(ctx, x, y, w, h, PAL.rug);
    px(ctx, x + 2, y + 2, w - 4, h - 4, "#7a5636");
  }

  function bin(ctx, x, y) {
    box(ctx, x, y, 8, 10, PAL.metal, PAL.wallDark);
  }

  function cubicleWall(ctx, x, y, w, h) {
    px(ctx, x, y, w, h, PAL.cubicle);
    px(ctx, x, y, w, 3, PAL.cubicleHi);
    px(ctx, x, y + h - 4, w, 4, PAL.cubicleLo);
    px(ctx, x + w - 2, y + 1, 2, h - 2, PAL.cubicleLo);
    px(ctx, x + 1, y + 4, w - 4, 1, "rgba(255,255,255,0.08)");
  }

  function cubicle(ctx, x, y) {
    cubicleWall(ctx, x, y, 52, 8);
    cubicleWall(ctx, x, y, 6, 40);
    cubicleWall(ctx, x + 46, y, 6, 40);
    workstation(ctx, x + 8, y + 10);
    chair(ctx, x + 18, y + 28, false);
  }

  function doorGap(ctx, x, y) {
    px(ctx, x, y, 16, 16, PAL.door);
    px(ctx, x + 2, y + 2, 12, 12, PAL.doorHi);
    px(ctx, x + 10, y + 7, 2, 2, PAL.lamp);
  }

  function drawFloor(ctx) {
    for (let r = 0; r < ROWS; r += 1) {
      for (let c = 0; c < COLS; c += 1) {
        const x = c * T;
        const y = r * T;
        if (isWall(c, r)) {
          px(ctx, x, y, T, T, PAL.wallMid);
          px(ctx, x, y, T, 5, PAL.wallTop);
          px(ctx, x, y + 5, T, 1, PAL.wall);
          px(ctx, x, y + T - 3, T, 3, PAL.wallDark);
          if (isFloor(c, r + 1)) {
            px(ctx, x, y + T - WALL_H, T, WALL_H, PAL.wall);
            px(ctx, x, y + T - WALL_H, T, 2, PAL.wallTop);
            px(ctx, x, y + T - 3, T, 3, PAL.trim);
            px(ctx, x, y + T, T, 4, PAL.floorShadow);
            if (c % 5 === 2 && r > 0) {
              px(ctx, x + 3, y + T - WALL_H + 2, 10, 6, PAL.glass);
              px(ctx, x + 4, y + T - WALL_H + 3, 3, 2, PAL.screenHi);
            }
          }
          if (isFloor(c + 1, r)) {
            px(ctx, x + T - 2, y, 2, T, PAL.wallDark);
          }
        } else if (isWood(c, r)) {
          const a = (c + r) % 2 === 0;
          px(ctx, x, y, T, T, a ? PAL.woodTop : PAL.woodMid);
          px(ctx, x, y + T - 2, T, 2, PAL.woodDark);
          if (c % 2 === 0) px(ctx, x + 7, y, 1, T, PAL.woodGrain);
          if (!isWood(c, r + 1)) {
            px(ctx, x, y + T, T, 3, PAL.woodDark);
          }
        } else if (isFloor(c, r)) {
          const a = (c + r) % 2 === 0;
          px(ctx, x, y, T, T, a ? PAL.floorA : PAL.floorB);
          if ((c + r * 3) % 11 === 0) {
            px(ctx, x + 2, y + 2, T - 4, T - 4, PAL.floorLite);
            px(ctx, x + 2, y + 2, T - 4, T - 4, "rgba(255,255,255,0.06)");
          }
        } else {
          px(ctx, x, y, T, T, PAL.wallDark);
        }
      }
    }
    px(ctx, 48, 28, 80, 48, "rgba(255,255,220,0.07)");
    px(ctx, 176, 128, 64, 40, "rgba(255,255,220,0.05)");
    px(ctx, 360, 40, 72, 48, "rgba(255,255,220,0.06)");
  }

  function drawFurniture(ctx) {
    conferenceTable(ctx, 40, 28);
    chair(ctx, 48, 14, false);
    chair(ctx, 88, 14, false);
    chair(ctx, 128, 14, false);
    chair(ctx, 48, 66, false);
    chair(ctx, 88, 66, false);
    chair(ctx, 128, 66, false);
    plant(ctx, 200, 18);
    plant(ctx, 16, 18);
    bin(ctx, 16, 70);
    doorGap(ctx, 112, 96);

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
    redCabinet(ctx, 456, 36);
    plant(ctx, 360, 18);

    cubicle(ctx, 16, 116);
    cubicle(ctx, 96, 116);
    cubicle(ctx, 176, 116);
    plant(ctx, 80, 114);
    plant(ctx, 160, 114);
    plant(ctx, 232, 168);

    poolTable(ctx, 258, 128);
    plant(ctx, 336, 114);
    cooler(ctx, 338, 176);
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

  function drawSprite(ctx, x, y, look, highlight, bob, facing, walkFrame) {
    const gy = y + bob;
    const flip = facing === "left";
    function d(pxX, pxY, w, h, c) {
      const local = pxX - x;
      const dx = flip ? x + 16 - local - w : pxX;
      px(ctx, dx, pxY, w, h, c);
    }
    px(ctx, x + 2, gy + 22, 12, 4, "rgba(0,0,0,0.28)");
    if (highlight) {
      px(ctx, x - 3, gy - 3, 18, 26, "rgba(255,255,180,0.35)");
    }
    d(x + 4, gy, 8, 6, look.hair);
    d(x + 3, gy + 1, 10, 4, look.hair);
    d(x + 4, gy + 4, 8, 7, look.skin);
    d(x + 5, gy + 6, 2, 2, PAL.ink);
    d(x + 9, gy + 6, 2, 2, PAL.ink);
    d(x + 6, gy + 9, 4, 1, "#c47878");
    d(x + 3, gy + 11, 10, 8, look.body);
    const armSwing = walkFrame ? 1 : 0;
    d(x + 2, gy + 12 + armSwing, 2, 6, look.body);
    d(x + 12, gy + 12 - armSwing, 2, 6, look.body);
    d(x + 7, gy + 13, 2, 3, look.accent);
    const leg = walkFrame ? 2 : 0;
    d(x + 4, gy + 18, 3, 6 - (walkFrame ? 1 : 0), look.pants);
    d(x + 9, gy + 18 + (walkFrame ? 1 : 0), 3, 6 - (walkFrame ? 1 : 0), look.pants);
    d(x + 4 - leg, gy + 23, 3, 2, PAL.ink);
    d(x + 9 + leg, gy + 23, 3, 2, PAL.ink);
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
    const label = String(text || "...").slice(0, 14);
    const bw = Math.max(28, label.length * 5 + 8);
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

  function clampFloor(c, r) {
    const cc = Math.max(1, Math.min(COLS - 2, Math.round(c)));
    const rr = Math.max(1, Math.min(ROWS - 2, Math.round(r)));
    if (isFloor(cc, rr)) return { c: cc, r: rr };
    if (isFloor(cc, rr + 1)) return { c: cc, r: rr + 1 };
    if (isFloor(cc + 1, rr)) return { c: cc + 1, r: rr };
    return { c: cc, r: rr };
  }

  function walkPos(emp, now, index) {
    const home = SEATS[emp.slug] || { c: 8, r: 8 };
    const path = PATHS[emp.slug] || [home];
    const n = path.length;
    const cycle = 2800;
    const t = (now + index * 1100) % (cycle * n);
    const seg = Math.floor(t / cycle);
    const u = (t % cycle) / cycle;
    const a = path[seg];
    const b = path[(seg + 1) % n];
    let c;
    let r;
    let walking = false;
    if (u < 0.28) {
      c = a.c;
      r = a.r;
    } else if (u > 0.86) {
      c = b.c;
      r = b.r;
    } else {
      const p = (u - 0.28) / 0.58;
      const ease = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
      c = a.c + (b.c - a.c) * ease;
      r = a.r + (b.r - a.r) * ease;
      walking = Math.abs(b.c - a.c) + Math.abs(b.r - a.r) > 0.2;
    }
    const snapped = walking ? { c: c, r: r } : clampFloor(c, r);
    const dx = b.c - a.c;
    let facing = "down";
    if (walking && Math.abs(dx) >= Math.abs(b.r - a.r)) {
      facing = dx < 0 ? "left" : "right";
    } else if (walking && b.r < a.r) {
      facing = "up";
    }
    return {
      x: snapped.c * T + 2,
      y: snapped.r * T - 8,
      facing: facing,
      walking: walking,
    };
  }

  function seatFor(emp) {
    const s = SEATS[emp.slug];
    if (s) return { x: s.c * T + 2, y: s.r * T - 8 };
    return { x: emp.office_x || 96, y: emp.office_y || 108 };
  }

  function drawPortrait(ctx, canvas, slug) {
    const look = LOOK[slug] || LOOK["market-intelligence-research"];
    if (canvas.width !== 32) canvas.width = 32;
    if (canvas.height !== 32) canvas.height = 32;
    const scale = 2;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#0d1320";
    ctx.fillRect(0, 0, 32, 32);
    function p(x, y, w, h, c) {
      ctx.fillStyle = c;
      ctx.fillRect(Math.round(x * scale), Math.round(y * scale), Math.round(w * scale), Math.round(h * scale));
    }
    p(4, 1, 8, 6, look.hair);
    p(3, 2, 10, 4, look.hair);
    p(4, 5, 8, 7, look.skin);
    p(5, 7, 2, 2, PAL.ink);
    p(9, 7, 2, 2, PAL.ink);
    p(6, 10, 4, 1, "#c47878");
    p(3, 12, 10, 4, look.body);
    p(7, 13, 2, 2, look.accent);
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
    const drawn = (employees || []).map((emp, i) => {
      const pos = walkPos(emp, t, i);
      return { emp: emp, i: i, pos: pos };
    });
    drawn.sort((a, b) => a.pos.y - b.pos.y);
    drawn.forEach((item) => {
      const emp = item.emp;
      const pos = item.pos;
      const i = item.i;
      const bob = pos.walking ? 0 : Math.round(Math.sin(t / 380 + i) * 1);
      const look = LOOK[emp.slug] || LOOK["market-intelligence-research"];
      const on = selected && selected.slug === emp.slug;
      const walkFrame = pos.walking && Math.floor(t / 180) % 2 === 0;
      drawSprite(ctx, pos.x, pos.y, look, on, bob, pos.facing, walkFrame);
      const talking = Math.floor((t / 1600 + i) % 5) === 0 || pos.walking;
      if (talking) {
        drawBubble(ctx, pos.x + (i % 2 === 0 ? -6 : 4), pos.y + bob, "...");
      } else {
        drawBubble(ctx, pos.x + (i % 2 === 0 ? -6 : 4), pos.y + bob, emp.status_bubble || emp.status || "OK");
      }
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
    drawPortrait: drawPortrait,
    canvasSize: canvasSize,
    SEATS: SEATS,
    PATHS: PATHS,
    COLS: COLS,
    ROWS: ROWS,
    T: T,
    S: S,
    MAP: MAP,
  };
})(window);
