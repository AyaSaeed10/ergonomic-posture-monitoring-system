"""
Login screen - FRONTEND.

Checks email + password with Firebase (shared/auth_service.py),
then reads the user's name from Firestore (shared/database_service.py).

Run this screen alone (from the project root):
    python -m user_app.ui.login_screen
"""

import sys

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from shared.auth_service import login
from shared.database_service import get_user_profile
from user_app.ui import styles
from user_app.ui.brand_panel import build_brand_panel
from user_app.ui.widgets.glow_background import GlowBackground

# Firebase error codes -> friendly messages for the user
FIREBASE_ERRORS = {
    "INVALID_LOGIN_CREDENTIALS": "Wrong email or password.",
    "EMAIL_NOT_FOUND": "Wrong email or password.",
    "INVALID_PASSWORD": "Wrong email or password.",
    "INVALID_EMAIL": "The email address is not valid.",
    "USER_DISABLED": "This account has been disabled.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many failed attempts. Please try again later.",
    "PERMISSION_DENIED": "Could not load your profile (database permission denied).",
}


# =====================================================================
# Background worker - talks to Firebase without freezing the window
# =====================================================================
class LoginWorker(QThread):
    succeeded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, email, password):
        super().__init__()
        self.email = email
        self.password = password

    def run(self):
        try:
            # Step 1: check email + password in Firebase Authentication
            result = login(self.email, self.password)
            # Step 2: read the user's profile (name...) from Firestore
            profile = get_user_profile(result["localId"], result["idToken"])

            user = {
                "uid": result["localId"],
                "email": result["email"],
                "id_token": result["idToken"],
                "name": profile.get("name", ""),
            }
            self.succeeded.emit(user)
        except Exception as error:
            code = str(error).split(" ")[0]
            if "ConnectionError" in type(error).__name__ or "Max retries" in str(error):
                self.failed.emit("No internet connection. Please check your network.")
            else:
                self.failed.emit(FIREBASE_ERRORS.get(code, f"Login failed: {error}"))


