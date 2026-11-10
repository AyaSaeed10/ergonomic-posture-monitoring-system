"""
Cleanup screen - FRONTEND of the admin app.

Shows accounts that never verified their email (and have no profile in Firestore)
and lets the admin choose which ones to delete. The work itself is done by
admin_app/core/admin_service.py (BACKEND, uses the admin key).

Run this screen alone (from the project root):
    python -m admin_app.ui.cleanup_screen
"""

import sys
from datetime import datetime, timezone

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QFrame, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from admin_app.core.admin_service import delete_accounts, find_stuck_accounts
from user_app.ui import styles
from user_app.ui.widgets.glow_background import GlowBackground


# =====================================================================
# Background workers - talk to Firebase without freezing the window
# =====================================================================
class LoadWorker(QThread):
    succeeded = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, hours):
        super().__init__()
        self.hours = hours

    def run(self):
        try:
            self.succeeded.emit(find_stuck_accounts(older_than_hours=self.hours))
        except Exception as error:
            self.failed.emit(f"Could not load the accounts: {error}")


class DeleteWorker(QThread):
    succeeded = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, uids):
        super().__init__()
        self.uids = uids

    def run(self):
        try:
            self.succeeded.emit(delete_accounts(self.uids))
        except Exception as error:
            self.failed.emit(f"Could not delete the accounts: {error}")


