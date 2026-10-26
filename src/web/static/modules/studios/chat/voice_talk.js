/**
 * Optional Talk button (turn-taking voice). Shown only when /api/voice/status says
 * voice is enabled and reachable. Flow: tap to record -> tap again to send ->
 * /api/voice/transcribe -> normal chat send -> reply spoken via /api/voice/speak.
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
      speakNext = autoSpeak;
      setMode(speakNext ? 'waiting' : 'idle');
      if (typeof chatForm.requestSubmit === 'function') chatForm.requestSubmit();
      else chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    } catch (err) {
      showToast(`Voice failed: ${err.message}`, 'error');
      setMode('idle');
    }
  }

  async function speak(text) {
    const clean = stripForSpeech(text);
    if (!clean) { setMode('idle'); return; }
    setMode('speaking');
    try {
      const res = await fetchFn('/api/voice/speak', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: clean }) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const url = URL.createObjectURL(await res.blob());
      if (mode !== 'speaking') { URL.revokeObjectURL(url); return; }
      audio = new Audio(url);
      audio.onended = () => { URL.revokeObjectURL(url); audio = null; setMode('idle'); };
      await audio.play();
    } catch (err) {
      showToast(`Could not play reply: ${err.message}`, 'error');
      setMode('idle');
    }
  }

  btn.addEventListener('click', (e) => {
    e.preventDefault();
    if (mode === 'idle') startRecording();
    else if (mode === 'recording') recorder?.stop();
    else stopAll();
  });

  window.addEventListener('autoreiv:assistant-reply', (e) => {
    if (!speakNext) return;
    speakNext = false;
    speak(e.detail?.content || '');
  });
  window.addEventListener('autoreiv:voice-settings-changed', refresh);
  setMode('idle');
  refresh();
  return { refresh, stopAll };
}
