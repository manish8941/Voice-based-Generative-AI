# System Execution Flow & Code Lifecycle (Flow.md)

This document maps every feature, entry point, execution order, function call hierarchy, and data transformation pipeline across the **Voice-to-Insight** system.

---

## 1. System Entry Points

```mermaid
flowchart TD
    Start(["User Launches Application"]) --> CheckArgs{"CLI Arguments Provided?"}
    
    CheckArgs -- Yes --> RunCLI["src/cli.py: main()"]
    CheckArgs -- No --> RunGUI["src/ui/main_window.py: run_gui()"]
    
    subgraph CLI_Path ["CLI Execution Routes"]
        RunCLI --> CMD_Record["cmd: record -> AudioRecorder"]
        RunCLI --> CMD_Transcribe["cmd: transcribe -> STTService"]
        RunCLI --> CMD_Generate["cmd: generate -> RAG + InsightEngine"]
    end

    subgraph GUI_Path ["GUI Desktop Route"]
        RunGUI --> QAppInit["Initialize QApplication & Dark Theme"]
        QAppInit --> WinInit["MainWindow.__init__()"]
        WinInit --> RenderUI["Render Audio, Transcript & Blueprint Panels"]
    end
```

---

## 2. End-to-End Execution Sequence

### Workflow A: Live Speech Recording & Transcription Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as MainWindow (Qt Event Loop)
    participant Rec as AudioRecorder (Worker Thread)
    participant SD as sounddevice (Audio Driver)
    participant Vis as AudioVisualizer Widget
    participant STTWorker as TranscriptionWorker (QThread)
    participant STT as GroqWhisperProvider
    participant GroqAPI as Groq Cloud LPU

    User->>UI: Clicks "🎙️ Start Recording"
    UI->>Rec: start()
    Rec->>SD: Open InputStream(16kHz, int16)
    
    loop Every Audio Frame (1024 samples)
        SD-->>Rec: _audio_callback(indata)
        Rec->>Rec: Append frame to buffer & compute RMS
        Rec-->>Vis: set_level(normalized_rms)
        Vis->>Vis: Trigger QPainter repaint (waveform animation)
    end

    User->>UI: Clicks "🛑 Stop Recording"
    UI->>Rec: stop()
    Rec->>SD: Stop & Close InputStream
    UI->>Rec: save_wav("temp_audio/recording_xyz.wav")
    Rec-->>UI: Return saved WAV filepath

    User->>UI: Clicks "⚡ Transcribe Audio to Text"
    UI->>STTWorker: start() (Spawns QThread)
    STTWorker->>STT: transcribe_file(audio_path, model)
    STT->>GroqAPI: POST /v1/audio/transcriptions (multipart/form-data)
    GroqAPI-->>STT: Return JSON { text, segments, duration }
    STT-->>STTWorker: Return STTResult object
    STTWorker-->>UI: signals.finished.emit(STTResult)
    UI->>UI: Populate transcript_edit with text
    UI->>UI: Update word count, duration, and latency metrics
