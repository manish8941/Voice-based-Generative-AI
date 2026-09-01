"""
Unit Tests for Audio Recorder and Buffer Management
"""

import time
import unittest
import numpy as np
from src.audio_recorder import AudioRecorder


class TestAudioRecorder(unittest.TestCase):

    def test_recorder_initialization(self):
        rec = AudioRecorder(sample_rate=16000, channels=1)
        self.assertFalse(rec.is_recording)
        self.assertFalse(rec.is_paused)
        self.assertEqual(rec.sample_rate, 16000)
        self.assertEqual(rec.channels, 1)

    def test_audio_callback_and_rms_calculation(self):
        amplitude_values = []

        def on_amplitude(level: float):
            amplitude_values.append(level)

        rec = AudioRecorder(amplitude_callback=on_amplitude)
        rec._is_recording = True

        # Simulate 1024 audio samples
        synthetic_audio = np.full((1024, 1), fill_value=1000, dtype=np.int16)
        rec._audio_callback(synthetic_audio, 1024, None, None)

        self.assertEqual(len(rec._frames), 1)
        self.assertTrue(len(amplitude_values) > 0)
        self.assertTrue(amplitude_values[0] > 0.0)


if __name__ == "__main__":
    unittest.main()
