# Tutor Learning OS Inventory (CARD-436)

> Living inventory for the Education Tutor-first wave ([CARD-435](../cards/CARD-435-education-tutor-first-direction.md)).
> Education Studio stays alive on this card; retirement is [CARD-442](../cards/CARD-442-retire-education-studio-landing.md).

## Hard rails (product policy)

1. **Learning OS = Tutor OS**: education-mode Tutor must drive turns through **named Learning OS skill ids** listed below.
2. **`socratic-tutoring` is the dialogue method**, used *inside* Learning OS turns — not a bypass of the rails.
3. **Open vibes / freeform study chat without a named Learning OS skill are non-product.**
4. If an agent tool for a Learning OS HTTP contract does not exist yet, **do not invent one**. Cite the durable `/api/education/*` path and the owning successor card. Studio remains the live caller until that successor lands.
5. Residual chat hard-gate UX for vibes is owned by [CARD-437](../cards/CARD-437-study-entry-tutor-education-mode-thin-shell.md).

## Named Tutor Learning OS skills

Pack: `platform-packs/tutor/pack.json`  
Skill bodies: `platform-packs/tutor/skills/<id>/SKILL.md`

| Skill id | Intent | Durable APIs / modules | Agent tools today | Successor |
|---|---|---|---|---|
| `start-resume-topic` | Start / resume ordered course for a topic | `POST /api/education/course/start`, `GET /api/education/course`, `POST /api/education/course/jump`, `POST /api/education/tutor/context`; `src/application/education/course.py` (`start_or_resume_course`, `course_chrome_snapshot`), `tutor.py` (`assemble_tutor_topic_context`); ledger `education_course` | `wiki_note_read/search/list`, `wiki_template_list` | CARD-437 |
| `quiz-turn` | One retrieval quiz turn with durable binary grade | `POST /api/education/quiz/extract`, `GET /api/education/quiz/next`, `POST /api/education/quiz/grade`; `quiz_engine.py`; ledger `education_mastery` | wiki read tools | CARD-438 |
| `flashcard-turn` | One SRS / flashcard turn | **No** `/api/education/flashcard/*`. Shares mastery SRS: `GET /api/education/mastery/due`, `POST /api/education/mastery/upsert`, `POST /api/education/quiz/grade`; `srs.py` (`next_due_after_grade`); Wiki `education-flashcard` | wiki read tools | CARD-438 / CARD-439 |
| `due-review` | Due SRS set + retention routine | `GET /api/education/mastery/due`, `GET /api/education/mastery`, `POST /api/education/retention/run`; `retention_routine.py` (`run_education_retention`) | wiki read tools | CARD-439 |
| `education-wiki-curation` | Curate education notes into Wiki library | `src/application/education/templates.py`; Wiki `data/wiki/02_Resources/_Templates/education-*.md`; `POST /api/education/priming/writeback`; `POST /api/education/course/portfolio/create` | `wiki_note_read/search/list/create/update`, `wiki_template_list/read` | CARD-440 |
| `progress-summary` | Trustable progress from durable stores | `GET /api/education/course`, `GET /api/education/course/depth`, mastery routes, `GET /api/education/learner`, `GET /api/education/analysis` (+ `/errors`, `/patterns`); `depth.py`, `learner_model.py`, `analysis.py` | wiki read tools | CARD-441 |
| `socratic-tutoring` | Dialogue **method** inside Learning OS turns | Wiki grounding | wiki read tools | keep (not a rails bypass) |

---

## Education Studio chrome map

Sources walked: `src/web/static/modules/studios/education.js`, `#view-education` in `src/web/templates/index.html`, `src/web/routers/education.py`, `src/web/routers/education_priming.py`, `src/application/education/*`, `platform-packs/tutor/*`, Wiki templates, seeds `src/infrastructure/skills/seeds/education-*`.

