"""
Speech-to-Text (STT) Service Module
Supports fast cloud transcription via Groq Whisper API (whisper-large-v3 / turbo)
with a pluggable provider interface for local Whisper or alternate providers.
"""

import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Union
from groq import Groq

from src.config import (
    GROQ_API_KEY,
    DEFAULT_GROQ_STT_MODEL,
    has_groq_key,
)


class STTResult:
    """Standardized Speech-to-Text output data structure."""

    def __init__(
        self,
        text: str,
        duration_seconds: float = 0.0,
        latency_seconds: float = 0.0,
        language: str = "en",
        segments: Optional[list] = None,
        provider: str = "groq",
        model: str = DEFAULT_GROQ_STT_MODEL,
    ):
        self.text = text.strip()
        self.duration_seconds = duration_seconds
        self.latency_seconds = latency_seconds
        self.language = language
        self.segments = segments or []
        self.provider = provider
        self.model = model

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "duration_seconds": self.duration_seconds,
            "latency_seconds": self.latency_seconds,
            "language": self.language,
            "segments_count": len(self.segments),
            "provider": self.provider,
            "model": self.model,
        }

    def __repr__(self) -> str:
        return f"<STTResult ({self.provider}/{self.model}) text_len={len(self.text)} latency={self.latency_seconds:.2f}s>"


class BaseSTTProvider(ABC):
    """Abstract Base Class for STT Providers."""

    @abstractmethod
    def transcribe(self, audio_file_path: str, model: Optional[str] = None, **kwargs) -> STTResult:
        """Transcribe an audio file to text."""
        pass


class GroqWhisperProvider(BaseSTTProvider):
    """Groq Cloud LPU Accelerated Whisper STT Provider."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GROQ_API_KEY
        self._client: Optional[Groq] = None

    @property
    def client(self) -> Groq:
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "Groq API Key is missing. Please set GROQ_API_KEY in .env or pass it to STTService."
                )
            self._client = Groq(api_key=self.api_key)
        return self._client

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self._client = None  # Reset client to recreate with new key

    def transcribe(
        self,
        audio_file_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        **kwargs,
    ) -> STTResult:
        """Transcribe audio file using Groq Whisper API."""
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        chosen_model = model or DEFAULT_GROQ_STT_MODEL
        start_time = time.time()

        with open(audio_file_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                file=(Path(audio_file_path).name, audio_file.read()),
                model=chosen_model,
                response_format="verbose_json",
                language=language,
                prompt=prompt,
                temperature=0.0,
            )

        latency = time.time() - start_time

        # Extract text and metadata
        transcript_text = getattr(response, "text", "")
        detected_language = getattr(response, "language", language or "en")
        duration = getattr(response, "duration", 0.0)
        segments = getattr(response, "segments", [])

        return STTResult(
            text=transcript_text,
            duration_seconds=float(duration) if duration else 0.0,
            latency_seconds=latency,
            language=detected_language,
            segments=segments,
            provider="groq",
            model=chosen_model,
        )


class STTService:
    """Unified Facade for Speech-to-Text operations."""

    def __init__(self, provider: str = "groq", api_key: Optional[str] = None):
        self.provider_name = provider.lower()
        self.api_key = api_key or GROQ_API_KEY
        self._groq_provider = GroqWhisperProvider(api_key=self.api_key)

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        self._groq_provider.set_api_key(api_key)

    def transcribe_file(
        self,
        audio_path: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        context_prompt: Optional[str] = None,
    ) -> STTResult:
        """Transcribe a given audio file path."""
        if self.provider_name == "groq":
            return self._groq_provider.transcribe(
                audio_path, model=model, language=language, prompt=context_prompt
            )
        else:
            # Fallback to groq provider by default
            return self._groq_provider.transcribe(
                audio_path, model=model, language=language, prompt=context_prompt
            )

    @staticmethod
    def get_supported_formats() -> list[str]:
        return [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".mp4", ".mpeg", ".mpga"]
