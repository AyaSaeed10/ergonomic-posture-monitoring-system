"""
Sidebar - floating glass icon bar on the left of the app (after login).

Top: logo + one icon per page (tooltip on hover, the active page is highlighted).
     If the user has a profile photo, it is shown instead of the Profile icon.
Bottom: theme switch (sun / moon) and Log out.
Pages that are not built yet show "coming soon" in their tooltip and do nothing.

Guest mode (set_guest(True)): only the pages in GUEST_PAGES can be opened. The
others stay visible but dimmed ("locked"); clicking one shows "Create an account
to use this". The Log out button becomes "Sign in" (back to the Login screen).
"""

import base64

from PyQt5.QtCore import QPoint, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QImage
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QToolTip, QVBoxLayout

from user_app.ui import styles
from user_app.ui.profile_screen import round_pixmap

# (page name, Lucide icon file, tooltip, is the page built yet?)
PAGES = [
    ("monitor", "video", "Monitor", True),
    ("dashboard", "layout-dashboard", "Dashboard", False),
    ("profile", "user", "Profile", True),
    ("settings", "settings", "Settings", False),
    ("help", "circle-question-mark", "Help", True),
]
GUEST_PAGES = {"monitor", "help"}   # the only pages a guest can open (main.py checks this too)

PHOTO_SIZE = 30                     # the user's photo on the Profile button (the icons are 22)


class Sidebar(QFrame):
    page_selected = pyqtSignal(str)    # sends the page name, e.g. "monitor"
    logout_requested = pyqtSignal()    # "Log out" (signed in) or "Sign in" (guest)

    def __init__(self):
        super().__init__(objectName="GlassPanel")
        self.setFixedWidth(76)
        self.active_page = "monitor"
        self.guest = False
        self.photo = ""                # the user's photo (Base64) -> shown instead of the Profile icon
        self.buttons = {}              # page name -> (button, icon, label, ready)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(8)
        logo = QLabel("EM", objectName="SidebarLogo", alignment=Qt.AlignCenter)
        logo.setFixedSize(40, 40)
        layout.addWidget(logo, 0, Qt.AlignHCenter)
        layout.addSpacing(22)

        for name, icon, label, ready in PAGES:
            button = self._add_button(layout, "")
            button.clicked.connect(lambda _, n=name: self._on_page_clicked(n))
            self.buttons[name] = (button, icon, label, ready)

        layout.addStretch()
        self.theme_button = self._add_button(layout, "")
        self.theme_button.clicked.connect(styles.theme.toggle)
        self.logout_button = self._add_button(layout, "")
        self.logout_button.clicked.connect(self.logout_requested.emit)

        styles.theme.changed.connect(lambda _: self._refresh())
        self._refresh()

    def _add_button(self, layout, tooltip):
        button = QPushButton(objectName="SidebarButton", toolTip=tooltip)
        button.setFixedSize(48, 48)
        button.setIconSize(QSize(22, 22))
        button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(button, 0, Qt.AlignHCenter)
        return button

    def set_guest(self, guest):
        """Switch between the signed-in look and the guest look (locked pages, "Sign in")."""
        self.guest = guest
        self._refresh()

    def set_photo(self, photo):
        """Show the user's photo instead of the Profile icon ("" -> the normal icon)."""
        self.photo = photo or ""
        self._refresh()

    def _is_locked(self, name):
        return self.guest and name not in GUEST_PAGES

    def _on_page_clicked(self, name):
        button, _, label, ready = self.buttons[name]
        if self._is_locked(name):
            # show the message right away next to the icon (not only on hover)
            QToolTip.showText(button.mapToGlobal(QPoint(button.width() + 4, 12)),
                              button.toolTip(), button)
        elif ready:
            self.select_page(name)

    def select_page(self, name):
        self.active_page = name
        self._refresh()
        self.page_selected.emit(name)

    def _refresh(self):
        """Redraw icons in the current theme's colors and highlight the active page."""
        colors = styles.theme.colors
        for name, (button, icon, label, ready) in self.buttons.items():
            active = name == self.active_page
            if self._is_locked(name):
                tooltip, color = f"{label}: create an account to use this", colors["DISABLED_TEXT"]
            else:
                tooltip = label if ready else f"{label} (coming soon)"
                color = colors["ICON_ACTIVE"] if active else colors["ICON"]
            button.setToolTip(tooltip)
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
            if name == "profile" and self.photo and not self.guest:     # the photo instead of the icon
                image = QImage()
                image.loadFromData(base64.b64decode(self.photo))
                button.setIconSize(QSize(PHOTO_SIZE, PHOTO_SIZE))
                button.setIcon(QIcon(round_pixmap(image, PHOTO_SIZE, button.devicePixelRatioF())))
            else:
                button.setIconSize(QSize(22, 22))
                button.setIcon(styles.load_icon(icon, color))

        dark = styles.theme.name == "dark"   # the icon shows the theme you will switch TO
        self.theme_button.setIcon(styles.load_icon("sun" if dark else "moon", colors["ICON"]))
        self.theme_button.setToolTip("Light mode" if dark else "Dark mode")
        if self.guest:
            self.logout_button.setIcon(styles.load_icon("log-in", colors["ICON"]))
            self.logout_button.setToolTip("Sign in or create an account")
        else:
            self.logout_button.setIcon(styles.load_icon("log-out", colors["ICON"]))
            self.logout_button.setToolTip("Log out")