| Studio chrome | DOM / module anchors | Application module(s) | HTTP API | Durable store | Wiki template(s) | Tutor skill id | Disposition |
|---|---|---|---|---|---|---|---|
| Bottom-nav Education | `#tab-education` | shell | — | — | — | — | **keep** until CARD-442 |
| Education view shell | `#view-education`, `#educationStudio` | education.js | — | localStorage `autoreiv.education.sessions.v1` | — | — | **keep** until CARD-442; entry re-home CARD-437 |
| Ask / Launch Study Session | `#educationAskForm`, `#educationTopicInput`, `#educationAskSubmitBtn`, `#educationMode*` | course, priming, tutor, environment | `POST /api/education/course/start`, `GET /api/education/course`, `POST /api/education/ask/pressure`, priming routes | `education_course`; Education Jobs | education-priming | `start-resume-topic` | **re-home** CARD-437 |
| Discuss with Tutor | `#educationDiscussTutorBtn` | tutor.py | `POST /api/education/tutor/context` | session + wiki | — | `socratic-tutoring` + Learning OS skill for the turn | **re-home** CARD-437 |
| Course chrome | `#educationCourseChrome`, steps, jump, status | course.py, depth.py, knowledge_types.py | `GET /api/education/course`, `POST /api/education/course/jump`, `POST /api/education/course/complete-step`, `GET /api/education/course/depth` | `education_course` | step templates via `get_template_for_step` | `start-resume-topic`, `progress-summary` | **re-home** 437/441 |
| Mastery / rank / progress | `#educationMasteryBadge`, `#educationAcademicRank`, `#educationMasteryProgressBar`, `#educationNextMilestone` | depth.py, learner_model.py | mastery + course + depth | `education_mastery` | education-score, education-portfolio | `progress-summary` | **re-home** CARD-441 |
| Growth portfolio | `#educationGrowthPortfolioBtn` | depth.py | `POST /api/education/course/portfolio/create` | Wiki `00_Inbox/` + memory | education-portfolio | `education-wiki-curation`, `progress-summary` | **re-home** 440/441 |
| Knowledge type bar | `#educationKnowledgeTypeBadge`, `#educationKnowledgeTypeSelect` | knowledge_types.py | `GET /api/education/knowledge-types`, `POST /api/education/knowledge-artifact` | course/knowledge facts | education-concept / tool / method / problem | `education-wiki-curation` | **re-home** CARD-440 |
| Delivery profile toolbar | `#educationDeliveryProfileToolbar` | environment.py | environment select/apply-ask; course environment preview/complete | delivery profile | education-priming | `start-resume-topic` (context) | **re-home** later |
| Pedagogy style + Wiki grounding | `#educationTeachStyleInput`, `#educationWikiSearchInput`, `#educationWikiHits` | studio wiki search | wiki search APIs | — | — | `education-wiki-curation`, `start-resume-topic` | **re-home** into Tutor tools |
| Dual Coding section | `#educationDualCodingSection`, `#educationDualCodingPanel` | course dual-coding; visual_amplifiers | course dual-coding preview + complete-step | course artifact + wiki | education-dual-coding | `education-wiki-curation` (+ course via start-resume) | **re-home**; seed `education-dual-coding` related |
| Quiz / SRS panel | `#educationQuizPanel`, `#educationDueList`, `#educationRefreshDueBtn`, `#educationRunRetentionBtn` | quiz_engine.py, srs.py, retention_routine.py, learner_model.py | `/api/education/quiz/*`, `/api/education/mastery/due`, `/api/education/retention/run`, `/api/education/ask/pressure`, `/api/education/learner` | `education_mastery` | education-quiz, education-flashcard | `quiz-turn`, `flashcard-turn`, `due-review` | **re-home** 438/439 |
| Elaboration panel | `#educationElaborationPanel` | elaboration.py | `/api/education/elaboration/*`, course elaboration preview/complete | mastery + wiki | education-elaboration | *(no day-one Tutor skill — gap)* | **keep** Studio; later rails |
| Construction lab | `#educationConstructionPanel` | construction.py, labs.py | `/api/education/construction/*`, course lab preview/grade | wiki + mastery | education-lab | seed `education-construction` (not Tutor pack id) | **keep** Studio; later rails |
| Application lab | `#educationApplicationPanel` | application.py | `/api/education/application/*`, course application complete | exercise jobs + mastery | education-lab, education-problem | seed `education-application` | **keep** Studio; later rails |
| Analysis panel | `#educationAnalysisPanel` | analysis.py | `/api/education/analysis*`, course analysis/handoff | analysis + mastery | education-score | `progress-summary` (partial) | **re-home** partial via 441 |
| Environment panel | `#educationEnvironmentPanel` | environment.py | `/api/education/environment*` | delivery profiles | education-priming | — | **re-home** later |
| Amplifiers panel | `#educationAmplifiersPanel` (+ Lumina) | visual_amplifiers.py, lumina.py | `/api/education/amplifiers*`, `/api/lumina/*` | amplifier attachments | education-dual-coding | — | Lumina **stays** (CARD-435); amplifiers later |
| Education Jobs / sessions | `#educationSessionList` | jobs mint (CARD-236/315) | job APIs | jobs store + localStorage | — | `start-resume-topic` (continuity) | **re-home** CARD-437 |

