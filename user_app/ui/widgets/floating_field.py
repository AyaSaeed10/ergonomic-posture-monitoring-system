"""
Floating field - a text box whose label sits inside it like a placeholder,
and smoothly moves up and shrinks when the box is focused or has text
(like Facebook's login form).

It IS a QLineEdit (subclass), so screens use it exactly like one:
text(), setText(), clear(), returnPressed, textChanged, setProperty("invalid", ...).

Password fields also get an eye button on the right (shown only when there
is text) to show / hide the password.
"""

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, pyqtProperty
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt5.QtWidgets import QLineEdit, QToolButton

from user_app.ui import styles

LABEL_LEFT = 15        # x position of the label (matches the text's left padding)
LABEL_TOP = 8          # y position of the label when it is "floated" at the top
FLOATED_SCALE = 0.78   # floated label size compared to the resting one (14px -> ~11px)


class FloatingField(QLineEdit):
    def __init__(self, label, password=False):
        super().__init__(objectName="FloatingField")
        self.label = label
        self._lift = 0.0     # 0 = label resting in the middle, 1 = label floated at the top

        # animates the "lift" property below from its current value to 0 or 1
        self.animation = QPropertyAnimation(self, b"lift", self)
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.textChanged.connect(self._on_text_changed)

        self.eye_button = None
        if password:
            self.setEchoMode(QLineEdit.Password)
            self.eye_button = QToolButton(self, objectName="EyeButton")
            self.eye_button.setCursor(Qt.PointingHandCursor)
            self.eye_button.setFocusPolicy(Qt.NoFocus)    # Tab still jumps field to field
            self.eye_button.setFixedSize(32, 32)
            self.eye_button.setIconSize(QSize(18, 18))
            self.eye_button.clicked.connect(self._toggle_password)
            self.eye_button.hide()
            self.setTextMargins(0, 0, 34, 0)              # typed text must not go under the eye
            styles.theme.changed.connect(lambda _: self._update_eye_icon())
            self._update_eye_icon()

    # ------------------------------------------------------------ "lift" property (animated)
    def get_lift(self):
        return self._lift

    def set_lift(self, value):
        self._lift = value
        self.update()          # repaint with the label at its new position / size

    lift = pyqtProperty(float, get_lift, set_lift)

    def _move_label(self):
        """Float the label up if the box is focused or has text, otherwise rest it."""
        target = 1.0 if (self.hasFocus() or self.text()) else 0.0
        if self.animation.endValue() != target or self.animation.state() != QPropertyAnimation.Running:
            self.animation.stop()
            self.animation.setStartValue(self._lift)
            self.animation.setEndValue(target)
            self.animation.start()

    # ------------------------------------------------------------ events
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._move_label()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._move_label()

    def _on_text_changed(self, text):
        self._move_label()
        if self.eye_button:
            self.eye_button.setVisible(bool(text))
            if not text:                                  # field cleared -> hide password again
                self.setEchoMode(QLineEdit.Password)
                self._update_eye_icon()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.eye_button:   # keep the eye at the right edge, vertically centered
            self.eye_button.move(self.width() - self.eye_button.width() - 10,
                                 (self.height() - self.eye_button.height()) // 2)

    # ------------------------------------------------------------ password eye
    def _toggle_password(self):
        hidden = self.echoMode() == QLineEdit.Password
        self.setEchoMode(QLineEdit.Normal if hidden else QLineEdit.Password)
        self._update_eye_icon()

    def _update_eye_icon(self):
        hidden = self.echoMode() == QLineEdit.Password
        # eye = "click to show", eye-off = "click to hide"
        self.eye_button.setIcon(styles.load_icon("eye" if hidden else "eye-off",
                                                 styles.theme.colors["MUTED"], 18))
        self.eye_button.setToolTip("Show password" if hidden else "Hide password")

    # ------------------------------------------------------------ drawing the label
    def paintEvent(self, event):
        super().paintEvent(event)          # the normal text box first, then the label on top
        colors = styles.theme.colors
        if self.property("invalid"):
            color = colors["ERROR"]
        elif self.hasFocus():
            color = colors["LINK"]
        else:
            color = colors["MUTED"]

        font = QFont(self.font())
        font.setPixelSize(14)
        if self._lift > 0:
            font.setWeight(QFont.Medium)
        text_height = QFontMetrics(font).height()

        # move between the resting spot (middle) and the floated spot (top), and shrink
        rest_y = (self.height() - text_height) / 2
        y = rest_y + (LABEL_TOP - rest_y) * self._lift
        scale = 1 - (1 - FLOATED_SCALE) * self._lift

        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.translate(LABEL_LEFT, y)
        painter.scale(scale, scale)        # scaling (not font size steps) = smooth shrinking
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(0, QFontMetrics(font).ascent(), self.label)
