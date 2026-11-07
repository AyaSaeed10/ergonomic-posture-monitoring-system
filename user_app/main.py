"""
ErgoMon user app - entry point.

The main window holds all the screens, one on top of the other
(like a deck of cards), and shows one at a time.

Run from the project root:
    python -m user_app.main
"""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout

from user_app.ui import styles
from user_app.ui.login_screen import LoginScreen
from user_app.ui.register_screen import RegisterScreen
from user_app.ui.widgets.glow_background import GlowBackground


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ErgoMon")
        self.resize(1100, 800)
        self.setMinimumSize(1000, 760)

        # 1. Create the screens
        self.login_screen = LoginScreen()
        self.register_screen = RegisterScreen()

        # 2. Put them in a "deck" - only one is visible at a time
        self.stack = QStackedWidget()
        self.stack.addWidget(self.login_screen)
        self.stack.addWidget(self.register_screen)

        # the glow background sits behind the deck (the screens are see-through)
        background = GlowBackground()
        background_layout = QVBoxLayout(background)
        background_layout.setContentsMargins(0, 0, 0, 0)
        background_layout.addWidget(self.stack)
        self.setCentralWidget(background)

        # 3. Connect the screens' signals to navigation
        self.login_screen.go_to_register.connect(self.show_register)
        self.register_screen.go_to_login.connect(self.show_login)
        self.register_screen.registered.connect(self.after_register)
        self.login_screen.logged_in.connect(self.after_login)
    
        # 4. ONE theme button for the whole app (floats in the top-right corner)
        self.theme_button = QPushButton(self, objectName="ThemeToggle")
        self.theme_button.setCursor(Qt.PointingHandCursor)
        self.theme_button.clicked.connect(styles.theme.toggle)
        styles.theme.changed.connect(self.update_theme_button)
        self.update_theme_button(styles.theme.name)

        # 5. Start on the login screen
        self.show_login()
        
        # ------------------------------------------------------------ theme button
    def update_theme_button(self, theme_name):
        # the button shows the theme you will switch TO
        self.theme_button.setText("☀  Light mode" if theme_name == "dark" else "☾  Dark mode")
        self.theme_button.adjustSize()
        self.place_theme_button()

    def place_theme_button(self):
        margin = 20
        self.theme_button.move(self.width() - self.theme_button.width() - margin, margin)
        self.theme_button.raise_()   # keep it above the screens

    def resizeEvent(self, event):
        """Runs every time the window changes size - keep the button in the corner."""
        super().resizeEvent(event)
        self.place_theme_button()
        
    # ------------------------------------------------------------ navigation
    def show_login(self):
        self.login_screen.reset()
        self.stack.setCurrentWidget(self.login_screen)

    def show_register(self):
        self.register_screen.reset()
        self.stack.setCurrentWidget(self.register_screen)

    def after_register(self, email):
        """Registration succeeded -> go to Login with the email already filled in."""
        self.register_screen.reset()
        self.login_screen.show_account_created(email)
        self.stack.setCurrentWidget(self.login_screen)

    def after_login(self, user):
        """Login succeeded -> later we will open the Dashboard here."""
        print(f"Logged in: {user['name']} ({user['email']})")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    styles.theme.apply()
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())