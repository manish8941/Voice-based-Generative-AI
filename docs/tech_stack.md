# Technology Stack & Environment Specification (tech_stack.md)

This document specifies the technology stack choices, dependency versions, hardware requirements, and setup instructions for the **Voice-to-Insight System**.

---

## 1. Core Technology Stack

| Layer | Technology | Version | Rationale |
| :--- | :--- | :--- | :--- |
| **Language** | Python | `3.10+` / `3.12` | Broad ecosystem support for audio processing, ML SDKs, Qt bindings, and file manipulation. |
| **GUI Framework** | PyQt6 | `^6.6.1` | Native OS desktop performance, robust multi-threading via `QThread`, custom `QPainter` visualizers, and responsive layout management. |
| **UI Theme** | PyQtDarkTheme | `^0.1.7` | Modern, cohesive dark mode design system across all standard Qt widgets. |
| **Audio Capture** | sounddevice | `^0.5.6` | Cross-platform PortAudio bindings for low-latency live microphone streaming and buffer collection. |
| **Audio Processing** | numpy / scipy / wave | `^1.26.0` | High-speed PCM array manipulation, RMS power computation, and 16-bit WAV encoding. |
| **Cloud STT** | Groq Whisper API | `whisper-large-v3-turbo` | Sub-second audio transcription (200–400ms) with zero local GPU VRAM requirements. |
| **Local / Cloud LLM** | Groq Cloud / Ollama | `llama-3.3-70b` / `llama3.2` | High-throughput specification synthesis, complex Mermaid diagram generation, and offline fallback. |
| **RAG Retrieval** | BM25 Inverted Index | Custom / zero-dep | Fast, zero-configuration local semantic retrieval, query decomposition, and code grounding. |
| **PDF Generation** | ReportLab | `^4.3.1` | High-fidelity PDF compilation with custom styles, headers, tables of contents, and cover pages. |

---

## 2. Dependency Matrix (`requirements.txt`)

```text
groq>=0.18.0
PyQt6>=6.6.1
PyQtDarkTheme>=0.1.7
sounddevice>=0.4.6
numpy>=1.26.0
scipy>=1.12.0
python-dotenv>=1.0.1
requests>=2.31.0
reportlab>=4.1.0
markdown>=3.6
pydantic>=2.6.0
```

---

## 3. Environment Variables Configuration

| Variable Name | Required? | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | Recommended | `""` | API key from [Groq Console](https://console.groq.com/keys). |
| `DEFAULT_STT_PROVIDER` | No | `"groq"` | STT provider (`"groq"` or `"local"`). |
| `DEFAULT_GROQ_STT_MODEL`| No | `"whisper-large-v3-turbo"` | Whisper model identifier on Groq. |
| `DEFAULT_LLM_PROVIDER` | No | `"groq"` | LLM provider (`"groq"` or `"ollama"`). |
| `DEFAULT_GROQ_LLM_MODEL`| No | `"llama-3.3-70b-versatile"`| Groq LLM model for blueprint generation. |
| `OLLAMA_HOST` | No | `"http://localhost:11434"` | Local Ollama endpoint address. |
| `AUDIO_SAMPLE_RATE` | No | `16000` | Audio sampling frequency in Hz. |

---

## 4. Local Installation & Launch Guide

```bash
# 1. Clone or navigate to the repository
cd voice_insights_app

# 2. (Optional) Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and paste your GROQ_API_KEY

# 5. Launch the Graphical Desktop App
python main.py

# Or run in CLI mode
python main.py transcribe temp_audio/sample.wav
```
