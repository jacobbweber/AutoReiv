/**
 * Wiki Studio & Obsidian-Style Mind-Map Module [REQ-FE-001, REQ-WIKI-006, REQ-MIND-003, CARD-399]
 * Orchestrator module coordinating single-responsibility submodules:
 * - export.js: Message turn export to Wiki Inbox.
 * - templates.js: Structured templates, new note modal, inbox graduation.
 * - note.js: Note content loading, view mode toggle, save/delete, frontmatter inspector.
 * - tree.js: Vault tree hierarchy, collapsible folders, folder overview, folder deletion.
 * - mindmap.js: Obsidian-style force-directed interactive mind map canvas.
 */

import {
  loadWikiNote,
  setupWikiNoteOperations,
  getActiveWikiNotePath,
  setActiveWikiNotePath,
} from './wiki/note.js';
import {
  loadWikiVault,
  setupWikiTreeOperations,
  setActiveWikiFolderPath,
} from './wiki/tree.js';
import {
  loadWikiTemplates,
  setupWikiCuration,
  setupNewNoteModal,
} from './wiki/templates.js';
import {
  openMindMap,
  setupMindMap,
} from './wiki/mindmap.js';

export * from './wiki/export.js';
export * from './wiki/templates.js';
export * from './wiki/note.js';
export * from './wiki/tree.js';
export * from './wiki/mindmap.js';

/**
 * Initializes the Wiki Studio controller and coordinates all submodules.
 * @param {object} state - Global application state.
 * @param {object} callbacks - Shared markdown renderer callbacks.
 * @returns {object} Controller API.
 */
export function initWikiStudio(state, callbacks = {}) {
  // Shared vault reload coordinator
  const handleReloadVault = async () => {
    await loadWikiVault({
      onNoteSelect: handleNoteSelect,
      onClearActiveNote: () => setActiveWikiNotePath(''),
      getActiveNotePath: getActiveWikiNotePath,
    });
  };

  // Shared note select coordinator
  const handleNoteSelect = async (relPath) => {
    await loadWikiNote(relPath, {
      callbacks,
      onReloadVault: handleReloadVault,
      onFolderDeselect: () => setActiveWikiFolderPath(''),
    });
  };

  // Setup Note Operations (preview, edit, save, delete, frontmatter)
  setupWikiNoteOperations({
    callbacks,
    onReloadVault: handleReloadVault,
    onFolderDeselect: () => setActiveWikiFolderPath(''),
  });

  // Setup Tree Operations (search, refresh, folder delete)
  setupWikiTreeOperations({
    onNoteSelect: handleNoteSelect,
    onClearActiveNote: () => setActiveWikiNotePath(''),
    getActiveNotePath: getActiveWikiNotePath,
  });

  // Setup Curation (Rule-based Inbox Graduation)
  setupWikiCuration({
    onReloadVault: handleReloadVault,
  });

  // Setup New Note Modal (category toggle, template prefilling, submission)
  setupNewNoteModal({
    onNoteCreated: handleNoteSelect,
    onReloadVault: handleReloadVault,
  });

  // Setup Obsidian-Style Mind Map (modal, canvas physics, tooltips)
  setupMindMap({
    onNoteSelect: handleNoteSelect,
  });

  // Initial Data Loads
  loadWikiTemplates();
  loadWikiVault({
    onNoteSelect: handleNoteSelect,
    onClearActiveNote: () => setActiveWikiNotePath(''),
    getActiveNotePath: getActiveWikiNotePath,
  });

  return {
    loadWikiVault: (opts = {}) =>
      loadWikiVault({
        onNoteSelect: handleNoteSelect,
        onClearActiveNote: () => setActiveWikiNotePath(''),
        getActiveNotePath: getActiveWikiNotePath,
        ...opts,
      }),
    loadWikiNote: (relPath, opts = {}) =>
      loadWikiNote(relPath, {
        callbacks,
        onReloadVault: handleReloadVault,
        onFolderDeselect: () => setActiveWikiFolderPath(''),
        ...opts,
      }),
    openMindMap: (opts = {}) =>
      openMindMap({
        onNoteSelect: handleNoteSelect,
        ...opts,
      }),
    loadWikiTemplates,
  };
}
