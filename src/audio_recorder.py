"""
Audio Recorder Module
Provides thread-safe live audio recording via sounddevice, real-time amplitude metrics for UI visualization,
and WAV serialization for downstream STT pipelines.
"""

import io
import time
import wave
import threading
from typing import Callable, Optional
import numpy as np
import sounddevice as sd

from src.config import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, TEMP_AUDIO_DIR


class AudioRecorder:
    """Thread-safe live audio recorder with real-time amplitude callbacks."""

    def __init__(
        self,
        sample_rate: int = AUDIO_SAMPLE_RATE,
        channels: int = AUDIO_CHANNELS,
        amplitude_callback: Optional[Callable[[float], None]] = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.amplitude_callback = amplitude_callback

        self._frames: list[np.ndarray] = []
        self._is_recording = False
        self._is_paused = False
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._elapsed_time: float = 0.0

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._is_recording and not self._is_paused

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self._is_paused

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Internal callback invoked by sounddevice for each audio buffer."""
        if status:
            pass  # Overflow or underflow handling if needed

        with self._lock:
            if not self._is_recording or self._is_paused:
                return
            # Store audio chunk
            self._frames.append(indata.copy())

        # Calculate Root Mean Square (RMS) amplitude for UI visualizer
        if self.amplitude_callback:
            rms = float(np.sqrt(np.mean(indata**2)))
            # Normalize to approximate 0.0 - 1.0 range
            normalized = min(1.0, rms * 10.0)
            try:
                self.amplitude_callback(normalized)
            except Exception:
                pass

    def start(self):
        """Start or restart recording from default microphone."""
        with self._lock:
            if self._is_recording:
                return
            self._frames = []
            self._is_recording = True
            self._is_paused = False
            self._start_time = time.time()
            self._elapsed_time = 0.0

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=self._audio_callback,
            )
            self._stream.start()

    def pause(self):
        """Pause active recording."""
        with self._lock:
            if self._is_recording and not self._is_paused:
                self._is_paused = True
                self._elapsed_time += time.time() - self._start_time

    def resume(self):
        """Resume paused recording."""
        with self._lock:
            if self._is_recording and self._is_paused:
                self._is_paused = False
                self._start_time = time.time()

    def stop(self) -> Optional[np.ndarray]:
        """Stop recording and return the concatenated audio data."""
        with self._lock:
            if not self._is_recording:
                return None
            self._is_recording = False
            self._is_paused = False

            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

            if not self._frames:
                return None

            full_audio = np.concatenate(self._frames, axis=0)
            return full_audio

    def get_duration(self) -> float:
        """Get the current recorded duration in seconds."""
        with self._lock:
            if not self._is_recording:
                return self._elapsed_time
            if self._is_paused:
                return self._elapsed_time
            return self._elapsed_time + (time.time() - self._start_time)

    def save_wav(self, file_path: Optional[str] = None) -> str:
        """Save recorded audio frames to a 16-bit PCM WAV file."""
        with self._lock:
            if not self._frames:
                raise ValueError("No recorded audio frames to save.")
            data = np.concatenate(self._frames, axis=0)

        if file_path is None:
            filename = f"recording_{int(time.time())}.wav"
            file_path = str(TEMP_AUDIO_DIR / filename)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit integer = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(data.tobytes())

        return file_path

    def get_wav_bytes(self) -> bytes:
        """Return recorded audio directly as WAV-formatted bytes in memory."""
        with self._lock:
            if not self._frames:
                raise ValueError("No recorded audio frames.")
            data = np.concatenate(self._frames, axis=0)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(data.tobytes())

        return buf.getvalue()
