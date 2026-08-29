/**
 * AutoReiv Control Plane - Central SPA Orchestrator [REQ-FE-001 - REQ-FE-003, REQ-A11Y-001 - REQ-A11Y-003]
 */

import { $, $queryAll, safeCreateIcons } from './modules/dom.js';
import { state } from './modules/state/store.js';
import { handleFocusTrapKeydown, handleTablistKeydown, syncTabAria } from './modules/utils/accessibility.js';
import { initConnectivityMonitor, showToast } from './modules/ui/toast.js';
import { initChatStudio } from './modules/studios/chat.js';
import { initRoutinesStudio } from './modules/studios/routines.js';
import { initObservability } from './modules/studios/observability.js';
import { initAgentForge } from './modules/studios/forge.js';
import { initSettingsStudio } from './modules/studios/settings.js';
import { initWikiStudio, exportMessageToWiki } from './modules/studios/wiki.js';
import { initProjectsStudio } from './modules/studios/projects.js';

export function initApp() {
  safeCreateIcons();

  // Mobile navigation elements
  const mobileMenuBtn = $('mobileMenuBtn');
  const closeSidebarBtn = $('closeSidebarBtn');
  const sidebar = $('sidebar');
  const sidebarNav = $('sidebarNav');
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
  let wikiCtrl = null;
  let projectsCtrl = null;

  // Tab Switching & ARIA Synchronization [REQ-A11Y-001, REQ-A11Y-003]
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

    syncTabAria(tabName, tabBtns, tabViews);
    safeCreateIcons();

    // Isolated Tab Loader Execution
    try {
      if (tabName === 'chat' && chatCtrl) {
        chatCtrl.updateActiveAgentHeader();
        if (!state.sessions || state.sessions.length === 0) {
          chatCtrl.loadSessions();
        }
      } else if (tabName === 'routines' && routinesCtrl) {
        routinesCtrl.loadRoutines();
      } else if (tabName === 'observability' && obsCtrl) {
        obsCtrl.loadObservability();
      } else if (tabName === 'agents' && forgeCtrl) {
        forgeCtrl.loadAgentForge();
      } else if (tabName === 'settings' && settingsCtrl) {
        settingsCtrl.loadSettings();
      } else if (tabName === 'wiki' && wikiCtrl) {
        wikiCtrl.loadWikiVault();
      } else if (tabName === 'projects' && projectsCtrl) {
        projectsCtrl.loadProjects();
      }
    } catch (err) {
      console.error(`[AutoReiv UI] Tab loader error on '${tabName}':`, err);
    }

    // Close mobile drawer on tab select
    if (window.innerWidth < 768 && sidebar) {
      sidebar.classList.add('-translate-x-full');
    }
  }

  // Keyboard navigation on studio tabs [REQ-A11Y-003]
  if (sidebarNav) {
    sidebarNav.addEventListener('keydown', (event) => {
      handleTablistKeydown(event, Array.from(tabBtns), switchTab);
    });
  }

  tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetTab = btn.dataset.tab;
      switchTab(targetTab);
    });
  });

  // Modal Focus Trapping and Escape Key Handler [REQ-A11Y-002]
  const allModals = ['routineModal', 'wikiNewNoteModal', 'wikiMindMapModal', 'wikiGraphModal', 'mermaidZoomModal']
    .map((id) => $(id))
    .filter(Boolean);

  allModals.forEach((modal) => {
    modal.addEventListener('keydown', (event) => {
      handleFocusTrapKeydown(event, modal);
    });
  });

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      const openModal = allModals.find((m) => !m.classList.contains('hidden'));
      if (openModal) {
        const closeBtn =
          openModal.querySelector('#closeRoutineModalBtn') ||
          openModal.querySelector('#cancelRoutineModalBtn') ||
          openModal.querySelector('#wikiNewNoteCloseBtn') ||
          openModal.querySelector('#wikiNewNoteCancelBtn') ||
          openModal.querySelector('#wikiMindMapCloseBtn') ||
          openModal.querySelector('#wikiGraphCloseBtn') ||
          openModal.querySelector('#mermaidCloseModalBtn') ||
          openModal.querySelector('button[aria-label="Close"]') ||
          openModal.querySelector('button');

        if (closeBtn && typeof closeBtn.click === 'function') {
          closeBtn.click();
        } else {
          openModal.classList.add('hidden');
        }
      }
    }
  });

  // Cross-module callbacks
  const sharedCallbacks = {
    showToast: (msg, type, dur) => showToast(msg, type, dur),
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
      name: 'Agent Forge',
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
    {
      name: 'Projects Studio',
      init: () => {
        projectsCtrl = initProjectsStudio(state, sharedCallbacks);
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

  // Initial tab setup
  syncTabAria(state.activeTab || 'chat', tabBtns, tabViews);

  // Proactive Gateway Connectivity Monitoring [REQ-TOAST-003]
  try {
    initConnectivityMonitor({
      healthUrl: '/api/health',
      intervalMs: 20000,
    });
  } catch (err) {
    console.error('[AutoReiv UI] Failed to initialize connectivity monitor:', err);
  }
}

// Auto-boot if DOM is ready or on DOMContentLoaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
