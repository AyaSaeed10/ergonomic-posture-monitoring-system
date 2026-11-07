"""
Glow background - the dark (or light) background with big soft color glows,
painted behind every screen.

PyQt has no live blur, so instead of blurring we paint each glow as a
"radial gradient": a circle of color that fades smoothly to transparent
towards its edge. Several of them on top of each other look like blurred
light. The colors and positions come from styles.py (the GLOWS list).
"""

import math

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QColor, QPainter, QRadialGradient
from PyQt5.QtWidgets import QWidget

from user_app.ui import styles

# How strong each glow is from its center (0) to its edge (1).
# This follows a bell curve (like a real blur), so there is no visible edge.
FADE_STEPS = [(t / 10, math.exp(-4.5 * (t / 10) ** 2)) for t in range(11)]


class GlowBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # repaint with the new colors whenever the theme changes
        styles.theme.changed.connect(lambda _: self.update())

    def paintEvent(self, event):
        colors = styles.theme.colors
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(colors["BACKGROUND"]))

        w, h = self.width(), self.height()
        size = max(w, h)
        painter.setPen(QColor(0, 0, 0, 0))   # no outline around the glows
        for glow in colors["GLOWS"]:
            center = QPointF(glow["x"] * w, glow["y"] * h)
            radius = glow["radius"] * size
            r, g, b, opacity = glow["color"]

            gradient = QRadialGradient(center, radius)
            for position, strength in FADE_STEPS:
                alpha = round(opacity * strength * 255) if position < 1 else 0
                gradient.setColorAt(position, QColor(r, g, b, alpha))
            painter.setBrush(gradient)
            painter.drawEllipse(center, radius, radius)
