/**
 * Clipboard helper utility [REQ-FE-004]
 */

export function copyToClipboard(text) {
  if (typeof navigator !== 'undefined' && navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text).catch(() => {
      fallbackCopyTextToClipboard(text);
    });
  } else {
    fallbackCopyTextToClipboard(text);
    return Promise.resolve();
  }
}

function fallbackCopyTextToClipboard(text) {
  if (typeof document === 'undefined') return;
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.top = '0';
  textArea.style.left = '0';
  textArea.style.width = '2em';
  textArea.style.height = '2em';
  textArea.style.padding = '0';
  textArea.style.border = 'none';
  textArea.style.outline = 'none';
  textArea.style.boxShadow = 'none';
  textArea.style.background = 'transparent';
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  try {
    document.execCommand('copy');
  } catch (err) {
    console.warn('[AutoReiv UI] Fallback copy failed:', err);
  }
  document.body.removeChild(textArea);
}
