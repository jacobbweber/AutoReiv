# Radical UI Demo 04 — Agent Desktop

**Branch:** `demo/ui-radical-04-agent-desktop`
**Paradigm:** Agent desktop — OS-style multi-window environment. Dock launches studios as windows.

Fresh from stock qa @ b208233 — independent of radical 01-03.

## Mission

Replace stock Control Plane chrome (app rail + sidebar + surface pills) with an OS-style multi-window desktop. Dock icons launch Chat, Wiki, Projects, Agents/Forge, Factory, Routines, Observability, Settings, Prompts (and Sessions) as windows. Multiple windows can be open at once (e.g. Chat + Observability). HITL / deliverable modals are styled as dialog windows.

## Hard bans (this branch)

- No persistent left sidebar / app rail as primary nav
- No orb+pie, no void-palette-only, no infinite graph cosmos home
- No fighter HUD FABs as primary nav
- No single-column SaaS app shell
- Zero shared layout DNA with radical-01/02/03 as the home/nav model

## Interaction architecture

1. Desktop wallpaper/stage fills the viewport (`#desktopStage`).
2. Dock at the bottom (`#desktopDock`) launches studios; each opens a window in `#desktopWindowLayer`.
3. Windows: title bar, focus z-index, minimize (to dock indicator) / close, drag to move, SE resize. Chat title bar includes an agent switcher.
4. Agent interface: Chat is a window hosting the real `#view-chat` / `#messagesContainer` / `#chatForm` / streaming IDs (not a clone). HITL deliverable / tools modals get dialog-window chrome.
5. Stock `#appRail` / header / mobile surface switcher / persistent `#sidebar` are CSS-hidden; Sessions opens as its own window hosting `#sidebar`.
6. Mobile: dock becomes an icon row; every opened/focused window maximizes above the dock (no 50/50 stack). Other windows minimize.

## Files

| Path | Role |
|------|------|
| `src/web/templates/index.html` | Desktop CSS (wallpaper, dock, windows, hosted views, mobile) |
| `src/web/static/modules/ui/agent-desktop.js` | Dock, window manager, hosting sync, HITL dialog enhance |
| `src/web/static/app.js` | `initAgentDesktop` + `onTabChanged` hook |
| `docs/demos/ui-radical-04-agent-desktop.md` | This note |
| `tests/unit/frontend/agent_desktop.test.js` | Cascade / clamp / dock launcher unit tests |

## Preserve

Existing APIs and IDs remain (`messagesContainer`, `chatForm`, `promptInput`, agent selects, HITL modals, studio `view-*` sections, module inits). This is a re-skin / re-host of chrome, not a backend fork.

## How to run

```bash
# From repo root, on branch demo/ui-radical-04-agent-desktop
# Start gateway/web as usual for local AutoReiv, then open Control Plane URL.
# First paint: desktop wallpaper + bottom dock (no app rail / sidebar).
```
Typical local entry uses the usual AutoReiv web start.
Unit tests cover dock launchers, cascade offsets, and window clamp helpers.

## Limitations
- One window per studio tab; agent switching via Chat title-bar select; real chat IDs/streaming preserved.
- Studio content is CSS-positioned into window bodies from stock view nodes (not reparented).
- Workbench / journey / debug panels remain inside Chat window chrome. Workbench starts collapsed (desktop + mobile) behind the Workbench button; a red badge shows session artifact count only when > 0.
- In-stream approvals stay as chat cards; factory deliverable and tools modals get dialog-window chrome.
- App rail / mobile surface header / persistent sidebar are CSS-hidden; Sessions is dock-launched.
- Lucide icons depend on the pinned CDN build; missing glyphs fail soft.
- First paint is an empty desktop; launch studios from the dock.

## Keyboard shortcuts (refine)

- Ctrl+Alt+T tile
- Ctrl+Alt+C cascade
- Ctrl+Alt+Left/Right snap half
- Ctrl+Alt+M maximize/restore
- Ctrl+Alt+G grid overlay
- Alt while drag/resize disables snap

## Mobile dock (refine)

Full-width bottom bar; scroll chevrons; swipeable icon strip; safe-area insets. Every focused window maximizes above the dock; prior windows minimize (no 50/50 stack).

