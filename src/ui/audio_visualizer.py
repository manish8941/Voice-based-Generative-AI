"""
Audio Visualizer Widget for PyQt6
Renders dynamic real-time audio volume bars and waveform pulses during live microphone recording.
"""

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QLinearGradient
from PyQt6.QtWidgets import QWidget


class AudioVisualizer(QWidget):
    """Real-time audio visualizer widget displaying multi-bar amplitude levels."""

    def __init__(self, num_bars: int = 24, parent=None):
        super().__init__(parent)
        self.num_bars = num_bars
        self.levels = [0.0] * num_bars
        self.target_level = 0.0
        self.is_active = False

        self.setMinimumHeight(48)
        self.setMaximumHeight(80)

        # Decay timer for smooth falling bars
        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self._update_decay)
        self.decay_timer.start(30)

    def set_level(self, normalized_level: float):
        """Update current audio amplitude (0.0 to 1.0)."""
        self.target_level = max(0.0, min(1.0, normalized_level))
        self.is_active = True

    def reset(self):
        """Reset visualizer levels to zero."""
        self.is_active = False
        self.target_level = 0.0
        self.levels = [0.0] * self.num_bars
        self.update()

    def _update_decay(self):
        """Smooth animation step."""
        import random

        if not self.is_active:
            # Gradually drop all bars to 0
            for i in range(self.num_bars):
                self.levels[i] = max(0.0, self.levels[i] - 0.05)
            self.update()
            return

        # Distribute the target level across bars with realistic sound frequency variations
        center = self.num_bars // 2
        for i in range(self.num_bars):
            dist_from_center = abs(i - center) / (self.num_bars / 2)
            bell_factor = max(0.2, 1.0 - (dist_from_center * 0.7))
            jitter = random.uniform(0.7, 1.3)
            bar_target = self.target_level * bell_factor * jitter
            bar_target = max(0.05, min(1.0, bar_target))

            # Smooth interpolation
            self.levels[i] += (bar_target - self.levels[i]) * 0.35

        self.update()

    def paintEvent(self, event):
        """Paint the animated waveform bars."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Background
        painter.fillRect(self.rect(), QColor(20, 24, 30))

        if width <= 0 or height <= 0:
            return

        bar_width = (width / self.num_bars) * 0.7
        gap = (width / self.num_bars) * 0.3

        gradient = QLinearGradient(0, height, 0, 0)
        gradient.setColorAt(0.0, QColor(41, 128, 185))   # Blue
        gradient.setColorAt(0.5, QColor(46, 204, 113))   # Green
        gradient.setColorAt(1.0, QColor(231, 76, 60))    # Red on peak

        brush = QBrush(gradient)
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(self.num_bars):
            bar_h = max(4.0, self.levels[i] * (height - 8))
            x = i * (bar_width + gap) + gap / 2
            y = (height - bar_h) / 2.0

            rect = QRectF(x, y, bar_width, bar_h)
            painter.drawRoundedRect(rect, 3.0, 3.0)
