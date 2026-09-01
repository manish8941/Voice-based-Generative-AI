"""
Unit Tests for STT Service and Data Structures
"""

import unittest
from src.stt_service import STTResult, STTService


class TestSTTService(unittest.TestCase):

    def test_stt_result_model(self):
        result = STTResult(
            text="Hello world test",
            duration_seconds=5.2,
            latency_seconds=0.34,
            language="en",
            segments=[{"id": 0, "text": "Hello world"}],
            provider="groq",
            model="whisper-large-v3-turbo",
        )
        self.assertEqual(result.text, "Hello world test")
        self.assertEqual(result.latency_seconds, 0.34)
        d = result.to_dict()
        self.assertEqual(d["provider"], "groq")
        self.assertEqual(d["segments_count"], 1)

    def test_supported_formats(self):
        formats = STTService.get_supported_formats()
        self.assertIn(".wav", formats)
        self.assertIn(".mp3", formats)
        self.assertIn(".m4a", formats)
        self.assertIn(".flac", formats)


if __name__ == "__main__":
    unittest.main()
