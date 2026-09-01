# Engineering Decisions & Architectural Rationale

This document provides a line-by-line, file-by-file account of all architectural choices, engineering trade-offs, and implementation strategies used across the **Voice-to-Insight** codebase.

---

## 1. File-by-File Technical Decisions

### `src/config.py`
- **Decision**: Centralized environment variable management with fallback paths and auto-creation of runtime folders (`output/`, `docs/`, `temp_audio/`).
- **Why**: Prevents scattered `os.getenv()` calls across multiple modules. When modules import `config.py`, base paths and directories are guaranteed to exist, preventing `FileNotFoundError` or permission issues during runtime recording.
- **Key Implementation Details**: Uses `python-dotenv` with graceful fallbacks. Includes a helper `has_groq_key()` to detect placeholder vs. active keys.

---

### `src/audio_recorder.py`
- **Decision**: Built a non-blocking, thread-safe audio recorder using `sounddevice.InputStream` with 16-bit PCM integer sampling at 16,000 Hz mono.
- **Why**: 
  - **16 kHz Mono**: Human speech frequencies are between 80 Hz and 8 kHz (Nyquist theorem requires 16 kHz). Higher sample rates (44.1 kHz or 48 kHz) waste memory and network bandwidth without improving Whisper's word error rate.
  - **Thread-Safety (`threading.Lock`)**: Prevents race conditions between audio streaming callbacks (which run on low-level OS threads) and UI control events (which run on the PyQt event loop).
  - **Real-Time Amplitude Callbacks**: The internal `_audio_callback` calculates Root Mean Square (RMS) amplitude:
    $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^N x_i^2}$$
    This provides low-latency volume metrics directly to the UI visualizer without blocking the audio driver.

---

### `src/stt_service.py`
- **Decision**: Implemented an Abstract Factory / Provider pattern with `BaseSTTProvider`, `GroqWhisperProvider`, and a unified `STTService` facade.
- **Why**:
  - Decouples the UI and insight layers from specific speech APIs.
  - Groq's Tensor Streaming Processors (LPUs) transcribe audio in **sub-second latency (200–400ms)** vs 10–30 seconds on local CPU.
  - Returns a standardized `STTResult` object containing text, duration, inference latency, detected language, and timestamped segments.

---

### `src/rag_engine.py`
- **Decision**: Implemented a self-contained, lightweight BM25 retrieval engine with **Spoken Query Decomposition** and **Markdown Header-Aware Chunking**.
- **Why**:
  - **Why RAG for Voice?**: Spontaneous spoken brainstorming lacks formal structure. Users say: *"Connect the frontend to the payment service we created earlier."* RAG indexes local repositories (`.py`, `.md`, `.ts`, `.json`), retrieves exact function signatures, schemas, and architecture rules, and grounds the LLM prompt in factual code context.
  - **Query Decomposition**: A 2-minute voice recording frequently covers multiple disparate topics (e.g. database schema, auth tokens, deployment). The engine extracts key domain terms and splits multi-sentence transcripts into focused sub-queries, searches the index, and aggregates the top scoring chunks.
  - **Okapi BM25 Scoring**:
    $$\text{Score}(D, Q) = \sum_{q \in Q} \text{IDF}(q) \cdot \frac{f(q, D) \cdot (k_1 + 1)}{f(q, D) + k_1 \cdot \left(1 - b + b \cdot \frac{|D|}{\text{avgdl}}\right)}$$
    BM25 provides exact keyword and symbol matching for code identifiers (function names, API paths) where semantic embeddings often lose exact string fidelity.

---

### `src/insight_engine.py`
- **Decision**: Engineered specialized, multi-stage system prompts for 6 distinct engineering artifacts: `PRD.md`, `architecture.md`, `flow.md`, `tech_stack.md`, `tasks.md`, and `implementation_plan.md`.
- **Why**:
  - Rather than generating a single monolithic text blob, modular generation allows targeted refinement.
  - Incorporates strict markdown guidelines, Mermaid syntax constraints, and Agile task checklists (`- [ ]`).
  - Supports switching between **Groq (`llama-3.3-70b-versatile`)** for ultra-fast generation and **Ollama** for offline privacy.

---

### `src/export_service.py`
- **Decision**: Decoupled document persistence into a standalone static utility service.
- **Why**: Enables one-click exports directly into the root or `/docs` folder of target user repositories, facilitating seamless Git commits.

---

### `src/ui/audio_visualizer.py`
- **Decision**: Created a custom `QWidget` utilizing `QPainter` with antialiased rounded rectangles, linear gradients, and an internal decay timer.
- **Why**: Provides fluid, dynamic visual feedback when the user is speaking. The visualizer applies a Gaussian-like bell curve from center bars with subtle jitter to create a natural frequency spectrum aesthetic.

---

### `src/ui/main_window.py`
- **Decision**: Built a 3-pane responsive desktop UI using PyQt6 with background worker threads (`QThread`) and `WorkerSignals`.
- **Why**:
  - **Worker Threads**: Network I/O (Groq API) and file processing are executed off the main Qt UI thread, ensuring the GUI remains 60fps responsive without stuttering or "Not Responding" freezes.
  - **Drag-and-Drop (`DropZoneWidget`)**: Native OS drag-and-drop handles `.wav`, `.mp3`, `.m4a`, `.ogg`, and `.flac` files directly from Explorer.
  - **Tabbed Editor**: Each generated artifact can be reviewed, edited, or copied in isolated tabs with monospace formatting.

---

### `src/cli.py` & `main.py`
- **Decision**: Dual-mode entry point that auto-detects CLI arguments vs GUI execution.
- **Why**: Gives developers the flexibility to run automated batch transcriptions and blueprint generations in CI/CD scripts or terminal environments while providing the full GUI for interactive brainstorming.
