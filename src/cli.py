"""
CLI Module for Voice-to-Insight System
Allows running live recording, transcription, RAG indexing, and blueprint generation directly from terminal.
"""

import argparse
import sys
import time
from pathlib import Path

from src.audio_recorder import AudioRecorder
from src.config import OUTPUT_DIR, has_groq_key
from src.export_service import ExportService
from src.insight_engine import InsightEngine
from src.rag_engine import LocalRAGEngine
from src.stt_service import STTService


def main():
    parser = argparse.ArgumentParser(
        description="Voice-to-Insight: Speech-to-Text & Technical Blueprint CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available sub-commands")

    # Command: record
    rec_parser = subparsers.add_parser("record", help="Record audio from microphone and save to WAV")
    rec_parser.add_argument(
        "--duration", "-d", type=float, default=10.0, help="Duration in seconds (default: 10s)"
    )
    rec_parser.add_argument(
        "--output", "-o", type=str, default=None, help="Output WAV file path"
    )

    # Command: transcribe
    trans_parser = subparsers.add_parser("transcribe", help="Transcribe audio file via Groq Whisper")
    trans_parser.add_argument("audio_path", type=str, help="Path to audio file (.wav, .mp3, .m4a)")
    trans_parser.add_argument(
        "--model", "-m", type=str, default="whisper-large-v3-turbo", help="Whisper model"
    )

    # Command: generate
    gen_parser = subparsers.add_parser(
        "generate", help="Generate PRD, Architecture, Tasks and Blueprints from transcript"
    )
    gen_parser.add_argument(
        "--input", "-i", type=str, help="Path to text transcript file or raw audio file"
    )
    gen_parser.add_argument(
        "--text", "-t", type=str, help="Direct text prompt / transcript string"
    )
    gen_parser.add_argument(
        "--rag-dir", "-r", type=str, default=None, help="Target codebase to index for RAG context"
    )
    gen_parser.add_argument(
        "--export-dir", "-e", type=str, default=str(OUTPUT_DIR), help="Output directory for generated docs"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "record":
        print(f"🎙️ Recording microphone for {args.duration} seconds...")
        rec = AudioRecorder()
        rec.start()
        time.sleep(args.duration)
        rec.stop()
        saved = rec.save_wav(args.output)
        print(f"✅ Audio recorded and saved to: {saved}")

    elif args.command == "transcribe":
        if not has_groq_key():
            print("❌ Error: GROQ_API_KEY environment variable is not set.")
            sys.exit(1)
        stt = STTService()
        print(f"⚡ Transcribing {args.audio_path} using {args.model}...")
        result = stt.transcribe_file(args.audio_path, model=args.model)
        print("\n" + "=" * 50)
        print(f"Transcript ({result.latency_seconds:.2f}s):")
        print("=" * 50)
        print(result.text)

    elif args.command == "generate":
        transcript = ""
        if args.text:
            transcript = args.text
        elif args.input:
            input_path = Path(args.input)
            if input_path.suffix.lower() in STTService.get_supported_formats():
                print(f"⚡ Transcribing audio input {input_path}...")
                stt = STTService()
                result = stt.transcribe_file(str(input_path))
                transcript = result.text
            else:
                with open(input_path, "r", encoding="utf-8") as f:
                    transcript = f.read()

        if not transcript.strip():
            print("❌ Error: No transcript provided via --text or --input.")
            sys.exit(1)

        rag_context = ""
        if args.rag_dir:
            print(f"📁 Indexing codebase for RAG context: {args.rag_dir}...")
            rag = LocalRAGEngine()
            count = rag.index_directory(args.rag_dir)
            print(f"Indexed {count} files ({len(rag.chunks)} chunks).")
            rag_context = rag.retrieve_grounded_context(transcript)

        print("🚀 Generating full engineering blueprint suite...")
        engine = InsightEngine()
        docs = engine.generate_all(transcript, rag_context)

        saved = ExportService.export_documents(docs, args.export_dir)
        print(f"\n✅ Generated {len(saved)} blueprint documents:")
        for s in saved:
            print(f"  - {s}")


if __name__ == "__main__":
    main()
