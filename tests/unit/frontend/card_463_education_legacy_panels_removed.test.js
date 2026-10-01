/**
 * CARD-463: Education Studio legacy panels removed; operator bar + players only.
 * REQ-463-001..007
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  clearLegacyEducationSessions,
  LEGACY_EDUCATION_SESSIONS_KEY,
} from '../../../src/web/static/modules/studios/education.js';

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

const REMOVED_IDS = [
  'educationAskForm',
  'educationAskSubmitBtn',
  'educationCourseChrome',
  'educationKnowledgeAnchorBar',
  'educationModeGroup',
  'educationDeliveryProfileToolbar',
  'educationTeachStyleInput',
  'educationWikiSearchInput',
  'educationWikiHits',
  'educationDiscussTutorBtn',
  'educationMainColumn',
  'educationPedagogyColumns',
  'educationSessionList',
  'educationSessionsRefreshBtn',
  'educationAmpWatchLuminaBtn',
  'educationDueList',
];

function educationSection(html) {
  const start = html.indexOf('id="view-education"');
  const end = html.indexOf('<!-- ==================== VIEW: LUMINA');
  expect(start).toBeGreaterThan(-1);
  expect(end).toBeGreaterThan(start);
  return html.slice(start, end);
}

describe('CARD-463 Education Studio legacy panels removed', () => {
  it('removed ids are absent from the page and the Studio JS [REQ-463-001..004]', () => {
    const html = read('src/web/templates/index.html');
    const js = [
      read('src/web/static/modules/studios/education.js'),
      read('src/web/static/app.js'),
    ].join('\n');
    for (const id of REMOVED_IDS) {
      expect(html, id).not.toContain(`id="${id}"`);
      expect(js, id).not.toContain(`'${id}'`);
    }
    expect(html).not.toContain('edu-section');
  });

  it('operator bar and players stay; the topic box lives in the operator bar [REQ-463-005]', () => {
    const sec = educationSection(read('src/web/templates/index.html'));
    const opStart = sec.indexOf('id="educationOperatorConsole"');
    const playersStart = sec.indexOf('id="educationPlayersConsole"');
    expect(opStart).toBeGreaterThan(-1);
    expect(playersStart).toBeGreaterThan(opStart);
    const topic = sec.indexOf('id="educationTopicInput"');
    expect(topic).toBeGreaterThan(opStart);
    expect(topic).toBeLessThan(playersStart);
    for (const id of ['educationSetActiveContextBtn', 'educationPairTutorBtn', 'educationOperatorDueBtn',
      'educationOperatorProgressBtn', 'educationOperatorCurateBtn', 'educationPlayerModeFlashcardBtn',
      'educationPlayerModeQuizBtn', 'educationPlayerModeTestBtn']) {
      expect(sec, id).toContain(`id="${id}"`);
    }
  });

  it('education.js is a thin shell that loads the operator and players modules [REQ-463-007]', () => {
    const js = read('src/web/static/modules/studios/education.js');
    expect(js).toContain("import('./education_operator.js')");
    expect(js).toContain("import('./education_players.js')");
    expect(js.split('\n').length).toBeLessThan(120);
  });

  it('clears the browser-only Education Jobs list once [REQ-463-006]', () => {
    const store = new Map([[LEGACY_EDUCATION_SESSIONS_KEY, '[{"id":"x"}]'], ['other', '1']]);
    const storage = {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      removeItem: (k) => store.delete(k),
    };
    expect(LEGACY_EDUCATION_SESSIONS_KEY).toBe('autoreiv.education.sessions.v1');
    expect(clearLegacyEducationSessions(storage)).toBe(true);
    expect(store.has(LEGACY_EDUCATION_SESSIONS_KEY)).toBe(false);
    expect(store.get('other')).toBe('1');
    expect(clearLegacyEducationSessions(storage)).toBe(false);
    expect(clearLegacyEducationSessions(null)).toBe(false);
  });
});
