"""
ErgoMon design system - "glass" style, Light / Dark themes for the WHOLE app.

- DARK and LIGHT hold the colors of each theme (the "design tokens").
- build_stylesheet() turns a color set into a stylesheet (QSS = CSS for Qt).
- load_fonts() registers the bundled Sora / Inter fonts with Qt.
- add_glass_shadow() gives a glass panel its soft drop shadow.
- `theme` is ONE object shared by all screens: theme.toggle() switches
  the whole application, and the choice is remembered for next time.

The glowing background behind the screens is painted by
user_app/ui/widgets/glow_background.py using the GLOWS colors below.
"""

from pathlib import Path

from PyQt5.QtCore import QObject, QSettings, pyqtSignal
from PyQt5.QtGui import QColor, QFontDatabase
from PyQt5.QtWidgets import QApplication, QGraphicsDropShadowEffect

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def rgba(r, g, b, opacity):
    """Color with transparency for QSS. opacity is 0..1 (e.g. 0.09 = 9%).
    QSS expects alpha as 0..255, so we convert it here."""
    return f"rgba({r}, {g}, {b}, {round(opacity * 255)})"


# ======================================================================
# 1. Color sets
# ======================================================================
# GLOWS: big soft color spots painted behind everything.
#   (x, y) = center as a fraction of the window (0..1, may be outside),
#   radius = fraction of the window's longer side, color = (r, g, b, opacity).
# SHADOW: color of the glass panels' drop shadow (r, g, b, opacity).
DARK = {
    "BACKGROUND": "#070A12",
    "GLOWS": [
        {"x": 0.05, "y": 0.02, "radius": 0.60, "color": (108, 123, 255, 0.35)},  # indigo, top-left
        {"x": 0.98, "y": 1.00, "radius": 0.60, "color": (25, 195, 181, 0.25)},   # teal, bottom-right
        {"x": 0.62, "y": -0.08, "radius": 0.45, "color": (154, 107, 255, 0.24)}, # violet, top
    ],
    # glass panel
    "GLASS_TOP": rgba(255, 255, 255, 0.09),
    "GLASS_BOTTOM": rgba(255, 255, 255, 0.025),
    "GLASS_BORDER": rgba(255, 255, 255, 0.11),
    "GLASS_HIGHLIGHT": rgba(255, 255, 255, 0.22),   # brighter top edge
    "SHADOW": (0, 0, 0, 0.55),
    # text
    "TEXT": "#E9ECF5",
    "MUTED": "#9AA3B8",
    "LABEL": "#C9CFDD",
    # inputs
    "INPUT_BG": rgba(255, 255, 255, 0.04),
    "INPUT_FOCUS_BG": rgba(255, 255, 255, 0.07),
    "INPUT_BORDER": rgba(255, 255, 255, 0.12),
    "INPUT_BORDER_HOVER": rgba(255, 255, 255, 0.22),
    "BORDER": rgba(255, 255, 255, 0.10),            # thin tracks (e.g. strength bar)
    # primary action (same gradient in both themes)
    "PRIMARY_START": "#6C7BFF",
    "PRIMARY_END": "#9A6BFF",
    "PRIMARY_HOVER_START": "#7E8BFF",
    "PRIMARY_HOVER_END": "#A97FFF",
    "PRIMARY_PRESSED_START": "#5A69EE",
    "PRIMARY_PRESSED_END": "#8758F0",
    "DISABLED_BG": rgba(255, 255, 255, 0.08),
    "DISABLED_TEXT": "#6B7489",
    "LINK": "#8E9AFF",
    "LINK_HOVER": "#B4BCFF",
    # colors with meaning
    "SUCCESS": "#34E3A4",   # good
    "WARNING": "#FFB547",
    "ERROR": "#FF7A6B",     # stop / danger
    "ACCENT": "#19C3B5",    # teal
    "SUCCESS_BG": rgba(52, 227, 164, 0.10),
    "SUCCESS_BORDER": rgba(52, 227, 164, 0.30),
    "ERROR_BG": rgba(255, 122, 107, 0.10),
    "ERROR_BORDER": rgba(255, 122, 107, 0.30),
}