```

---

### Workflow B: RAG Context Retrieval & Insight Generation Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as MainWindow
    participant RAG as LocalRAGEngine
    participant GenWorker as InsightGenerationWorker (QThread)
    participant Engine as InsightEngine
    participant GroqLLM as Groq Cloud API (Llama-3.3-70B)
    participant Exporter as ExportService

    opt Index Codebase for RAG Grounding
        User->>UI: Clicks "📁 Index Target Codebase..."
        UI->>RAG: index_directory(selected_repo_path)
        RAG->>RAG: Scan .py, .md, .ts, .json files
        RAG->>RAG: Section & fixed-window chunking
        RAG->>RAG: Build token inverted index & compute BM25 IDF stats
        RAG-->>UI: Return indexed file & chunk counts
    end

    User->>UI: Clicks "🚀 Generate All Blueprints"
    UI->>RAG: retrieve_grounded_context(transcript)
    RAG->>RAG: decompose_query(transcript) -> [subquery1, subquery2, ...]
    RAG->>RAG: search(subqueries) -> Rank chunks using Okapi BM25
    RAG-->>UI: Return formatted grounded context markdown block

    UI->>GenWorker: start(transcript, rag_context, doc_type="all")
    
    par Parallel/Sequential LLM Syntheses
        GenWorker->>Engine: generate_prd(transcript, rag_context)
        Engine->>GroqLLM: POST /v1/chat/completions (PRD Prompt)
        GroqLLM-->>Engine: Return PRD.md content
    and
        GenWorker->>Engine: generate_architecture(transcript, rag_context)
        Engine->>GroqLLM: POST /v1/chat/completions (Architecture Prompt)
        GroqLLM-->>Engine: Return architecture.md content
    and
        GenWorker->>Engine: generate_flow(transcript, rag_context)
        Engine->>GroqLLM: POST /v1/chat/completions (Flow Prompt)
        GroqLLM-->>Engine: Return flow.md content
    and
        GenWorker->>Engine: generate_tech_stack(transcript, rag_context)
        Engine->>GroqLLM: POST /v1/chat/completions (Tech Stack Prompt)
        GroqLLM-->>Engine: Return tech_stack.md content
    and
        GenWorker->>Engine: generate_tasks(transcript, rag_context)
        Engine->>GroqLLM: POST /v1/chat/completions (Tasks Checklist Prompt)
        GroqLLM-->>Engine: Return tasks.md content
    and
        GenWorker->>Engine: generate_implementation_plan(transcript, rag_context)
        Engine->>GroqLLM: POST /v1/chat/completions (Implementation Plan Prompt)
        GroqLLM-->>Engine: Return implementation_plan.md content
    end

    GenWorker-->>UI: signals.finished.emit(all_generated_docs)
    UI->>UI: Populate each QTabWidget document tab
    
    opt Export to User Repository
        User->>UI: Clicks "💾 Export All to Repository..."
        UI->>Exporter: export_documents(docs, target_dir)
        Exporter->>Exporter: Write files to target folder
        Exporter-->>UI: Return list of saved file paths
    end
```

---

## 3. Function Call Hierarchy Matrix

| User Trigger | Initiating Function | Called Methods & Hierarchy | Destination Artifact / State |
| :--- | :--- | :--- | :--- |
| **Click "Start Recording"** | `_toggle_recording()` | `AudioRecorder.start()` $\to$ `sd.InputStream.start()` | Streaming microphone PCM buffer |
| **Audio Chunk Arrives** | `sd` driver | `_audio_callback()` $\to$ `AudioVisualizer.set_level()` $\to$ `QPainter.paintEvent()` | Real-time animated waveform UI |
| **Click "Stop Recording"** | `_toggle_recording()` | `AudioRecorder.stop()` $\to$ `AudioRecorder.save_wav()` | `temp_audio/recording_*.wav` |
| **Drop Audio File** | `DropZoneWidget.dropEvent()` | `MainWindow._on_file_selected()` | `current_audio_file` state updated |
| **Click "Transcribe"** | `_run_transcription()` | `TranscriptionWorker.start()` $\to$ `STTService.transcribe_file()` $\to$ `Groq.audio.transcriptions.create()` | Populates `transcript_edit` with cleaned text |
| **Click "Index Codebase"** | `_index_codebase_dir()` | `LocalRAGEngine.index_directory()` $\to$ `index_file()` $\to$ `_recompute_bm25_stats()` | In-memory BM25 index of project |
| **Click "Generate All"** | `_run_generation("all")` | `LocalRAGEngine.retrieve_grounded_context()` $\to$ `InsightGenerationWorker.start()` $\to$ `InsightEngine.generate_all()` | Populates all 6 tabs (`PRD`, `Arch`, `Flow`, `Tech`, `Tasks`, `Plan`) |
| **Click "Export to Repo"** | `_export_to_directory()` | `ExportService.export_documents()` | Writes `.md` files to user's Git directory |
| **Click "Export PDF"** | `_generate_pdf_report()` | `generate_master_pdf()` (ReportLab) | `Voice_Insights_Master_Documentation.pdf` |
