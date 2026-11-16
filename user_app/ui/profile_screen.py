"""
Profile screen - FRONTEND.

Shows the logged-in user's details and lets them:
  - add / remove a profile photo     (Firestore, as Bytes)
  - change their first / last name   (Firestore)
  - change their password            (Authentication)
  - delete their account             (Firestore first, then Authentication)

The main window gives the user to this screen with load_user(user) after login,
and listens to its signals (see the bottom of the class).

Run this screen alone (from the project root):
    python -m user_app.ui.profile_screen
"""

import base64
import os
import sys

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from shared.auth_service import change_password, delete_account, login
from shared.database_service import (
    delete_user_profile, get_user_profile, remove_user_photo, save_user_photo, update_user_profile,
)
from user_app.services.session import session
from user_app.ui import styles
from user_app.ui.widgets.confirm_overlay import ConfirmOverlay
from user_app.ui.widgets.floating_field import FloatingField
from user_app.ui.widgets.glow_background import GlowBackground

PHOTO_SIZE = 256                    # the photo is saved as a 256 x 256 JPEG (about 20-40 KB)
MAX_FILE_MB = 10                    # bigger files are refused

# Firebase error codes -> friendly messages for the user
FIREBASE_ERRORS = {
    "INVALID_LOGIN_CREDENTIALS": "Your current password is wrong.",
    "INVALID_PASSWORD": "Your current password is wrong.",
    "WEAK_PASSWORD": "The new password must be at least 6 characters.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please try again later.",
    "CREDENTIAL_TOO_OLD_LOGIN_AGAIN": "Please log out and log in again, then try once more.",
    "PERMISSION_DENIED": "The database refused the request (permission denied).",
}


# =====================================================================
# One background worker for every action on this screen:
# it runs a function in the background and reports the result.
# =====================================================================
class TaskWorker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, task):
        super().__init__()
        self.task = task          # a function with no arguments

    def run(self):
        try:
            self.succeeded.emit(self.task())
        except Exception as error:
            code = str(error).split(" ")[0]
            if "ConnectionError" in type(error).__name__ or "Max retries" in str(error):
                self.failed.emit("No internet connection. Please check your network.")
            else:
                self.failed.emit(FIREBASE_ERRORS.get(code, f"Something went wrong: {error}"))