# =====================================================================
# The screen
# =====================================================================
class LoginScreen(QWidget):
    logged_in = pyqtSignal(dict)    # sent after a successful login (with the user)
    go_to_register = pyqtSignal()   # sent when "Sign up" is clicked

    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.worker = None
        self._build_ui()

    # ------------------------------------------------------------ layout
    def _build_ui(self):
        # glass card on the right holds the form
        card = QFrame(objectName="GlassPanel")
        card.setFixedSize(460, 580)
        styles.add_glass_shadow(card)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addWidget(self._build_form())

        # brand message on the left, directly on the background
        brand = build_brand_panel()
        brand.setFixedSize(416, 700)

        # [stretch | brand | gap | card | stretch] -> both stay centered in the window
        root = QHBoxLayout(self)
        root.addStretch()
        root.addWidget(brand, 0, Qt.AlignVCenter)
        root.addSpacing(64)
        root.addWidget(card, 0, Qt.AlignVCenter)
        root.addStretch()

    def _build_form(self):
        form = QWidget()
        layout = QVBoxLayout(form)
        layout.setContentsMargins(56, 44, 56, 36)
        layout.setSpacing(0)
        layout.addStretch()

        layout.addWidget(QLabel("Welcome back", objectName="Title"))
        layout.addSpacing(6)
        layout.addWidget(QLabel("Log in to continue caring for your posture.", objectName="Subtitle"))
        layout.addSpacing(24)

        self.banner = QLabel(objectName="Banner", wordWrap=True)
        self.banner.setMinimumHeight(40)
        self.banner.hide()
        layout.addWidget(self.banner)
        layout.addSpacing(12)

        self.email_input, self.email_error = self._add_field(layout, "Email", "you@example.com")
        self.password_input, self.password_error = self._add_field(
            layout, "Password", "Your password", password=True)

        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(
            lambda visible: self.password_input.setEchoMode(
                QLineEdit.Normal if visible else QLineEdit.Password))
        layout.addWidget(self.show_password)
        layout.addSpacing(22)

        self.submit_button = QPushButton("Log in", objectName="PrimaryButton")
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.clicked.connect(self._on_submit)
        layout.addWidget(self.submit_button)
        layout.addSpacing(14)

        register_row = QHBoxLayout()
        register_row.setSpacing(6)
        register_row.addStretch()
        register_row.addWidget(QLabel("Don't have an account?", objectName="Hint"))
        register_link = QPushButton("Sign up", objectName="LinkButton")
        register_link.setCursor(Qt.PointingHandCursor)
        register_link.clicked.connect(self.go_to_register.emit)
        register_row.addWidget(register_link)
        register_row.addStretch()
        layout.addLayout(register_row)
        layout.addStretch()

        # Enter key = click "Log in"
        self.email_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self._on_submit)
        for field in (self.email_input, self.password_input):
            field.textChanged.connect(lambda _, f=field: self._set_invalid(f, False))
        return form

    def _add_field(self, layout, label, placeholder, password=False):
        layout.addWidget(QLabel(label, objectName="FieldLabel"))
        layout.addSpacing(6)
        field = QLineEdit(placeholderText=placeholder)
        if password:
            field.setEchoMode(QLineEdit.Password)
        layout.addWidget(field)
        layout.addSpacing(4)
        error = QLabel("", objectName="FieldError")
        error.setFixedHeight(16)
        layout.addWidget(error)
        layout.addSpacing(4)
        return field, error

    # ------------------------------------------------------------ called by the main window
    def show_account_created(self, email):
        """Called right after registration: fill the email and show a green message."""
        self.reset()
        self.email_input.setText(email)
        self._show_banner("Your account was created! Please log in.", "success")
        self.password_input.setFocus()

    def reset(self):
        """Clear the form."""
        for field in (self.email_input, self.password_input):
            field.clear()
            self._set_invalid(field, False)
        self.show_password.setChecked(False)
        self.banner.hide()
        self._set_loading(False)

    # ------------------------------------------------------------ behaviour
    def _set_invalid(self, field, invalid, message=""):
        field.setProperty("invalid", invalid)
        field.style().unpolish(field)
        field.style().polish(field)
        errors = {self.email_input: self.email_error, self.password_input: self.password_error}
        errors[field].setText(message)

    def _validate(self):
        ok = True
        if not self.email_input.text().strip():
            self._set_invalid(self.email_input, True, "Please enter your email")
            ok = False
        if not self.password_input.text():
            self._set_invalid(self.password_input, True, "Please enter your password")
            ok = False
        return ok

    def _show_banner(self, text, kind):
        self.banner.setText(text)
        self.banner.setProperty("kind", kind)
        self.banner.style().unpolish(self.banner)
        self.banner.style().polish(self.banner)
        self.banner.show()

    def _set_loading(self, loading):
        self.submit_button.setEnabled(not loading)
        self.submit_button.setText("Logging in..." if loading else "Log in")

    def _on_submit(self):
        self.banner.hide()
        if not self._validate():
            return
        self._set_loading(True)
        self.worker = LoginWorker(self.email_input.text().strip(), self.password_input.text())
        self.worker.succeeded.connect(self._on_success)
        self.worker.failed.connect(self._on_failure)
        self.worker.start()

    def _on_success(self, user):
        self._set_loading(False)
        self._show_banner(f"Welcome back, {user['name'] or user['email']}!", "success")
        self.logged_in.emit(user)

    def _on_failure(self, message):
        self._set_loading(False)
        self._show_banner(message, "error")


# =====================================================================
# Run this screen alone for testing
# =====================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    styles.theme.apply()
    window = GlowBackground()          # the screen sits on the glow background
    QVBoxLayout(window).addWidget(LoginScreen())
    window.setWindowTitle("ErgoMon - Log in")
    window.resize(1100, 800)
    window.show()
    sys.exit(app.exec_())