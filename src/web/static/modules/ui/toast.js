/**
 * Non-Blocking Accessible Toast Notification & Connectivity Subsystem [REQ-TOAST-001, REQ-TOAST-003]
 */

import { $, safeCreateIcons } from '../dom.js';

function getToastDocument() {
  return typeof document !== 'undefined' ? document : null;
}

/**
 * Returns or creates the fixed toast container in the DOM.
 * @returns {HTMLElement|null}
 */
export function getOrCreateToastContainer() {
  const doc = getToastDocument();
  if (!doc) return null;

  let container = doc.getElementById('toastContainer');
  if (!container) {
    container = doc.createElement('div');
    container.id = 'toastContainer';
    container.className =
      'fixed bottom-4 right-4 z-50 flex flex-col space-y-2 pointer-events-none max-w-sm w-full px-4 sm:px-0';
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'true');
    doc.body.appendChild(container);
  }
  return container;
}

/**
 * Dismisses a toast element with animation and DOM cleanup.
 * @param {HTMLElement} toastEl
 */
export function dismissToast(toastEl) {
  if (!toastEl) return;
  toastEl.classList.add('opacity-0', 'translate-x-4');
  setTimeout(() => {
    if (toastEl.parentNode) {
      toastEl.parentNode.removeChild(toastEl);
    }
  }, 200);
}

/**
 * Displays a non-blocking toast notification.
 * @param {string} message - Notification message.
 * @param {'info'|'success'|'warning'|'error'} [type='info'] - Variant type.
 * @param {number} [duration=4000] - Auto-dismiss duration in ms (0 for persistent).
 * @returns {HTMLElement|null}
 */
export function showToast(message, type = 'info', duration = 4000) {
  const doc = getToastDocument();
  if (!doc) return null;

  const container = getOrCreateToastContainer();
  if (!container) return null;

  const toast = doc.createElement('div');
  const isError = type === 'error';
  toast.setAttribute('role', isError ? 'alert' : 'status');
  toast.setAttribute('aria-live', isError ? 'assertive' : 'polite');

  const colorStyles = {
    info: 'bg-slate-900/95 border-indigo-500/40 text-slate-200',
    success: 'bg-slate-900/95 border-emerald-500/40 text-emerald-100',
    warning: 'bg-slate-900/95 border-amber-500/40 text-amber-100',
    error: 'bg-slate-900/95 border-rose-500/40 text-rose-100',
  }[type] || 'bg-slate-900/95 border-slate-700 text-slate-200';

  const iconName = {
    info: 'info',
    success: 'check-circle-2',
    warning: 'alert-triangle',
    error: 'alert-circle',
  }[type] || 'info';

  const iconColor = {
    info: 'text-indigo-400',
    success: 'text-emerald-400',
    warning: 'text-amber-400',
    error: 'text-rose-400',
  }[type] || 'text-indigo-400';

  toast.className = `pointer-events-auto flex items-start space-x-3 p-3.5 rounded-xl border shadow-2xl backdrop-blur-md transition-all duration-200 transform translate-x-0 opacity-100 ${colorStyles}`;

  toast.innerHTML = `
    <i data-lucide="${iconName}" class="w-5 h-5 ${iconColor} flex-shrink-0 mt-0.5"></i>
    <div class="flex-1 text-xs font-medium leading-relaxed pr-2">${message}</div>
    <button type="button" aria-label="Close notification" class="text-slate-400 hover:text-white transition p-0.5 rounded hover:bg-slate-800/60 flex-shrink-0">
      <i data-lucide="x" class="w-4 h-4"></i>
    </button>
  `;

  const closeBtn = toast.querySelector('button');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => dismissToast(toast));
  }

  container.appendChild(toast);
  safeCreateIcons();

  if (duration > 0) {
    setTimeout(() => {
      dismissToast(toast);
    }, duration);
  }

  return toast;
}

/**
 * Initializes proactive background connectivity polling [REQ-TOAST-003].
 * @param {Object} options
 * @param {string} [options.healthUrl='/api/health']
 * @param {number} [options.intervalMs=15000]
 * @param {Function} [options.onStatusChange]
 * @returns {{ check: Function, stop: Function }}
 */
export function initConnectivityMonitor(options = {}) {
  const {
    healthUrl = '/api/health',
    intervalMs = 15000,
    onStatusChange,
  } = options;

  let isOffline = false;
  let timerId = null;

  async function checkConnectivity() {
    try {
      const res = await fetch(healthUrl, { method: 'GET', cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      if (isOffline) {
        isOffline = false;
        const banner = $('offlineBanner');
        if (banner) banner.classList.add('hidden');
        showToast('Connected back to AutoReiv Gateway', 'success', 3000);
        if (typeof onStatusChange === 'function') onStatusChange(true);
      }
    } catch {
      if (!isOffline) {
        isOffline = true;
        const banner = $('offlineBanner');
        if (banner) banner.classList.remove('hidden');
        showToast('Gateway connection lost. Retrying...', 'warning', 4000);
        if (typeof onStatusChange === 'function') onStatusChange(false);
      }
    }
  }

  const retryBtn = $('offlineBannerRetryBtn');
  if (retryBtn) {
    retryBtn.addEventListener('click', () => checkConnectivity());
  }

  if (intervalMs > 0 && typeof setInterval === 'function') {
    timerId = setInterval(checkConnectivity, intervalMs);
  }

  return {
    check: checkConnectivity,
    stop() {
      if (timerId) clearInterval(timerId);
    },
  };
}
