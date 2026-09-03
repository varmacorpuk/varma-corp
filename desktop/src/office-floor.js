/* Vendored office floor: Parcha-ai/ai-office rpg-tileset.png (the photographed
   room) + pixel-agents Metro City character sheets. Do not fillRect a lookalike.
   Staff are Board Addendum F names (person · department). No sitcom names.
   Click never grants authority. Talk/voice stays disabled. LIVE stays blocked. */
(function (global) {
  const T = 32;
  const S = 1;
  const COLS = 25;
  const ROWS = 25;
  const TILESET_URL = "vendor/ai-office/rpg-tileset.png";
  const CHAR_DIR = "vendor/pixel-agents/characters/";
  const FW = 16;
  const FH = 32;
  const CHAR_SCALE = 2;
  const FRAMES = 7;

  /* Collision layer from Parcha-ai/ai-office convex/maps/firstmap.ts objmap.
     -1 is walkable. The painted office is rpg-tileset.png (identity bgtiles). */
  const OBJ = [
    [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24],
    [25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49],
    [50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74],
    [75,76,77,-1,-1,80,-1,-1,83,84,85,-1,87,88,89,-1,-1,-1,93,94,95,-1,97,98,99],
    [100,101,102,-1,-1,105,-1,-1,108,109,110,-1,112,113,-1,-1,-1,-1,-1,-1,-1,-1,122,123,124],
    [125,126,127,-1,-1,130,-1,-1,-1,-1,-1,-1,137,138,139,-1,141,142,143,144,145,146,147,148,149],
    [150,151,-1,-1,-1,155,-1,-1,-1,-1,-1,-1,162,163,164,-1,166,167,168,169,170,171,172,173,174],
    [175,176,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,199],
    [200,201,202,-1,-1,-1,-1,-1,208,209,-1,-1,-1,-1,-1,-1,216,217,218,219,-1,-1,-1,-1,224],
    [225,226,227,228,229,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,241,242,243,244,-1,-1,-1,248,249],
    [250,251,252,253,254,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,266,267,268,269,-1,-1,-1,273,274],
    [275,276,277,278,279,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,298,299],
    [300,301,302,303,304,-1,-1,-1,-1,-1,-1,-1,-1,313,314,-1,316,317,318,319,-1,-1,-1,323,324],
    [325,326,327,328,-1,-1,-1,-1,-1,-1,-1,-1,-1,338,339,-1,341,342,-1,-1,-1,-1,-1,348,349],
    [350,351,352,353,-1,-1,-1,357,358,359,360,-1,-1,363,364,-1,366,367,368,369,370,371,372,373,374],
    [375,376,377,378,-1,-1,-1,382,383,384,385,-1,-1,388,389,-1,391,392,393,394,395,396,397,398,399],
    [400,401,402,403,-1,-1,-1,-1,-1,-1,-1,-1,-1,413,-1,-1,-1,-1,-1,-1,-1,-1,-1,423,424],
    [425,426,-1,-1,-1,-1,-1,-1,-1,434,435,436,437,438,-1,-1,441,442,443,444,445,-1,-1,448,449],
    [450,451,-1,-1,454,455,-1,-1,-1,459,460,461,462,463,-1,-1,466,467,468,469,470,-1,-1,473,474],
    [475,476,-1,-1,479,480,-1,-1,-1,484,485,486,487,488,-1,-1,491,492,493,494,495,-1,-1,498,499],
    [500,501,-1,-1,504,505,-1,-1,-1,509,510,511,512,513,-1,-1,516,517,518,519,520,-1,-1,523,524],
    [525,526,-1,-1,529,530,-1,-1,-1,534,535,536,537,538,-1,-1,541,542,543,544,545,-1,-1,548,549],
    [550,551,-1,-1,-1,-1,-1,-1,-1,559,560,561,562,563,-1,-1,-1,-1,-1,-1,-1,-1,-1,573,574],
    [575,576,577,578,579,580,581,582,583,584,585,586,587,588,589,590,591,592,593,594,595,596,597,598,599],
    [600,601,602,603,604,605,606,607,608,609,610,611,612,613,614,615,616,617,618,619,620,621,622,623,624],
  ];

  const MAP = OBJ.map((row) => row.map((v) => (v === -1 ? "." : "#")).join(""));

  const SEATS = {
    ceo: { c: 10, r: 10 },
    "market-intelligence-research": { c: 15, r: 10 },
    challenge: { c: 12, r: 12 },
    risk: { c: 6, r: 6 },
    trader: { c: 8, r: 6 },
    "quant-strategy": { c: 15, r: 15 },
    technology: { c: 20, r: 15 },
  };

  const PATHS = {
    ceo: [
      { c: 10, r: 10 },
      { c: 9, r: 10 },
      { c: 8, r: 9 },
      { c: 10, r: 8 },
      { c: 11, r: 10 },
      { c: 10, r: 10 },
    ],
    "market-intelligence-research": [
      { c: 15, r: 10 },
      { c: 14, r: 10 },
      { c: 13, r: 9 },
      { c: 15, r: 8 },
      { c: 15, r: 10 },
    ],
    challenge: [
      { c: 12, r: 12 },
      { c: 11, r: 11 },
      { c: 10, r: 12 },
      { c: 11, r: 13 },
      { c: 12, r: 12 },
    ],
    risk: [
      { c: 6, r: 6 },
      { c: 7, r: 6 },
      { c: 8, r: 7 },
      { c: 6, r: 8 },
      { c: 6, r: 6 },
    ],
    trader: [
      { c: 8, r: 6 },
      { c: 9, r: 6 },
      { c: 10, r: 7 },
      { c: 8, r: 8 },
      { c: 8, r: 6 },
    ],
    "quant-strategy": [
      { c: 15, r: 15 },
      { c: 14, r: 13 },
      { c: 13, r: 12 },
      { c: 15, r: 13 },
      { c: 15, r: 15 },
    ],
    technology: [
      { c: 20, r: 15 },
      { c: 18, r: 13 },
      { c: 16, r: 12 },
      { c: 18, r: 15 },
      { c: 20, r: 15 },
    ],
  };

  const CHAR = {
    ceo: { sheet: 0, hue: 0 },
    "market-intelligence-research": { sheet: 1, hue: 0 },
    challenge: { sheet: 2, hue: 0 },
    risk: { sheet: 3, hue: 0 },
    trader: { sheet: 2, hue: 48 },
    "quant-strategy": { sheet: 4, hue: 0 },
    technology: { sheet: 5, hue: 0 },
  };

  const sheets = [];
  const tinted = {};
  let tileset = null;
  let tilesetReady = false;
  let charsReady = false;
  let loadStarted = false;

  function canvasSize() {
    return { w: COLS * T * S, h: ROWS * T * S };
  }

  function isFloor(c, r) {
    if (r < 0 || r >= ROWS || c < 0 || c >= COLS) return false;
    return OBJ[r][c] === -1;
  }

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(src));
      img.src = src;
    });
  }

  function tintSheet(img, hue) {
    if (!hue) return img;
    const key = img.src + ":" + hue;
    if (tinted[key]) return tinted[key];
    const c = document.createElement("canvas");
    c.width = img.width;
    c.height = img.height;
    const x = c.getContext("2d");
    x.imageSmoothingEnabled = false;
    x.filter = "hue-rotate(" + hue + "deg)";
    x.drawImage(img, 0, 0);
    tinted[key] = c;
    return c;
  }

  function ensureLoaded() {
    if (loadStarted) return;
    loadStarted = true;
    loadImage(TILESET_URL)
      .then((img) => {
        tileset = img;
        tilesetReady = true;
      })
      .catch(() => {
        tilesetReady = false;
      });
    Promise.all([0, 1, 2, 3, 4, 5].map((n) => loadImage(CHAR_DIR + "char_" + n + ".png")))
      .then((imgs) => {
        imgs.forEach((img, i) => {
          sheets[i] = img;
        });
        charsReady = true;
      })
      .catch(() => {
        charsReady = false;
      });
  }

  function drawFloor(ctx) {
    if (tilesetReady && tileset) {
      ctx.drawImage(tileset, 0, 0, COLS * T, ROWS * T);
      return;
    }
    ctx.fillStyle = "#3aa8a8";
    ctx.fillRect(0, 0, COLS * T, ROWS * T);
  }

  function walkPos(emp, now, index) {
    const home = SEATS[emp.slug] || { c: 10, r: 10 };
    const path = PATHS[emp.slug] || [home];
    const period = 9000 + index * 700;
    const t = ((now || 0) + index * 1200) % period;
    const segTime = period / path.length;
    const seg = Math.min(path.length - 1, Math.floor(t / segTime));
    const next = path[(seg + 1) % path.length];
    const cur = path[seg];
    const u = (t % segTime) / segTime;
    const rest = u < 0.28 || u > 0.92;
    const a = rest ? cur : cur;
    const b = rest ? cur : next;
    const p = rest ? 0 : (u - 0.28) / 0.64;
    const c = a.c + (b.c - a.c) * p;
    const r = a.r + (b.r - a.r) * p;
    let facing = "down";
    if (!rest) {
      const dc = b.c - a.c;
      const dr = b.r - a.r;
      if (Math.abs(dc) > Math.abs(dr)) facing = dc < 0 ? "left" : "right";
      else if (dr < 0) facing = "up";
      else facing = "down";
    }
    return {
      x: c * T + T / 2,
      y: r * T + T / 2,
      walking: !rest,
      facing: facing,
    };
  }

  function sheetFor(slug) {
    const spec = CHAR[slug] || CHAR["market-intelligence-research"];
    const img = sheets[spec.sheet];
    if (!img) return null;
    return tintSheet(img, spec.hue);
  }

  function drawSprite(ctx, x, y, slug, highlight, now, facing, walking) {
    const sheet = sheetFor(slug);
    const w = FW * CHAR_SCALE;
    const h = FH * CHAR_SCALE;
    const dx = Math.round(x - w / 2);
    const dy = Math.round(y - h + 6);
    if (highlight) {
      ctx.fillStyle = "rgba(255,255,180,0.28)";
      ctx.fillRect(dx - 3, dy - 3, w + 6, h + 6);
    }
    if (!sheet) {
      ctx.fillStyle = "#1d3557";
      ctx.fillRect(dx + 8, dy + 16, 16, 20);
      return;
    }
    const dirRow = facing === "up" ? 1 : facing === "down" ? 0 : 2;
    const flip = facing === "left";
    const frame = walking ? Math.floor((now || 0) / 150) % 3 : 1;
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    if (flip) {
      ctx.translate(dx + w, dy);
      ctx.scale(-1, 1);
      ctx.drawImage(sheet, frame * FW, dirRow * FH, FW, FH, 0, 0, w, h);
    } else {
      ctx.drawImage(sheet, frame * FW, dirRow * FH, FW, FH, dx, dy, w, h);
    }
    ctx.restore();
  }

  function drawBubble(ctx, x, y, text) {
    const label = String(text || "...").slice(0, 14);
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, monospace";
    const tw = Math.max(18, ctx.measureText(label).width);
    const bw = tw + 10;
    const bh = 14;
    const bx = Math.round(x - bw / 2);
    const by = Math.round(y - 42);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(bx, by, bw, bh);
    ctx.fillStyle = "#181425";
    ctx.fillRect(bx, by, bw, 1);
    ctx.fillRect(bx, by + bh - 1, bw, 1);
    ctx.fillRect(bx, by, 1, bh);
    ctx.fillRect(bx + bw - 1, by, 1, bh);
    ctx.fillRect(bx + Math.floor(bw / 2) - 2, by + bh, 3, 3);
    ctx.fillStyle = "#181425";
    ctx.fillText(label, bx + 5, by + 10);
    ctx.restore();
  }

  function drawPortrait(ctx, canvas, slug) {
    if (canvas.width !== 32) canvas.width = 32;
    if (canvas.height !== 32) canvas.height = 32;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#181425";
    ctx.fillRect(0, 0, 32, 32);
    const sheet = sheetFor(slug);
    if (!sheet) return;
    ctx.drawImage(sheet, 1 * FW, 0, FW, 20, 8, 4, 16, 24);
  }

  function draw(ctx, canvas, employees, selected, now) {
    ensureLoaded();
    const size = canvasSize();
    if (canvas.width !== size.w) canvas.width = size.w;
    if (canvas.height !== size.h) canvas.height = size.h;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#181425";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawFloor(ctx);
    const t = now || 0;
    const drawn = (employees || []).map((emp, i) => ({
      emp: emp,
      i: i,
      pos: walkPos(emp, t, i),
    }));
    drawn.sort((a, b) => a.pos.y - b.pos.y);
    drawn.forEach((item) => {
      const emp = item.emp;
      const pos = item.pos;
      const i = item.i;
      const on = selected && selected.slug === emp.slug;
      drawSprite(ctx, pos.x, pos.y, emp.slug, on, t, pos.facing, pos.walking);
      if (i % 3 !== 2) drawBubble(ctx, pos.x, pos.y, "...");
      emp._hit = {
        x: pos.x - 20,
        y: pos.y - 40,
        w: 40,
        h: 48,
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
    TILESET_URL: TILESET_URL,
    isFloor: isFloor,
  };
})(window);
