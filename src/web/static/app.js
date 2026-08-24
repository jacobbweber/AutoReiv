/**
 * AutoReiv Control Plane - Central SPA Orchestrator [REQ-FE-001 - REQ-FE-003]
 */

import { $, $queryAll, safeCreateIcons } from './modules/dom.js';
import { state } from './modules/state/store.js';
import { initChatStudio } from './modules/studios/chat.js';
import { initRoutinesStudio } from './modules/studios/routines.js';
import { initObservability } from './modules/studios/observability.js';
import { initAgentForge } from './modules/studios/forge.js';
import { initSettingsStudio } from './modules/studios/settings.js';
import { initDocsStudio } from './modules/studios/docs.js';
import { initWikiStudio, exportMessageToWiki } from './modules/studios/wiki.js';

export function initApp() {
  safeCreateIcons();

  // Mobile navigation elements
  const mobileMenuBtn = $('mobileMenuBtn');
  const closeSidebarBtn = $('closeSidebarBtn');
  const sidebar = $('sidebar');
  const tabBtns = $queryAll('.tab-btn');
  const tabViews = $queryAll('.tab-view');

  // Wiki mobile drawer
  const wikiMobileDrawerBtn = $('wikiMobileDrawerBtn');
  const wikiDrawerPane = $('wikiDrawerPane');
  const wikiDrawerCloseBtn = $('wikiDrawerCloseBtn');
  const wikiDrawerBackdrop = $('wikiDrawerBackdrop');

  function openWikiDrawer() {
    if (wikiDrawerPane) wikiDrawerPane.classList.remove('-translate-x-full');
    if (wikiDrawerBackdrop) wikiDrawerBackdrop.classList.remove('hidden');
  }

  function closeWikiDrawer() {
    if (wikiDrawerPane) wikiDrawerPane.classList.add('-translate-x-full');
    if (wikiDrawerBackdrop) wikiDrawerBackdrop.classList.add('hidden');
  }

  if (wikiMobileDrawerBtn) wikiMobileDrawerBtn.addEventListener('click', openWikiDrawer);
  if (wikiDrawerCloseBtn) wikiDrawerCloseBtn.addEventListener('click', closeWikiDrawer);
  if (wikiDrawerBackdrop) wikiDrawerBackdrop.addEventListener('click', closeWikiDrawer);

  // Docs mobile drawer
  const docsMobileDrawerBtn = $('docsMobileDrawerBtn');
  const docsDrawerPane = $('docsDrawerPane');
  const docsDrawerCloseBtn = $('docsDrawerCloseBtn');
  const docsDrawerBackdrop = $('docsDrawerBackdrop');

  function openDocsDrawer() {
    if (docsDrawerPane) docsDrawerPane.classList.remove('-translate-x-full');
    if (docsDrawerBackdrop) docsDrawerBackdrop.classList.remove('hidden');
  }

  function closeDocsDrawer() {
    if (docsDrawerPane) docsDrawerPane.classList.add('-translate-x-full');
    if (docsDrawerBackdrop) docsDrawerBackdrop.classList.add('hidden');
  }

  if (docsMobileDrawerBtn) docsMobileDrawerBtn.addEventListener('click', openDocsDrawer);
  if (docsDrawerCloseBtn) docsDrawerCloseBtn.addEventListener('click', closeDocsDrawer);
  if (docsDrawerBackdrop) docsDrawerBackdrop.addEventListener('click', closeDocsDrawer);

  // Mobile Sidebar Toggle
  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', () => {
      if (sidebar) sidebar.classList.toggle('-translate-x-full');
    });
  }
  if (closeSidebarBtn) {
    closeSidebarBtn.addEventListener('click', () => {
      if (sidebar) sidebar.classList.add('-translate-x-full');
    });
  }

  // Studios and Controllers references
  let chatCtrl = null;
  let routinesCtrl = null;
  let obsCtrl = null;
  let forgeCtrl = null;
  let settingsCtrl = null;
  let docsCtrl = null;
  let wikiCtrl = null;

  // Tab Switching
  function switchTab(tabName) {
    if (!tabName) return;
    state.activeTab = tabName;

    tabBtns.forEach((b) => {
      if (b.dataset.tab === tabName) {
        b.className =
          'tab-btn active w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition bg-brand-600 text-white shadow-sm shadow-brand-500/20';
      } else {
        b.className =
          'tab-btn w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition text-slate-400 hover:text-white hover:bg-slate-800';
      }
    });

    tabViews.forEach((v) => {
      if (v.id === `view-${tabName}`) {
        v.classList.remove('hidden');
        v.classList.add('flex');
      } else {
        v.classList.add('hidden');
        v.classList.remove('flex');
      }
    });

    safeCreateIcons();

    // Isolated Tab Loader Execution
    try {
      if (tabName === 'chat' && chatCtrl) {
        chatCtrl.updateActiveAgentHeader();
      } else if (tabName === 'routines' && routinesCtrl) {
        routinesCtrl.loadRoutines();
      } else if (tabName === 'observability' && obsCtrl) {
        obsCtrl.loadObservability();
      } else if (tabName === 'agents' && forgeCtrl) {
        forgeCtrl.loadAgentForge();
      } else if (tabName === 'settings' && settingsCtrl) {
        settingsCtrl.loadSettings();
      } else if (tabName === 'docs' && docsCtrl) {
        docsCtrl.loadSystemDocsNav();
      } else if (tabName === 'wiki' && wikiCtrl) {
        wikiCtrl.loadWikiVault();
      }
    } catch (err) {
      console.error(`[AutoReiv UI] Tab loader error on '${tabName}':`, err);
    }

    // Close mobile drawer on tab select
    if (window.innerWidth < 768 && sidebar) {
      sidebar.classList.add('-translate-x-full');
    }
  }

  tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetTab = btn.dataset.tab;
      switchTab(targetTab);
    });
  });

  // Cross-module callbacks
  const sharedCallbacks = {
    openMermaidInspector: (svg, title) => docsCtrl?.openMermaidInspector(svg, title),
    openRoutineModal: (routine, agentId) => routinesCtrl?.openRoutineModal(routine, agentId),
    exportMessageToWiki: (content) => exportMessageToWiki(state, content),
    onAgentSaved: async () => {
      await chatCtrl?.loadAgents();
    },
    onAgentDeleted: async () => {
      await chatCtrl?.loadAgents();
    },
    renderMarkdown: (el, md) => chatCtrl?.renderMarkdown(el, md),
  };

  // Isolated Initialization Ring [REQ-FE-002]
  const moduleInitializers = [
    {
      name: 'Docs Studio',
      init: () => {
        docsCtrl = initDocsStudio(state, sharedCallbacks);
      },
    },
    {
      name: 'Chat Studio',
      init: () => {
        chatCtrl = initChatStudio(state, sharedCallbacks);
      },
    },
    {
      name: 'Routines Studio',
      init: () => {
        routinesCtrl = initRoutinesStudio(state, sharedCallbacks);
      },
    },
    {
      name: 'Observability Studio',
      init: () => {
        obsCtrl = initObservability(state, sharedCallbacks);
      },
    },
    {
      name: 'Agent Forge Studio',
      init: () => {
        forgeCtrl = initAgentForge(state, sharedCallbacks);
      },
    },
    {
      name: 'Settings Studio',
      init: () => {
        settingsCtrl = initSettingsStudio(state, sharedCallbacks);
      },
    },
    {
      name: 'Wiki Studio',
      init: () => {
        wikiCtrl = initWikiStudio(state, sharedCallbacks);
      },
    },
  ];

  moduleInitializers.forEach((mod) => {
    try {
      mod.init();
    } catch (err) {
      console.error(`[AutoReiv UI] Failed to initialize ${mod.name}:`, err);
    }
  });

  // Initial Bootstrap
  try {
    chatCtrl?.loadAgents();
    settingsCtrl?.loadSettings();
  } catch (err) {
    console.error('[AutoReiv UI] Bootstrap error:', err);
  }
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }
}
