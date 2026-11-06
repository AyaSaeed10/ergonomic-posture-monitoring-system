"""
ErgoMon design system - Light / Dark themes for the WHOLE app.

- LIGHT and DARK hold the colors of each theme.
- build_stylesheet() turns a color set into a stylesheet (QSS = CSS for Qt).
- `theme` is ONE object shared by all screens: theme.toggle() switches
  the whole application, and the choice is remembered for next time.
"""

from PyQt5.QtCore import QObject, QSettings, pyqtSignal
from PyQt5.QtWidgets import QApplication

# ======================================================================
# 1. Color sets
# ======================================================================
LIGHT = {
    "BACKGROUND": "#EEF2FF",
    "CARD": "#FFFFFF",
    "TEXT": "#0F172A",
    "MUTED": "#64748B",
    "LABEL": "#334155",
    "BORDER": "#E2E8F0",
    "BORDER_HOVER": "#CBD5E1",
    "INPUT_BG": "#F8FAFC",
    "INPUT_FOCUS_BG": "#FFFFFF",
    "PRIMARY": "#4F46E5",
    "PRIMARY_DARK": "#4338CA",
    "ACCENT": "#06B6D4",
    "ACCENT_DARK": "#0891B2",
    "DISABLED": "#A5B4FC",
    "BRAND_START": "#4F46E5",
    "BRAND_END": "#06B6D4",
    "ERROR": "#DC2626",
    "ERROR_BG": "#FEF2F2",
    "ERROR_BORDER": "#FECACA",
    "SUCCESS": "#16A34A",
    "SUCCESS_BG": "#F0FDF4",
    "SUCCESS_BORDER": "#BBF7D0",
    "WARNING": "#F59E0B",
}

DARK = {
    "BACKGROUND": "#0B1120",
    "CARD": "#111827",
    "TEXT": "#F1F5F9",
    "MUTED": "#94A3B8",
    "LABEL": "#CBD5E1",
    "BORDER": "#1F2A3C",
    "BORDER_HOVER": "#334155",
    "INPUT_BG": "#1A2333",
    "INPUT_FOCUS_BG": "#1E293B",
    "PRIMARY": "#6366F1",
    "PRIMARY_DARK": "#4F46E5",
    "ACCENT": "#22D3EE",
    "ACCENT_DARK": "#06B6D4",
    "DISABLED": "#3730A3",
    "BRAND_START": "#4338CA",
    "BRAND_END": "#0E7490",
    "ERROR": "#F87171",
    "ERROR_BG": "#2A1215",
    "ERROR_BORDER": "#7F1D1D",
    "SUCCESS": "#4ADE80",
    "SUCCESS_BG": "#0B2416",
    "SUCCESS_BORDER": "#166534",
    "WARNING": "#FBBF24",
}