`EDUCATION_SECTION_KEYS` (education.js): quiz, elaboration, construction, application, analysis, environment, amplifiers.  
`EDUCATION_MODES`: custom, priming, dual_coding, construction, application, analysis, environment, amplifiers.  
`EDUCATION_PEDAGOGY_PANEL_IDS`: educationQuizPanel, educationElaborationPanel, educationConstructionPanel, educationApplicationPanel, educationAnalysisPanel, educationEnvironmentPanel, educationAmplifiersPanel.

---

## Wiki education templates

| Slug | File | Typical skill / step |
|---|---|---|
| education-priming | `data/wiki/02_Resources/_Templates/education-priming.md` | start-resume-topic / wiki curation |
| education-dual-coding | `.../education-dual-coding.md` | dual_coding |
| education-elaboration | `.../education-elaboration.md` | elaboration (Studio; later rails) |
| education-quiz | `.../education-quiz.md` | quiz-turn |
| education-flashcard | `.../education-flashcard.md` | flashcard-turn |
| education-lab | `.../education-lab.md` | construction / application |
| education-score | `.../education-score.md` | analysis / progress-summary |
| education-portfolio | `.../education-portfolio.md` | progress-summary / wiki curation |
| education-concept | `.../education-concept.md` | wiki curation |
| education-tool | `.../education-tool.md` | wiki curation |
| education-method | `.../education-method.md` | wiki curation |
| education-problem | `.../education-problem.md` | application / wiki curation |

Code catalog: `src/application/education/templates.py` (`list_education_templates`, `get_education_template`, `get_template_for_step`).

---

## Related seed runbooks (not Tutor pack skill ids)

`src/infrastructure/skills/seeds/education-priming`, `education-dual-coding`, `education-construction`, `education-application` — Ask/Job matched seeds. Do not conflate with Tutor Learning OS skill ids in allowlists.

Autoreiv pack still mirrors `socratic-tutoring` for historical parity; Tutor is the education-first Learning OS agent.

---

## Gaps deferred (honest)

| Gap | Notes | Owner |
|---|---|---|
| No `education_*` agent tools | Skills cite HTTP contracts; Studio is live caller | CARD-437..441 per surface |
| No dedicated flashcard router | Shares mastery/SRS + quiz grade | CARD-438 / 439 |
| Elaboration / construction / application Tutor skills | Not in day-one six; Studio panels remain SoT | later (after 437–441) |
| Chat UX hard-gate for open vibes | Policy documented; enforcement in Study/Tutor shell | CARD-437 |
| Links / curriculum ingest API | Wiki tools + templates only | CARD-440 |
| Non-Studio progress surface | APIs exist; UI still Studio chrome | CARD-441 |
| Education Studio retirement | Explicitly out of this card | CARD-442 |
| `user_modified` Tutor allowlist | Seed sync updates non-`user_modified`; modified packs may need operator tick | live-proof note |

---

## Live proof for Jacob

1. Education Studio still present: bottom-nav Education, `#view-education`, Ask → course chrome → quiz → Discuss with Tutor.
2. Tutor pack skill list shows Learning OS ids (`start-resume-topic`, `quiz-turn`, `flashcard-turn`, `due-review`, `education-wiki-curation`, `progress-summary`, plus `socratic-tutoring`).
3. Contract: `pytest tests/unit/agent_packs/test_card_436_tutor_learning_os_skills.py`.
4. After live proof: say **merge to qa** (or **continue** if gaps).
