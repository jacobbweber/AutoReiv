# [CARD-146] Video Extraction and Processing Architecture Exploration

> **Status**: Ready
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:rfc`, `architecture-review`, `needs-discussion`

---

## 1. Why / Intent

Jacob has requested the ability to attach and analyze video files (`.mp4`, `.webm`, `.mov`, `.mkv`) in AutoReiv. With powerful local hardware available (high-end GPU/CPU) and the potential for external tool integrations, this card outlines the technical architecture, hardware requirements, and trade-offs for video processing before building.

---

## 2. Technical Architecture Options

### Option A: Local Audio Extraction & Speech-to-Text (Transcripts)
- **Mechanism**: Use `ffmpeg` to extract the audio track from the video, then run a fast local transcription model (e.g. `faster-whisper` on local GPU/CUDA or CPU).
- **Pros**: Extremely fast, low resource overhead, produces exact word-for-word transcripts with timestamps. Works completely offline.
- **Cons**: Cannot see visual actions, on-screen text, or visual diagrams.

### Option B: Local Keyframe Extraction + Vision Model (Visual Inspection)
- **Mechanism**: Use `ffmpeg` to extract 1 frame every $N$ seconds (or scene change keyframes) into temporary image thumbnails. Pass the sequence of keyframes into vision models (like Gemini Flash or local `qwen2.5-vl`).
- **Pros**: Understands visual diagrams, UI recordings, slides, and physical actions.
- **Cons**: Requires more GPU memory or token context; sampling rate must be tuned to avoid token bloat.

### Option C: Google Gemini File API (Direct Multimodal Video)
- **Mechanism**: When using Gemini Flash, upload the video directly to Google's File API (`gemini.upload_file`). Gemini natively processes video audio and visual frames together at 1 frame per second.
- **Pros**: Zero local CPU/GPU load, state-of-the-art native audio/video comprehension.
- **Cons**: Requires sending the video bytes to Google Cloud (not local-only).

### Option D: Hybrid Pipeline (Recommended)
- **Local FFmpeg Pipeline**:
  1. Extract audio track ➔ Whisper transcription.
  2. Extract keyframes (1 frame every 5–10s).
  3. Combine transcript + keyframe thumbnails into a structured video summary packet for the agent.

---

## 3. Hardware & External Tooling Requirements

1. **FFmpeg**: The universal media swiss-army knife (executable on Windows PATH or bundled).
2. **GPU Acceleration**: NVIDIA CUDA for `faster-whisper` (or CPU fallback with `whisper.cpp`).
3. **Storage**: Ephemeral scratch directory for extracted frames/audio, auto-cleaned after turn.

---

## 4. Discussion & Alignment Questions for Jacob

1. **Primary Use Case**: Are you mainly looking to:
   - Understand what people are saying in videos (Transcripts / Meetings / Lectures)?
   - Visually analyze what is happening on screen (App demo recordings, UI walkthroughs, security camera clips)?
   - Both?
2. **Local vs. Cloud**: Do you prefer 100% local processing (using your local GPU with `ffmpeg` + `whisper`), or leveraging cloud Gemini Flash for quick video upload?
