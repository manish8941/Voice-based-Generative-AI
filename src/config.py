"""
Configuration Module for Voice-to-Insight System.
Manages environment variables, default model identifiers, audio sampling constants, and storage paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DOCS_DIR = BASE_DIR / "docs"
TEMP_AUDIO_DIR = BASE_DIR / "temp_audio"

# Ensure runtime directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# API Keys & Endpoints
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# STT Configuration
DEFAULT_STT_PROVIDER = os.getenv("DEFAULT_STT_PROVIDER", "groq")  # 'groq' | 'local'
DEFAULT_GROQ_STT_MODEL = os.getenv("DEFAULT_GROQ_STT_MODEL", "whisper-large-v3-turbo")
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
AUDIO_CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))
AUDIO_CHUNK_SIZE = int(os.getenv("AUDIO_CHUNK_SIZE", "1024"))

# LLM / Insight Generation Configuration
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "groq")  # 'groq' | 'ollama'
DEFAULT_GROQ_LLM_MODEL = os.getenv("DEFAULT_GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
DEFAULT_OLLAMA_MODEL = os.getenv("DEFAULT_OLLAMA_MODEL", "llama3.2:latest")

# RAG Configuration
DEFAULT_RAG_TOP_K = int(os.getenv("DEFAULT_RAG_TOP_K", "4"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

def has_groq_key() -> bool:
    """Check if a valid Groq API key is present."""
    key = os.getenv("GROQ_API_KEY", "")
    return bool(key and key.strip() and not key.startswith("your_"))
