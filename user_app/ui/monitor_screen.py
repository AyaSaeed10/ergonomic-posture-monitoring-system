"""
Monitor screen - FRONTEND (home screen after login).

Ready state (for now): a camera placeholder on the left and the setup
checklist on the right, with the Start Monitoring button.
The checklist shows a fixed state for now; the real camera, skeleton and
checklist logic will be added with the real pipeline.

Run this screen alone (from the project root):
    python -m user_app.ui.monitor_screen
"""

import sys

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from user_app.ui import styles
from user_app.ui.widgets.glow_background import GlowBackground

ICONS = {"ok": "✓", "fail": "!", "wait": "…"}


# =====================================================================
# One row of the checklist: [icon]  Title
#                                   detail text
# =====================================================================
class CheckRow(QWidget):
    def __init__(self, title):
        super().__init__()
        self.icon = QLabel(objectName="CheckIcon", alignment=Qt.AlignCenter)
        self.icon.setFixedSize(26, 26)
        self.detail = QLabel(objectName="CheckDetail")

        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(QLabel(title, objectName="CheckTitle"))
        text.addWidget(self.detail)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        row.addWidget(self.icon, 0, Qt.AlignTop)
        row.addLayout(text, 1)

    def set_state(self, state, detail):
        """state: "ok", "fail" or "wait" (changes the icon's color via QSS)."""
        self.icon.setText(ICONS[state])
        self.icon.setProperty("state", state)
        self.icon.style().unpolish(self.icon)
        self.icon.style().polish(self.icon)
        self.detail.setText(detail)


# =====================================================================
# The screen
# =====================================================================
class MonitorScreen(QWidget):
    start_requested = pyqtSignal()   # sent when "Start Monitoring" is clicked

    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui()

    # ------------------------------------------------------------ layout
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(20)
        root.addWidget(self._build_camera_card(), 1)
        root.addWidget(self._build_checklist_panel())

    def _build_camera_card(self):
        card = QFrame(objectName="GlassPanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(4)
        layout.addWidget(QLabel("Camera setup", objectName="PanelTitle"))
        layout.addWidget(QLabel("Sit as you normally work. Place the camera at your side, 1.5–2 m away.",
                                objectName="PanelSubtitle", wordWrap=True))
        layout.addSpacing(14)
        # placeholder until the real camera is connected
        layout.addWidget(QLabel("Camera preview", objectName="CameraPlaceholder",
                                alignment=Qt.AlignCenter), 1)
        return card

    def _build_checklist_panel(self):
        panel = QFrame(objectName="GlassPanel")
        panel.setFixedWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(26, 22, 26, 26)
        layout.setSpacing(4)
        layout.addWidget(QLabel("Setup checklist", objectName="PanelTitle"))
        layout.addWidget(QLabel("All checks must pass before monitoring starts.",
                                objectName="PanelSubtitle", wordWrap=True))
        layout.addSpacing(22)

        # fixed state for now - the real checks come with the real pipeline
        self.rows = {
            "camera": CheckRow("Camera connected"),
            "side": CheckRow("Side view detected"),
            "distance": CheckRow("Distance 1.5–2 m"),
            "body": CheckRow("Ear, shoulder, hip, knee visible"),
        }
        for row in self.rows.values():
            row.set_state("ok", "Ready")
            layout.addWidget(row)
            layout.addSpacing(16)

        layout.addStretch()
        self.start_button = QPushButton("Start Monitoring", objectName="PrimaryButton")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.start_requested.emit)
        layout.addWidget(self.start_button)
        return panel


# =====================================================================
# Run this screen alone for testing
# =====================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    styles.theme.apply()
    window = GlowBackground()
    screen = MonitorScreen()
    screen.start_requested.connect(lambda: print("Start Monitoring clicked"))
    layout = QVBoxLayout(window)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.addWidget(screen)
    window.setWindowTitle("ErgoMon - Monitor")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec_())
