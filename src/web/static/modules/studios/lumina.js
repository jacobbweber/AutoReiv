/**
 * Lumina Studio Controller [CARD-328].
 * Multimodal Concept Cinema & Stage Player for AutoReiv.
 */

import { $ } from '../dom.js';
import { renderLuminaVisual } from '../lumina/visual.js';
import { showToast as toast } from '../ui/toast.js';

export const POST_SPEECH_PAUSE_MS = 1400; // 1.4s natural breathing room to absorb concept
export const MIN_SCENE_DURATION_MS = 3800; // Minimum viewing time for visual diagram

export function calculateEstimatedDuration(narrationText, postSpeechPauseMs = POST_SPEECH_PAUSE_MS, minDurationMs = MIN_SCENE_DURATION_MS) {
  const words = (narrationText || '').trim().split(/\s+/).filter(Boolean).length;
  // Natural explanatory speech pace is ~135-145 wpm (~2.3 words/sec)
  const estimatedSpeechMs = Math.max(2400, Math.round((words / 2.3) * 1000));
  return Math.max(minDurationMs, estimatedSpeechMs + postSpeechPauseMs);
}

export function initLuminaStudio(state, callbacks = {}) {

  // Studio Containers
  const composeView = $('luminaComposeView');
  const stageView = $('luminaStageView');

  // Compose Elements
  const composeForm = $('luminaComposeForm');
  const topicInput = $('luminaTopicInput');
  const composeBtn = $('luminaComposeBtn');
  const startersList = $('luminaStartersList');
  const composeStatus = $('luminaComposeStatus');

  // Stage Player Elements
  const stageVisual = $('luminaStageVisual');
  const headlineEl = $('luminaHeadline');
  const whisperEl = $('luminaWhisper');
  const narrationEl = $('luminaNarration');
  const progressBar = $('luminaProgressBar');
  const playPauseBtn = $('luminaPlayPauseBtn');
  const playPauseIcon = $('luminaPlayPauseIcon');
  const prevBtn = $('luminaPrevBtn');
  const nextBtn = $('luminaNextBtn');
  const voiceToggleBtn = $('luminaVoiceToggleBtn');
  const sceneIndicators = $('luminaSceneIndicators');
  const backToComposeBtn = $('luminaBackToComposeBtn');
  const sendToCourseBtn = $('luminaSendToCourseBtn');
  const timeDisplay = $('luminaTimeDisplay');

  let currentLesson = null;
  let currentSceneIndex = 0;
  let isPlaying = false;
  let isVoiceEnabled = true;
  let elapsedMs = 0;
  let timerId = null;
  let speechUtterance = null;
  let currentSceneDuration = 10000;
  let speechFinished = false;

  function setView(mode) {
    if (mode === 'playing') {
      if (composeView) composeView.classList.add('hidden');
      if (stageView) stageView.classList.remove('hidden');
    } else {
      pause();
      if (composeView) composeView.classList.remove('hidden');
      if (stageView) stageView.classList.add('hidden');
    }
  }

  function speakNarration(text) {
    if (!isVoiceEnabled || !('speechSynthesis' in window)) {
      speechFinished = true;
      return;
    }
    window.speechSynthesis.cancel();
    if (!text) {
      speechFinished = true;
      return;
    }
    speechFinished = false;
    const clean = text.replace(/[*_#`]/g, '');
    speechUtterance = new SpeechSynthesisUtterance(clean);
    speechUtterance.rate = 0.95;
    speechUtterance.pitch = 1.0;

    speechUtterance.onend = () => {
      speechFinished = true;
      // When voice ends, dynamically snap the scene duration to wrap up after a natural digest pause
      const targetDuration = elapsedMs + POST_SPEECH_PAUSE_MS;
      currentSceneDuration = Math.max(targetDuration, MIN_SCENE_DURATION_MS);
    };

    speechUtterance.onerror = () => {
      speechFinished = true;
    };

    window.speechSynthesis.speak(speechUtterance);
  }

  function renderScene(index) {
    if (!currentLesson || !currentLesson.scenes || !currentLesson.scenes[index]) return;
    currentSceneIndex = index;
    elapsedMs = 0;
    speechFinished = false;
    const scene = currentLesson.scenes[index];

    if (headlineEl) headlineEl.textContent = scene.headline || '';
    if (whisperEl) whisperEl.textContent = scene.whisper || '';
    if (narrationEl) narrationEl.textContent = scene.narration || '';

    if (stageVisual && scene.visual) {
      renderLuminaVisual(scene.visual, stageVisual);
    }

    // Dynamic initial duration calculation based on narration length
    currentSceneDuration = calculateEstimatedDuration(scene.narration);

    // Render timeline dots
    if (sceneIndicators) {
      sceneIndicators.innerHTML = currentLesson.scenes.map((s, i) => `
        <button type="button" class="h-1.5 flex-1 rounded-full transition-all duration-300 ${
          i === index ? 'bg-indigo-400 shadow-sm shadow-indigo-500/50' : i < index ? 'bg-slate-600' : 'bg-slate-800'
        }" data-scene-idx="${i}" title="Scene ${i+1}: ${s.headline}"></button>
      `).join('');

      sceneIndicators.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
          const idx = parseInt(btn.dataset.sceneIdx, 10);
          renderScene(idx);
        });
      });
    }

    if (progressBar) progressBar.style.width = '0%';
    if (isPlaying) {
      speakNarration(scene.narration);
    }
  }

  function tick() {
    if (!isPlaying || !currentLesson) return;
    const scene = currentLesson.scenes[currentSceneIndex];
    if (!scene) return;

    elapsedMs += 100;
    const progress = Math.min(100, (elapsedMs / currentSceneDuration) * 100);

    if (progressBar) progressBar.style.width = `${progress}%`;
    if (timeDisplay) {
      const sec = Math.floor(elapsedMs / 1000);
      const totalSec = Math.floor(currentSceneDuration / 1000);
      timeDisplay.textContent = `0:${sec.toString().padStart(2, '0')} / 0:${totalSec.toString().padStart(2, '0')}`;
    }

    if (elapsedMs >= currentSceneDuration) {
      // Guard: if speech is still talking (e.g. slow TTS voice), extend duration dynamically so we don't cut off speech
      if (isVoiceEnabled && 'speechSynthesis' in window && !speechFinished && window.speechSynthesis.speaking) {
        currentSceneDuration = elapsedMs + 800;
        return;
      }

      if (currentSceneIndex + 1 < currentLesson.scenes.length) {
        renderScene(currentSceneIndex + 1);
      } else {
        pause();
      }
    }
  }

  function play() {
    isPlaying = true;
    if (playPauseIcon) {
      playPauseIcon.setAttribute('data-lucide', 'pause');
      if (window.lucide) window.lucide.createIcons();
    }
    const scene = currentLesson && currentLesson.scenes[currentSceneIndex];
    if (scene && !speechFinished && (!('speechSynthesis' in window) || !window.speechSynthesis.speaking)) {
      speakNarration(scene.narration);
    }
    if (!timerId) {
      timerId = setInterval(tick, 100);
    }
  }

  function pause() {
    isPlaying = false;
    if (playPauseIcon) {
      playPauseIcon.setAttribute('data-lucide', 'play');
      if (window.lucide) window.lucide.createIcons();
    }
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }

  function playLesson(lesson) {
    if (!lesson || !lesson.scenes || lesson.scenes.length === 0) {
      toast('Invalid Lumina lesson', 'error');
      return;
    }
    currentLesson = lesson;
    setView('playing');
    isPlaying = true;
    if (playPauseIcon) {
      playPauseIcon.setAttribute('data-lucide', 'pause');
      if (window.lucide) window.lucide.createIcons();
    }
    renderScene(0);
    if (!timerId) {
      timerId = setInterval(tick, 100);
    }
  }

  async function loadStarters() {
    try {
      const res = await fetch('/api/lumina/starters');
      if (!res.ok) return;
      const data = await res.json();
      const starters = data.starters || [];
      if (!startersList) return;

      startersList.innerHTML = starters.map(s => `
        <button type="button" class="lumina-starter-chip group flex flex-col items-start p-4 rounded-xl border border-slate-800 bg-slate-900/50 hover:bg-slate-800/80 hover:border-indigo-500/50 transition text-left" data-starter-id="${s.id}">
          <span class="text-sm font-semibold text-slate-200 group-hover:text-indigo-300 transition">${s.topic}</span>
          <span class="text-xs text-slate-400 line-clamp-2 mt-1">${s.essence || s.title}</span>
        </button>
      `).join('');

      startersList.querySelectorAll('.lumina-starter-chip').forEach(btn => {
        btn.addEventListener('click', async () => {
          const starterId = btn.dataset.starterId;
          const lres = await fetch(`/api/lumina/lesson/${encodeURIComponent(starterId)}`);
          if (lres.ok) {
            const ldata = await lres.json();
            playLesson(ldata.lesson);
          }
        });
      });
    } catch (err) {
      console.error('[Lumina Studio] Failed to load starters:', err);
    }
  }

  async function composeTopic(topic) {
    const clean = (topic || '').trim();
    if (!clean) return;
    if (composeStatus) composeStatus.textContent = `Composing cinematic concept for "${clean}"...`;
    if (composeBtn) composeBtn.disabled = true;

    try {
      const res = await fetch('/api/lumina/compose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: clean }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.ok && data.lesson) {
        if (composeStatus) composeStatus.textContent = 'Ready.';
        playLesson(data.lesson);
      } else {
        throw new Error(data.error || 'Failed to compose lesson');
      }
    } catch (err) {
      toast(`Composition failed: ${err.message}`, 'error');
      if (composeStatus) composeStatus.textContent = 'Composition failed.';
    } finally {
      if (composeBtn) composeBtn.disabled = false;
    }
  }

  // Event Listeners
  if (composeForm) {
    composeForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (topicInput) composeTopic(topicInput.value);
    });
  }

  if (composeBtn && topicInput) {
    composeBtn.addEventListener('click', (e) => {
      e.preventDefault();
      composeTopic(topicInput.value);
    });
    topicInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        composeTopic(topicInput.value);
      }
    });
  }

  if (playPauseBtn) {
    playPauseBtn.addEventListener('click', () => {
      if (isPlaying) pause();
      else play();
    });
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentSceneIndex > 0) {
        renderScene(currentSceneIndex - 1);
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (currentLesson && currentSceneIndex + 1 < currentLesson.scenes.length) {
        renderScene(currentSceneIndex + 1);
      }
    });
  }

  if (voiceToggleBtn) {
    voiceToggleBtn.addEventListener('click', () => {
      isVoiceEnabled = !isVoiceEnabled;
      voiceToggleBtn.classList.toggle('text-indigo-400', isVoiceEnabled);
      voiceToggleBtn.classList.toggle('text-slate-500', !isVoiceEnabled);
      if (!isVoiceEnabled && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      } else if (isPlaying && currentLesson) {
        speakNarration(currentLesson.scenes[currentSceneIndex].narration);
      }
    });
  }

  if (backToComposeBtn) {
    backToComposeBtn.addEventListener('click', () => setView('compose'));
  }

  if (sendToCourseBtn) {
    sendToCourseBtn.addEventListener('click', async () => {
      if (!currentLesson) return;
      try {
        const res = await fetch('/api/lumina/send-to-course', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ topic: currentLesson.topic }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.ok) {
          toast(`Course created for "${currentLesson.topic}" on mastery ledger`, 'success');
          // Switch tab to education if switcher available
          if (typeof callbacks.switchTab === 'function') {
            callbacks.switchTab('education');
          }
        }
      } catch (err) {
        toast(`Failed to bridge to course: ${err.message}`, 'error');
      }
    });
  }

  // Load initial starters immediately on studio initialization
  loadStarters();

  return {
    loadLuminaStudio: () => {
      loadStarters();
      if (!currentLesson) {
        setView('compose');
      }
    },
    openTopicInLumina: async (topic) => {
      if (topicInput) topicInput.value = topic;
      await composeTopic(topic);
    },
  };
}
