/**
 * Optional Talk button (turn-taking voice). Shown only when /api/voice/status says
 * voice is enabled and reachable. Flow: tap to record -> tap again to send ->
 * /api/voice/transcribe -> normal chat send -> reply spoken sentence-by-sentence
 * as it streams (one /api/voice/speak call per chunk, played in order).
 * Tapping while a reply is playing stops playback. Not full duplex.
 */
import { setComposerText } from './composer.js';

export function stripForSpeech(md = '') {
  return String(md)
    .replace(/```[\s\S]*?```/g, ' (code omitted) ')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[#*_>~|]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 4000);
}

export function setupVoiceTalk({ state, chatForm, promptInput, showToast = () => {}, doc = document, fetchFn = fetch } = {}) {
  const btn = doc.getElementById('talkBtn');
  if (!btn || !chatForm || !promptInput) return null;
  const icon = () => btn.querySelector('[data-voice-icon]');
  let mode = 'idle'; // idle | recording | transcribing | waiting | speaking
  let recorder = null; let chunks = []; let stream = null; let audio = null;
  let autoSpeak = true; let speakNext = false;

  const setMode = (m) => {
    mode = m;
    btn.dataset.mode = m;
    const titles = { idle: 'Talk (tap to speak)', recording: 'Listening… tap to send', transcribing: 'Transcribing…', waiting: 'Waiting for reply…', speaking: 'Speaking… tap to stop' };
    btn.title = titles[m] || 'Talk';
    btn.classList.toggle('bg-rose-600', m === 'recording');
    btn.classList.toggle('animate-pulse', m === 'recording' || m === 'transcribing' || m === 'speaking');
    btn.disabled = m === 'transcribing';
    const i = icon(); if (i) i.textContent = m === 'speaking' ? '■' : m === 'recording' ? '●' : '🎤';
  };

  async function refresh() {
    try {
      const res = await fetchFn('/api/voice/status');
      const data = res.ok ? await res.json() : {};
      autoSpeak = data.auto_speak !== false;
      const usable = Boolean(data.enabled && data.reachable);
      btn.classList.toggle('hidden', !usable);
      if (!usable && mode !== 'idle') stopAll();
    } catch { btn.classList.add('hidden'); }
  }

  function stopAll() {
    try { if (recorder && recorder.state !== 'inactive') recorder.stop(); } catch { /* ignore */ }
    if (stream) stream.getTracks().forEach((t) => t.stop());
    stream = null;
    if (audio) { audio.pause(); audio = null; }
    resetSpeech();
    speakNext = false;
    setMode('idle');
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      showToast('Microphone needs HTTPS or localhost in this browser.', 'error');
      return;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      showToast(`Microphone blocked: ${err.message}`, 'error');
      return;
    }
    chunks = [];
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    recorder.onstop = () => sendRecording();
    recorder.start();
    setMode('recording');
  }

  async function sendRecording() {
    if (stream) stream.getTracks().forEach((t) => t.stop());
    stream = null;
    if (mode !== 'recording') return;
    setMode('transcribing');
    const blob = new Blob(chunks, { type: recorder?.mimeType || 'audio/webm' });
    try {
      const res = await fetchFn('/api/voice/transcribe', { method: 'POST', headers: { 'Content-Type': blob.type || 'audio/webm' }, body: blob });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.message || `HTTP ${res.status}`);
      const text = String(data.text || '').trim();
      if (!text) { showToast('Did not catch that. Try again.', 'warning'); setMode('idle'); return; }
      if (state.isStreaming || state.sessionBusy) { setComposerText(promptInput, text); showToast('Reply still running; your words are in the box.', 'info'); setMode('idle'); return; }
      setComposerText(promptInput, text);
      resetSpeech();
      speakNext = autoSpeak;
      setMode(speakNext ? 'waiting' : 'idle');
      if (typeof chatForm.requestSubmit === 'function') chatForm.requestSubmit();
      else chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    } catch (err) {
      showToast(`Voice failed: ${err.message}`, 'error');
      setMode('idle');
    }
  }

  // Streaming speech: split the growing reply into sentence/clause chunks, synthesize
  // each via /api/voice/speak (prefetching ahead), and play them strictly in order.
  let gen = 0; let spokenUpTo = 0; let queue = []; let playing = false; let replyDone = false;

  function resetSpeech() {
    gen += 1; spokenUpTo = 0; queue = []; playing = false; replyDone = false;
  }

  function synth(text, myGen) {
    return fetchFn('/api/voice/speak', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })
      .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.blob(); })
      .then((b) => (myGen === gen ? URL.createObjectURL(b) : null));
  }

  function enqueue(text) {
    const clean = stripForSpeech(text);
    if (!clean || !/[\p{L}\p{N}]/u.test(clean)) return;
    const myGen = gen;
    queue.push({ myGen, p: synth(clean, myGen).catch((err) => { showToast(`Could not speak: ${err.message}`, 'error'); return null; }) });
    if (mode === 'waiting') setMode('speaking');
    pump();
  }

  async function pump() {
    if (playing) return;
    playing = true;
    while (queue.length) {
      const item = queue.shift();
      const url = await item.p;
      if (item.myGen !== gen || mode !== 'speaking') { if (url) URL.revokeObjectURL(url); playing = false; return; }
      if (!url) continue;
      await new Promise((resolve) => {
        audio = new Audio(url);
        audio.onended = audio.onerror = () => { URL.revokeObjectURL(url); audio = null; resolve(); };
        audio.play().catch((err) => { showToast(`Could not play reply: ${err.message}`, 'error'); resolve(); });
      });
      if (item.myGen !== gen) { playing = false; return; }
    }
    playing = false;
    if (replyDone && mode === 'speaking') setMode('idle');
  }

  // Find the last good break point in the unspoken text. First chunk breaks early
  // (clause, ~40 chars) for fast first audio; later chunks prefer full sentences.
  function takeChunks(full, final) {
    const text = full.slice(spokenUpTo);
    if (/```/.test(text) && (text.match(/```/g) || []).length % 2 === 1 && !final) {
      const fence = text.indexOf('```');
      if (fence > 0) { const head = text.slice(0, fence); spokenUpTo += head.length; enqueue(head); }
      return;
    }
    if (final) { spokenUpTo = full.length; enqueue(text); return; }
    const minLen = spokenUpTo === 0 ? 20 : 60;
    const re = /[.!?]+["')\]]*\s+|\n\s*\n|\n[-*\d]|[;:]\s+|,\s+/g;
    let cut = -1; let m;
    while ((m = re.exec(text))) {
      const isSentence = /[.!?\n]/.test(m[0]);
      const end = m.index + m[0].length;
      if (end < minLen) continue;
      if (isSentence || (end >= 120)) cut = end;
    }
    if (cut < 0 && text.length > 220) { const sp = text.lastIndexOf(' ', 200); if (sp > 40) cut = sp + 1; }
    if (cut > 0) { spokenUpTo += cut; enqueue(text.slice(0, cut)); }
  }

  function onDelta(content) {
    if (!speakNext && mode !== 'speaking') return;
    if (spokenUpTo > 4000) return;
    takeChunks(content || '', false);
  }

  function onFinal(content) {
    if (!speakNext && mode !== 'speaking') return;
    speakNext = false;
    takeChunks(content || '', true);
    replyDone = true;
    if (mode === 'waiting') setMode('idle');
    else if (!playing && !queue.length && mode === 'speaking') setMode('idle');
  }

  btn.addEventListener('click', (e) => {
    e.preventDefault();
    if (mode === 'idle') startRecording();
    else if (mode === 'recording') recorder?.stop();
    else stopAll();
  });

  window.addEventListener('autoreiv:assistant-delta', (e) => onDelta(e.detail?.content));
  window.addEventListener('autoreiv:assistant-reply', (e) => onFinal(e.detail?.content));
  window.addEventListener('autoreiv:voice-settings-changed', refresh);
  setMode('idle');
  refresh();
  return { refresh, stopAll };
}