LIGHT = {
    "BACKGROUND": "#EEF1FA",
    "GLOWS": [
        {"x": 0.05, "y": 0.02, "radius": 0.60, "color": (108, 123, 255, 0.28)},
        {"x": 0.98, "y": 1.00, "radius": 0.60, "color": (25, 195, 181, 0.20)},
        {"x": 0.62, "y": -0.08, "radius": 0.45, "color": (154, 107, 255, 0.20)},
    ],
    "GLASS_TOP": rgba(255, 255, 255, 0.72),
    "GLASS_BOTTOM": rgba(255, 255, 255, 0.45),
    "GLASS_BORDER": rgba(20, 30, 70, 0.08),
    "GLASS_HIGHLIGHT": rgba(255, 255, 255, 1.0),
    "SHADOW": (40, 50, 110, 0.12),
    "TEXT": "#141A2E",
    "MUTED": "#5C6680",
    "LABEL": "#2A3248",
    "INPUT_BG": rgba(255, 255, 255, 0.60),
    "INPUT_FOCUS_BG": rgba(255, 255, 255, 0.95),
    "INPUT_BORDER": rgba(20, 30, 70, 0.12),
    "INPUT_BORDER_HOVER": rgba(20, 30, 70, 0.22),
    "BORDER": rgba(20, 30, 70, 0.10),
    "PRIMARY_START": "#6C7BFF",
    "PRIMARY_END": "#9A6BFF",
    "PRIMARY_HOVER_START": "#7E8BFF",
    "PRIMARY_HOVER_END": "#A97FFF",
    "PRIMARY_PRESSED_START": "#5A69EE",
    "PRIMARY_PRESSED_END": "#8758F0",
    "DISABLED_BG": rgba(20, 30, 70, 0.10),
    "DISABLED_TEXT": "#8A93A8",
    "LINK": "#4F5BE0",
    "LINK_HOVER": "#3A45C2",
    "SUCCESS": "#087A54",
    "WARNING": "#955800",
    "ERROR": "#C23A27",
    "ACCENT": "#0B7F77",
    "SUCCESS_BG": rgba(8, 122, 84, 0.08),
    "SUCCESS_BORDER": rgba(8, 122, 84, 0.25),
    "ERROR_BG": rgba(194, 58, 39, 0.08),
    "ERROR_BORDER": rgba(194, 58, 39, 0.25),
}


