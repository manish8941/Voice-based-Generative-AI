# Project Engineering Rules & Conventions (rules.md)

This document establishes development standards, code conventions, prompt engineering principles, and architectural guidelines for the **Voice-to-Insight** repository.

---

## 1. Python Code Standards
1. **Type Annotations**: All public functions and methods must include Python 3.10+ type hints (`typing.Optional`, `typing.List`, `typing.Dict`, `typing.Tuple`).
2. **Docstrings & Comments**: Every module, class, and public function must have clear docstrings explaining purpose, parameters, return values, and potential exceptions.
3. **Thread Safety**: Never perform network I/O, heavy file operations, or audio processing directly on the Qt main thread. Use `QThread` with custom `pyqtSignal` objects.
4. **Error Handling**: Use explicit `try-except` blocks. Never use bare `except:` without logging or bubbling up user-friendly error messages.

---

## 2. Audio & Signal Processing Rules
1. **Sample Rate Standardization**: All recorded or processed audio must be normalized to **16,000 Hz, 16-bit PCM mono**.
2. **Audio Buffer Cleanliness**: Always release audio streams (`stream.stop()`, `stream.close()`) in `finally:` blocks or when closing the application.
3. **Temporary File Hygiene**: Audio files stored in `temp_audio/` must use unique timestamped names to avoid write collisions.

---

## 3. RAG & Retrieval Rules
1. **Header-Aware Chunking**: Markdown files must be segmented by section headers (`#`, `##`, `###`) to preserve logical semantic context.
2. **Query Decomposition**: Free-form transcripts must be filtered for domain keywords and split into individual search queries before hitting the BM25 index.
3. **Grounding Prompts**: Injected context blocks must clearly state source filenames and chunk IDs for traceability.

---

## 4. Prompt Engineering & Markdown Output Rules
1. **Valid Mermaid Diagrams**: All generated architecture diagrams and sequence flows must follow strict, parseable Mermaid syntax (`flowchart TD`, `sequenceDiagram`, `stateDiagram-v2`).
2. **Actionable Tasks**: Task checklists must use standard GitHub Markdown checkbox formatting (`- [ ]`) with clear acceptance criteria.
3. **No Conversational Fluff**: System prompts must instruct the LLM to output pure Markdown without conversational intro or outro filler text (*"Sure, here is your PRD..."*).
