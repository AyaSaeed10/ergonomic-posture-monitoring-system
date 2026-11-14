"""
Help screen - FRONTEND (text only, no Firebase, no camera).

One glass card: topics on the left, the chosen topic on the right.
  1. Camera setup     - drawing (top view + what the camera sees) and numbered steps
  2. Setup checklist  - what each check means and how to fix it
  3. Posture tips     - neck, lower back, breaks
  4. FAQ              - questions that open / close on click
  5. About            - the project, the team, the technologies

Guests can open this page too (they need the camera guide the most).

Run this screen alone (from the project root):
    python -m user_app.ui.help_screen
"""

import re
import sys

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QTransform
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QStackedWidget,
    QVBoxLayout, QWidget,
)

from user_app.ui import styles
from user_app.ui.widgets.glow_background import GlowBackground


# =====================================================================
# The texts (from the Phase A book) - change them here, not in the layout code
# =====================================================================
CAMERA_STEPS = [
    ("Place the camera at your side",
     "Left or right of you - not in front. ErgoMon reads your posture from the side."),
    ("1.5 – 2 m away, at shoulder height",
     "Close enough to see you clearly, far enough to see your whole upper body and knees."),
    ("Ear, shoulder, hip and knee in the frame",
     "These four points are used to measure your neck angle and your back angle."),
    ("Good light, calm background",
     "Light in front of you or from above. Avoid a bright window behind you."),
    ("Sit as you normally work",
     "Don't pose for the camera - ErgoMon learns from your real working posture."),
]

CHECKLIST_ITEMS = [
    ("Camera connected",
     "ErgoMon can open your camera.",
     "Check the cable, choose another camera in the list, or close apps that use it (Zoom, Teams)."),
    ("Side view detected",
     "The camera sees you from the side.",
     "Turn the camera so it faces your shoulder, not your face."),
    ("Distance 1.5 – 2 m",
     "You are at a good distance from the camera.",
     "Move the camera closer or further until the check turns green."),
    ("Ear, shoulder, hip, knee visible",
     "All four body points are inside the frame.",
     "Move the camera back or lower it a little, and make sure nothing covers you."),
]

POSTURE_TIPS = [
    ("Neck", [
        "Keep your ears above your shoulders - don't push your head forward.",
        "Raise the screen so its top edge is at eye level.",
        "Bring the screen closer instead of leaning towards it.",
    ]),
    ("Lower back", [
        "Sit all the way back and let the chair support your lower back.",
        "Keep your back straight - avoid slouching or leaning far back.",
        "Feet flat on the floor, knees at about 90°.",
    ]),
    ("Breaks", [
        "Stand up and move for a few minutes every 45–60 minutes.",
        "Use the break for a short neck or back stretch.",
        "Change position from time to time - no posture is good for hours.",
    ]),
]

FAQ = [
    ("Is my video saved or sent anywhere?",
     "No. The video is analysed only on your computer and is never uploaded. "
     "Only results such as your posture score and alerts are saved to your account."),
    ("Why didn't I get an alert?",
     "Alerts appear only when a bad posture lasts for a few seconds, so short movements "
     "don't disturb you. Also check that all items in the setup checklist are green."),
    ("How do I change the camera?",
     "Open the Monitor page and choose another camera from the list at the top of the camera card."),
    ("Can I use ErgoMon without an account?",
     "Yes - choose \"Continue without an account\" on the login screen. "
     "Monitoring works, but nothing is saved."),
    ("I forgot my password.",
     "On the login screen, type your email and click \"Forgot password?\". "
     "We will email you a link to choose a new password."),
    ("How do I change my name or delete my account?",
     "Open the Profile page from the sidebar."),
]

TECHNOLOGIES = ["Python", "PyQt5", "OpenCV", "MediaPipe Pose", "scikit-learn", "Firebase"]


# =====================================================================
# Colors for painting: styles.theme.colors may hold "#RRGGBB" or "rgba(r, g, b, a)"
# =====================================================================
def theme_color(name, alpha=None):
    value = styles.theme.colors[name]
    color = QColor(value) if isinstance(value, str) else QColor(*value)
    if isinstance(value, str) and not color.isValid():
        numbers = [float(n) for n in re.findall(r"[\d.]+", value)]
        color = QColor(int(numbers[0]), int(numbers[1]), int(numbers[2]))
        if len(numbers) > 3:
            color.setAlphaF(numbers[3] if numbers[3] <= 1 else numbers[3] / 255)
    if alpha is not None:
        color.setAlphaF(alpha)
    return color