# ======================================================================
# 2. Stylesheet built from a color set
# ======================================================================
def build_stylesheet(c):
    return f"""
QWidget {{
    font-family: "Inter", "Segoe UI";
    font-size: 14px;
    color: {c["TEXT"]};
}}
/* screens are see-through: the glow background behind them shows */
QMainWindow, QStackedWidget, #Root {{ background: transparent; }}

/* ---------- glass panel ---------- */
#GlassPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {c["GLASS_TOP"]}, stop:1 {c["GLASS_BOTTOM"]});
    border: 1px solid {c["GLASS_BORDER"]};
    border-top-color: {c["GLASS_HIGHLIGHT"]};
    border-radius: 26px;
}}

/* ---------- brand message (left side of login / register) ---------- */
#BrandPanel {{ background: transparent; }}
#BrandPanel QLabel {{ background: transparent; }}
#BrandPanel #Logo {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 {c["PRIMARY_START"]}, stop:1 {c["PRIMARY_END"]});
    color: white;
    border-radius: 16px;
    font-family: "Sora";
    font-size: 20px;
    font-weight: 700;
}}
#BrandName {{ font-family: "Sora"; font-size: 40px; font-weight: 700; }}
#BrandTagline {{ font-size: 17px; color: {c["MUTED"]}; }}
#Feature {{ font-size: 14px; font-weight: 500; }}
#BrandPanel #FeatureIcon {{
    background: {c["SUCCESS_BG"]};
    border: 1px solid {c["SUCCESS_BORDER"]};
    color: {c["SUCCESS"]};
    border-radius: 12px;
    font-weight: 700;
}}
#BrandFooter {{ font-size: 12px; color: {c["MUTED"]}; }}

/* ---------- form ---------- */
#Title {{ font-family: "Sora"; font-size: 26px; font-weight: 700; }}
#Subtitle {{ font-size: 14px; color: {c["MUTED"]}; }}
#FieldLabel {{ font-size: 13px; font-weight: 600; color: {c["LABEL"]}; }}
#FieldError {{ font-size: 12px; font-weight: 500; color: {c["ERROR"]}; }}
#Hint {{ font-size: 13px; color: {c["MUTED"]}; }}

QLineEdit {{
    min-height: 44px;
    background: {c["INPUT_BG"]};
    border: 1px solid {c["INPUT_BORDER"]};
    border-radius: 12px;
    padding: 0 14px;
    font-size: 14px;
    color: {c["TEXT"]};
    selection-background-color: {c["PRIMARY_START"]};
    selection-color: white;
}}
QLineEdit:hover {{ border-color: {c["INPUT_BORDER_HOVER"]}; }}
QLineEdit:focus {{ border-color: {c["PRIMARY_START"]}; background: {c["INPUT_FOCUS_BG"]}; }}
QLineEdit[invalid="true"] {{ border-color: {c["ERROR"]}; background: {c["ERROR_BG"]}; }}

QCheckBox {{ color: {c["MUTED"]}; font-size: 13px; spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {c["INPUT_BORDER_HOVER"]}; border-radius: 5px;
    background: {c["INPUT_BG"]};
}}
QCheckBox::indicator:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 {c["PRIMARY_START"]}, stop:1 {c["PRIMARY_END"]});
    border-color: {c["PRIMARY_START"]};
}}

QProgressBar {{
    background: {c["BORDER"]};
    border: none;
    border-radius: 3px;
    max-height: 6px;
}}

#PrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {c["PRIMARY_START"]}, stop:1 {c["PRIMARY_END"]});
    color: white;
    border: none;
    border-radius: 14px;
    min-height: 48px;
    font-size: 15px;
    font-weight: 600;
}}
#PrimaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {c["PRIMARY_HOVER_START"]}, stop:1 {c["PRIMARY_HOVER_END"]});
}}
#PrimaryButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {c["PRIMARY_PRESSED_START"]}, stop:1 {c["PRIMARY_PRESSED_END"]});
}}
#PrimaryButton:disabled {{ background: {c["DISABLED_BG"]}; color: {c["DISABLED_TEXT"]}; }}

#LinkButton {{
    background: transparent;
    border: none;
    color: {c["LINK"]};
    font-weight: 600;
    font-size: 13px;
}}
#LinkButton:hover {{ color: {c["LINK_HOVER"]}; text-decoration: underline; }}

#Banner {{ border-radius: 12px; padding: 8px 14px; font-size: 13px; font-weight: 500; }}
#Banner[kind="error"] {{
    background: {c["ERROR_BG"]}; color: {c["ERROR"]}; border: 1px solid {c["ERROR_BORDER"]};
}}
#Banner[kind="success"] {{
    background: {c["SUCCESS_BG"]}; color: {c["SUCCESS"]}; border: 1px solid {c["SUCCESS_BORDER"]};
}}

/* ---------- theme switch button (top-right corner, small glass pill) ---------- */
#ThemeToggle {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {c["GLASS_TOP"]}, stop:1 {c["GLASS_BOTTOM"]});
    color: {c["TEXT"]};
    border: 1px solid {c["GLASS_BORDER"]};
    border-top-color: {c["GLASS_HIGHLIGHT"]};
    border-radius: 18px;
    padding: 0 16px;
    min-height: 36px;
    font-size: 13px;
    font-weight: 600;
}}
#ThemeToggle:hover {{ border-color: {c["PRIMARY_START"]}; }}
"""


# ======================================================================
# 3. Fonts and shadow helpers
# ======================================================================
_fonts_loaded = False


def load_fonts():
    """Register the bundled Sora / Inter .ttf files with Qt (only once).
    After this, QSS can use font-family: "Sora" / "Inter"."""
    global _fonts_loaded
    if _fonts_loaded:
        return
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(path)) == -1:
            print(f"Warning: could not load font {path.name}")
    _fonts_loaded = True


def add_glass_shadow(widget):
    """Give a glass panel a large soft drop shadow in the current theme's color."""
    shadow = QGraphicsDropShadowEffect(blurRadius=70, xOffset=0, yOffset=24)

    def update_color(_theme_name=None):
        r, g, b, opacity = theme.colors["SHADOW"]
        shadow.setColor(QColor(r, g, b, round(opacity * 255)))

    update_color()
    widget.setGraphicsEffect(shadow)
    theme.changed.connect(update_color)   # new theme -> new shadow color


# ======================================================================
# 4. Theme manager - ONE object for the whole app
# ======================================================================
class ThemeManager(QObject):
    changed = pyqtSignal(str)   # sends "light" or "dark" after every change

    def __init__(self):
        super().__init__()
        # QSettings saves small values on the computer (remembered after closing)
        self.settings = QSettings("ErgoMon", "UserApp")
        self.name = self.settings.value("theme", "light")

    @property
    def colors(self):
        return DARK if self.name == "dark" else LIGHT

    def apply(self):
        """Apply the current theme to the whole application."""
        load_fonts()
        QApplication.instance().setStyleSheet(build_stylesheet(self.colors))
        self.changed.emit(self.name)

    def toggle(self):
        """Switch light <-> dark, remember the choice and apply it."""
        self.name = "dark" if self.name == "light" else "light"
        self.settings.setValue("theme", self.name)
        self.apply()


theme = ThemeManager()