# =====================================================================
# Photo helpers (round_pixmap is also used by the sidebar)
# =====================================================================
def image_to_base64(image):
    """Crop the image to a centered square, shrink it to PHOTO_SIZE and return a JPEG as Base64."""
    side = min(image.width(), image.height())
    square = image.copy((image.width() - side) // 2, (image.height() - side) // 2, side, side)
    small = square.scaled(PHOTO_SIZE, PHOTO_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    small.save(buffer, "JPG", 88)               # 88 = good quality, small file
    return base64.b64encode(bytes(data)).decode()


def round_pixmap(image, size, pixel_ratio=1.0):
    """The image cut into a circle of `size` pixels (sharp on high-DPI screens)."""
    real = int(size * pixel_ratio)
    scaled = image.scaled(real, real, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    result = QPixmap(real, real)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(QRectF(0, 0, real, real))
    painter.setClipPath(path)
    painter.drawImage(0, 0, scaled)
    painter.end()
    result.setDevicePixelRatio(pixel_ratio)
    return result


# =====================================================================
# The screen
# =====================================================================
class ProfileScreen(QWidget):
    profile_updated = pyqtSignal(dict)   # new first/last name -> main window updates the greeting
    tokens_changed = pyqtSignal(dict)    # after a password change -> main window updates the session
    account_deleted = pyqtSignal()       # main window logs out and shows the Login screen
    photo_changed = pyqtSignal(str)      # new photo (Base64) or "" when removed -> main window updates the sidebar

    def __init__(self):
        super().__init__()
        self.setObjectName("Root")                       # see-through -> the glows show
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.user = {}
        self.worker = None
        self.photo_loader = None
        self._build_ui()

    # ------------------------------------------------------------ layout
    def _build_ui(self):
        """ONE centered glass card, split into sections (like account settings pages):

            (AS)  Aya Saeed / email
                  Change photo · Remove
            ───────────────────────────────────────────
            Personal details   |  [First name] [Last name]
            description        |              [Save changes]
            ───────────────────────────────────────────
            Password           |  [Current password]
            description        |  [New password] [Confirm]
                               |           [Change password]
            ───────────────────────────────────────────
            Delete account     |            [Delete account]
            description        |
        """
        card = QFrame(objectName="GlassPanel")
        card.setMaximumWidth(860)
        styles.add_glass_shadow(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(44, 36, 44, 36)
        layout.setSpacing(0)

        # messages about the photo appear at the very top of the card
        self.photo_message = QWidget()                   # banner + a gap under it
        message_layout = QVBoxLayout(self.photo_message)
        message_layout.setContentsMargins(0, 0, 0, 18)
        self.photo_banner = QLabel(objectName="Banner", wordWrap=True)
        message_layout.addWidget(self.photo_banner)
        self.photo_message.hide()
        layout.addWidget(self.photo_message)
        layout.addWidget(self._build_header())
        self._add_divider(layout)
        layout.addLayout(self._build_details_section())
        self._add_divider(layout)
        layout.addLayout(self._build_password_section())
        self._add_divider(layout)
        layout.addLayout(self._build_delete_section())

        # the card stays centered, both horizontally and vertically
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(card, 1)
        row.addStretch()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addStretch()
        root.addLayout(row)
        root.addStretch()

    def _build_header(self):
        """(AS)  Aya Saeed
                 ayas@gmail.com
                 Change photo · Remove"""
        self.avatar = QLabel("", objectName="Avatar", alignment=Qt.AlignCenter)
        self.avatar.setFixedSize(64, 64)
        self.name_label = QLabel("", objectName="Title")
        self.email_label = QLabel("", objectName="Subtitle")

        # Change photo · Remove   (small links under the email)
        self.change_photo_button = QPushButton("Change photo", objectName="LinkButton")
        self.change_photo_button.setCursor(Qt.PointingHandCursor)
        self.change_photo_button.clicked.connect(self._on_change_photo)
        self.remove_photo_button = QPushButton("Remove", objectName="LinkButton")
        self.remove_photo_button.setCursor(Qt.PointingHandCursor)
        self.remove_photo_button.clicked.connect(self._on_remove_photo)
        self.photo_dot = QLabel("·", objectName="Hint")
        photo_links = QHBoxLayout()
        photo_links.setSpacing(8)
        photo_links.addWidget(self.change_photo_button)
        photo_links.addWidget(self.photo_dot)
        photo_links.addWidget(self.remove_photo_button)
        photo_links.addStretch()

        text = QVBoxLayout()
        text.setSpacing(2)
        text.addStretch()
        text.addWidget(self.name_label)
        text.addWidget(self.email_label)
        text.addSpacing(4)
        text.addLayout(photo_links)
        text.addStretch()

        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(18)
        row.addWidget(self.avatar)
        row.addLayout(text)
        row.addStretch()
        return header

    @staticmethod
    def _add_divider(layout):
        """A thin line between two sections (#Divider in styles.py)."""
        layout.addSpacing(26)
        line = QFrame(objectName="Divider")
        line.setFixedHeight(1)
        layout.addWidget(line)
        layout.addSpacing(26)

    def _new_section(self, title, description):
        """[title + description on the left | content on the right].
        Returns (section_layout, content_layout, banner)."""
        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(4)
        info.addWidget(QLabel(title, objectName="PanelTitle"))
        info.addWidget(QLabel(description, objectName="PanelSubtitle", wordWrap=True))
        info.addStretch()
        info_widget = QWidget()
        info_widget.setLayout(info)
        info_widget.setFixedWidth(230)

        content = QVBoxLayout()
        content.setSpacing(12)
        banner = QLabel(objectName="Banner", wordWrap=True)
        banner.hide()
        content.addWidget(banner)

        section = QHBoxLayout()
        section.setSpacing(36)
        section.addWidget(info_widget, 0, Qt.AlignTop)
        section.addLayout(content, 1)
        return section, content, banner

    @staticmethod
    def _right_aligned(button):
        """Put a button on the right side of its own row."""
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedWidth(190)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button)
        return row

    def _build_details_section(self):
        section, content, self.details_banner = self._new_section(
            "Personal details", "The name ErgoMon uses to greet you.")

        names = QHBoxLayout()
        names.setSpacing(12)
        self.first_name_input = FloatingField("First name")
        self.last_name_input = FloatingField("Last name")
        names.addWidget(self.first_name_input)
        names.addWidget(self.last_name_input)
        content.addLayout(names)

        self.save_button = QPushButton("Save changes", objectName="PrimaryButton")
        self.save_button.clicked.connect(self._on_save_name)
        content.addLayout(self._right_aligned(self.save_button))

        for field in (self.first_name_input, self.last_name_input):
            field.textChanged.connect(lambda _, f=field: self._set_invalid(f, False))
            field.returnPressed.connect(self._on_save_name)
        return section

    def _build_password_section(self):
        section, content, self.password_banner = self._new_section(
            "Password", "Enter your current password first. Other devices will be signed out.")

        self.current_password = FloatingField("Current password", password=True)
        self.new_password = FloatingField("New password", password=True)
        self.confirm_password = FloatingField("Confirm new password", password=True)
        content.addWidget(self.current_password)
        new_row = QHBoxLayout()
        new_row.setSpacing(12)
        new_row.addWidget(self.new_password)
        new_row.addWidget(self.confirm_password)
        content.addLayout(new_row)

        self.password_button = QPushButton("Change password", objectName="PrimaryButton")
        self.password_button.clicked.connect(self._on_change_password)
        content.addLayout(self._right_aligned(self.password_button))

        for field in (self.current_password, self.new_password, self.confirm_password):
            field.textChanged.connect(lambda _, f=field: self._set_invalid(f, False))
        self.confirm_password.returnPressed.connect(self._on_change_password)
        return section

    def _build_delete_section(self):
        section, content, self.delete_banner = self._new_section(
            "Delete account", "Permanently delete your account and all your data.")

        self.delete_button = QPushButton("Delete account", objectName="DangerButton")
        self.delete_button.clicked.connect(self._on_delete_account)
        content.addLayout(self._right_aligned(self.delete_button))
        content.addStretch()
        return section

    # ------------------------------------------------------------ called by the main window
    def load_user(self, user):
        """Show this user. `user` is the dict from the login (uid, email, id_token, first_name...)."""
        self.user = dict(user)
        first, last = user.get("first_name", ""), user.get("last_name", "")
        self.first_name_input.setText(first)
        self.last_name_input.setText(last)
        self._update_header(first, last)
        for field in (self.current_password, self.new_password, self.confirm_password):
            field.clear()
        for banner in (self.details_banner, self.password_banner, self.delete_banner):
            banner.hide()
        self.photo_message.hide()
        self._show_photo(None)          # initials first, then the photo once it is loaded
        self._load_photo()

    def _update_header(self, first, last):
        self.name_label.setText(f"{first} {last}".strip() or "Your profile")
        self.email_label.setText(self.user.get("email", ""))
        if not self.user.get("photo"):
            self._show_photo(None)      # refresh the initials

    # ------------------------------------------------------------ photo (circle)
    def _load_photo(self):
        """Read the saved photo from Firestore in the background."""
        uid, token = session.uid, session.id_token
        if not uid:
            return
        self.photo_loader = TaskWorker(lambda: get_user_profile(uid, token).get("photo"))
        self.photo_loader.succeeded.connect(self._show_photo)
        self.photo_loader.start()

    def _show_photo(self, photo_base64):
        """Photo inside the circle - or the initials (AS) when there is no photo."""
        self.user["photo"] = photo_base64 or ""
        has_photo = bool(photo_base64)
        self.remove_photo_button.setVisible(has_photo)
        self.photo_dot.setVisible(has_photo)
        if not has_photo:
            first, last = self.user.get("first_name", ""), self.user.get("last_name", "")
            initials = (first[:1] + last[:1]).upper() or self.user.get("email", "?")[:1].upper()
            self.avatar.setPixmap(QPixmap())
            self.avatar.setText(initials)
            return
        image = QImage()
        image.loadFromData(base64.b64decode(photo_base64))
        self.avatar.setText("")
        self.avatar.setPixmap(round_pixmap(image, self.avatar.width(), self.devicePixelRatioF()))

    def _on_change_photo(self):
        self.photo_message.hide()
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a profile photo", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return                                        # the user closed the window
        if os.path.getsize(path) > MAX_FILE_MB * 1024 * 1024:
            self._show_photo_message(
                f"This image is too big. Please choose one under {MAX_FILE_MB} MB.", "error")
            return
        image = QImage(path)
        if image.isNull():
            self._show_photo_message("This file is not a valid image.", "error")
            return

        photo_base64 = image_to_base64(image)
        uid, token = session.uid, session.id_token
        self._run(self.change_photo_button, "Uploading...",
                  lambda: save_user_photo(uid, token, photo_base64),
                  lambda _: (self._show_photo(photo_base64),
                             self._show_photo_message("Your photo was saved.", "success"),
                             self.photo_changed.emit(photo_base64)),
                  self.photo_banner, self.photo_message)

    def _on_remove_photo(self):
        self.photo_message.hide()
        uid, token = session.uid, session.id_token
        self._run(self.remove_photo_button, "Removing...",
                  lambda: remove_user_photo(uid, token),
                  lambda _: (self._show_photo(None),
                             self._show_photo_message("Your photo was removed.", "success"),
                             self.photo_changed.emit("")),
                  self.photo_banner, self.photo_message)

    def _show_photo_message(self, text, kind):
        """Message at the top of the card (photo saved / removed / errors)."""
        self._show_banner(self.photo_banner, text, kind)
        self.photo_message.show()

    # ------------------------------------------------------------ 1. change name
    def _on_save_name(self):
        self.details_banner.hide()
        first = self.first_name_input.text().strip()
        last = self.last_name_input.text().strip()
        if not first:
            self._set_invalid(self.first_name_input, True)
            self._show_banner(self.details_banner, "Please enter your first name.", "error")
            return
        if not last:
            self._set_invalid(self.last_name_input, True)
            self._show_banner(self.details_banner, "Please enter your last name.", "error")
            return

        uid, token = session.uid, session.id_token     # always the newest token
        self._run(self.save_button, "Saving...",
                  lambda: update_user_profile(uid, token, first, last),
                  lambda _: self._on_name_saved(first, last),
                  self.details_banner)

    def _on_name_saved(self, first, last):
        self.user["first_name"], self.user["last_name"] = first, last
        self._update_header(first, last)
        self._show_banner(self.details_banner, "Your name was saved.", "success")
        self.profile_updated.emit({"first_name": first, "last_name": last})

    # ------------------------------------------------------------ 2. change password
    def _on_change_password(self):
        self.password_banner.hide()
        current = self.current_password.text()
        new = self.new_password.text()
        if not current:
            self._set_invalid(self.current_password, True)
            self._show_banner(self.password_banner, "Please enter your current password.", "error")
            return
        if len(new) < 6:
            self._set_invalid(self.new_password, True)
            self._show_banner(self.password_banner, "The new password must be at least 6 characters.", "error")
            return
        if new != self.confirm_password.text():
            self._set_invalid(self.confirm_password, True)
            self._show_banner(self.password_banner, "The new passwords do not match.", "error")
            return
        if new == current:
            self._set_invalid(self.new_password, True)
            self._show_banner(self.password_banner, "The new password is the same as the current one.", "error")
            return

        email = self.user["email"]

        def task():
            fresh = login(email, current)                    # 1. fresh login with the current password
            return change_password(fresh["idToken"], new)   # 2. set the new password -> new tokens

        self._run(self.password_button, "Changing...", task,
                  self._on_password_changed, self.password_banner)

    def _on_password_changed(self, result):
        for field in (self.current_password, self.new_password, self.confirm_password):
            field.clear()
        tokens = {
            "id_token": result["idToken"],
            "refresh_token": result["refreshToken"],
            "expires_in": int(result["expiresIn"]),
        }
        self.user.update(tokens)
        self._show_banner(self.password_banner,
                          "Your password was changed. Other devices were signed out.", "success")
        self.tokens_changed.emit(tokens)

    # ------------------------------------------------------------ 3. delete account
    def _on_delete_account(self):
        self.delete_banner.hide()
        ConfirmOverlay.ask(
            self, "Delete your account?",
            "This permanently deletes your account and all your data. It cannot be undone. "
            "Enter your password to confirm.",
            "Delete account", on_confirm=self._delete_account_now, ask_password=True)

    def _delete_account_now(self, password):
        """The user confirmed in the overlay -> delete (in the background)."""
        email = self.user["email"]

        def task():
            fresh = login(email, password)                          # 1. fresh login
            delete_user_profile(fresh["localId"], fresh["idToken"])  # 2. Firestore first
            delete_account(fresh["idToken"])                        # 3. then Authentication

        self._run(self.delete_button, "Deleting...", task,
                  lambda _: self.account_deleted.emit(), self.delete_banner)

    # ------------------------------------------------------------ helpers
    def _run(self, button, busy_text, task, on_success, banner, banner_box=None):
        """Run `task` in the background; lock `button` meanwhile; show errors in `banner`
        (and show `banner_box` too, if the banner sits inside one)."""
        normal_text = button.text()
        button.setEnabled(False)
        button.setText(busy_text)

        def finish():
            button.setEnabled(True)
            button.setText(normal_text)

        self.worker = TaskWorker(task)
        self.worker.succeeded.connect(lambda result: (finish(), on_success(result)))
        self.worker.failed.connect(lambda message: (
            finish(), self._show_banner(banner, message, "error"), banner_box and banner_box.show()))
        self.worker.start()

    @staticmethod
    def _set_invalid(field, invalid):
        field.setProperty("invalid", invalid)
        field.style().unpolish(field)
        field.style().polish(field)

    @staticmethod
    def _show_banner(banner, text, kind):
        banner.setText(text)
        banner.setProperty("kind", kind)
        banner.style().unpolish(banner)
        banner.style().polish(banner)
        banner.show()


# =====================================================================
# Run this screen alone for testing (with a sample user - nothing is sent
# to Firebase until you click a button)
# =====================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    styles.theme.apply()
    window = GlowBackground()          # the screen sits on the glow background
    screen = ProfileScreen()
    screen.load_user({"uid": "test", "email": "aya@example.com", "id_token": "",
                      "first_name": "Aya", "last_name": "Saeed"})
    screen.profile_updated.connect(lambda names: print("profile_updated:", names))
    screen.tokens_changed.connect(lambda _: print("tokens_changed"))
    screen.account_deleted.connect(lambda: print("account_deleted"))
    screen.photo_changed.connect(lambda photo: print("photo_changed:", "removed" if not photo else "new photo"))
    layout = QVBoxLayout(window)
    layout.setContentsMargins(32, 32, 32, 32)
    layout.addWidget(screen)
    window.setWindowTitle("ErgoMon - Profile")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec_())