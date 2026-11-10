"""
Monitor screen - FRONTEND (home screen after login).

Ready state: live camera (with a camera dropdown) on the left and the setup
checklist on the right, with the Start Monitoring button.
"Camera connected" shows the real camera state; the other checks come in Stage 3.

Run this screen alone (from the project root):
    python -m user_app.ui.monitor_screen
"""

import sys
from PyQt5.QtGui import QImage, QPainter, QPainterPath, QPixmap
from PyQt5.QtCore import QRectF, QSettings, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget, QComboBox,
                             QStyledItemDelegate,)

from user_app.services.camera_service import CameraService, list_cameras
from user_app.ui import styles
from user_app.ui.widgets.glow_background import GlowBackground

ICONS = {"ok": "✓", "fail": "!", "wait": "…"}
CAMERA_ERRORS = {
    "not_found": "No camera found",
    "busy": "Camera is used by another app",
    "disconnected": "Camera disconnected",
}

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
        self.camera = None
        self.settings = QSettings("ErgoMon", "UserApp")
        self._build_ui()

    # ------------------------------------------------------------ layout
    def _build_ui(self):
        # greeting header, directly on the background (text set by set_greeting)
        self.greeting = QLabel("Hello", objectName="Title")

        panels = QHBoxLayout()
        panels.setSpacing(20)
        panels.addWidget(self._build_camera_card(), 1)
        panels.addWidget(self._build_checklist_panel())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        root.addWidget(self.greeting)
        root.addLayout(panels, 1)

    def set_greeting(self, first_name):
        """ "Hello, {first_name}" - or just "Hello" for a guest / an account without a first name.
        Gets first_name from the session (never a word taken from a full name)."""
        self.greeting.setText(f"Hello, {first_name}" if first_name else "Hello")

    def _build_camera_card(self):
        card = QFrame(objectName="GlassPanel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(4)
        self.camera_list = QComboBox(objectName="CameraSelect")
        self.camera_list.setFixedSize(220, 36)
        self.camera_list.setIconSize(QSize(16, 16))
        self.camera_list.setItemDelegate(QStyledItemDelegate())   # lets QSS style the list items
        popup = self.camera_list.view().window()                   # rounded corners on the open list
        popup.setWindowFlags(popup.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        popup.setAttribute(Qt.WA_TranslucentBackground)
        self.camera_list.addItems(list_cameras())
        self._update_camera_icons()
        styles.theme.changed.connect(self._update_camera_icons)
        saved = self.camera_list.findText(self.settings.value("camera", ""))
        if saved >= 0:
            self.camera_list.setCurrentIndex(saved)
        self.camera_list.currentIndexChanged.connect(self.on_camera_changed)

        header = QHBoxLayout()
        header.addWidget(QLabel("Camera setup", objectName="PanelTitle"))
        header.addStretch()
        header.addWidget(self.camera_list)
        layout.addLayout(header)
        layout.addWidget(QLabel("Sit as you normally work. Place the camera at your side, 1.5–2 m away.",
                                objectName="PanelSubtitle", wordWrap=True))
        layout.addSpacing(14)
        self.video = QLabel("Starting camera…", objectName="CameraPlaceholder", alignment=Qt.AlignCenter)
        self.video.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout.addWidget(self.video, 1)
        self.retry_button = QPushButton("Retry", objectName="SecondaryButton")
        self.retry_button.setCursor(Qt.PointingHandCursor)
        self.retry_button.clicked.connect(lambda: self.start_camera())
        self.retry_button.hide()
        layout.addWidget(self.retry_button, 0, Qt.AlignCenter)
        return card

    def _update_camera_icons(self, _theme_name=None):
        """Video icon before each camera name, in the theme's MUTED color."""
        icon = styles.load_icon("video", styles.theme.colors["MUTED"], 16)
        for i in range(self.camera_list.count()):
            self.camera_list.setItemIcon(i, icon)

    def set_monitoring(self, running):
        """Lock the camera choice while monitoring runs."""
        self.camera_list.setEnabled(not running)

    def show_frame(self, frame):
        h, w, _ = frame.shape
        image = QImage(frame.data, w, h, 3 * w, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(image).scaled(self.video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rounded.rect()), 18, 18)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        self.video.setPixmap(rounded)

    def start_camera(self):
        self.stop_camera()
        index = self.camera_list.currentIndex()
        if index < 0:
            self.show_camera_error("not_found")
            return
        self.retry_button.hide()
        self.video.setText("Starting camera…")
        self.rows["camera"].set_state("wait", "Connecting…")
        self.camera = CameraService(index)
        self.camera.frame_ready.connect(self.show_frame)
        self.camera.opened.connect(lambda: self.rows["camera"].set_state("ok", "Connected"))
        self.camera.error.connect(self.show_camera_error)
        self.camera.start()

    def on_camera_changed(self):
        self.settings.setValue("camera", self.camera_list.currentText())
        self.start_camera()

    def stop_camera(self):
        if self.camera:
            self.camera.frame_ready.disconnect()
            self.camera.opened.disconnect()
            self.camera.error.disconnect()
            self.camera.stop()
            self.camera = None
        self.video.setText("Camera off")

    def show_camera_error(self, error):
        self.video.setText(CAMERA_ERRORS[error])
        self.rows["camera"].set_state("fail", CAMERA_ERRORS[error])
        self.retry_button.show()

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

        self.rows = {
            "camera": CheckRow("Camera connected"),
            "side": CheckRow("Side view detected"),
            "distance": CheckRow("Distance 1.5–2 m"),
            "body": CheckRow("Ear, shoulder, hip, knee visible"),
        }
        for row in self.rows.values():
            row.set_state("wait", "Not implemented yet")
            layout.addWidget(row)
            layout.addSpacing(16)

        layout.addStretch()
        self.start_button = QPushButton("Start Monitoring", objectName="PrimaryButton")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.start_requested.emit)
        layout.addWidget(self.start_button)

        # shown only in guest mode (see set_guest)
        self.guest_hint = QLabel("You're using ErgoMon as a guest. Nothing is saved.",
                                 objectName="FieldHint", alignment=Qt.AlignCenter, wordWrap=True)
        self.guest_hint.setContentsMargins(0, 10, 0, 0)   # gap only when visible
        layout.addWidget(self.guest_hint)
        self.guest_hint.hide()
        return panel

    def set_guest(self, guest):
        """Show or hide the guest hint under the Start button."""
        self.guest_hint.setVisible(guest)


# =====================================================================
# Run this screen alone for testing
# =====================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    styles.theme.apply()
    window = GlowBackground()
    screen = MonitorScreen()
    screen.start_camera()
    app.aboutToQuit.connect(screen.stop_camera)
    screen.start_requested.connect(lambda: print("Start Monitoring clicked"))
    layout = QVBoxLayout(window)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.addWidget(screen)
    window.setWindowTitle("ErgoMon - Monitor")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec_())
