"""
Brand panel - the colorful left side used by the Login and Register screens.
Written once here, used by both screens.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

FEATURES = (
    "Real-time neck & back monitoring",
    "Smart alerts - only when needed",
    "Personal stretching exercises",
    "Track your progress every day",
)


def build_brand_panel():
    panel = QFrame(objectName="BrandPanel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(44, 48, 44, 36)
    layout.setSpacing(0)

    logo = QLabel("EM", objectName="Logo", alignment=Qt.AlignCenter)
    logo.setFixedSize(56, 56)
    layout.addWidget(logo)
    layout.addSpacing(28)

    layout.addWidget(QLabel("ErgoMon", objectName="BrandName"))
    layout.addSpacing(8)
    layout.addWidget(QLabel("Your AI posture coach.\nSit better, feel better.", objectName="BrandTagline"))
    layout.addSpacing(40)

    for text in FEATURES:
        layout.addLayout(_feature_row(text))
        layout.addSpacing(16)

    layout.addStretch()
    layout.addWidget(QLabel("Braude College  ·  Final Project 2026", objectName="BrandFooter"))
    return panel


def _feature_row(text):
    row = QHBoxLayout()
    row.setSpacing(12)
    icon = QLabel("✓", objectName="FeatureIcon", alignment=Qt.AlignCenter)
    icon.setFixedSize(24, 24)
    row.addWidget(icon)
    row.addWidget(QLabel(text, objectName="Feature"))
    row.addStretch()
    return row