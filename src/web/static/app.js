/**
 * AutoReiv Control Plane - Central SPA Orchestrator [REQ-FE-001 - REQ-FE-003, REQ-A11Y-001 - REQ-A11Y-003]
 */

import { $, $queryAll, isMobile, safeCreateIcons } from './modules/dom.js';
import { state, subscribeAgentsLoaded } from './modules/state/store.js';
import { bindStudioAgentPickers, PICKER_KEYS } from './modules/studios/agent_picker.js';
import { storageGet } from './modules/utils/storage.js';
import { handleFocusTrapKeydown, handleTablistKeydown, syncTabAria } from './modules/utils/accessibility.js';
import { initConnectivityMonitor, showToast } from './modules/ui/toast.js';
import { initChatStudio } from './modules/studios/chat.js';
import { initRoutinesStudio } from './modules/studios/routines.js';
import { initObservability } from './modules/studios/observability.js';
import { initSettingsStudio } from './modules/studios/settings.js';
import { initWikiStudio, exportMessageToWiki, exportSessionToWiki } from './modules/studios/wiki.js';
import { initProjectsStudio } from './modules/studios/projects.js';
import { initPromptsStudio } from './modules/studios/prompts.js';
import { initFactoryStudio } from './modules/studios/factory.js';
import { initSkillStudio } from './modules/studios/skill_studio.js';
import { initToolsStudio } from './modules/studios/tools_studio.js';
import { initAgentDesktop } from './modules/ui/agent-desktop.js';
import { initStudyEntry } from './modules/studios/study_entry.js';
import { initThemeEngine } from './modules/ui/theme-engine.js';
import { studioRegistry } from './modules/studios/registry.js';
import { eventBus, EVENTS } from './modules/events/event-bus.js';
import { setupModal, handleEscapeKey } from './modules/ui/modal.js';

