"""
Register screen - FRONTEND.

Shows the registration form. When the user clicks "Create account",
it calls shared/auth_service.py (which talks to Firebase):
  1. register()                - creates the account (not verified yet)
  2. set_display_name()        - keeps the name until the email is verified
  3. send_verification_email() - Firebase emails a verification link
The Firestore profile is created later, on the first VERIFIED login.

Run this screen alone (from the project root):
    python -m user_app.ui.register_screen
"""

import re
import sys

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout,
    QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from shared.auth_service import (
    delete_account, is_email_verified, login, register,
    send_verification_email, set_display_name,
)
from user_app.ui import styles
from user_app.ui.brand_panel import build_brand_panel
from user_app.ui.widgets.floating_field import FloatingField
from user_app.ui.widgets.glow_background import GlowBackground

# Firebase error codes -> friendly messages for the user
FIREBASE_ERRORS = {
    "EMAIL_EXISTS": "This email is already registered. Try logging in.",
    "INVALID_EMAIL": "The email address is not valid.",
    "WEAK_PASSWORD": "Password must be at least 6 characters.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please try again later.",
}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# =====================================================================
# Background worker - talks to Firebase without freezing the window
# =====================================================================
class RegisterWorker(QThread):
    succeeded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, first_name, last_name, email, password):
        super().__init__()
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password

    def run(self):
        try:
            # Step 1: create the account (or reuse an unverified one - see below)
            user = self._create_or_reuse_account()
            try:
                # Step 2: keep the name in Authentication until the email is verified
                full_name = f"{self.first_name} {self.last_name}".strip()
                set_display_name(user["idToken"], full_name)
                # Step 3: Firebase sends the verification email
                send_verification_email(user["idToken"])
            except Exception:
                # something failed half-way -> delete the account, as if nothing happened
                delete_account(user["idToken"])
                raise
            self.succeeded.emit(user)
        except Exception as error:
            code = str(error).split(" ")[0]
            if "ConnectionError" in type(error).__name__ or "Max retries" in str(error):
                self.failed.emit("No internet connection. Please check your network.")
            else:
                self.failed.emit(FIREBASE_ERRORS.get(code, f"Registration failed: {error}"))

    def _create_or_reuse_account(self):
        """Create a new account. If the email already exists but was never verified
        and the password matches, reuse it (the user just needs a new email)."""
        try:
            return register(self.email, self.password)
        except Exception as error:
            if str(error) != "EMAIL_EXISTS":
                raise
            try:
                user = login(self.email, self.password)
            except Exception:
                raise error from None      # different password -> someone else's account
            if is_email_verified(user["idToken"]):
                raise error                # a real, verified account -> "already registered"
            return user                    # unverified account with the same password -> reuse it                   # unverified account with the same password -> reuse it

