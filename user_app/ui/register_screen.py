"""
Register screen - FRONTEND.

Shows the registration form. When the user clicks "Create account",
it calls register() from shared/auth_service.py (which talks to Firebase).

Run this screen alone (from the project root):
    python -m user_app.ui.register_screen
"""

import re
import sys

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal

from shared.auth_service import register
from shared.database_service import create_user_profile
from user_app.ui import styles
from user_app.ui.brand_panel import build_brand_panel
from user_app.ui.widgets.glow_background import GlowBackground
# Firebase error codes -> friendly messages for the user
FIREBASE_ERRORS = {
    "EMAIL_EXISTS": "This email is already registered. Try logging in.",
    "INVALID_EMAIL": "The email address is not valid.",
    "WEAK_PASSWORD": "Password must be at least 6 characters.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please try again later.",
    "PERMISSION_DENIED": "Could not save your profile (database permission denied).",
}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# =====================================================================
# Background worker - talks to Firebase without freezing the window
# =====================================================================
class RegisterWorker(QThread):
    succeeded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, name, email, password):
            super().__init__()
            self.name = name
            self.email = email
            self.password = password

    def run(self):
        try:
            # Step 1: create the account in Firebase Authentication
            user = register(self.email, self.password)
            # Step 2: save the profile in Firestore -> users/{uid}
            create_user_profile(user["localId"], user["idToken"], self.name, self.email)
            self.succeeded.emit(user)
        except Exception as error:
            code = str(error).split(" ")[0]
            if "ConnectionError" in type(error).__name__ or "Max retries" in str(error):
                self.failed.emit("No internet connection. Please check your network.")
            else:
                self.failed.emit(FIREBASE_ERRORS.get(code, f"Registration failed: {error}"))


