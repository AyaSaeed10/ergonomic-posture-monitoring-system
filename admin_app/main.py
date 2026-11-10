"""
ErgoMon ADMIN app - entry point.

Uses the Firebase admin key (secrets/firebase-admin-key.json).
Same look as the user app: glow background, glass panels, Light/Dark theme.

Run from the project root:
    python -m admin_app.main
"""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout

from admin_app.ui.cleanup_screen import CleanupScreen
from user_app.ui import styles
from user_app.ui.widgets.glow_background import GlowBackground


class AdminWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ErgoMon Admin")
        self.resize(1100, 760)
        self.setMinimumSize(900, 620)

        # the screen sits on the glow background
        background = GlowBackground()
        QVBoxLayout(background).addWidget(CleanupScreen())
        self.setCentralWidget(background)

        # Light / Dark button in the top-right corner (#ThemeToggle in styles.py)
        self.theme_button = QPushButton(self, objectName="ThemeToggle")
        self.theme_button.setCursor(Qt.PointingHandCursor)
        self.theme_button.clicked.connect(styles.theme.toggle)
        styles.theme.changed.connect(self.update_theme_button)
        self.update_theme_button(styles.theme.name)

    def update_theme_button(self, theme_name):
        self.theme_button.setText("Light mode" if theme_name == "dark" else "Dark mode")
        self.theme_button.adjustSize()
        self.place_theme_button()

    def place_theme_button(self):
        margin = 20
        self.theme_button.move(self.width() - self.theme_button.width() - margin, margin)
        self.theme_button.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.place_theme_button()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    styles.theme.apply()
    window = AdminWindow()
    window.show()
    sys.exit(app.exec_())