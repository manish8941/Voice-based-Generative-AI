"""
Main Window GUI for Voice-to-Insight System (PyQt6)
Provides an interactive desktop interface with live audio recording, visualizer,
file drop, Groq Whisper transcription, local RAG indexing, and multi-document insight generation.
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import QObject, QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.audio_recorder import AudioRecorder
from src.config import (
    DEFAULT_GROQ_LLM_MODEL,
    DEFAULT_GROQ_STT_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_OLLAMA_MODEL,
    DOCS_DIR,
    GROQ_API_KEY,
    OUTPUT_DIR,
    TEMP_AUDIO_DIR,
    has_groq_key,
)
from src.export_service import ExportService
from src.insight_engine import InsightEngine
from src.rag_engine import LocalRAGEngine
from src.stt_service import STTResult, STTService
from src.ui.audio_visualizer import AudioVisualizer


class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)


class TranscriptionWorker(QThread):
    """Background worker for Speech-to-Text inference."""

    def __init__(self, stt_service: STTService, audio_path: str, model: str):
        super().__init__()
        self.stt_service = stt_service
        self.audio_path = audio_path
        self.model = model
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.progress.emit("Transcribing audio via Groq Whisper...")
            result = self.stt_service.transcribe_file(self.audio_path, model=self.model)
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))


class InsightGenerationWorker(QThread):
    """Background worker for LLM & Document Generation."""

    def __init__(
        self,
        insight_engine: InsightEngine,
        transcript: str,
        rag_context: str,
        doc_type: str = "all",
    ):
        super().__init__()
        self.insight_engine = insight_engine
        self.transcript = transcript
        self.rag_context = rag_context
        self.doc_type = doc_type
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.doc_type == "all":
                self.signals.progress.emit("Synthesizing PRD, Architecture, Flow & Tasks...")
                results = self.insight_engine.generate_all(self.transcript, self.rag_context)
                self.signals.finished.emit(results)
            else:
                self.signals.progress.emit(f"Generating {self.doc_type}...")
                if self.doc_type == "prd.md":
                    content = self.insight_engine.generate_prd(self.transcript, self.rag_context)
                elif self.doc_type == "architecture.md":
                    content = self.insight_engine.generate_architecture(self.transcript, self.rag_context)
                elif self.doc_type == "flow.md":
                    content = self.insight_engine.generate_flow(self.transcript, self.rag_context)
                elif self.doc_type == "tech_stack.md":
                    content = self.insight_engine.generate_tech_stack(self.transcript, self.rag_context)
                elif self.doc_type == "tasks.md":
                    content = self.insight_engine.generate_tasks(self.transcript, self.rag_context)
                else:
                    content = self.insight_engine.generate_implementation_plan(self.transcript, self.rag_context)
                self.signals.finished.emit({self.doc_type: content})
        except Exception as e:
            self.signals.error.emit(str(e))


class DropZoneWidget(QFrame):
    """Drag-and-drop file target widget."""

    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            """
            DropZoneWidget {
                border: 2px dashed #4a5568;
                border-radius: 8px;
                background-color: #1a202c;
                min-height: 80px;
            }
            DropZoneWidget:hover {
                border-color: #3182ce;
                background-color: #2d3748;
            }
        """
        )
        layout = QVBoxLayout(self)
        self.label = QLabel("Drag & Drop Audio File Here\n(.wav, .mp3, .m4a, .ogg, .flac)", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #a0aec0; font-size: 13px;")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            ext = Path(file_path).suffix.lower()
            if ext in STTService.get_supported_formats():
                self.file_dropped.emit(file_path)
            else:
                QMessageBox.warning(
                    self, "Unsupported Format", f"File format {ext} is not supported."
                )


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoGenFlow: Voice-based Generative AI for Workflows")
        self.resize(1350, 850)

        # Core Services
        self.stt_service = STTService()
        self.rag_engine = LocalRAGEngine()
        self.insight_engine = InsightEngine()
        self.recorder = AudioRecorder(amplitude_callback=self._on_audio_amplitude)

        self.current_audio_file: Optional[str] = None
        self.generated_docs: Dict[str, str] = {}
        self.active_worker: Optional[QThread] = None

        # Timer for recording clock
        self.record_timer = QTimer(self)
        self.record_timer.timeout.connect(self._update_record_clock)

        self._init_ui()
        self._check_api_keys()

    def _init_ui(self):
        """Construct UI layout and widgets."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # 1. Top Header Bar
        header_bar = self._build_header_bar()
        main_layout.addLayout(header_bar)

        # 2. Main 3-Pane Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Pane: Audio Capture & STT
        left_pane = self._build_audio_panel()
        splitter.addWidget(left_pane)

        # Center Pane: Transcript & RAG Grounding
        center_pane = self._build_transcript_rag_panel()
        splitter.addWidget(center_pane)

        # Right Pane: Insight Blueprint Generator & Document Tabs
        right_pane = self._build_blueprint_panel()
        splitter.addWidget(right_pane)

        splitter.setSizes([360, 420, 570])
        main_layout.addWidget(splitter, 1)

        # 3. Status Bar & Progress
        status_bar_layout = QHBoxLayout()
        self.status_label = QLabel("Ready.")
        self.status_label.setStyleSheet("color: #718096; font-size: 12px;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)

        status_bar_layout.addWidget(self.status_label, 1)
        status_bar_layout.addWidget(self.progress_bar)
        main_layout.addLayout(status_bar_layout)

    def _build_header_bar(self) -> QHBoxLayout:
        """Top application status and settings header."""
        layout = QHBoxLayout()

        title_label = QLabel("⚡ VoGenFlow: Voice-based Generative AI for Workflows")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #63b3ed;")

        # Provider Selector
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Groq Cloud (Fast LPU)", "Ollama (Local LLM)"])
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        # API Key Config Button
        self.api_key_btn = QPushButton("🔑 Set Groq API Key")
        self.api_key_btn.clicked.connect(self._prompt_api_key)

        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(QLabel("Engine:"))
        layout.addWidget(self.provider_combo)
        layout.addWidget(self.api_key_btn)

        return layout

    def _build_audio_panel(self) -> QWidget:
        """Left panel for recording and audio file management."""
        panel = QGroupBox("1. Audio Input (Mic / File)")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # Live Recording Visualizer
        self.visualizer = AudioVisualizer(num_bars=28)
        layout.addWidget(self.visualizer)

        # Record Timer Label
        self.record_time_label = QLabel("00:00.0")
        self.record_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.record_time_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #e2e8f0;")
        layout.addWidget(self.record_time_label)

        # Record Action Buttons
        btn_layout = QHBoxLayout()
        self.record_btn = QPushButton("🎙️ Start Recording")
        self.record_btn.setStyleSheet("background-color: #2b6cb0; font-weight: bold; padding: 8px;")
        self.record_btn.clicked.connect(self._toggle_recording)

        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._toggle_pause)

        btn_layout.addWidget(self.record_btn)
        btn_layout.addWidget(self.pause_btn)
        layout.addLayout(btn_layout)

        # Drag and Drop Zone
        layout.addWidget(QLabel("Or upload audio file:"))
        self.drop_zone = DropZoneWidget()
        self.drop_zone.file_dropped.connect(self._on_file_selected)
        layout.addWidget(self.drop_zone)

        # File Select Button
        self.select_file_btn = QPushButton("📂 Browse Audio File...")
        self.select_file_btn.clicked.connect(self._browse_audio_file)
        layout.addWidget(self.select_file_btn)

        # Current File Label
        self.selected_file_label = QLabel("No audio selected.")
        self.selected_file_label.setWordWrap(True)
        self.selected_file_label.setStyleSheet("color: #a0aec0; font-size: 11px;")
        layout.addWidget(self.selected_file_label)

        # STT Model Selection
        stt_layout = QHBoxLayout()
        stt_layout.addWidget(QLabel("STT Model:"))
        self.stt_model_combo = QComboBox()
        self.stt_model_combo.addItems(["whisper-large-v3-turbo", "whisper-large-v3"])
        stt_layout.addWidget(self.stt_model_combo)
        layout.addLayout(stt_layout)

        # Transcribe Button
        self.transcribe_btn = QPushButton("⚡ Transcribe Audio to Text")
        self.transcribe_btn.setStyleSheet("background-color: #2c5282; font-weight: bold; padding: 10px;")
        self.transcribe_btn.clicked.connect(self._run_transcription)
        layout.addWidget(self.transcribe_btn)

        layout.addStretch()
        return panel

    def _build_transcript_rag_panel(self) -> QWidget:
        """Center panel for transcript display and RAG codebase indexing."""
        panel = QGroupBox("2. Spoken Transcript & RAG Grounding")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # Transcript text area
        layout.addWidget(QLabel("Recognized Speech / Prompt:"))
        self.transcript_edit = QTextEdit()
        self.transcript_edit.setPlaceholderText(
            "Spoken words will appear here automatically...\nYou can also manually edit or type your brain-dump here."
        )
        layout.addWidget(self.transcript_edit, 2)

        # Character / word count label
        self.transcript_meta_label = QLabel("Words: 0 | Latency: 0.0s")
        self.transcript_meta_label.setStyleSheet("color: #718096; font-size: 11px;")
        layout.addWidget(self.transcript_meta_label)
        self.transcript_edit.textChanged.connect(self._update_transcript_word_count)

        # RAG Grounding Section
        rag_box = QGroupBox("Context Grounding (RAG)")
        rag_layout = QVBoxLayout(rag_box)

        self.use_rag_checkbox = QCheckBox("Enable RAG Grounding with Local Codebase / Docs")
        self.use_rag_checkbox.setChecked(True)
        rag_layout.addWidget(self.use_rag_checkbox)

        rag_btn_layout = QHBoxLayout()
        self.index_repo_btn = QPushButton("📁 Index Target Codebase...")
        self.index_repo_btn.clicked.connect(self._index_codebase_dir)
        self.rag_status_label = QLabel("0 chunks indexed")
        self.rag_status_label.setStyleSheet("color: #a0aec0; font-size: 11px;")

        rag_btn_layout.addWidget(self.index_repo_btn)
        rag_btn_layout.addWidget(self.rag_status_label)
        rag_layout.addLayout(rag_btn_layout)

        layout.addWidget(rag_box, 1)
        return panel

    def _build_blueprint_panel(self) -> QWidget:
        """Right panel with blueprint generation tabs and export tools."""
        panel = QGroupBox("3. Generated Project Blueprints & Insights")
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        # Action Buttons
        action_layout = QHBoxLayout()
        self.gen_all_btn = QPushButton("🚀 Generate All Blueprints")
        self.gen_all_btn.setStyleSheet("background-color: #276749; font-weight: bold; padding: 8px;")
        self.gen_all_btn.clicked.connect(lambda: self._run_generation("all"))

        self.gen_tab_btn = QPushButton("📄 Generate Active Tab Only")
        self.gen_tab_btn.clicked.connect(self._generate_active_tab)

        action_layout.addWidget(self.gen_all_btn)
        action_layout.addWidget(self.gen_tab_btn)
        layout.addLayout(action_layout)

        # Document Tabs
        self.tabs = QTabWidget()
        self.doc_views: Dict[str, QTextEdit] = {}

        tab_specs = [
            ("PRD.md", "prd.md"),
            ("Architecture.md", "architecture.md"),
            ("Flow.md", "flow.md"),
            ("Tech Stack.md", "tech_stack.md"),
            ("Tasks.md", "tasks.md"),
            ("Implementation Plan.md", "implementation_plan.md"),
        ]

        for label, filename in tab_specs:
            text_view = QTextEdit()
            text_view.setPlaceholderText(f"{label} will be generated here...")
            text_view.setFont(QFont("Consolas", 10))
            self.doc_views[filename] = text_view
            self.tabs.addTab(text_view, label)

        layout.addWidget(self.tabs, 1)

        # Export Buttons
        export_layout = QHBoxLayout()
        self.export_repo_btn = QPushButton("💾 Export All to Repository...")
        self.export_repo_btn.setStyleSheet("background-color: #4a5568; padding: 6px;")
        self.export_repo_btn.clicked.connect(self._export_to_directory)

        self.export_pdf_btn = QPushButton("📑 Export Combined PDF...")
        self.export_pdf_btn.setStyleSheet("background-color: #4a5568; padding: 6px;")
        self.export_pdf_btn.clicked.connect(self._generate_pdf_report)

        export_layout.addWidget(self.export_repo_btn)
        export_layout.addWidget(self.export_pdf_btn)
        layout.addLayout(export_layout)

        return panel

    # -------------------------------------------------------------
    # Audio Recording Handlers
    # -------------------------------------------------------------
    def _toggle_recording(self):
        if not self.recorder.is_recording and not self.recorder.is_paused:
            # Start recording
            try:
                self.recorder.start()
                self.record_timer.start(100)
                self.visualizer.reset()
                self.record_btn.setText("🛑 Stop Recording")
                self.record_btn.setStyleSheet("background-color: #9b2c2c; font-weight: bold; padding: 8px;")
                self.pause_btn.setEnabled(True)
                self.status_label.setText("Recording audio from microphone...")
            except Exception as e:
                QMessageBox.critical(self, "Recording Error", f"Failed to start recording: {e}")
        else:
            # Stop recording
            self.recorder.stop()
            self.record_timer.stop()
            self.visualizer.reset()
            self.record_btn.setText("🎙️ Start Recording")
            self.record_btn.setStyleSheet("background-color: #2b6cb0; font-weight: bold; padding: 8px;")
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸️ Pause")

            try:
                saved_path = self.recorder.save_wav()
                self.current_audio_file = saved_path
                self.selected_file_label.setText(f"Recorded: {Path(saved_path).name}")
                self.status_label.setText("Recording saved. Ready to transcribe.")
            except Exception as e:
                QMessageBox.warning(self, "Save Error", f"Could not save recorded audio: {e}")

    def _toggle_pause(self):
        if self.recorder.is_paused:
            self.recorder.resume()
            self.pause_btn.setText("⏸️ Pause")
            self.status_label.setText("Recording resumed...")
        else:
            self.recorder.pause()
            self.pause_btn.setText("▶️ Resume")
            self.status_label.setText("Recording paused.")

    def _update_record_clock(self):
        duration = self.recorder.get_duration()
        mins = int(duration // 60)
        secs = duration % 60
        self.record_time_label.setText(f"{mins:02d}:{secs:04.1f}")

    def _on_audio_amplitude(self, level: float):
        self.visualizer.set_level(level)

    def _browse_audio_file(self):
        file_filter = "Audio Files (*.wav *.mp3 *.m4a *.ogg *.flac *.webm *.mp4)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", file_filter)
        if file_path:
            self._on_file_selected(file_path)

    def _on_file_selected(self, file_path: str):
        self.current_audio_file = file_path
        self.selected_file_label.setText(f"File: {Path(file_path).name}")
        self.status_label.setText(f"Loaded {Path(file_path).name}")

    # -------------------------------------------------------------
    # Transcription Handlers
    # -------------------------------------------------------------
    def _run_transcription(self):
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            QMessageBox.warning(
                self, "No Audio File", "Please record audio or select an audio file first."
            )
            return

        if not has_groq_key() and self.provider_combo.currentIndex() == 0:
            self._prompt_api_key()
            if not has_groq_key():
                return

        model = self.stt_model_combo.currentText()
        self.transcribe_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Transcribing speech via Groq Whisper...")

        self.active_worker = TranscriptionWorker(self.stt_service, self.current_audio_file, model)
        self.active_worker.signals.finished.connect(self._on_transcription_success)
        self.active_worker.signals.error.connect(self._on_transcription_error)
        self.active_worker.start()

    def _on_transcription_success(self, result: STTResult):
        self.transcribe_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.transcript_edit.setPlainText(result.text)
        self.status_label.setText(f"Transcription completed in {result.latency_seconds:.2f}s!")
        self.transcript_meta_label.setText(
            f"Words: {len(result.text.split())} | Duration: {result.duration_seconds:.1f}s | Latency: {result.latency_seconds:.2f}s"
        )

    def _on_transcription_error(self, err_msg: str):
        self.transcribe_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Transcription failed.")
        QMessageBox.critical(self, "Transcription Error", f"Error during transcription:\n{err_msg}")

    def _update_transcript_word_count(self):
        words = len(self.transcript_edit.toPlainText().split())
        self.transcript_meta_label.setText(f"Words: {words}")

    # -------------------------------------------------------------
    # RAG Indexing Handlers
    # -------------------------------------------------------------
    def _index_codebase_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Codebase Directory to Index for RAG")
        if dir_path:
            count = self.rag_engine.index_directory(dir_path)
            total_chunks = len(self.rag_engine.chunks)
            self.rag_status_label.setText(f"{total_chunks} chunks ({count} files)")
            self.status_label.setText(f"RAG indexed {count} files from {Path(dir_path).name}")
            QMessageBox.information(
                self, "RAG Indexing", f"Successfully indexed {count} files ({total_chunks} chunks) for grounded generation!"
            )

    # -------------------------------------------------------------
    # Insight & Blueprint Generation Handlers
    # -------------------------------------------------------------
    def _generate_active_tab(self):
        current_index = self.tabs.currentIndex()
        tab_text = self.tabs.tabText(current_index)
        mapping = {
            "PRD.md": "prd.md",
            "Architecture.md": "architecture.md",
            "Flow.md": "flow.md",
            "Tech Stack.md": "tech_stack.md",
            "Tasks.md": "tasks.md",
            "Implementation Plan.md": "implementation_plan.md",
        }
        doc_type = mapping.get(tab_text, "prd.md")
        self._run_generation(doc_type)

    def _run_generation(self, doc_type: str = "all"):
        transcript = self.transcript_edit.toPlainText().strip()
        if not transcript:
            QMessageBox.warning(
                self, "Empty Transcript", "Please transcribe audio or enter text into the transcript area."
            )
            return

        # Prepare RAG context if enabled
        rag_context = ""
        if self.use_rag_checkbox.isChecked() and self.rag_engine.chunks:
            rag_context = self.rag_engine.retrieve_grounded_context(transcript)

        self.gen_all_btn.setEnabled(False)
        self.gen_tab_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Generating technical blueprints with LLM...")

        self.active_worker = InsightGenerationWorker(
            self.insight_engine, transcript, rag_context, doc_type
        )
        self.active_worker.signals.finished.connect(self._on_generation_success)
        self.active_worker.signals.error.connect(self._on_generation_error)
        self.active_worker.start()

    def _on_generation_success(self, results: Dict[str, str]):
        self.gen_all_btn.setEnabled(True)
        self.gen_tab_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Blueprints generated successfully!")

        for filename, content in results.items():
            self.generated_docs[filename] = content
            if filename in self.doc_views:
                self.doc_views[filename].setPlainText(content)

    def _on_generation_error(self, err_msg: str):
        self.gen_all_btn.setEnabled(True)
        self.gen_tab_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Generation error.")
        QMessageBox.critical(self, "Generation Error", f"Error generating insights:\n{err_msg}")

    # -------------------------------------------------------------
    # Export & PDF Handlers
    # -------------------------------------------------------------
    def _export_to_directory(self):
        docs_to_export = {}
        for filename, view in self.doc_views.items():
            content = view.toPlainText().strip()
            if content:
                docs_to_export[filename] = content

        if not docs_to_export:
            QMessageBox.warning(self, "No Content", "No generated documents to export.")
            return

        target_dir = QFileDialog.getExistingDirectory(self, "Select Target Repository Folder")
        if target_dir:
            saved = ExportService.export_documents(docs_to_export, target_dir)
            QMessageBox.information(
                self, "Export Complete", f"Exported {len(saved)} blueprint documents to:\n{target_dir}"
            )

    def _generate_pdf_report(self):
        from docs.generate_pdf_documentation import generate_master_pdf
        pdf_path = str(OUTPUT_DIR / "Voice_Insights_Master_Documentation.pdf")
        try:
            generate_master_pdf(output_pdf_path=pdf_path)
            QMessageBox.information(
                self, "PDF Generated", f"Master Documentation PDF created at:\n{pdf_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"Failed to compile PDF: {e}")

    # -------------------------------------------------------------
    # Settings & API Keys
    # -------------------------------------------------------------
    def _on_provider_changed(self, index: int):
        if index == 0:
            self.insight_engine.provider = "groq"
            self.insight_engine.model = DEFAULT_GROQ_LLM_MODEL
            self.stt_service.provider_name = "groq"
        else:
            self.insight_engine.provider = "ollama"
            self.insight_engine.model = DEFAULT_OLLAMA_MODEL

    def _check_api_keys(self):
        if not has_groq_key():
            self.status_label.setText("⚠️ Groq API Key not detected. Click 'Set Groq API Key' to configure.")

    def _prompt_api_key(self):
        key, ok = QInputDialog.getText(
            self,
            "Groq API Key Configuration",
            "Enter your Groq API Key (from console.groq.com):",
            QLineEdit.EchoMode.Password,
            GROQ_API_KEY,
        )
        if ok and key.strip():
            self.stt_service.set_api_key(key.strip())
            self.insight_engine.set_api_key(key.strip())
            self.status_label.setText("Groq API Key configured.")


def run_gui():
    """Launch the PyQt6 Application."""
    app = QApplication(sys.argv)
    try:
        import qdarktheme
        app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    except Exception:
        pass

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