# =====================================================================
# The screen
# =====================================================================
class RegisterScreen(QWidget):
    registered = pyqtSignal(str)   # sent after a successful registration
    go_to_login = pyqtSignal()      # sent when "Log in" is clicked

    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # when the theme changes, repaint the password strength bar in the new colors
        styles.theme.changed.connect(lambda _: self._update_strength(self.password_input.text())) 
        self.worker = None
        self._build_ui()

    # ------------------------------------------------------------ layout
    def _build_ui(self):
        # glass card on the right holds the form
        card = QFrame(objectName="GlassPanel")
        card.setFixedSize(460, 700)
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

        layout.addWidget(QLabel("Create your account", objectName="Title"))
        layout.addSpacing(6)
        layout.addWidget(QLabel("Start building healthier sitting habits today.", objectName="Subtitle"))
        layout.addSpacing(18)

        self.banner = QLabel(objectName="Banner", wordWrap=True)
        self.banner.setMinimumHeight(40)
        self.banner.hide()
        layout.addWidget(self.banner)
        layout.addSpacing(12)

        self.name_input, self.name_error = self._add_field(layout, "Full name", " ")
        self.email_input, self.email_error = self._add_field(layout, "Email", "you@example.com")
        self.password_input, self.password_error = self._add_field(
            layout, "Password", "At least 6 characters", password=True)

        # password strength bar
        strength_row = QHBoxLayout()
        self.strength_bar = QProgressBar(textVisible=False, maximum=4)
        self.strength_bar.setFixedHeight(6)
        self.strength_label = QLabel("", objectName="Hint")
        self.strength_label.setFixedWidth(56)
        self.strength_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        strength_row.setSpacing(10)
        strength_row.addWidget(self.strength_bar)
        strength_row.addWidget(self.strength_label)
        layout.addLayout(strength_row)
        layout.addSpacing(10)

        self.confirm_input, self.confirm_error = self._add_field(
            layout, "Confirm password", "Repeat your password", password=True)

        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(self._toggle_password_visibility)
        layout.addWidget(self.show_password)
        layout.addSpacing(18)

        self.submit_button = QPushButton("Create account", objectName="PrimaryButton")
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.clicked.connect(self._on_submit)
        layout.addWidget(self.submit_button)
        layout.addSpacing(14)

        login_row = QHBoxLayout()
        login_row.addStretch()
        login_row.setSpacing(6)
        login_row.addWidget(QLabel("Already have an account?", objectName="Hint"))
        login_link = QPushButton("Log in", objectName="LinkButton")
        login_link.setCursor(Qt.PointingHandCursor)
        login_link.clicked.connect(self.go_to_login.emit)
        login_row.addWidget(login_link)
        login_row.addStretch()
        layout.addLayout(login_row)
        layout.addStretch()

        # live behaviour
        self.password_input.textChanged.connect(self._update_strength)
        self.confirm_input.returnPressed.connect(self._on_submit)
        for field in (self.name_input, self.email_input, self.password_input, self.confirm_input):
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

    # ------------------------------------------------------------ behaviour
    def _toggle_password_visibility(self, visible):
        mode = QLineEdit.Normal if visible else QLineEdit.Password
        self.password_input.setEchoMode(mode)
        self.confirm_input.setEchoMode(mode)

    def _update_strength(self, password):
        score = sum([
            len(password) >= 6,
            len(password) >= 10,
            bool(re.search(r"[A-Z]", password)) and bool(re.search(r"[a-z]", password)),
            bool(re.search(r"\d", password)) and bool(re.search(r"[^\w]", password)),
        ])
        labels = ["", "Weak", "Fair", "Good", "Strong"]
        c = styles.theme.colors
        colors = [c["BORDER"], c["ERROR"], c["WARNING"], c["ACCENT"], c["SUCCESS"]]
        self.strength_bar.setValue(score)
        self.strength_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {colors[score]}; border-radius: 3px; }}")
        self.strength_label.setText(labels[score] if password else "")

    def _set_invalid(self, field, invalid, message=""):
        field.setProperty("invalid", invalid)
        field.style().unpolish(field)
        field.style().polish(field)
        errors = {self.name_input: self.name_error, self.email_input: self.email_error,
                  self.password_input: self.password_error, self.confirm_input: self.confirm_error}
        errors[field].setText(message)

    def _validate(self):
        """Check the form before sending anything to Firebase."""
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        ok = True
        if not name:
            self._set_invalid(self.name_input, True, "Please enter your name")
            ok = False
        if not EMAIL_PATTERN.match(email):
            self._set_invalid(self.email_input, True, "Please enter a valid email")
            ok = False
        if len(password) < 6:
            self._set_invalid(self.password_input, True, "At least 6 characters")
            ok = False
        if confirm != password or not confirm:
            self._set_invalid(self.confirm_input, True, "Passwords do not match")
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
        self.submit_button.setText("Creating account..." if loading else "Create account")

    def _on_submit(self):
        self.banner.hide()
        if not self._validate():
            return
        self._set_loading(True)
        self.worker = RegisterWorker(
            self.name_input.text().strip(),
            self.email_input.text().strip(),
            self.password_input.text(),
        )
        self.worker.succeeded.connect(self._on_success)
        self.worker.failed.connect(self._on_failure)
        self.worker.start()

    def _on_success(self, user):
        self._set_loading(False)
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        self._show_banner(f"Welcome to ErgoMon, {name}! Taking you to log in...", "success")
        self.submit_button.setEnabled(False)
        # wait 1.5 seconds so the user can read the message, then tell the main window
        QTimer.singleShot(1500, lambda: self.registered.emit(email))

    def reset(self):
        """Clear the form (called by the main window when leaving this screen)."""
        for field in (self.name_input, self.email_input, self.password_input, self.confirm_input):
            field.clear()
            self._set_invalid(field, False)
        self.show_password.setChecked(False)
        self.banner.hide()
        self._set_loading(False)

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
    QVBoxLayout(window).addWidget(RegisterScreen())
    window.setWindowTitle("ErgoMon - Create account")
    window.resize(1100, 800)
    window.show()
    sys.exit(app.exec_())
