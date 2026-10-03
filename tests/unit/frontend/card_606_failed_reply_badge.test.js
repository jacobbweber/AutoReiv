import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import { markStreamFailed, showFailedTurn } from '../../../src/web/static/modules/studios/chat/failed_send.js';

/** CARD-606: a failed reply bubble no longer says "Streaming...". Element fakes, no jsdom (repo convention). */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

function badge(text, className) {
  return { textContent: text, className, attrs: {}, setAttribute(k, v) { this.attrs[k] = v; } };
}
function bubbleWith(...els) {
  return { querySelectorAll: (sel) => (sel === '.animate-pulse' ? els.filter((e) => e.className.includes('animate-pulse')) : []) };
}

describe('REQ-606: the streaming badge becomes Failed', () => {
  it('the plain header badge reads Failed in rose and is marked', () => {
    const b = badge('Streaming...', 'text-brand-400 font-mono text-[10px] animate-pulse');
    expect(markStreamFailed(bubbleWith(b))).toBe(true);
    expect(b.textContent).toBe('Failed');
    expect(b.className).toContain('text-rose-400');
    expect(b.className).not.toContain('animate-pulse');
    expect(b.attrs['data-stream-status']).toBe('failed');
  });

  it('the job-chrome header badge (STREAMING...) is changed too; other pulsing elements are left alone', () => {
    const job = badge('STREAMING...', 'text-brand-400 font-mono text-[10px] animate-pulse');
    const dot = badge('.', 'step-dot animate-pulse');
    markStreamFailed(bubbleWith(job, dot));
    expect(job.textContent).toBe('Failed');
    expect(dot.textContent).toBe('.');
  });

  it('no bubble or no badge is a no-op', () => {
    expect(markStreamFailed(null)).toBe(false);
    expect(markStreamFailed(bubbleWith())).toBe(false);
  });

  it('showFailedTurn marks the bubble along with the toast and inline error', () => {
    const b = badge('Streaming...', 'text-brand-400 animate-pulse');
    const content = { innerHTML: '' };
    const toasts = [];
    showFailedTurn({ err: new Error('Stream error: HTTP 500'), showToast: (m) => toasts.push(m), streamContentEl: content, streamBubble: bubbleWith(b), userPrompt: 'hi' });
    expect(toasts).toEqual(['Chat turn failed: Stream error: HTTP 500']);
    expect(content.innerHTML).toContain('Error: Stream error: HTTP 500');
    expect(b.textContent).toBe('Failed');
  });

  it('the job-chrome header still uses the animate-pulse class markStreamFailed looks for', () => {
    const src = read('src/web/static/modules/studios/chat/job_chrome.js');
    expect(src).toContain("m.streaming ? 'text-brand-400 font-mono text-[10px] animate-pulse'");
    expect(src).toContain("m.streaming ? 'STREAMING...' : 'JOB'");
  });

  it('wiring: executeChatTurn passes the stream bubble to showFailedTurn', () => {
    const src = read('src/web/static/modules/studios/chat.js');
    expect(src).toContain('showFailedTurn({ err, showToast, streamContentEl, streamBubble,');
    expect(src).toContain('<span class="text-brand-400 font-mono text-[10px] animate-pulse">Streaming...</span>');
  });
});
