# Quality Assurance, Test Checklists & Rollback Procedures

This document provides testing checklists, edge-case validation matrices, and disaster recovery / rollback plans for the **Voice-to-Insight** system.

---

## 1. Automated & Manual Test Checklist

### A. Audio Recording Subsystem
- [ ] **Default Input Device Detection**: Verify `sounddevice.query_devices()` identifies an active microphone on Windows/macOS/Linux.
- [ ] **Buffer Continuity**: Verify no audio clipping or frame drops occur during a 60-second continuous recording session.
- [ ] **Pause & Resume**: Verify that pausing the recording halts frame capture and resuming appends seamlessly without audio glitches or duration skew.
- [ ] **WAV File Integrity**: Verify saved `.wav` files match standard specifications: 16,000 Hz, 16-bit PCM, single-channel mono.
- [ ] **Visualizer Responsiveness**: Verify the `AudioVisualizer` widget renders dynamic amplitude bars during speech and decays gracefully to zero during silence.

### B. Speech-to-Text (STT) Subsystem
- [ ] **Valid Groq API Key**: Verify successful sub-second transcription of a sample 10-second `.wav` file.
- [ ] **Multi-Format Ingestion**: Verify transcription works seamlessly across `.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`, and `.webm`.
- [ ] **Missing API Key Handling**: Verify an informative user dialog is presented if `GROQ_API_KEY` is missing or empty.
- [ ] **Large Audio File Handling**: Verify files up to 25 MB are handled cleanly without timeout or memory exhaustion.

### C. RAG Knowledge Base Subsystem
- [ ] **Recursive Indexing**: Verify `LocalRAGEngine.index_directory()` parses subdirectories and ignores binary/unsupported extensions.
- [ ] **Header-Aware Chunking**: Verify `.md` files are split cleanly at `#`, `##`, and `###` headers.
- [ ] **BM25 Retrieval Scoring**: Verify that searching for specific domain terms (e.g. `fastapi`, `database`, `jwt`) retrieves the exact matching code chunks as top 1.
- [ ] **Query Decomposition**: Verify that a multi-sentence transcript is successfully decomposed into domain-specific subqueries.

### D. Insight & Blueprint Generation Subsystem
- [ ] **PRD Generation**: Verify `PRD.md` includes Vision, Goals, Functional Requirements (P0/P1/P2), and Non-Functional Requirements.
- [ ] **Architecture Generation**: Verify `architecture.md` includes valid, parseable Mermaid diagrams (`flowchart TD` or `sequenceDiagram`).
- [ ] **Flow Generation**: Verify `flow.md` details initialization order, call hierarchy, and state transitions.
- [ ] **Tasks Checklist**: Verify `tasks.md` outputs standard Markdown checkboxes (`- [ ]`).
- [ ] **Provider Toggle**: Verify seamless switching between Groq Cloud and Ollama Local without restarting the app.

---

## 2. Edge Case Matrix & Error Handling

| Scenario / Edge Case | Expected System Behavior | Recovery / Mitigation |
| :--- | :--- | :--- |
| **No Microphone Detected** | `AudioRecorder.start()` catches `sd.PortAudioError`. | Displays critical QMessageBox: *"No microphone found. Please connect an audio input device."* |
| **Silent Audio Recording (Mic Muted)** | Whisper outputs empty string or warning token. | System detects empty transcript and prompts the user: *"No speech detected in audio."* |
| **Network Timeout or 429 Rate Limit** | `TranscriptionWorker` / `InsightWorker` catches HTTP exception. | Emits `error` signal to UI; displays user-friendly error dialog without crashing the application. |
| **Target Directory Read-Only** | `ExportService` catches `PermissionError`. | Alerts the user to select an alternate directory with write permissions. |
| **Ollama Service Offline** | `requests.exceptions.ConnectionError` on `http://localhost:11434`. | Prompts user: *"Could not connect to Ollama at localhost:11434. Please ensure Ollama is running (`ollama serve`)."* |

---

## 3. Rollback & Disaster Recovery Procedures

### Scenario A: API Key Invalidation or Cloud Outage
1. **Immediate Fallback**: Switch the **Engine** dropdown from *Groq Cloud* to *Ollama (Local LLM)*.
2. **Local Transcription**: Point the STT pipeline to local `faster-whisper` or local audio files.
3. **Data Preservation**: All recorded WAV files remain safely preserved inside the `temp_audio/` folder.

### Scenario B: Corrupted Document Generation
1. Each tab in the UI is an editable `QTextEdit`. If an LLM response has formatting issues, users can click **"Generate Active Tab Only"** to re-synthesize that single document without losing progress on other tabs.
2. The user can manually edit the markdown directly in the tab before clicking **"Export All to Repository"**.

---

## 4. Diagnostic Commands

```bash
# Run unit test suite
python tests/test_stt.py
python tests/test_recorder.py
python tests/test_rag.py

# Test CLI transcription
python main.py transcribe temp_audio/sample.wav

# Test CLI end-to-end blueprint generation
python main.py generate --text "Build a high-performance voice-to-insight system with PyQt6 and Groq" --export-dir ./output
```