# =====================================================================
# The screen
# =====================================================================
class RegisterScreen(QWidget):
    registered = pyqtSignal(str)    # sent after a successful registration (with the email)
    go_to_login = pyqtSignal()      # sent when "I already have an account" is clicked

    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.worker = None
        self._build_ui()
        # when the theme changes, repaint the password strength bar in the new colors
        styles.theme.changed.connect(lambda _: self._update_strength(self.password_input.text()))

    # ------------------------------------------------------------ layout
    def _build_ui(self):
        # glass card on the right holds the form
        card = QFrame(objectName="GlassPanel")
        card.setFixedSize(460, 710)
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
        layout.setContentsMargins(56, 30, 56, 24)
        layout.setSpacing(0)

        layout.addWidget(QLabel("Create your account", objectName="Title"))
        layout.addSpacing(6)
        layout.addWidget(QLabel("Start building healthier sitting habits today.", objectName="Subtitle"))
        layout.addSpacing(12)

        self.banner = QLabel(objectName="Banner", wordWrap=True)
        self.banner.setMinimumHeight(40)
        self.banner.hide()
        layout.addWidget(self.banner)
        layout.addSpacing(12)

        # "Name" heading + First name / Last name side by side, each with its own error
        layout.addWidget(QLabel("Name", objectName="FieldLabel"))
        layout.addSpacing(6)
        name_row = QHBoxLayout()
        name_row.setSpacing(12)
        first_column, last_column = QVBoxLayout(), QVBoxLayout()
        self.first_name_input, self.first_name_error = self._add_field(first_column, "First name")
        self.last_name_input, self.last_name_error = self._add_field(last_column, "Last name")
        name_row.addLayout(first_column)
        name_row.addLayout(last_column)
        layout.addLayout(name_row)

        self.email_input, self.email_error = self._add_field(
            layout, "Email",
            hint="Use an email you can access. We'll send you a verification link.")
        self.password_input, self.password_error = self._add_field(layout, "Password", password=True)

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
        layout.addSpacing(6)

        self.confirm_input, self.confirm_error = self._add_field(
            layout, "Confirm password", password=True)
        layout.addSpacing(10)

        self.submit_button = QPushButton("Create account", objectName="PrimaryButton")
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.clicked.connect(self._on_submit)
        layout.addWidget(self.submit_button)
        layout.addSpacing(8)

        login_button = QPushButton("I already have an account", objectName="SecondaryButton")
        login_button.setCursor(Qt.PointingHandCursor)
        login_button.clicked.connect(self.go_to_login.emit)
        layout.addWidget(login_button)
        layout.addStretch()

        # live behaviour
        self.password_input.textChanged.connect(self._update_strength)
        self.confirm_input.returnPressed.connect(self._on_submit)
        for field in self._fields():
            field.textChanged.connect(lambda _, f=field: self._set_invalid(f, False))
        return form

    def _fields(self):
        return (self.first_name_input, self.last_name_input, self.email_input,
                self.password_input, self.confirm_input)

    def _add_field(self, layout, label, password=False, hint=None):
        field = FloatingField(label, password=password)   # label sits inside the box
        layout.addWidget(field)
        if hint:                                          # short muted help text under the box
            layout.addSpacing(4)
            layout.addWidget(QLabel(hint, objectName="FieldHint", wordWrap=True))
        layout.addSpacing(2)
        error = QLabel("", objectName="FieldError")
        error.setFixedHeight(16)   # room for the error is always kept -> nothing moves or overlaps
        layout.addWidget(error)
        return field, error

    # ------------------------------------------------------------ behaviour
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
        errors = {self.first_name_input: self.first_name_error,
                  self.last_name_input: self.last_name_error, self.email_input: self.email_error,
                  self.password_input: self.password_error, self.confirm_input: self.confirm_error}
        errors[field].setText(message)

    def _validate(self):
        """Check the form before sending anything to Firebase."""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        ok = True
        if not self.first_name_input.text().strip():
            self._set_invalid(self.first_name_input, True, "Please enter your first name")
            ok = False
        if not self.last_name_input.text().strip():
            self._set_invalid(self.last_name_input, True, "Please enter your last name")
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
            self.first_name_input.text().strip(),
            self.last_name_input.text().strip(),
            self.email_input.text().strip(),
            self.password_input.text(),
        )
        self.worker.succeeded.connect(self._on_success)
        self.worker.failed.connect(self._on_failure)
        self.worker.start()

    def _on_success(self, user):
        self._set_loading(False)
        email = self.email_input.text().strip()
        self._show_banner(f"We sent a verification email to {email}. Taking you to log in...", "success")
        self.submit_button.setEnabled(False)
        # wait 2.5 seconds so the user can read the message, then tell the main window
        QTimer.singleShot(2500, lambda: self.registered.emit(email))

    def _on_failure(self, message):
        self._set_loading(False)
        self._show_banner(message, "error")

    def reset(self):
        """Clear the form (called by the main window when leaving this screen)."""
        for field in self._fields():
            field.clear()
            self._set_invalid(field, False)   # clearing also hides the passwords again
        self.banner.hide()
        self._set_loading(False)


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