# Technical Architecture & Design: Agent Forge Studio Mobile Responsive Toolbar and UI Polish

## 1. Context & Layout Architecture

### 1.1 Toolbar Mobile Layout ($\le 480\text{px}$)
```text
+-------------------------------------------------------------+
| [🛡️] Agent Forge Studio                                     |
|      Inspect components, configure skill scopes...          |
+-------------------------------------------------------------+
| [ Assistant (Built-in)                                    v] |
| [+ New Agent]    [💾 Save Profile]    [🗑️ Delete]           |
+-------------------------------------------------------------+
```

### 1.2 Default Collapsed Skill Packs
```text
+-------------------------------------------------------------+
| [x] 🧰 Wiki & Knowledge Pack                 [9 tools] [ > ]|
| [x] 🧰 Linux Sysadmin Pack                   [3 tools] [ > ]|
| [x] 🧰 MCP: github-tools                     [5 tools] [ > ]|
+-------------------------------------------------------------+
```
When clicked:
```text
+-------------------------------------------------------------+
| [x] 🧰 Wiki & Knowledge Pack                 [9 tools] [ v ]|
|  [x] wiki_note_create   [x] wiki_note_read   [x] wiki_search|
|  [x] wiki_note_update   [x] wiki_overview    [x] wiki_graph |
+-------------------------------------------------------------+
```

---

## 2. Technical Modifications

### 2.1 `src/web/templates/index.html`
- Header: Remove `<span class="... font-mono ...">RPG Character Sheet</span>`.
- Top Toolbar: Replace rigid layout with responsive flex wrapper:
  ```html
  <div class="p-3.5 sm:p-4 border-b border-slate-800 bg-slate-900/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
    <div class="flex items-center space-x-3">
      ...
      <h2 class="text-sm font-bold text-white tracking-tight">Agent Forge Studio</h2>
    </div>
    <div class="flex flex-wrap items-center gap-2 w-full sm:w-auto">
      <select id="forgeAgentSelect" class="flex-1 sm:flex-none min-w-[140px] ...">...</select>
      <div class="flex items-center gap-1.5 sm:gap-2 flex-wrap">
        <button id="newAgentBtn" ...>...</button>
        <button id="saveAgentBtn" ...>...</button>
        <button id="deleteAgentBtn" ...>...</button>
      </div>
    </div>
  </div>
  ```

### 2.2 `src/web/static/modules/studios/forge.js`
- In `renderSkillsCatalog(catalog)`:
  - Add class `hidden` to `.pack-tools-grid`:
    `<div class="pack-tools-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 pt-1 hidden">`
  - Style the chevron with `style="transform: rotate(-90deg)"`:
    `<i data-lucide="chevron-down" class="w-4 h-4 transition-transform duration-200" style="transform: rotate(-90deg)"></i>`
  - When the collapse button is clicked, toggle `hidden` and update `transform`:
    `chevron.style.transform = isHidden ? 'rotate(-90deg)' : 'rotate(0deg)'`.