# =====================================================================
# The screen
# =====================================================================
class CleanupScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Root")                       # see-through -> the glows show
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.accounts = []
        self.worker = None
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------ layout
    def _build_ui(self):
        panel = QFrame(objectName="GlassPanel")
        styles.add_glass_shadow(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(40, 36, 40, 32)
        layout.setSpacing(0)

        layout.addWidget(QLabel("Unverified accounts", objectName="Title"))
        layout.addSpacing(6)
        layout.addWidget(QLabel(
            "Accounts that never verified their email and have no profile. "
            "Deleting them frees the email for its real owner.",
            objectName="Subtitle", wordWrap=True))
        layout.addSpacing(20)

        self.banner = QLabel(objectName="Banner", wordWrap=True)
        self.banner.hide()
        layout.addWidget(self.banner)
        layout.addSpacing(12)

        # controls: Older than [24 h] [Refresh] .......... 3 account(s)
        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(QLabel("Older than", objectName="FieldLabel"))
        self.hours_input = QSpinBox(minimum=0, maximum=720, value=24, suffix=" h")
        self.hours_input.setFixedWidth(110)
        controls.addWidget(self.hours_input)
        self.refresh_button = QPushButton("Refresh", objectName="SecondaryButton")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setFixedWidth(140)
        self.refresh_button.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_button)
        controls.addStretch()
        self.count_label = QLabel("", objectName="Hint")
        controls.addWidget(self.count_label)
        layout.addLayout(controls)
        layout.addSpacing(16)

        # the table: [x] email | created | waiting for  (styled by #DataTable in styles.py)
        self.table = QTableWidget(0, 3, objectName="DataTable")
        self.table.setHorizontalHeaderLabels(["Email", "Created", "Waiting for"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.itemChanged.connect(self._update_buttons)
        layout.addWidget(self.table, 1)
        layout.addSpacing(20)

        # bottom: [Select all] .......... [Delete selected]
        bottom = QHBoxLayout()
        self.select_all_button = QPushButton("Select all", objectName="TextButton")
        self.select_all_button.setCursor(Qt.PointingHandCursor)
        self.select_all_button.clicked.connect(self._toggle_select_all)
        bottom.addWidget(self.select_all_button)
        bottom.addStretch()
        self.delete_button = QPushButton("Delete selected", objectName="DangerButton")
        self.delete_button.setCursor(Qt.PointingHandCursor)
        self.delete_button.setFixedWidth(220)
        self.delete_button.clicked.connect(self._on_delete)
        bottom.addWidget(self.delete_button)
        layout.addLayout(bottom)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.addWidget(panel)
        self._update_buttons()

    # ------------------------------------------------------------ load
    def refresh(self):
        self.banner.hide()
        self._set_busy(True, "Loading...")
        self.worker = LoadWorker(self.hours_input.value())
        self.worker.succeeded.connect(self._show_accounts)
        self.worker.failed.connect(self._on_error)
        self.worker.start()

    def _show_accounts(self, accounts):
        self._set_busy(False)
        self.accounts = accounts
        self.table.blockSignals(True)            # don't react to every cell while filling
        self.table.setRowCount(len(accounts))
        now = datetime.now(timezone.utc)
        for row, account in enumerate(accounts):
            email = QTableWidgetItem(account["email"] or "(no email)")
            email.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            email.setCheckState(Qt.Unchecked)
            created = account["created"].astimezone()         # show in local time
            self.table.setItem(row, 0, email)
            self.table.setItem(row, 1, QTableWidgetItem(created.strftime("%d/%m/%Y  %H:%M")))
            self.table.setItem(row, 2, QTableWidgetItem(self._age_text(now - account["created"])))
        self.table.blockSignals(False)
        self.count_label.setText(f"{len(accounts)} account(s)" if accounts else "No stuck accounts")
        self._update_buttons()

    @staticmethod
    def _age_text(age):
        hours = int(age.total_seconds() // 3600)
        return f"{hours // 24} days" if hours >= 48 else f"{hours} h"

    # ------------------------------------------------------------ select
    def _selected(self):
        """Accounts whose checkbox is ticked."""
        return [self.accounts[row] for row in range(self.table.rowCount())
                if self.table.item(row, 0).checkState() == Qt.Checked]

    def _toggle_select_all(self):
        tick = len(self._selected()) < self.table.rowCount()   # not all ticked -> tick all
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.Checked if tick else Qt.Unchecked)
        self.table.blockSignals(False)
        self._update_buttons()

    def _update_buttons(self, *_):
        count = len(self._selected()) if self.accounts else 0
        self.delete_button.setEnabled(count > 0)
        self.delete_button.setText(f"Delete selected ({count})" if count else "Delete selected")
        all_ticked = bool(self.accounts) and count == len(self.accounts)
        self.select_all_button.setText("Clear selection" if all_ticked else "Select all")
        self.select_all_button.setEnabled(bool(self.accounts))

    # ------------------------------------------------------------ delete
    def _on_delete(self):
        selected = self._selected()
        emails = "\n".join(f"  • {a['email']}" for a in selected[:8])
        if len(selected) > 8:
            emails += f"\n  ... and {len(selected) - 8} more"
        answer = QMessageBox.question(
            self, "Delete accounts?",
            f"Delete {len(selected)} account(s)?\n\n{emails}\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if answer != QMessageBox.Yes:
            return
        self._set_busy(True, "Deleting...")
        self.worker = DeleteWorker([a["uid"] for a in selected])
        self.worker.succeeded.connect(self._on_deleted)
        self.worker.failed.connect(self._on_error)
        self.worker.start()

    def _on_deleted(self, count):
        self.refresh()
        self._show_banner(f"Deleted {count} account(s). Their emails are free to register again.",
                          "success")

    # ------------------------------------------------------------ helpers
    def _set_busy(self, busy, text=""):
        for widget in (self.refresh_button, self.hours_input, self.select_all_button):
            widget.setEnabled(not busy)
        if busy:
            self.delete_button.setEnabled(False)
            self.count_label.setText(text)

    def _on_error(self, message):
        self._set_busy(False)
        self._update_buttons()
        self._show_banner(message, "error")

    def _show_banner(self, text, kind):
        self.banner.setText(text)
        self.banner.setProperty("kind", kind)
        self.banner.style().unpolish(self.banner)
        self.banner.style().polish(self.banner)
        self.banner.show()


# =====================================================================
# Run this screen alone for testing
# =====================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    styles.theme.apply()
    window = GlowBackground()          # the screen sits on the glow background
    QVBoxLayout(window).addWidget(CleanupScreen())
    window.setWindowTitle("ErgoMon Admin - Unverified accounts")
    window.resize(1100, 760)
    window.show()
    sys.exit(app.exec_())