# ======================================================================
# 2. Stylesheet built from a color set
# ======================================================================
def build_stylesheet(c):
    return f"""
QWidget {{
    font-family: "Segoe UI", "Arial";
    font-size: 14px;
    color: {c["TEXT"]};
}}
QMainWindow, QStackedWidget {{ background: {c["BACKGROUND"]}; }}

/* ---------- window & card ---------- */
#Root {{ background: {c["BACKGROUND"]}; }}
#Card {{ background: {c["CARD"]}; border-radius: 24px; }}

/* ---------- left brand panel ---------- */
#BrandPanel {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 {c["BRAND_START"]}, stop:1 {c["BRAND_END"]});
    border-top-left-radius: 24px;
    border-bottom-left-radius: 24px;
}}
#BrandPanel QLabel {{ color: white; background: transparent; }}
#BrandPanel #Logo {{
    background: rgba(255, 255, 255, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: 16px;
    font-size: 22px;
    font-weight: 700;
}}
#BrandName {{ font-size: 30px; font-weight: 700; }}
#BrandTagline {{ font-size: 15px; color: rgba(255, 255, 255, 0.85); }}
#Feature {{ font-size: 14px; }}
#BrandPanel #FeatureIcon {{
    background: rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    font-weight: 700;
}}
#BrandFooter {{ font-size: 12px; color: rgba(255, 255, 255, 0.7); }}

/* ---------- form ---------- */
#Title {{ font-size: 26px; font-weight: 700; }}
#Subtitle {{ font-size: 14px; color: {c["MUTED"]}; }}
#FieldLabel {{ font-size: 13px; font-weight: 600; color: {c["LABEL"]}; }}
#FieldError {{ font-size: 12px; color: {c["ERROR"]}; }}
#Hint {{ font-size: 12px; color: {c["MUTED"]}; }}

QLineEdit {{
    min-height: 44px;
    background: {c["INPUT_BG"]};
    border: 1.5px solid {c["BORDER"]};
    border-radius: 10px;
    padding: 0 14px;
    font-size: 14px;
    color: {c["TEXT"]};
    selection-background-color: {c["PRIMARY"]};
}}
QLineEdit:hover {{ border-color: {c["BORDER_HOVER"]}; }}
QLineEdit:focus {{ border-color: {c["PRIMARY"]}; background: {c["INPUT_FOCUS_BG"]}; }}
QLineEdit[invalid="true"] {{ border-color: {c["ERROR"]}; background: {c["ERROR_BG"]}; }}

QCheckBox {{ color: {c["MUTED"]}; font-size: 13px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1.5px solid {c["BORDER_HOVER"]}; border-radius: 4px;
    background: {c["INPUT_BG"]};
}}
QCheckBox::indicator:checked {{ background: {c["PRIMARY"]}; border-color: {c["PRIMARY"]}; }}

QProgressBar {{
    background: {c["BORDER"]};
    border: none;
    border-radius: 3px;
    max-height: 6px;
}}

#PrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {c["PRIMARY"]}, stop:1 {c["ACCENT"]});
    color: white;
    border: none;
    border-radius: 12px;
    min-height: 48px;
    font-size: 15px;
    font-weight: 600;
}}
#PrimaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {c["PRIMARY_DARK"]}, stop:1 {c["ACCENT_DARK"]});
}}
#PrimaryButton:disabled {{ background: {c["DISABLED"]}; }}

#LinkButton {{
    background: transparent;
    border: none;
    color: {c["PRIMARY"]};
    font-weight: 600;
    font-size: 13px;
}}
#LinkButton:hover {{ color: {c["PRIMARY_DARK"]}; text-decoration: underline; }}

#Banner {{ border-radius: 10px; padding: 8px 14px; font-size: 13px; }}
#Banner[kind="error"] {{
    background: {c["ERROR_BG"]}; color: {c["ERROR"]}; border: 1px solid {c["ERROR_BORDER"]};
}}
#Banner[kind="success"] {{
    background: {c["SUCCESS_BG"]}; color: {c["SUCCESS"]}; border: 1px solid {c["SUCCESS_BORDER"]};
}}

/* ---------- theme switch button (top-right corner) ---------- */
#ThemeToggle {{
    background: {c["CARD"]};
    color: {c["TEXT"]};
    border: 1px solid {c["BORDER"]};
    border-radius: 18px;
    padding: 0 16px;
    min-height: 36px;
    font-size: 13px;
    font-weight: 600;
}}
#ThemeToggle:hover {{ border-color: {c["PRIMARY"]}; color: {c["PRIMARY"]}; }}
"""


# ======================================================================
# 3. Theme manager - ONE object for the whole app
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
        QApplication.instance().setStyleSheet(build_stylesheet(self.colors))
        self.changed.emit(self.name)

    def toggle(self):
        """Switch light <-> dark, remember the choice and apply it."""
        self.name = "dark" if self.name == "light" else "light"
        self.settings.setValue("theme", self.name)
        self.apply()


theme = ThemeManager()