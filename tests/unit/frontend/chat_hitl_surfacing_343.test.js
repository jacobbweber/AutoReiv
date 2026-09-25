import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { shouldSkipPendingHitlCard } from '../../../src/web/static/modules/studios/chat.js';

describe('CARD-343 Real-time HITL Approval Surfacing', () => {
  const chatJsPath = path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js');
  const chatJs = fs.readFileSync(chatJsPath, 'utf-8');

  it('streamBubble places .hitl-approval-card at the bottom (after reasoning-drawer and stream-content)', () => {
    // Locate streamBubble HTML inside chat.js
    const bubbleStart = chatJs.indexOf('streamBubble.innerHTML = `');
    expect(bubbleStart).toBeGreaterThan(0);
    const bubbleEnd = chatJs.indexOf('`;', bubbleStart);
    const bubbleHtml = chatJs.slice(bubbleStart, bubbleEnd);

    const reasoningIdx = bubbleHtml.indexOf('class="reasoning-drawer');
    const contentIdx = bubbleHtml.indexOf('class="stream-content');
    const hitlCardIdx = bubbleHtml.indexOf('class="hitl-approval-card');

    expect(reasoningIdx).toBeGreaterThan(0);
    expect(contentIdx).toBeGreaterThan(0);
    expect(hitlCardIdx).toBeGreaterThan(0);

    // Crucial for mobile viewports: approval prompt must not be placed above
    // the expandable reasoning drawer and stream content, which scrolls it out of view.
    expect(hitlCardIdx).toBeGreaterThan(reasoningIdx);
    expect(hitlCardIdx).toBeGreaterThan(contentIdx);
  });

  it('shouldSkipPendingHitlCard never suppresses phase child approvals or non-streaming parked states', () => {
    const liveIds = new Set(['appr_123']);

    // 1. Phase child approval (multi-phase job parked for HITL)
    expect(shouldSkipPendingHitlCard({
      id: 'appr_123',
      item: { id: 'appr_123', session_id: 'sess_parent_child_phase1' },
      liveIds,
      isStreaming: true,
      originSid: 'sess_parent',
    })).toBe(false);

    // 2. Routine approval
    expect(shouldSkipPendingHitlCard({
      id: 'appr_123',
      item: { id: 'appr_123', routine_id: 'routine_daily' },
      liveIds,
      isStreaming: true,
      originSid: 'sess_parent',
    })).toBe(false);

    // 3. Not streaming (e.g. turn ended or parked): pinned tray must always render pending approvals
    expect(shouldSkipPendingHitlCard({
      id: 'appr_123',
      item: { id: 'appr_123', session_id: 'sess_parent' },
      liveIds,
      isStreaming: false,
      originSid: 'sess_parent',
    })).toBe(false);

    // 4. Active streaming on same session with live inline card: skip duplicate pinned card
    expect(shouldSkipPendingHitlCard({
      id: 'appr_123',
      item: { id: 'appr_123', session_id: 'sess_parent' },
      liveIds,
      isStreaming: true,
      originSid: 'sess_parent',
    })).toBe(true);
  });

  it('scrolls approval card into view on approval_required event during live turn', () => {
    // CARD-470: the inline card (with working Approve/Reject) is rendered by chat/hitl.js renderInlineHitlCard.
    const hitlJs = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/chat/hitl.js'), 'utf-8');
    expect(chatJs).toMatch(/eventType === 'approval_required'\) \{\s*renderInlineHitlCard\(hitlCard, ev,/);
    expect(hitlJs).toMatch(/export function renderInlineHitlCard[\s\S]*?cardEl\.scrollIntoView/);
  });
});
