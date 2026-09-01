# Product Requirements Document (PRD): Voice-to-Insight & Blueprint Generator

---

## 1. Executive Summary & Problem Statement
Engineers and technical founders spend hours translating high-level spoken brainstorming, meeting notes, and voice memos into structured technical specifications (PRDs, Architecture documents, Task lists, and Sequence flows). 

**Voice-to-Insight** is an AI-powered desktop and CLI automation engine that ingests live or recorded speech, transcribes it in sub-second latency using Groq Whisper LPUs, grounds the context against local project codebases using an embedded RAG engine, and automatically generates production-ready engineering documentation suites.

---

## 2. Goals & Success Metrics (KPIs)
- **Transcription Latency**: $< 500\text{ ms}$ for 60 seconds of audio via Groq Whisper LPU.
- **Specification Accuracy**: Zero hallucinations on existing APIs/schemas when grounded with the RAG engine.
- **Time to Blueprint**: $< 10\text{ seconds}$ to generate a full 6-document engineering specification suite from a raw voice recording.
- **User Interface Responsiveness**: Continuous 60 FPS UI during audio capture and background network operations.

---

## 3. User Personas & Use Cases
1. **The Solo Architect / Indie Hacker**: Wants to speak an idea aloud while driving or walking, then click one button to generate a complete `PRD.md`, `architecture.md`, `flow.md`, and `tasks.md` ready to implement.
2. **The Engineering Lead**: Records a team design debate or sprint planning session, indexes the current codebase, and generates grounded technical task lists with acceptance criteria.
3. **The Developer (CLI Power User)**: Uses terminal commands (`python main.py generate --text "..."`) in automation scripts or Git commit hooks.

---

## 4. Functional Requirements

### P0 (Critical / Core MVP)
- **Live Microphone Recording**: Non-blocking audio capture with real-time waveform visualizer, pause, resume, and stop controls.
- **File Upload & Drag-and-Drop**: Support for `.wav`, `.mp3`, `.m4a`, `.ogg`, and `.flac`.
- **Groq Whisper STT Integration**: Ultra-fast cloud speech-to-text with timestamp and segment extraction.
- **Full Blueprint Suite Synthesis**: Generation of `PRD.md`, `architecture.md`, `flow.md`, `tech_stack.md`, `tasks.md`, and `implementation_plan.md`.
- **Direct Repository Export**: Saving generated documents directly into user-selected target directories.

### P1 (Important)
- **Embedded RAG Engine**: Indexing local codebases (`.py`, `.md`, `.ts`, `.json`), query decomposition, and BM25 grounded context retrieval.
- **Ollama Local LLM Fallback**: Ability to run completely offline without internet or cloud credits.
- **Multi-Tab Markdown Editor**: Review, edit, and copy generated documents in individual tabs.
- **PDF Compilation**: Generating a combined, styled master `.pdf` file of all documentation.

### P2 (Nice-to-Have / Future)
- **Speaker Diarization**: Multi-speaker identification for meeting notes.
- **Voice-Back Audio Feedback (TTS)**: Conversational audio responses via `edge-tts` or ElevenLabs.

---

## 5. Non-Functional Requirements
- **Performance**: Instant UI feedback; memory footprint $< 150\text{ MB}$.
- **Security**: No hardcoded API keys; dynamic masked key input; local-only processing for audio recordings.
- **Reliability**: Graceful degradation when network drops; informative user alerts without application crashes.
