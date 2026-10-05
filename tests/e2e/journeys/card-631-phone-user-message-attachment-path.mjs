/**
 * CARD-631: at phone width, a user bubble with a long Local Path stays inside the viewport.
 */
import { openApp } from './lib/app.mjs';

const LONG_PATH =
  'D:\\\\Projects\\\\Active\\\\AutoReiv\\\\data\\\\attachments\\\\sessions\\\\64797e5bd11e_launch-notes-with-a-very-long-name.txt';
const ATTACH_MSG =
  `what is in this file?\n\n📎 [launch-notes.txt (78 bytes)](/api/chat/attachments/x/launch-notes.txt) (Local Path: \`${LONG_PATH}\`)`;
const URL_MSG =
  'please open https://example.com/very/long/path/that/should/wrap/on/a/phone/without/pushing/the/bubble/offscreen/index.html?q=1';

async function ensureChat(page) {
  if (!(await page.locator('#promptInput').isVisible().catch(() => false))) {
    await page.locator('#dock-chat').click();
  }
  await page.locator('#promptInput').waitFor({ state: 'visible', timeout: 15000 });
}

async function appendUserBubble(page, text) {
  await page.evaluate(async (content) => {
    const mod = await import('/static/modules/studios/chat/render.js');
    const box = document.getElementById('messagesContainer');
    if (!box) throw new Error('no messagesContainer');
    mod.appendMessageBubble('user', content, null, {
      messagesContainer: box,
      renderMarkdownFn: (el, t) => {
        // Minimal markdown: keep backticks as code so Local Path is one long run
        el.innerHTML = String(t || '')
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/`([^`]+)`/g, '<code>$1</code>')
          .replace(/\n/g, '<br>');
      },
    });
  }, text);
}

async function assertNoOverflow(page, viewportWidth) {
  const bad = await page.evaluate((vw) => {
    const root = document.getElementById('messagesContainer');
    if (!root) return 'missing messagesContainer';
    const out = [];
    const walk = (el) => {
      if (!el || el.nodeType !== 1) return;
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) {
        if (r.left < -1 || r.right > vw + 1) {
          out.push({
            tag: el.tagName,
            cls: (el.className || '').toString().slice(0, 80),
            left: r.left,
            right: r.right,
            width: r.width,
          });
        }
      }
      for (const c of el.children) walk(c);
    };
    walk(root);
    return out.slice(0, 8);
  }, viewportWidth);
  if (Array.isArray(bad) && bad.length) {
    throw new Error('overflow: ' + JSON.stringify(bad));
  }
  if (typeof bad === 'string') throw new Error(bad);
}

export default {
  id: 'card-631-phone-user-message-attachment-path',
  card: 'CARD-631',
  title: 'Phone user bubble wraps long attachment paths',
  async run(j, { page, base, viewport }) {
    const vw = (viewport && viewport.width) || 390;
    await j.step('User bubbles with long Local Path and URL stay inside the viewport', async () => {
      await openApp(page, base);
      await ensureChat(page);
      // Clear any prior bubbles for a clean measure
      await page.evaluate(() => {
        const box = document.getElementById('messagesContainer');
        if (box) box.innerHTML = '';
      });
      await appendUserBubble(page, ATTACH_MSG);
      await appendUserBubble(page, URL_MSG);
      await page.waitForTimeout(300);
      await assertNoOverflow(page, vw);
      // Path should wrap: the code element height > one line (~16px) on phone, or bubble width <= vw
      const metrics = await page.evaluate(() => {
        const code = document.querySelector('#messagesContainer .msg-body code');
        const bubble = document.querySelector('#messagesContainer .msg-body')?.parentElement;
        const br = code ? code.getBoundingClientRect() : null;
        const bb = bubble ? bubble.getBoundingClientRect() : null;
        return {
          codeHeight: br && br.height,
          bubbleWidth: bb && bb.width,
          bubbleLeft: bb && bb.left,
        };
      });
      if (!metrics.bubbleWidth || metrics.bubbleWidth > vw + 1) {
        throw new Error('bubble wider than viewport: ' + JSON.stringify(metrics));
      }
      if (metrics.bubbleLeft < -1) {
        throw new Error('bubble off left edge: ' + JSON.stringify(metrics));
      }
    });
  },
};
