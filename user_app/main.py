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

from user_app.services.session import session
from user_app.ui import styles
from user_app.ui.login_screen import LoginScreen
from user_app.ui.monitor_screen import MonitorScreen
from user_app.ui.register_screen import RegisterScreen
from user_app.ui.widgets.glow_background import GlowBackground
from user_app.ui.widgets.sidebar import GUEST_PAGES, Sidebar


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
        self.login_screen.continue_as_guest.connect(self.open_guest)
    
        # 4. ONE theme button for the whole app (floats in the top-right corner)
        self.theme_button = QPushButton(self, objectName="ThemeToggle")
        self.theme_button.setCursor(Qt.PointingHandCursor)
        self.theme_button.clicked.connect(styles.theme.toggle)
        styles.theme.changed.connect(self.update_theme_button)
        self.update_theme_button(styles.theme.name)

        # 5. The session (who is signed in) can end or be restored on its own
        session.expired.connect(self.on_session_expired)
        session.restored.connect(self.open_app)
        session.restore_failed.connect(self.on_restore_failed)

        # 6. Start on the login screen; if "Remember me" saved a token, sign in with it
        self.show_login()
        if session.has_saved_token():
            self.login_screen.show_signing_in()
            session.restore()

    def _build_app_shell(self):
        """The part of the app after login: [sidebar | pages].
        Each page is a screen; the sidebar chooses which one is shown."""
        self.monitor_screen = MonitorScreen()
        self.monitor_screen.start_requested.connect(lambda: print("Start Monitoring clicked"))

        self.pages = QStackedWidget()
        self.pages.addWidget(self.monitor_screen)
        self.page_by_name = {"monitor": self.monitor_screen}

        self.sidebar = Sidebar()
        self.sidebar.page_selected.connect(self.show_page)
        self.sidebar.logout_requested.connect(self.on_logout_clicked)

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

    def closeEvent(self, event):
        """Runs when the window is closed - turn the camera off first."""
        self.monitor_screen.stop_camera()
        super().closeEvent(event)
        
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
        """Login succeeded (the Login screen already filled the session)."""
        self.open_app()

    def open_app(self):
        """Open the app on the Monitor screen (after login or after "Remember me")."""
        print(f"Signed in: {session.first_name or session.email} ({session.email})")
        self._enter_app_shell(guest=False)

    def open_guest(self):
        """"Continue without an account": Monitor only, nothing is saved."""
        session.start_guest()
        print("Guest mode: nothing is saved")
        self._enter_app_shell(guest=True)

    def _enter_app_shell(self, guest):
        self.theme_button.hide()            # after login the theme switch is in the sidebar
        self.sidebar.set_guest(guest)
        self.monitor_screen.set_guest(guest)
        # refreshed every time the app opens, so it always matches the current user (or guest)
        self.monitor_screen.set_greeting("" if guest else session.first_name)
        self.sidebar.select_page("monitor")   # -> show_page("monitor") (through the guard)
        self.monitor_screen.start_camera()

    # ------------------------------------------------------------ access guard
    def show_page(self, name):
        """The ONE place that opens a page after login. Checks who is using the app first:
        signed in -> every page; guest -> only GUEST_PAGES; signed out -> Login.
        (This only prevents mistakes in the app - real data protection is the
        Firestore security rules.)"""
        state = session.state
        if state == "signed_out":
            self.show_login()
            return
        if state == "guest" and name not in GUEST_PAGES:
            print(f"Access guard: guests cannot open '{name}'")
            return
        if name not in self.page_by_name:   # page not built yet
            return
        self.pages.setCurrentWidget(self.page_by_name[name])
        self.stack.setCurrentWidget(self.app_shell)

    def on_logout_clicked(self):
        """Bottom sidebar button: "Log out" when signed in, "Sign in" for a guest."""
        if session.is_guest:
            self.leave_guest()
        else:
            self.logout()

    def leave_guest(self):
        """Guest -> Login. Does NOT call session.clear(), so a saved "Remember me" token stays."""
        self.monitor_screen.stop_camera()
        session.end_guest()
        self.theme_button.show()
        self.show_login()

    def logout(self):
        self.monitor_screen.stop_camera()
        session.clear()                     # also deletes the saved "Remember me" token
        self.theme_button.show()
        self.show_login()

    def on_session_expired(self):
        """Firebase rejected the token while the app was open -> back to Login."""
        self.logout()
        self.login_screen.show_message("Your session expired. Please log in again.")

    def on_restore_failed(self, reason):
        """App start: signing in with the saved token did not work."""
        self.login_screen.reset()
        if reason == "network":             # the saved token is kept for next time
            self.login_screen.show_message("No internet connection. Please try again.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    styles.theme.apply()
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())