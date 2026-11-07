"""
ErgoMon user app - entry point.

The main window holds all the screens, one on top of the other
(like a deck of cards), and shows one at a time.

Run from the project root:
    python -m user_app.main
"""

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from user_app.ui import styles
from user_app.ui.login_screen import LoginScreen
from user_app.ui.monitor_screen import MonitorScreen
from user_app.ui.register_screen import RegisterScreen
from user_app.ui.widgets.glow_background import GlowBackground
from user_app.ui.widgets.sidebar import Sidebar


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
        self.app_shell = self._build_app_shell()   # sidebar + pages, shown after login
        self.stack.addWidget(self.app_shell)

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

    def _build_app_shell(self):
        """The part of the app after login: [sidebar | pages].
        Each page is a screen; the sidebar chooses which one is shown."""
        self.monitor_screen = MonitorScreen()
        self.monitor_screen.start_requested.connect(lambda: print("Start Monitoring clicked"))

        self.pages = QStackedWidget()
        self.pages.addWidget(self.monitor_screen)
        self.page_by_name = {"monitor": self.monitor_screen}

        self.sidebar = Sidebar()
        self.sidebar.page_selected.connect(lambda name: self.pages.setCurrentWidget(self.page_by_name[name]))
        self.sidebar.logout_requested.connect(self.logout)

        shell = QWidget()
        layout = QHBoxLayout(shell)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.pages, 1)
        return shell

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
        """Login succeeded -> open the app on the Monitor screen."""
        print(f"Logged in: {user['name']} ({user['email']})")
        self.user = user
        self.theme_button.hide()            # after login the theme switch is in the sidebar
        self.sidebar.select_page("monitor")
        self.stack.setCurrentWidget(self.app_shell)

    def logout(self):
        self.user = None
        self.theme_button.show()
        self.show_login()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    styles.theme.apply()
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())