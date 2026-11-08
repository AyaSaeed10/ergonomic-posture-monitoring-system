"""
Session - ONE shared object that knows who is signed in.

    from user_app.services.session import session
    session.first_name, session.email, session.id_token, ...

- Login calls session.start(user, remember); Log out calls session.clear().
- The Firebase ID token lasts 1 hour. The session renews it automatically
  a few minutes before it runs out, using the refresh token:
    * Firebase rejects the token (invalid / revoked) -> session ends, `expired` is sent.
    * Network problem -> nothing changes, it simply tries again every minute.
- "Remember me": ONLY the refresh token (never the password) is saved in
  Windows Credential Manager (keyring library). On the next start, restore()
  uses it to sign in again without the password.
- Three states (session.state): "signed_in", "guest" or "signed_out".
  Guest = "Continue without an account": live monitoring only, nothing is saved
  (no Firebase, no keyring) and a saved "Remember me" token is left untouched.
"""

import keyring
import requests
from keyring.errors import KeyringError
from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSignal

from shared.auth_service import TokenRejected, refresh_id_token
from shared.database_service import get_user_profile

KEYRING_SERVICE = "ErgoMon"          # the name shown in Windows Credential Manager
KEYRING_USERNAME = "refresh_token"
RENEW_BEFORE_EXPIRY_S = 5 * 60       # renew 5 minutes before the token runs out
RETRY_AFTER_NETWORK_ERROR_S = 60     # no internet -> try again after 1 minute


# =====================================================================
# Background worker - renews the token without freezing the window
# =====================================================================
class RenewWorker(QThread):
    succeeded = pyqtSignal(dict)
    failed = pyqtSignal(str)          # "rejected" or "network"

    def __init__(self, refresh_token, with_profile):
        super().__init__()
        self.refresh_token = refresh_token
        self.with_profile = with_profile   # True at app start: we also need name + email

    def run(self):
        try:
            result = refresh_id_token(self.refresh_token)
            if self.with_profile:
                profile = get_user_profile(result["uid"], result["id_token"])
                result["first_name"] = profile.get("first_name", "")
                result["last_name"] = profile.get("last_name", "")
                result["email"] = profile.get("email", "")
            self.succeeded.emit(result)
        except requests.exceptions.RequestException:
            self.failed.emit("network")    # no internet, timeout, Firebase server error
        except TokenRejected:
            self.failed.emit("rejected")
        except Exception:
            self.failed.emit("rejected")   # e.g. the profile could not be read


# =====================================================================
# The session
# =====================================================================
class Session(QObject):
    expired = pyqtSignal()             # Firebase rejected the token -> the user must log in again
    restored = pyqtSignal()            # app start: signed in again with the saved token
    restore_failed = pyqtSignal(str)   # app start: "rejected" or "network"

    def __init__(self):
        super().__init__()
        self._reset_fields()
        self.remember = False
        self.is_guest = False
        self.worker = None
        self.timer = QTimer(self, singleShot=True)
        self.timer.timeout.connect(self._renew)

    def _reset_fields(self):
        self.uid = None
        self.first_name = ""
        self.last_name = ""
        self.email = ""
        self.id_token = None
        self.refresh_token = None

    # ------------------------------------------------------------ who is signed in
    @property
    def is_signed_in(self):
        return self.uid is not None

    @property
    def state(self):
        """"signed_in", "guest" or "signed_out" - main.py uses this to decide which pages open."""
        if self.is_signed_in:
            return "signed_in"
        return "guest" if self.is_guest else "signed_out"

    @property
    def full_name(self):
        """For display only: first + last name joined (never split a full name)."""
        return " ".join(part for part in (self.first_name, self.last_name) if part)

    # ------------------------------------------------------------ sign in / out
    def start(self, user, remember):
        """Called after a successful login. `user` has uid, first_name, last_name,
        email, id_token, refresh_token and expires_in (seconds)."""
        self.is_guest = False
        self.uid = user["uid"]
        self.first_name = user.get("first_name", "")
        self.last_name = user.get("last_name", "")
        self.email = user.get("email", "")
        self.id_token = user["id_token"]
        self.refresh_token = user["refresh_token"]
        self.remember = remember
        if remember:
            _save_token(self.refresh_token)
        else:
            _delete_saved_token()   # e.g. another account was remembered before
        self._schedule_renewal(user["expires_in"] - RENEW_BEFORE_EXPIRY_S)

    def clear(self):
        """Log out: forget the user and delete the saved token."""
        self.timer.stop()
        self._reset_fields()
        self.remember = False
        _delete_saved_token()

    # ------------------------------------------------------------ guest mode
    def start_guest(self):
        """"Continue without an account": no Firebase, no timer, no keyring - nothing is saved."""
        self.is_guest = True

    def end_guest(self):
        """Guest goes back to Login. Unlike clear(), this does NOT delete a saved
        "Remember me" token - guest mode must leave it untouched."""
        self.is_guest = False

    # ------------------------------------------------------------ automatic renewal
    def _schedule_renewal(self, seconds):
        self.timer.start(max(seconds, 1) * 1000)

    def _renew(self):
        if not self.is_signed_in:
            return
        if self.worker and self.worker.isRunning():   # still busy - check again later
            self._schedule_renewal(RETRY_AFTER_NETWORK_ERROR_S)
            return
        self.worker = RenewWorker(self.refresh_token, with_profile=False)
        self.worker.succeeded.connect(self._on_renewed)
        self.worker.failed.connect(self._on_renew_failed)
        self.worker.start()

    def _on_renewed(self, result):
        if result["uid"] != self.uid:     # the user logged out meanwhile - ignore
            return
        self.id_token = result["id_token"]
        if result["refresh_token"] != self.refresh_token:
            self.refresh_token = result["refresh_token"]
            if self.remember:
                _save_token(self.refresh_token)
        self._schedule_renewal(result["expires_in"] - RENEW_BEFORE_EXPIRY_S)

    def _on_renew_failed(self, reason):
        if not self.is_signed_in:
            return
        if reason == "network":
            self._schedule_renewal(RETRY_AFTER_NETWORK_ERROR_S)   # keep the session, retry
        else:
            self.clear()
            self.expired.emit()

    # ------------------------------------------------------------ app start ("Remember me")
    def has_saved_token(self):
        return _load_token() is not None

    def restore(self):
        """Sign in with the saved token (in the background). Sends restored / restore_failed."""
        token = _load_token()
        if token is None:
            self.restore_failed.emit("rejected")
            return
        self.worker = RenewWorker(token, with_profile=True)
        self.worker.succeeded.connect(self._on_restored)
        self.worker.failed.connect(self._on_restore_failed)
        self.worker.start()

    def _on_restored(self, result):
        self.start(result, remember=True)
        self.restored.emit()

    def _on_restore_failed(self, reason):
        if reason == "rejected":
            _delete_saved_token()   # the saved token is useless now
        # "network": keep the saved token, the user can try again later
        self.restore_failed.emit(reason)


# =====================================================================
# Saved token in Windows Credential Manager
# =====================================================================
def _save_token(token):
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
    except KeyringError as error:
        print(f"Warning: could not save the login token: {error}")


def _load_token():
    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except KeyringError:
        return None


def _delete_saved_token():
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except KeyringError:
        pass   # nothing was saved - fine


session = Session()
