/**
 * CARD-630: approval args formatting hides _tool_call_id (display-time).
 * Full Approve-resume live path is covered by existing HITL tests; this journey checks formatHitlArgs in-page.
 */
import { openApp } from './lib/app.mjs';
import { waitFor } from './lib/runner.mjs';

export default {
  id: 'card-630-approval-card-hides-tool-call-id',
  card: 'CARD-630',
  title: 'Approval args hide _tool_call_id',
  async run(j, { page, base }) {
    await j.step('formatHitlArgs drops _tool_call_id in the browser module', async () => {
      await openApp(page, base);
      const out = await page.evaluate(async () => {
        const { formatHitlArgs } = await import('/static/modules/studios/chat/hitl.js');
        const a = formatHitlArgs({ text: 'buy milk', _tool_call_id: 'chatcmpl-tool-b222' });
        const b = formatHitlArgs(JSON.stringify({ text: 'buy milk', _tool_call_id: 'x' }));
        const c = formatHitlArgs({ _tool_call_id: 'only' });
        const d = formatHitlArgs({ tool_call_id: 'keep-me', text: 'hi' });
        return { a, b, c, d };
      });
      if (!out.a.includes('buy milk') || out.a.includes('_tool_call_id')) throw new Error('object leak: ' + out.a);
      if (!out.b.includes('buy milk') || out.b.includes('_tool_call_id')) throw new Error('json leak: ' + out.b);
      if (String(out.c || '').trim() !== '') throw new Error('only-id should be empty: ' + JSON.stringify(out.c));
      if (!out.d.includes('tool_call_id') || !out.d.includes('keep-me')) throw new Error('negative failed: ' + out.d);
    });
  },
};
