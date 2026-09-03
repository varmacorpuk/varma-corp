# Vendored office renderer

The Varma control-room floor is the **actual W17ant/Claude-Office camera**:
their isometric room PNG, furniture sprites, character sprites, and percentage
layout. Varma did not draw these assets. This is not a fillRect lookalike
and not a Parcha-ai/ai-office tileset blit.

## W17ant/Claude-Office (MIT)

Source: https://github.com/W17ant/Claude-Office
Commit: `291e7608aa3beb614aca80fe86077ef8c0cbc21d`

Copyright (c) 2026 W17ANT. License: `claude-office/LICENSE` (MIT).

Vendored:

- `rooms/office-day.png` — generic main-office background (not Dunder Mifflin)
- `sprites/furniture`, `appliances`, `decoration`, `culture`, `effects`
- `sprites/characters` — generic directional sprites only (`Me-1`, `Claude-1`,
  `dev-*`, `employee-*`, `Frontend-dev-1`, `security-audit-1`, `explore-1`)
- `src/rooms.ts` furniture + agentSpots as `layout.json`
- `src/assets.ts` display sizes
- `src/styles/rooms.css` and character/window rules from `office.css`

Not vendored:

- `public/sprites/office/` (TV-cast sprites)
- `office-day-dm.png` / `office-night-dm.png` (Dunder Mifflin room art)
- Sitcom names or likenesses

Varma staff labels (Board Addendum F) are ours. Click a person opens chat/work.
Click never grants trading authority. No Approve LIVE.