export function initApp() {
  try {
    subscribeAgentsLoaded((agents) => {
      bindStudioAgentPickers(agents, { state });
    });
  } catch (err) {
    console.error('[AutoReiv UI] Failed to subscribe agent roster picker:', err);
  }

  try {
    initThemeEngine();
  } catch (err) {
    console.error('[AutoReiv UI] Failed to initialize theme engine:', err);
  }
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

  // Desktop & Mobile Sidebar Toggle [CARD-138, CARD-139]
  const toggleSidebarBtn = $('toggleSidebarBtn');
  if (toggleSidebarBtn && sidebar) {
    toggleSidebarBtn.addEventListener('click', () => {
      sidebar.classList.toggle('md:hidden');
      sidebar.classList.toggle('-translate-x-full');
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
  let promptsCtrl = null;
  let factoryCtrl = null;
  let skillCtrl = null;
  let toolsCtrl = null;
  let educationCtrl = null;
  let luminaCtrl = null;
  let desktopCtrl = null;

  // Mobile Surface Elements [CARD-139]
  const surfaceBtns = {
    cockpit: $('surfaceBtnCockpit'),
    vault: $('surfaceBtnVault'),
    fleet: $('surfaceBtnFleet'),
  };

  function updateMobileSurfaces(tabName) {
    // Update Mobile Surface Pills [CARD-139]
    Object.values(surfaceBtns).forEach((b) => {
      if (!b) return;
      b.className = 'surface-btn px-2.5 py-1 rounded-lg text-slate-400 hover:text-white transition flex items-center space-x-1';
    });
    const activeSurfaceClass = 'surface-btn active px-2.5 py-1 rounded-lg bg-brand-600 text-white transition flex items-center space-x-1';
    if (tabName === 'chat' && surfaceBtns.cockpit) {
      surfaceBtns.cockpit.className = activeSurfaceClass;
    } else if ((tabName === 'wiki' || tabName === 'projects') && surfaceBtns.vault) {
      surfaceBtns.vault.className = activeSurfaceClass;
    } else if ((tabName === 'agents' || tabName === 'routines' || tabName === 'observability' || tabName === 'factory' || tabName === 'skill-studio' || tabName === 'tools-studio' || tabName === 'settings') && surfaceBtns.fleet) {
      surfaceBtns.fleet.className = activeSurfaceClass;
    }
  }

  if (surfaceBtns.cockpit) surfaceBtns.cockpit.addEventListener('click', () => switchTab('chat'));
  if (surfaceBtns.vault) surfaceBtns.vault.addEventListener('click', () => switchTab('wiki'));
  if (surfaceBtns.fleet) surfaceBtns.fleet.addEventListener('click', () => switchTab('agents'));

  // Tab Switching & ARIA Synchronization [REQ-A11Y-001, REQ-A11Y-003]
  function switchTab(tabName) {
    if (!tabName) return;
    state.activeTab = tabName;
    updateMobileSurfaces(tabName);

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

    // Stop polling if leaving factory studio
    if (tabName !== 'factory' && factoryCtrl && typeof factoryCtrl.stopPolling === 'function') {
      factoryCtrl.stopPolling();
    }

    // Isolated Tab Loader Execution [REQ-EDU-SHELL-005]
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
      } else if (tabName === 'factory' && factoryCtrl) {
        factoryCtrl.loadFactoryStudio();
      } else if (tabName === 'skill-studio' && skillCtrl) {
        skillCtrl.loadSkillStudio();
      } else if (tabName === 'tools-studio' && toolsCtrl) {
        toolsCtrl.loadToolsStudio();
      } else if (tabName === 'settings' && settingsCtrl) {
        settingsCtrl.loadSettings();
      } else if (tabName === 'wiki' && wikiCtrl) {
        wikiCtrl.loadWikiVault();
      } else if (tabName === 'projects' && projectsCtrl) {
        projectsCtrl.loadProjects();
      } else if (tabName === 'prompts' && promptsCtrl) {
        promptsCtrl.loadPrompts();
      } else if (tabName === 'education' && educationCtrl) {
        educationCtrl.loadEducationStudio();
      } else if (tabName === 'lumina' && luminaCtrl) {
        luminaCtrl.loadLuminaStudio();
      }
    } catch (err) {
      console.error(`[AutoReiv UI] Tab loader error on '${tabName}':`, err);
    }

    // Studio Registry Lifecycle & EventBus Notification [REQ-ARCH-002, REQ-ARCH-001]
    try {
      studioRegistry.activate(tabName);
      eventBus.emit(EVENTS.TAB_SWITCH, { tabName });
    } catch (registryErr) {
      console.warn('[AutoReiv UI] Studio registry activation error:', registryErr);
    }

    
    // Radical desktop demo: keep window chrome synced with active studio
    if (desktopCtrl && typeof desktopCtrl.onTabChanged === 'function') {
      desktopCtrl.onTabChanged(tabName);
    }
    // Close mobile drawer on tab select
    if (isMobile() && sidebar) {
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

  // Modal Focus Trapping and Escape Key Handler [REQ-A11Y-002, REQ-ARCH-004]
  const allModals = ['routineModal', 'wikiNewNoteModal', 'wikiMindMapModal']
    .map((id) => $(id))
    .filter(Boolean);

  allModals.forEach((modal) => {
    setupModal(modal);
    modal.addEventListener('keydown', (event) => {
      handleFocusTrapKeydown(event, modal);
    });
  });

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      handleEscapeKey();
    }
  });

  // Cross-module callbacks
  const sharedCallbacks = {
    showToast: (msg, type, dur) => showToast(msg, type, dur),
    openRoutineModal: (routine, agentId) => routinesCtrl?.openRoutineModal(routine, agentId),
    exportMessageToWiki: (content) => exportMessageToWiki(state, content),
    exportSessionToWiki: (sessionId) => exportSessionToWiki(state, sessionId),
    onAgentSaved: async () => {
      await chatCtrl?.loadAgents();
    },
    onAgentDeleted: async () => {
      await chatCtrl?.loadAgents();
    },
    onReloadAgents: async (agentId) => {
      await chatCtrl?.loadAgents();
      if (forgeCtrl && typeof forgeCtrl.loadAgentForge === 'function') {
        await forgeCtrl.loadAgentForge(agentId);
      }
    },
    onStartNewAgentPack: async () => {
      switchTab('chat');
      if (chatCtrl && typeof chatCtrl.startNewAgentAuthoring === 'function') {
        await chatCtrl.startNewAgentAuthoring();
      }
    },
    openFactoryStudio: (agentId = null) => {
      switchTab('factory');
      if (factoryCtrl && typeof factoryCtrl.loadFactoryStudio === 'function') {
        factoryCtrl.loadFactoryStudio(agentId);
      }
    },
    openSkillStudio: (agentId = null, skillId = null) => {
      if (skillCtrl && typeof skillCtrl.queueDeepLink === 'function') {
        skillCtrl.queueDeepLink(agentId, skillId);
      }
      switchTab('skill-studio');
    },
    openToolsStudio: (agentId = null, scope = null) => {
      const resolvedScope = scope || (agentId ? 'agent' : 'platform');
      if (toolsCtrl && typeof toolsCtrl.queueDeepLink === 'function') {
        toolsCtrl.queueDeepLink({ scope: resolvedScope, agentId });
      }
      switchTab('tools-studio');
    },
    getFactoryCtrl: () => factoryCtrl,
    onTalkToForge: async (targetAgentId = null) => {
      switchTab('chat');
      if (chatCtrl && typeof chatCtrl.switchSelectedAgent === 'function') {
        await chatCtrl.switchSelectedAgent('forge');
      }
      const promptInput = $('promptInput');
      if (promptInput) {
        const cleanId = String(targetAgentId || '').trim();
        promptInput.value = cleanId && cleanId !== 'all'
          ? `I want to design a new capability for agent "${cleanId}". Let's talk through what it needs.`
          : "I want to design a new capability. Let's talk through what it needs.";
        promptInput.focus();
      }
    },
    renderMarkdown: (el, md) => chatCtrl?.renderMarkdown(el, md),

    switchTab: (tab) => switchTab(tab),
    getChatCtrl: () => chatCtrl,
    getObsCtrl: () => obsCtrl,
    getLuminaCtrl: () => luminaCtrl,
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
      name: 'Agent Studio',
      init: () => {
        // Dynamic import: one studio module failure must not blank initApp [P0 empty-rail]
        import('./modules/studios/forge.js')
          .then((m) => {
            forgeCtrl = m.initAgentForge(state, sharedCallbacks);
            const agentsWindow = document.getElementById('desktopWin-agents');
            if (agentsWindow || state.activeTab === 'agents') {
              const stored = storageGet(PICKER_KEYS.agents);
              forgeCtrl.loadAgentForge(stored || undefined);
            }
          })
          .catch((err) => {
            console.error('[AutoReiv UI] Failed to initialize Agent Studio:', err);
          });
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
    {
      name: 'Prompts Studio',
      init: () => {
        promptsCtrl = initPromptsStudio(state, sharedCallbacks);
      },
    },
    {
      name: 'Skill Studio',
      init: () => {
        skillCtrl = initSkillStudio(state, sharedCallbacks);
      },
    },
    {
      name: 'Tools Studio',
      init: () => {
        toolsCtrl = initToolsStudio(state, sharedCallbacks);
      },
    },
    {
      name: 'Factory Studio',
      init: () => {
        factoryCtrl = initFactoryStudio(state, sharedCallbacks);
      },
    },
    {
      name: 'Education Studio',
      init: () => {
        // Dynamic import: one studio module failure must not blank initApp [REQ-EDU-SHELL-005]
        import('./modules/studios/education.js')
          .then((m) => {
            educationCtrl = m.initEducationStudio(state, sharedCallbacks);
          })
          .catch((err) => {
            console.error('[AutoReiv UI] Failed to initialize Education Studio:', err);
          });
      },
    },
    {
      name: 'Lumina Studio',
      init: () => {
        import('./modules/studios/lumina.js')
          .then((m) => {
            luminaCtrl = m.initLuminaStudio(state, sharedCallbacks);
            const ampWatchLuminaBtn = $('educationAmpWatchLuminaBtn');
            if (ampWatchLuminaBtn) {
              ampWatchLuminaBtn.addEventListener('click', () => {
                const topicInput = $('educationTopicInput');
                const topic = (topicInput && topicInput.value) || 'Photosynthesis';
                switchTab('lumina');
                if (luminaCtrl && typeof luminaCtrl.openTopicInLumina === 'function') {
                  luminaCtrl.openTopicInLumina(topic);
                }
              });
            }
          })
          .catch((err) => {
            console.error('[AutoReiv UI] Failed to initialize Lumina Studio:', err);
          });
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

  // Register studios with polymorphic lifecycle registry [REQ-ARCH-002]
  studioRegistry.register('chat', {
    getController: () => chatCtrl,
  });
  studioRegistry.register('routines', {
    getController: () => routinesCtrl,
  });
  studioRegistry.register('observability', {
    getController: () => obsCtrl,
  });
  studioRegistry.register('agents', {
    getController: () => forgeCtrl,
  });
  studioRegistry.register('factory', {
    deactivate: () => {
      if (factoryCtrl && typeof factoryCtrl.stopPolling === 'function') factoryCtrl.stopPolling();
    },
    getController: () => factoryCtrl,
  });
  studioRegistry.register('skill-studio', {
    deactivate: () => {
      if (skillCtrl && typeof skillCtrl.stopPolling === 'function') skillCtrl.stopPolling();
    },
    getController: () => skillCtrl,
  });
  studioRegistry.register('tools-studio', {
    getController: () => toolsCtrl,
  });
  studioRegistry.register('settings', {
    getController: () => settingsCtrl,
  });
  studioRegistry.register('wiki', {
    getController: () => wikiCtrl,
  });
  studioRegistry.register('projects', {
    getController: () => projectsCtrl,
  });
  studioRegistry.register('prompts', {
    getController: () => promptsCtrl,
  });
  studioRegistry.register('education', {
    getController: () => educationCtrl,
  });
  studioRegistry.register('lumina', {
    getController: () => luminaCtrl,
  });
  try {
    desktopCtrl = initAgentDesktop({
      switchTab,
      state,
      showToast: (msg, type, dur) => showToast(msg, type, dur),
      getChatCtrl: () => chatCtrl,
    });
  } catch (err) {
    console.error('[AutoReiv UI] Failed to initialize Agent Desktop demo:', err);
  }

  try {
    initStudyEntry({
      switchTab,
      getChatCtrl: () => chatCtrl,
      state,
    });
  } catch (err) {
    console.error('[AutoReiv UI] Failed to initialize Study entry (CARD-437):', err);
  }

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
