/**
 * Education Studio player HTTP & context helpers [CARD-448, CARD-716].
 */

import {
  STUDY_TUTOR_AGENT_ID,
  loadStudioActiveEducationContext,
  fetchSelectedEducationContext,
} from './study_entry.js';

export const EDUCATION_PLAYER_GRADE_HTTP = 'POST /api/education/quiz/grade';
export const EDUCATION_PLAYER_QUIZ_NEXT_HTTP = 'GET /api/education/quiz/next';
export const EDUCATION_PLAYER_DUE_HTTP = 'GET /api/education/mastery/due';
export const EDUCATION_PLAYER_MODES = ['flashcard', 'quiz', 'test', 'progress'];

export function resolvePlayerContext(selected) {
  const sel = selected || loadStudioActiveEducationContext() || {};
  const topic = String(sel.topic || '').trim();
  const courseId = String(sel.course_id || sel.courseId || '').trim();
  const agentId =
    String(sel.agent_id || sel.agentId || STUDY_TUTOR_AGENT_ID || 'tutor').trim() || 'tutor';
  return { topic, courseId, agentId, source: topic ? 'education_studio' : 'default' };
}

export async function loadPlayerStudioContext() {
  try {
    const data = await fetchSelectedEducationContext();
    const selected = data && (data.selected || data);
    if (selected && (selected.topic || selected.course_id || selected.agent_id)) {
      return resolvePlayerContext(selected);
    }
  } catch (err) {
    console.warn('[Education Players] selected context fetch failed:', err);
  }
  return resolvePlayerContext(loadStudioActiveEducationContext());
}

/**
 * Durable grade write. Failures return success=false and never set correct=true (no fake pass).
 */
export async function gradePlayerItem({ agentId, item, answer }) {
  const it = item || {};
  const itemId = String(it.item_id || '').trim();
  if (!itemId) {
    return {
      success: false,
      durable: false,
      correct: false,
      error: 'missing_item_id',
      fake_pass: false,
      http_contract: EDUCATION_PLAYER_GRADE_HTTP,
    };
  }
  try {
    const res = await fetch('/api/education/quiz/grade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: agentId || STUDY_TUTOR_AGENT_ID,
        item_id: itemId,
        answer: answer == null ? '' : String(answer),
        topic: it.topic || undefined,
        wiki_path: it.wiki_path || undefined,
        prompt: it._ledger_prompt || it.prompt || undefined,
        expected_answer: it.expected_answer || undefined,
      }),
    });
    if (!res.ok) {
      let detail = '';
      try {
        detail = await res.text();
      } catch {
        /* ignore */
      }
      return {
        success: false,
        durable: false,
        correct: false,
        error: 'HTTP ' + res.status + (detail ? ': ' + detail.slice(0, 180) : ''),
        http_contract: EDUCATION_PLAYER_GRADE_HTTP,
        fake_pass: false,
      };
    }
    const data = await res.json();
    const correct = data && data.correct === true;
    return {
      success: true,
      durable: true,
      correct,
      grade: data.grade || (correct ? 'pass' : 'miss'),
      next_due: data.next_due || null,
      item_id: itemId,
      http_contract: EDUCATION_PLAYER_GRADE_HTTP,
      raw: data,
      fake_pass: false,
    };
  } catch (err) {
    return {
      success: false,
      durable: false,
      correct: false,
      error: String(err && err.message ? err.message : err),
      http_contract: EDUCATION_PLAYER_GRADE_HTTP,
      fake_pass: false,
    };
  }
}

export async function fetchPlayerDueDeck({ agentId, limit = 10 } = {}) {
  const lim = Math.max(1, Math.min(Number(limit) || 10, 50));
  const res = await fetch(
    '/api/education/mastery/due?agent_id=' + encodeURIComponent(agentId || STUDY_TUTOR_AGENT_ID),
  );
  if (!res.ok) throw new Error('mastery/due HTTP ' + res.status);
  const data = await res.json();
  const items = Array.isArray(data.items) ? data.items.slice(0, lim) : [];
  return {
    items,
    count: items.length,
    http_contract: EDUCATION_PLAYER_DUE_HTTP,
    agent_id: data.agent_id,
  };
}

export async function fetchPlayerQuizDeck({ agentId, topic = '', limit = 5 } = {}) {
  const lim = Math.max(1, Math.min(Number(limit) || 5, 50));
  let url =
    '/api/education/quiz/next?agent_id=' +
    encodeURIComponent(agentId || STUDY_TUTOR_AGENT_ID) +
    '&limit=' +
    lim;
  if (topic) url += '&topic=' + encodeURIComponent(topic);
  const res = await fetch(url);
  if (!res.ok) throw new Error('quiz/next HTTP ' + res.status);
  const data = await res.json();
  const items = Array.isArray(data.items) ? data.items : [];
  return {
    items,
    count: items.length,
    http_contract: EDUCATION_PLAYER_QUIZ_NEXT_HTTP,
    delivery: data.delivery || null,
  };
}