# =====================================================================
# The drawing on the "Camera setup" page (painted in the theme's colors)
# =====================================================================
class CameraSetupDrawing(QWidget):
    """Left: the room from above (camera at your side, 1.5-2 m).
    Right: what the camera sees (your profile with the 4 body points)."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(230)
        styles.theme.changed.connect(lambda _: self.update())   # repaint in the new colors

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        half = self.width() / 2
        self._box(painter, QRectF(0, 0, half - 8, self.height()), "From above")
        self._box(painter, QRectF(half + 8, 0, half - 8, self.height()), "What the camera sees")
        self._draw_top_view(painter, QRectF(0, 30, half - 8, self.height() - 30))
        self._draw_side_view(painter, QRectF(half + 8, 30, half - 8, self.height() - 30))
        painter.end()

    def _box(self, painter, rect, title):
        painter.setPen(QPen(theme_color("BORDER"), 1))
        painter.setBrush(theme_color("CAMERA_BG", 0.55))
        painter.drawRoundedRect(rect, 18, 18)
        painter.setPen(theme_color("MUTED"))
        font = QFont(self.font())
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect.adjusted(16, 10, 0, 0), Qt.AlignLeft | Qt.AlignTop, title)

    def _label(self, painter, x, y, text, color, align=Qt.AlignLeft):
        font = QFont(self.font())
        font.setPixelSize(11)
        painter.setFont(font)
        painter.setPen(color)
        rect = QRectF(x, y - 8, 120, 16) if align == Qt.AlignLeft else QRectF(x - 120, y - 8, 120, 16)
        painter.drawText(rect, align | Qt.AlignVCenter, text)

    # ------------------------------------------------------------ from above
    def _draw_top_view(self, painter, r):
        line = theme_color("MUTED")
        camera = theme_color("ACCENT")
        cx = r.center().x() + 40            # the person sits a bit right of the middle
        cy = r.top() + r.height() * 0.58

        # desk + screen in front of the person (above them in this view)
        painter.setPen(QPen(line, 1.5))
        painter.setBrush(theme_color("MUTED", 0.12))
        painter.drawRoundedRect(QRectF(cx - 70, r.top() + 14, 140, 34), 6, 6)
        painter.setPen(QPen(line, 3, cap=Qt.RoundCap))
        painter.drawLine(QPointF(cx - 28, r.top() + 24), QPointF(cx + 28, r.top() + 24))

        # chair, shoulders and head (looking at the screen)
        painter.setPen(QPen(line, 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(QRectF(cx - 30, cy - 4, 60, 40), 10, 10)
        painter.setBrush(theme_color("MUTED", 0.35))
        painter.drawEllipse(QPointF(cx, cy + 4), 34, 13)            # shoulders
        painter.setBrush(theme_color("TEXT", 0.85))
        painter.drawEllipse(QPointF(cx, cy + 2), 11, 11)            # head

        # camera at the person's side + its view towards them
        cam = QPointF(r.left() + 46, cy + 4)
        view = QPainterPath(cam)
        view.lineTo(cx - 36, cy - 26)
        view.lineTo(cx - 36, cy + 34)
        view.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(theme_color("ACCENT", 0.16))
        painter.drawPath(view)
        painter.setBrush(camera)
        painter.drawRoundedRect(QRectF(cam.x() - 18, cam.y() - 10, 22, 20), 4, 4)
        lens = QPainterPath()
        lens.moveTo(cam.x() + 4, cam.y() - 5)
        lens.lineTo(cam.x() + 12, cam.y() - 9)
        lens.lineTo(cam.x() + 12, cam.y() + 9)
        lens.lineTo(cam.x() + 4, cam.y() + 5)
        lens.closeSubpath()
        painter.drawPath(lens)
        self._label(painter, cam.x() - 18, cam.y() + 24, "Camera", camera)

        # distance arrow under the view
        y = cy + 52
        pen = QPen(theme_color("LINK"), 1.5, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(cam.x(), y), QPointF(cx - 6, y))
        painter.setPen(QPen(theme_color("LINK"), 1.5))
        for x, d in ((cam.x(), 1), (cx - 6, -1)):
            painter.drawLine(QPointF(x, y), QPointF(x + 7 * d, y - 4))
            painter.drawLine(QPointF(x, y), QPointF(x + 7 * d, y + 4))
        self._label(painter, (cam.x() + cx) / 2 - 26, y - 12, "1.5 – 2 m", theme_color("LINK"))

    # ------------------------------------------------------------ what the camera sees
    def _draw_side_view(self, painter, r):
        line = theme_color("MUTED")
        body = theme_color("TEXT", 0.8)
        dot = theme_color("PRIMARY_START")
        floor_y = r.bottom() - 16
        x0 = r.left() + r.width() * 0.40          # the chair
        seat_y = floor_y - 52

        # floor, chair, desk + screen
        painter.setPen(QPen(theme_color("MUTED", 0.5), 1.5))
        painter.drawLine(QPointF(r.left() + 16, floor_y), QPointF(r.right() - 16, floor_y))
        painter.setPen(QPen(line, 2, cap=Qt.RoundCap))
        painter.drawLine(QPointF(x0 - 26, seat_y), QPointF(x0 + 24, seat_y))          # seat
        painter.drawLine(QPointF(x0 - 26, seat_y), QPointF(x0 - 31, seat_y - 58))     # backrest
        painter.drawLine(QPointF(x0, seat_y), QPointF(x0, floor_y))                   # chair leg
        desk_x = x0 + 104
        desk_y = floor_y - 78
        painter.drawLine(QPointF(desk_x - 26, desk_y), QPointF(desk_x + 40, desk_y))  # desk top
        painter.drawLine(QPointF(desk_x + 30, desk_y), QPointF(desk_x + 30, floor_y)) # desk leg
        painter.setPen(QPen(line, 3, cap=Qt.RoundCap))
        painter.drawLine(QPointF(desk_x + 22, desk_y - 6), QPointF(desk_x + 22, desk_y - 44))  # screen

        # the person (side view) and the 4 points ErgoMon uses
        ear = QPointF(x0 - 8, seat_y - 92)
        shoulder = QPointF(x0 - 12, seat_y - 64)
        hip = QPointF(x0 - 14, seat_y - 6)
        knee = QPointF(x0 + 46, seat_y - 8)
        foot = QPointF(x0 + 50, floor_y - 2)
        hand = QPointF(desk_x - 10, desk_y - 5)

        painter.setPen(QPen(body, 4, cap=Qt.RoundCap, join=Qt.RoundJoin))
        for a, b in ((shoulder, hip), (hip, knee), (knee, foot), (shoulder, hand)):
            painter.drawLine(a, b)
        painter.setPen(Qt.NoPen)
        painter.setBrush(body)
        painter.drawEllipse(QPointF(ear.x() + 4, ear.y() - 1), 11, 13)               # head

        # the lines ErgoMon measures: neck (ear-shoulder) and back (shoulder-hip)
        painter.setPen(QPen(dot, 2, Qt.DashLine))
        painter.drawLine(ear, shoulder)
        painter.drawLine(shoulder, hip)
        for point in (ear, shoulder, hip, knee):
            painter.setPen(QPen(theme_color("CAMERA_BG"), 2))
            painter.setBrush(dot)
            painter.drawEllipse(point, 5.5, 5.5)

        label = theme_color("LABEL")
        self._label(painter, ear.x() - 16, ear.y(), "Ear", label, Qt.AlignRight)
        self._label(painter, shoulder.x() - 16, shoulder.y(), "Shoulder", label, Qt.AlignRight)
        self._label(painter, hip.x() - 16, hip.y(), "Hip", label, Qt.AlignRight)
        self._label(painter, knee.x() - 10, knee.y() - 16, "Knee", label)


# =====================================================================
# Small building blocks
# =====================================================================
class FaqItem(QFrame):
    """A question that opens / closes its answer when clicked."""

    def __init__(self, question, answer):
        super().__init__(objectName="FaqItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("open", False)

        self.chevron = QLabel()
        self.chevron.setFixedSize(18, 18)
        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(QLabel(question, objectName="FaqQuestion", wordWrap=True), 1)
        header.addWidget(self.chevron, 0, Qt.AlignTop)

        self.answer = QLabel(answer, objectName="HelpText", wordWrap=True)
        self.answer.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.answer)

        styles.theme.changed.connect(lambda _: self._update_chevron())
        self._update_chevron()

    def mousePressEvent(self, event):
        self.set_open(not self.property("open"))
        super().mousePressEvent(event)

    def set_open(self, is_open):
        self.setProperty("open", is_open)
        self.style().unpolish(self)
        self.style().polish(self)
        self.answer.setVisible(is_open)
        self._update_chevron()

    def _update_chevron(self):
        icon = styles.load_icon("chevron-down", styles.theme.colors["ICON"])
        pixmap = icon.pixmap(18, 18)
        if self.property("open"):                       # point up when open
            pixmap = pixmap.transformed(QTransform().rotate(180))
        self.chevron.setPixmap(pixmap)


def numbered_step(number, title, text):
    """ (1)  Title
             explanation """
    badge = QLabel(str(number), objectName="StepNumber", alignment=Qt.AlignCenter)
    badge.setFixedSize(28, 28)
    words = QVBoxLayout()
    words.setSpacing(2)
    words.addWidget(QLabel(title, objectName="HelpItemTitle", wordWrap=True))
    words.addWidget(QLabel(text, objectName="HelpText", wordWrap=True))
    row = QHBoxLayout()
    row.setSpacing(14)
    row.addWidget(badge, 0, Qt.AlignTop)
    row.addLayout(words, 1)
    return row


def bullet(text):
    """ •  text """
    dot = QLabel("•", objectName="HelpBullet")
    dot.setFixedWidth(12)
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addWidget(dot, 0, Qt.AlignTop)
    row.addWidget(QLabel(text, objectName="HelpText", wordWrap=True), 1)
    return row


# =====================================================================
# The screen
# =====================================================================
class HelpScreen(QWidget):
    TOPICS = [
        # (key, title shown in the menu, Lucide icon)
        ("camera", "Camera setup", "video"),
        ("checklist", "Setup checklist", "list-checks"),
        ("posture", "Posture tips", "person-standing"),
        ("faq", "FAQ", "circle-question-mark"),
        ("about", "About", "info"),
    ]

    def __init__(self):
        super().__init__()
        self.setObjectName("Root")                       # see-through -> the glows show
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.nav_buttons = {}
        self._build_ui()
        styles.theme.changed.connect(lambda _: self._refresh_nav())
        self.show_topic("camera")

    # ------------------------------------------------------------ layout
    def _build_ui(self):
        card = QFrame(objectName="GlassPanel")
        styles.add_glass_shadow(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(0)

        layout.addWidget(QLabel("Help & guide", objectName="Title"))
        layout.addSpacing(4)
        layout.addWidget(QLabel("Everything you need to get the most out of ErgoMon.",
                                objectName="Subtitle"))
        layout.addSpacing(22)
        divider = QFrame(objectName="Divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        layout.addSpacing(22)

        body = QHBoxLayout()
        body.setSpacing(32)
        body.addLayout(self._build_menu())
        self.pages = QStackedWidget()
        self.page_index = {}
        for key, title, _ in self.TOPICS:
            self.page_index[key] = self.pages.addWidget(self._scrollable(self._build_page(key, title)))
        body.addWidget(self.pages, 1)
        layout.addLayout(body, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(card)

    def _build_menu(self):
        menu = QVBoxLayout()
        menu.setSpacing(6)
        for key, title, icon in self.TOPICS:
            button = QPushButton("   " + title, objectName="HelpNavButton")   # spaces = gap after the icon
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedWidth(210)
            button.clicked.connect(lambda _, k=key: self.show_topic(k))
            menu.addWidget(button)
            self.nav_buttons[key] = (button, icon)
        menu.addStretch()
        return menu

    @staticmethod
    def _scrollable(page):
        """Long pages scroll inside the card (the card itself never grows)."""
        scroll = QScrollArea(objectName="HelpScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        return scroll

    def _build_page(self, key, title):
        page = QWidget(objectName="HelpPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 14, 0)          # room for the scrollbar
        layout.setSpacing(0)
        layout.addWidget(QLabel(title, objectName="PanelTitle"))
        layout.addSpacing(18)
        builders = {
            "camera": self._camera_page,
            "checklist": self._checklist_page,
            "posture": self._posture_page,
            "faq": self._faq_page,
            "about": self._about_page,
        }
        builders[key](layout)
        layout.addStretch()
        return page

    # ------------------------------------------------------------ the 5 pages
    def _camera_page(self, layout):
        layout.addWidget(CameraSetupDrawing())
        layout.addSpacing(24)
        for number, (title, text) in enumerate(CAMERA_STEPS, start=1):
            layout.addLayout(numbered_step(number, title, text))
            layout.addSpacing(16)

    def _checklist_page(self, layout):
        layout.addWidget(QLabel("The checklist on the Monitor page must be all green before "
                                "monitoring starts. Here is what each check means:",
                                objectName="HelpText", wordWrap=True))
        layout.addSpacing(18)
        for number, (title, meaning, fix) in enumerate(CHECKLIST_ITEMS, start=1):
            layout.addLayout(numbered_step(number, title, f"{meaning}\nIf it fails: {fix}"))
            layout.addSpacing(16)

    def _posture_page(self, layout):
        for title, tips in POSTURE_TIPS:
            layout.addWidget(QLabel(title, objectName="HelpItemTitle"))
            layout.addSpacing(8)
            for tip in tips:
                layout.addLayout(bullet(tip))
                layout.addSpacing(6)
            layout.addSpacing(16)

    def _faq_page(self, layout):
        for question, answer in FAQ:
            layout.addWidget(FaqItem(question, answer))
            layout.addSpacing(10)

    def _about_page(self, layout):
        header = QHBoxLayout()
        header.setSpacing(16)
        logo = QLabel("EM", objectName="SidebarLogo", alignment=Qt.AlignCenter)
        logo.setFixedSize(48, 48)
        header.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(2)
        names.addWidget(QLabel("ErgoMon", objectName="HelpItemTitle"))
        names.addWidget(QLabel("AI-based ergonomic posture monitoring", objectName="HelpText"))
        header.addLayout(names, 1)
        layout.addLayout(header)
        layout.addSpacing(18)

        layout.addWidget(QLabel(
            "ErgoMon watches your neck and lower-back posture through a side camera while you "
            "work at the computer. It recognises bad posture with computer vision and machine "
            "learning, alerts you only when it is really needed, and helps you build healthier "
            "sitting habits over time.", objectName="HelpText", wordWrap=True))
        layout.addSpacing(22)

        for label, value in (("Team", "Aya Saeed · Marwan Zayyad"),
                             ("Advisor", "Dr. Reuven Cohen"),
                             ("Project", "Final Project (61998) · Braude College of Engineering")):
            row = QHBoxLayout()
            name = QLabel(label, objectName="FieldLabel")
            name.setFixedWidth(90)
            row.addWidget(name, 0, Qt.AlignTop)
            row.addWidget(QLabel(value, objectName="HelpText", wordWrap=True), 1)
            layout.addLayout(row)
            layout.addSpacing(10)
        layout.addSpacing(12)

        layout.addWidget(QLabel("Built with", objectName="FieldLabel"))
        layout.addSpacing(10)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        for tech in TECHNOLOGIES:
            chips.addWidget(QLabel(tech, objectName="HelpChip"))
        chips.addStretch()
        layout.addLayout(chips)

    # ------------------------------------------------------------ switching topics
    def show_topic(self, key):
        self.active_topic = key
        self.pages.setCurrentIndex(self.page_index[key])
        self.pages.currentWidget().verticalScrollBar().setValue(0)   # always start at the top
        self._refresh_nav()

    def _refresh_nav(self):
        colors = styles.theme.colors
        for key, (button, icon) in self.nav_buttons.items():
            active = key == self.active_topic
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
            button.setIcon(styles.load_icon(icon, colors["LINK"] if active else colors["ICON"]))


# =====================================================================
# Run this screen alone for testing
# =====================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    styles.theme.apply()
    window = GlowBackground()          # the screen sits on the glow background
    layout = QVBoxLayout(window)
    layout.setContentsMargins(32, 32, 32, 32)
    layout.addWidget(HelpScreen())
    window.setWindowTitle("ErgoMon - Help")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec_())