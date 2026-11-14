"""
Confirm overlay - an "Are you sure?" box INSIDE the app window (not a separate Windows window).

It covers the whole window with a dim layer (#Overlay, color OVERLAY_BG) and shows a card
(#OverlayCard, color POPUP_BG) in the middle. The screen behind can't be clicked until the user answers.

    ConfirmOverlay.ask(self, "Delete your account?", "This cannot be undone.",
                       "Delete account", on_confirm=self.delete_now, ask_password=True)

on_confirm gets the typed password ("" when ask_password is False).
Cancel button or Esc -> the overlay just closes.
"""

from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from user_app.ui import styles
from user_app.ui.widgets.floating_field import FloatingField


class ConfirmOverlay(QWidget):
    confirmed = pyqtSignal(str)    # the password ("" if no password was asked)
    cancelled = pyqtSignal()

    def __init__(self, host, title, message, confirm_text, ask_password=False):
        super().__init__(host)                           # a child of the app window
        self.setObjectName("Overlay")                    # dim layer (styles.py)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.host = host
        self.ask_password = ask_password

        # ---- the card in the middle (solid POPUP_BG, so the screen behind doesn't show through)
        card = QFrame(objectName="OverlayCard")
        card.setFixedWidth(480)
        styles.add_glass_shadow(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)

        layout.addWidget(QLabel(title, objectName="PanelTitle"))
        layout.addSpacing(8)
        layout.addWidget(QLabel(message, objectName="PanelSubtitle", wordWrap=True))

        if ask_password:
            layout.addSpacing(20)
            self.password_input = FloatingField("Password", password=True)
            self.password_input.returnPressed.connect(self._confirm)
            self.password_input.textChanged.connect(lambda _: self._set_error(""))
            layout.addWidget(self.password_input)
            layout.addSpacing(4)
            self.error = QLabel("", objectName="FieldError")
            self.error.setFixedHeight(16)
            layout.addWidget(self.error)
        layout.addSpacing(20)

        # [ ........ Cancel ] [ Confirm ]
        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addStretch()
        cancel = QPushButton("Cancel", objectName="TextButton")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setFixedWidth(120)
        cancel.clicked.connect(self._cancel)
        buttons.addWidget(cancel)
        confirm = QPushButton(confirm_text, objectName="DangerButton")
        confirm.setCursor(Qt.PointingHandCursor)
        confirm.setFixedWidth(190)
        confirm.clicked.connect(self._confirm)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)

        # ---- the card sits in the center of the dim layer
        center = QVBoxLayout(self)
        center.addWidget(card, 0, Qt.AlignCenter)

        # cover the whole window, now and whenever it is resized
        host.installEventFilter(self)
        self.setGeometry(host.rect())
        self.show()
        self.raise_()                                    # above everything (even the theme button)
        if ask_password:
            self.password_input.setFocus()
        else:
            self.setFocus()

    # ------------------------------------------------------------ follow the window size
    def eventFilter(self, watched, event):
        if watched is self.host and event.type() == QEvent.Resize:
            self.setGeometry(self.host.rect())
        return False

    # ------------------------------------------------------------ answers
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._cancel()
        else:
            super().keyPressEvent(event)

    def _confirm(self):
        if self.ask_password and not self.password_input.text():
            self._set_error("Please enter your password")
            self.password_input.setFocus()
            return
        password = self.password_input.text() if self.ask_password else ""
        self._close()
        self.confirmed.emit(password)

    def _cancel(self):
        self._close()
        self.cancelled.emit()

    def _close(self):
        self.host.removeEventFilter(self)
        self.hide()
        self.deleteLater()

    def _set_error(self, message):
        self.error.setText(message)
        self.password_input.setProperty("invalid", bool(message))
        self.password_input.style().unpolish(self.password_input)
        self.password_input.style().polish(self.password_input)

    # ------------------------------------------------------------ the easy way to use it
    @staticmethod
    def ask(widget, title, message, confirm_text, on_confirm, ask_password=False):
        """Show the overlay over the window that holds `widget`.
        on_confirm(password) runs only if the user confirms."""
        overlay = ConfirmOverlay(widget.window(), title, message, confirm_text, ask_password)
        overlay.confirmed.connect(on_confirm)
        return overlay