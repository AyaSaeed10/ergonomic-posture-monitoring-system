"""
Sidebar - floating glass icon bar on the left of the app (after login).

Top: logo + one icon per page (tooltip on hover, the active page is highlighted).
Bottom: theme switch (sun / moon) and Log out.
Pages that are not built yet show "coming soon" in their tooltip and do nothing.
"""

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from user_app.ui import styles

# (page name, Lucide icon file, tooltip, is the page built yet?)
PAGES = [
    ("monitor", "video", "Monitor", True),
    ("dashboard", "layout-dashboard", "Dashboard", False),
    ("profile", "user", "Profile", False),
    ("settings", "settings", "Settings", False),
    ("help", "circle-question-mark", "Help", False),
]


class Sidebar(QFrame):
    page_selected = pyqtSignal(str)    # sends the page name, e.g. "monitor"
    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__(objectName="GlassPanel")
        self.setFixedWidth(76)
        self.active_page = "monitor"
        self.buttons = {}              # page name -> button

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(8)
        logo = QLabel("EM", objectName="SidebarLogo", alignment=Qt.AlignCenter)
        logo.setFixedSize(40, 40)
        layout.addWidget(logo, 0, Qt.AlignHCenter)
        layout.addSpacing(22)

        for name, icon, label, ready in PAGES:
            button = self._add_button(layout, label if ready else f"{label} (coming soon)")
            if ready:
                button.clicked.connect(lambda _, n=name: self.select_page(n))
            self.buttons[name] = (button, icon)

        layout.addStretch()
        self.theme_button = self._add_button(layout, "")
        self.theme_button.clicked.connect(styles.theme.toggle)
        self.logout_button = self._add_button(layout, "Log out")
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

    def select_page(self, name):
        self.active_page = name
        self._refresh()
        self.page_selected.emit(name)

    def _refresh(self):
        """Redraw icons in the current theme's colors and highlight the active page."""
        colors = styles.theme.colors
        for name, (button, icon) in self.buttons.items():
            active = name == self.active_page
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
            button.setIcon(styles.load_icon(icon, colors["ICON_ACTIVE"] if active else colors["ICON"]))

        dark = styles.theme.name == "dark"   # the icon shows the theme you will switch TO
        self.theme_button.setIcon(styles.load_icon("sun" if dark else "moon", colors["ICON"]))
        self.theme_button.setToolTip("Light mode" if dark else "Dark mode")
        self.logout_button.setIcon(styles.load_icon("log-out", colors["ICON"]))
