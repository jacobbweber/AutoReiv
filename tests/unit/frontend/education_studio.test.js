import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import { loadPageHtml } from './template_helper.js';
import {
  EDUCATION_SESSIONS_KEY,
  EDUCATION_ASK_MARKER,
  buildEducationAsk,
  EDUCATION_MODES,
  loadEducationSessions,
  saveEducationSessions,
  upsertEducationSession,
  extractJobIdFromSsePayload,
  isEducationJobGoal,
  gradeEducationAnswerLocal,
  gradeElaborationAnswerLocal,
} from '../../../src/web/static/modules/studios/education.js';

describe('Education Studio shell [CARD-237 / REQ-EDU-SHELL-001..004]', () => {
  let html;
  let educationJs;
  let appJs;
  let desktopJs;

  beforeEach(() => {
    html = loadPageHtml();
    educationJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/education.js'),
      'utf-8',
    );
    appJs = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/app.js'), 'utf-8');
    desktopJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/ui/agent-desktop.js'),
      'utf-8',
    );
    const store = new Map();
    globalThis.localStorage = {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(String(k), String(v)),
      removeItem: (k) => store.delete(k),
      clear: () => store.clear(),
    };
  });

  it('registers Education Studio tab + view in SPA nav [REQ-EDU-SHELL-001]', () => {
    expect(html).toContain('id="tab-education"');
    expect(html).toContain('data-tab="education"');
    expect(html).toContain('id="view-education"');
    expect(html).toContain('id="educationStudio"');
    expect(html).toMatch(/Education\s*Studio|Education/);
    expect(appJs).toContain("initEducationStudio");
    expect(appJs).toContain("./modules/studios/education.js");
    expect(desktopJs).toContain("dock-education");
    expect(desktopJs).toContain("education: 'view-education'");
  });

  it('declares Wiki-backed ask fields (topic + how to teach) [REQ-EDU-SHELL-002]', () => {
    expect(html).toContain('id="educationTopicInput"');
    expect(html).toContain('id="educationTeachStyleInput"');
    expect(html).toContain('id="educationWikiSearchInput"');
    expect(html).toContain('id="educationWikiHits"');
    expect(html).toContain('id="educationAskSubmitBtn"');
    expect(html).toContain('id="educationJobIdChip"');
    expect(html).toContain('id="educationCopyJobIdBtn"');
  });

  it('declares Education Jobs session list with Chat/Observe open actions [REQ-EDU-SHELL-003]', () => {
    expect(html).toContain('id="educationSessionList"');
    expect(html).toContain('id="educationSessionsRefreshBtn"');
    expect(educationJs).toContain('Open in Chat');
    expect(educationJs).toContain('Open in Observe');
    expect(educationJs).toContain('openObserveJob');
  });

  it('wires ask → standing Chat/Job mint path (236) with copyable job_id [REQ-EDU-SHELL-002]', () => {
    expect(educationJs).toContain('/api/chat/stream');
    expect(educationJs).toContain('buildChatStreamPayload');
    expect(educationJs).toContain('job_created');
    expect(educationJs).toContain('/api/sessions');
    expect(educationJs).toContain('/api/wiki/search');
    expect(educationJs).toContain('copyToClipboard');
    expect(educationJs).toContain(EDUCATION_ASK_MARKER);
  });

  it('ships quiz/due operator path but still forbids concept-player/Lumina [REQ-EDU-SHELL-004 / CARD-242]', () => {
    expect(html).toMatch(/id=["']educationQuizPanel/i);
    expect(html).toMatch(/id=["']educationDueList/i);
    expect(html).not.toMatch(/id=["']educationConceptPlayer/i);
    expect(educationJs).not.toMatch(/conceptPlayer/i);
    expect(educationJs.toLowerCase()).not.toContain('lumina');
    expect(educationJs.toLowerCase()).not.toContain('mycel');
  });

  it('prefers weak/due quiz next + learner pressure Ask [CARD-243]', () => {
    expect(html).toMatch(/id=["']educationNextQuizBtn/i);
    expect(html).toMatch(/id=["']educationPressureAskBtn/i);
    expect(html).toMatch(/id=["']educationLearnerSummary/i);
    expect(educationJs).toContain('/api/education/quiz/next');
    expect(educationJs).toContain('/api/education/learner');
    expect(educationJs).toContain('/api/education/ask/pressure');
    expect(educationJs).toContain('buildLearnerPressureClause');
  });

  it('buildEducationAsk is outcome-shaped with topic, teach style, and done-when', () => {
    const ask = buildEducationAsk({
      topic: 'standing Jobs',
      teachStyle: 'ADHD bite-size with one analogy',
      wikiPath: 'concepts/jobs.md',
      wikiTitle: 'Jobs',
    });
    expect(ask).toContain(EDUCATION_ASK_MARKER);
    expect(ask.toLowerCase()).toContain('standing jobs');
    expect(ask.toLowerCase()).toContain('adhd bite-size');
    expect(ask).toContain('concepts/jobs.md');
    expect(ask.toLowerCase()).toContain('done-when');
    expect(isEducationJobGoal(ask)).toBe(true);
  });

  it('persists education sessions locally and upserts by job_id [REQ-EDU-SHELL-003]', () => {
    expect(EDUCATION_SESSIONS_KEY).toContain('education');
    saveEducationSessions([]);
    upsertEducationSession({
      job_id: 'job_abc',
      session_id: 'sess_1',
      topic: 'Jobs',
      teach_style: 'bite-size',
      created_at: '2026-09-11T12:00:00-04:00',
    });
    const rows = loadEducationSessions();
    expect(rows).toHaveLength(1);
    expect(rows[0].job_id).toBe('job_abc');
    upsertEducationSession({
      job_id: 'job_abc',
      session_id: 'sess_1',
      topic: 'Jobs updated',
      teach_style: 'bite-size',
      created_at: '2026-09-11T12:01:00-04:00',
    });
    expect(loadEducationSessions()).toHaveLength(1);
    expect(loadEducationSessions()[0].topic).toBe('Jobs updated');
  });

  it('extractJobIdFromSsePayload reads job_id from standing mint events', () => {
    expect(extractJobIdFromSsePayload({ type: 'job_created', job_id: 'job_xyz' })).toBe('job_xyz');
    expect(extractJobIdFromSsePayload({ type: 'token', text: 'hi' })).toBe('');
    expect(extractJobIdFromSsePayload({ job_id: 'job_plain' })).toBe('job_plain');
  });

  it('isolates Education load so a studio failure cannot blank initApp [REQ-EDU-SHELL-005]', () => {
    // No static top-level import — that would SyntaxError/abort the whole SPA module graph
    expect(appJs).not.toMatch(/import\s*\{\s*initEducationStudio\s*\}\s*from\s*['"]\.\/modules\/studios\/education\.js['"]/);
    expect(appJs).toMatch(/import\(\s*['"]\.\/modules\/studios\/education\.js['"]\s*\)/);
    // Education tab loader is a real else-if in the try, not a stray brace after the chain
    expect(appJs).toMatch(
      /promptsCtrl\.loadPrompts\(\);\s*\} else if \(tabName === 'education' && educationCtrl\)/,
    );
    expect(appJs).not.toMatch(
      /promptsCtrl\.loadPrompts\(\);\s*\}\s*\} else if \(tabName === 'education'/,
    );
  });


  it('Ask mint never reuses Chat/phase session [REQ-EDU-SHELL-002a]', () => {
    expect(educationJs).toMatch(/never reuse Chat\/phase activeSessionId/);
    expect(educationJs).toMatch(/ensureSession\(topic/);
    expect(educationJs).not.toMatch(/if \(state\.activeSessionId\) \{\s*lastSessionId = state\.activeSessionId/);
    expect(educationJs).toMatch(/AbortController/);
    expect(educationJs).toMatch(/educationAskSubmitBtn/);
  });


  it('keeps Education SSE open after job_created [REQ-HITL-ORIGIN-003]', () => {
    expect(educationJs).toMatch(/REQ-HITL-ORIGIN-003/);
    expect(educationJs).not.toMatch(/reader\.cancel\(\)/);
    expect(educationJs).toMatch(/onJobMinted/);
    expect(educationJs).toMatch(/openOriginChatForHitl|selectSession/);
  });

  it('surfaces Needs approval on Education Jobs with Approve in Chat [REQ-HITL-ORIGIN-002]', () => {
    expect(educationJs).toMatch(/needs_approval/);
    expect(educationJs).toMatch(/Approve in Chat/);
    expect(educationJs).toMatch(/refreshEducationApprovals/);
    expect(educationJs).toMatch(/\/api\/approvals\/pending/);
  });

  it('Priming / Dual Coding modes shape Ask + success_rule [REQ-LOS-012-001/002]', () => {
    expect(html).toContain('id="educationModePriming"');
    expect(html).toContain('id="educationModeDualCoding"');
    expect(html).toContain('id="educationModeCustom"');
    expect(educationJs).toContain('EDUCATION_MODES');
    const priming = buildEducationAsk({ topic: 'Jobs', mode: EDUCATION_MODES.priming });
    expect(priming).toContain('never wiki_overview');
    expect(priming).toContain('wiki_note_create');
    expect(priming).toMatch(/Mode: Priming/);
    expect(priming).toMatch(/education-priming/);
    expect(priming).toMatch(/Done-when:.*Priming schema note/i);
    const dual = buildEducationAsk({ topic: 'Jobs', mode: EDUCATION_MODES.dual_coding });
    expect(dual).toContain('never wiki_overview');
    expect(dual).toMatch(/Mode: Dual Coding/);
    expect(dual).toMatch(/education-dual-coding/);
    expect(dual).toMatch(/Mermaid/);
    expect(dual).toMatch(/Done-when:.*Dual Coding study note/i);
  });

  it('includes quiz/due path; still forbids concept-player/Lumina [REQ-LOS-012-003 / CARD-242]', () => {
    expect(html).toContain('id="educationQuizPanel"');
    expect(html).toContain('id="educationDueList"');
    expect(educationJs).toContain('/api/education/quiz/grade');
    expect(educationJs).toContain('/api/education/retention/run');
    expect(educationJs.toLowerCase()).not.toMatch(/concept-player|lumina/);
    expect(html.toLowerCase()).not.toMatch(/concept-player/);
  });

  it('binary external grade helper matches server posture [REQ-EDU-RR-002]', () => {
    expect(gradeEducationAnswerLocal('Standing Job', 'standing job')).toBe(true);
    expect(gradeEducationAnswerLocal('Standing Job', 'toast')).toBe(false);
  });

  it('declares Education Studio quiz / due controls [REQ-EDU-RR-004]', () => {
    expect(html).toContain('id="educationExtractQuizBtn"');
    expect(html).toContain('id="educationQuizAnswerInput"');
    expect(html).toContain('id="educationQuizGradeBtn"');
    expect(html).toContain('id="educationRunRetentionBtn"');
    expect(educationJs).toContain('educationExtractQuizBtn');
    expect(educationJs).toContain('refreshDueList');
  });



  it('ships elaboration explain-it-back operator path [CARD-244]', () => {
    expect(html).toMatch(/id=["']educationElaborationPanel/i);
    expect(html).toMatch(/id=["']educationElaborationAnswerInput/i);
    expect(html).toMatch(/id=["']educationElaborationGradeBtn/i);
    expect(html).toMatch(/id=["']educationNextElaborationBtn/i);
    expect(educationJs).toContain('/api/education/elaboration/grade');
    expect(educationJs).toContain('/api/education/elaboration/next');
    expect(educationJs).toContain('/api/education/elaboration/extract');
    expect(educationJs).toContain('gradeElaborationAnswerLocal');
  });

  it('grades elaboration locally via concepts rubric not fluff [CARD-244]', () => {
    expect(
      gradeElaborationAnswerLocal(
        'A standing Job is a durable outcome-shaped job.',
        { requiredConcepts: ['standing Job', 'durable', 'outcome'] },
      ),
    ).toBe(true);
    expect(
      gradeElaborationAnswerLocal('chat toast remind me', {
        requiredConcepts: ['standing Job', 'durable', 'outcome'],
      }),
    ).toBe(false);
  });


  it('ships Construction generative study-artifact operator path [CARD-245]', () => {
    expect(html).toMatch(/id=["']educationModeConstruction/i);
    expect(html).toMatch(/id=["']educationConstructionPanel/i);
    expect(html).toMatch(/id=["']educationGenerateConstructionBtn/i);
    expect(educationJs).toContain('EDUCATION_MODES.construction');
    expect(educationJs).toContain('/api/education/construction/generate');
    const ask = buildEducationAsk({ topic: 'Jobs', mode: EDUCATION_MODES.construction });
    expect(ask).toMatch(/Mode: Construction/);
    expect(ask).toMatch(/education-construction/);
    expect(ask).toContain('wiki_note_create');
    expect(ask).toContain('never wiki_overview');
    expect(ask).toMatch(/00_Inbox/);
    expect(educationJs.toLowerCase()).not.toMatch(/concept-player|lumina/);
  });


  it('Visual Amplifiers panel + Mermaid/step-through on Retrieval [CARD-249]', () => {
    expect(html).toContain('id="educationModeAmplifiers"');
    expect(html).toContain('id="educationAmplifiersPanel"');
    expect(html).toContain('id="educationAmpAttachBtn"');
    expect(html).toContain('id="educationAmpNextQuizBtn"');
    expect(educationJs).toContain("amplifiers: 'amplifiers'");
    expect(educationJs).toContain('/api/education/amplifiers');
    expect(educationJs).toContain('EDUCATION_MODES.amplifiers');
    const ask = buildEducationAsk({ topic: 'Jobs', mode: EDUCATION_MODES.amplifiers });
    expect(ask).toMatch(/Mode: Visual Amplifiers/);
    expect(ask).toMatch(/Retrieval/);
    expect(ask).toMatch(/Mermaid|step-through/i);
    expect(ask).toMatch(/edutainment|never ship visuals-only/i);
    expect(ask).toContain('never wiki_overview');
    expect(educationJs.toLowerCase()).not.toMatch(/concept-player/);
    // film player may be mentioned as OUT; bare lumina runtime string must stay absent
    expect(educationJs.toLowerCase()).not.toMatch(/\blumina\b/);
  });

  it('Analysis mode + error log panel [CARD-247 / REQ-EDU-AN-004]', () => {
    expect(html).toContain('id="educationModeAnalysis"');
    expect(html).toContain('id="educationAnalysisPanel"');
    expect(html).toContain('id="educationErrorLogList"');
    expect(html).toContain('id="educationMetacogList"');
    expect(html).toContain('id="educationRefreshAnalysisBtn"');
    expect(educationJs).toContain("analysis: 'analysis'");
    expect(educationJs).toContain('/api/education/analysis');
    expect(educationJs).toContain('EDUCATION_MODES.analysis');
    const ask = buildEducationAsk({ topic: 'Jobs', mode: EDUCATION_MODES.analysis });
    expect(ask).toMatch(/Mode: Analysis/);
    expect(ask).toMatch(/miss_reason|error log/i);
  });


  it('Learning OS pedagogy columns fit viewport without forever-horizontal overflow [CARD-250]', () => {
    expect(html).toContain('id="educationPedagogyColumns"');
    expect(html).toContain('id="educationMainColumn"');
    expect(html).toMatch(/education-pedagogy-columns/);
    // wrap/stack + in-panel vertical scroll; no sideways peek
    expect(html).toMatch(/#educationPedagogyColumns[\s\S]{0,400}?overflow-x:\s*hidden/);
    expect(html).toMatch(/#educationPedagogyColumns[\s\S]{0,400}?overflow-y:\s*auto/);
    expect(html).toMatch(/educationPedagogyColumns[^>]*overflow-y-auto/);
    expect(html).toMatch(/educationPedagogyColumns[^>]*overflow-x-hidden|educationPedagogyColumns[^>]*min-w-0/);
    expect(html).toMatch(/educationMainColumn[^>]*min-w-0/);

    const pedagogyIdx = html.indexOf('id="educationPedagogyColumns"');
    const sessionIdx = html.indexOf('id="educationSessionList"');
    expect(pedagogyIdx).toBeGreaterThan(-1);
    expect(sessionIdx).toBeGreaterThan(pedagogyIdx);
    const pedagogyChunk = html.slice(pedagogyIdx, sessionIdx);
    for (const panelId of [
      'educationQuizPanel',
      'educationElaborationPanel',
      'educationConstructionPanel',
      'educationApplicationPanel',
      'educationAnalysisPanel',
      'educationEnvironmentPanel',
      'educationAmplifiersPanel',
    ]) {
      expect(pedagogyChunk).toContain(`id="${panelId}"`);
    }

    // Ask pane remains outside pedagogy wrap; Jobs list after
    expect(html.indexOf('id="educationAskForm"')).toBeGreaterThan(-1);
    expect(html.indexOf('id="educationAskForm"')).toBeLessThan(pedagogyIdx);

    expect(educationJs).toContain('EDUCATION_PEDAGOGY_COLUMNS_ID');
    expect(educationJs).toContain('educationPedagogyColumns');
    expect(educationJs.toLowerCase()).not.toMatch(/\blumina\b/);
    expect(educationJs.toLowerCase()).not.toMatch(/concept-player/);
  });

  it('exposes Socratic Tutor entry button and handler [CARD-326 / REQ-EDU-TUTOR-001]', () => {
    expect(html).toContain('id="educationDiscussTutorBtn"');
    expect(html).toContain('Discuss with Tutor');
    expect(educationJs).toContain('educationDiscussTutorBtn');
    expect(educationJs).toContain('discussWithTutor');
    // CARD-437: discussWithTutor delegates to study_entry (durable tutor/context + course/start)
    expect(educationJs).toContain('enterTutorEducationMode');
    expect(educationJs).toContain("from './study_entry.js'");
    const studyJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/study_entry.js'),
      'utf-8',
    );
    expect(studyJs).toContain('/api/education/tutor/context');
  });

  it('exposes Dual Coding player with prose, diagram canvas, and complete action [CARD-321 / REQ-EDU-DUAL-002]', () => {
    expect(html).toContain('id="educationDualCodingSection"');
    expect(html).toContain('id="educationDualCodingPanel"');
    expect(html).toContain('id="educationDualCodingPreviewBtn"');
    expect(html).toContain('id="educationDualCodingCompleteBtn"');
    expect(html).toContain('id="educationDualCodingRenderBtn"');
    expect(html).toContain('id="educationDualCodingProse"');
    expect(html).toContain('id="educationDualCodingMermaidSource"');
    expect(html).toContain('id="educationDualCodingDiagram"');
    expect(educationJs).toContain('educationDualCodingCompleteBtn');
    expect(educationJs).toContain('previewDualCoding');
    expect(educationJs).toContain('completeDualCodingStep');
    expect(educationJs).toContain('/api/education/course/dual-coding/preview');
    expect(educationJs).toContain('/api/education/course/complete-step');
  });

  it('exposes Elaboration player with preview, explain-in-own-words, and complete action [CARD-323 / REQ-EDU-ELAB-001]', () => {
    expect(html).toContain('id="educationElaborationSection"');
    expect(html).toContain('id="educationElaborationPanel"');
    expect(html).toContain('id="educationElaborationPreviewBtn"');
    expect(html).toContain('id="educationElaborationCompleteBtn"');
    expect(html).toContain('id="educationElaborationPrompt"');
    expect(html).toContain('id="educationElaborationAnswerInput"');
    expect(educationJs).toContain('educationElaborationCompleteBtn');
    expect(educationJs).toContain('previewElaboration');
    expect(educationJs).toContain('completeElaborationStep');
    expect(educationJs).toContain('/api/education/course/elaboration/preview');
    expect(educationJs).toContain('/api/education/course/elaboration/complete');
  });

  it('exposes Construction and Application lab players with preview, verification, and complete actions [CARD-324 / REQ-EDU-LAB-001]', () => {
    // Construction Lab
    expect(html).toContain('id="educationConstructionSection"');
    expect(html).toContain('id="educationConstructionPanel"');
    expect(html).toContain('id="educationConstructionPreviewBtn"');
    expect(html).toContain('id="educationConstructionCompleteBtn"');
    expect(html).toContain('id="educationConstructionPrompt"');
    expect(html).toContain('id="educationConstructionAnswerInput"');
    expect(html).toContain('id="educationConstructionGradeBtn"');
    expect(html).toContain('id="educationConstructionGradeResult"');
    expect(educationJs).toContain('educationConstructionCompleteBtn');
    expect(educationJs).toContain('previewConstructionLab');
    expect(educationJs).toContain('completeConstructionLabStep');

    // Application Lab
    expect(html).toContain('id="educationApplicationSection"');
    expect(html).toContain('id="educationApplicationPanel"');
    expect(html).toContain('id="educationApplicationPreviewBtn"');
    expect(html).toContain('id="educationApplicationCompleteBtn"');
    expect(html).toContain('id="educationApplicationPrompt"');
    expect(html).toContain('id="educationApplicationAnswerInput"');
    expect(html).toContain('id="educationApplicationGradeBtn"');
    expect(html).toContain('id="educationApplicationGradeResult"');
    expect(educationJs).toContain('educationApplicationCompleteBtn');
    expect(educationJs).toContain('previewApplicationLab');
    expect(educationJs).toContain('completeApplicationLabStep');

    // API endpoints
    expect(educationJs).toContain('/api/education/course/lab/preview');
    expect(educationJs).toContain('/api/education/course/lab/grade');
  });

  it('exposes Environment framing and Analysis handoff controls [CARD-325 / REQ-EDU-ENV-001..004]', () => {
    // Analysis handoff
    expect(html).toContain('id="educationAnalysisHandoffBtn"');
    expect(educationJs).toContain('educationAnalysisHandoffBtn');
    expect(educationJs).toContain('handoffAnalysisToRetention');
    expect(educationJs).toContain('/api/education/course/analysis/handoff');

    // Environment framing
    expect(html).toContain('id="educationEnvironmentCompleteBtn"');
    expect(educationJs).toContain('educationEnvironmentCompleteBtn');
    expect(educationJs).toContain('completeEnvironmentStep');
    expect(educationJs).toContain('/api/education/course/environment/complete');
  });

  it('exposes adaptive mastery depth ladder, milestone chrome, and growth portfolio [CARD-327 / REQ-EDU-DEPTH-001..005]', () => {
    // Chrome elements
    expect(html).toContain('id="educationMasteryBadge"');
    expect(html).toContain('id="educationAcademicRank"');
    expect(html).toContain('id="educationMasteryProgressBar"');
    expect(html).toContain('id="educationNextMilestone"');
    expect(html).toContain('id="educationGrowthPortfolioBtn"');

    // JS bindings & helpers
    expect(educationJs).toContain('educationMasteryBadge');
    expect(educationJs).toContain('educationAcademicRank');
    expect(educationJs).toContain('educationMasteryProgressBar');
    expect(educationJs).toContain('educationNextMilestone');
    expect(educationJs).toContain('educationGrowthPortfolioBtn');
    expect(educationJs).toContain('createGrowthPortfolioNote');
    expect(educationJs).toContain('STEP_FRIENDLY_LABELS');

    // API endpoints
    expect(educationJs).toContain('/api/education/course/portfolio/create');
  });

  it('exposes dedicated presentation delivery profile toolbar visually separated from academic depth [CARD-333 / REQ-EDU-DELIVERY-001..005]', () => {
    // Toolbar and badges
    expect(html).toContain('id="educationDeliveryProfileToolbar"');
    expect(html).toContain('id="educationPrimaryDeliveryProfileSelect"');
    expect(html).toContain('id="educationActiveDeliveryProfileBadge"');
    expect(html).toContain('id="educationApplyDeliveryProfileBtn"');

    // Visual separation: delivery profile toolbar has data-card="333", distinct from depth chrome (data-card="327")
    expect(html).toContain('data-card="333"');
    expect(html).toContain('Presentation Delivery Profile');

    // JS bindings & helpers
    expect(educationJs).toContain('educationPrimaryDeliveryProfileSelect');
    expect(educationJs).toContain('educationActiveDeliveryProfileBadge');
    expect(educationJs).toContain('educationApplyDeliveryProfileBtn');
    expect(educationJs).toContain('fillProfileSelect');
    expect(educationJs).toContain('/api/education/environment/select');
  });

  it('exposes knowledge-type anchor badges and controls specialized by type [CARD-334 / REQ-EDU-KTYPE-001..004]', () => {
    // HTML Elements
    expect(html).toContain('id="educationKnowledgeAnchorBar"');
    expect(html).toContain('id="educationKnowledgeTypeBadge"');
    expect(html).toContain('id="educationKnowledgeTypeSelect"');
    expect(html).toContain('data-card="334"');

    // JS bindings
    expect(educationJs).toContain('educationKnowledgeTypeBadge');
    expect(educationJs).toContain('educationKnowledgeTypeSelect');
    expect(educationJs).toContain('Concept (Mental Model)');
    expect(educationJs).toContain('Tool (Interface Sheet)');
    expect(educationJs).toContain('Method (Procedural SOP)');
    expect(educationJs).toContain('Problem (Diagnostic Lab)');
  });
});




