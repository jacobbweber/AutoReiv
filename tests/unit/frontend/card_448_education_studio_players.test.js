/**
 * CARD-448: Education Studio flashcard / quiz / test players.
 * Durable Learning OS grades; flashcard front-then-reveal; no fake pass on failure.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';

describe('CARD-448 Education Studio players', () => {
  let html;
  let playersJs;
  let educationJs;
  let operatorJs;

  beforeEach(() => {
    html = loadPageHtml();
    playersJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/education_players.js'),
      'utf-8',
    );
    educationJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/education.js'),
      'utf-8',
    );
    operatorJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/education_operator.js'),
      'utf-8',
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('[REQ-448-001] exposes flashcard, quiz, and test player surfaces on Education view', () => {
    expect(html).toContain('id="view-education"');
    expect(html).toContain('id="educationPlayersConsole"');
    expect(html).toContain('id="educationPlayerFlashcardPanel"');
    expect(html).toContain('id="educationPlayerQuizPanel"');
    expect(html).toContain('id="educationPlayerTestPanel"');
    expect(html).toContain('id="educationPlayerModeFlashcardBtn"');
    expect(html).toContain('id="educationPlayerModeQuizBtn"');
    expect(html).toContain('id="educationPlayerModeTestBtn"');
    expect(playersJs).toContain('initEducationStudioPlayers');
    expect(educationJs).toContain('education_players.js');
    expect(educationJs).toContain('CARD-448');
  });

  it('[REQ-448-002] grades via Learning OS quiz/grade (same family as CARD-438)', () => {
    expect(playersJs).toContain('/api/education/quiz/grade');
    expect(playersJs).toContain('/api/education/quiz/next');
    expect(playersJs).toContain('/api/education/mastery/due');
    expect(playersJs).toContain('EDUCATION_PLAYER_GRADE_HTTP');
    expect(playersJs).toMatch(/POST \/api\/education\/quiz\/grade/);
  });

  it('[REQ-448-004] player sessions prefer Studio-active topic/course context', () => {
    expect(playersJs).toContain('loadStudioActiveEducationContext');
    expect(playersJs).toContain('fetchSelectedEducationContext');
    expect(html).toContain('id="educationPlayerContextTopic"');
    expect(html).toContain('id="educationPlayerContextCourse"');
    expect(playersJs).toContain('topic=');
  });

  it('[REQ-448-005] keeps Education Studio tab/landing (does not retire)', () => {
    expect(html).toContain('id="tab-education"');
    expect(html).toContain('id="view-education"');
    expect(html).toContain('id="educationStudio"');
    expect(html).toContain('id="educationOperatorConsole"');
  });

  it('[REQ-448-006] does not claim CARD-434 monolith split as success', () => {
    expect(playersJs).not.toMatch(/CARD-434.*success|split education\.js into education\//i);
    expect(educationJs).toContain('education_players.js');
  });

  it('[REQ-448-007] Lumina Studio remains available', () => {
    expect(html).toContain('id="tab-lumina"');
    expect(html).toContain('id="view-lumina"');
  });

  it('flashcard player is front-only until reveal (not both-sides dump only)', () => {
    expect(playersJs).toContain('educationPlayerFlashFront');
    expect(playersJs).toContain('educationPlayerFlashBack');
    expect(playersJs).toContain('educationPlayerFlashRevealBtn');
    expect(playersJs).toMatch(/Front-only until reveal/i);
    expect(playersJs).toContain('flashState.revealed');
    expect(playersJs).toContain('revealFlashcard');
    expect(html).toMatch(/id="educationPlayerFlashBack"[^>]*class="[^"]*hidden/);
  });

  it('grade failure never fakes a pass', () => {
    expect(playersJs).toContain('fake_pass: false');
    expect(playersJs).toMatch(/correct:\s*false/);
    expect(playersJs).toMatch(/no fake pass/i);
    expect(playersJs).toContain('if (!res.ok)');
  });

  it('keeps operator console; players live in education_players.js', () => {
    expect(operatorJs).toContain('CARD-447');
    expect(educationJs).toContain('education_operator.js');
    expect(playersJs).toContain('CARD-448');
    expect(playersJs).toMatch(/does not retire Studio|Does not retire Studio/i);
  });
});
