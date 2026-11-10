"""
Admin service - BACKEND of the admin app.

Uses the Firebase ADMIN key (secrets/firebase-admin-key.json), which can see and
delete EVERY user. Only admin_app may import this file - NEVER user_app.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import firebase_admin
from firebase_admin import auth, credentials, firestore

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ADMIN_KEY_PATH = ROOT_DIR / "secrets" / "firebase-admin-key.json"

# Connect to Firebase as ADMIN (only once, even if this file is imported many times)
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(credentials.Certificate(str(ADMIN_KEY_PATH)))

db = firestore.client()


def find_stuck_accounts(older_than_hours=24):
    """Accounts that never verified their email AND have no profile in Firestore.
    Only accounts older than `older_than_hours` - newer ones still get time to verify."""
    time_limit = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    stuck = []

    for user in auth.list_users().iterate_all():
        # 1. verified email -> a real user, keep
        if user.email_verified:
            continue

        # 2. too new -> give the person time to click the link
        created = datetime.fromtimestamp(user.user_metadata.creation_timestamp / 1000, timezone.utc)
        if created > time_limit:
            continue

        # 3. has a profile in Firestore -> a real user, keep
        if db.collection("users").document(user.uid).get().exists:
            continue

        stuck.append({"uid": user.uid, "email": user.email, "created": created})

    return stuck


def delete_accounts(uids):
    """Delete these accounts from Authentication. Returns how many were deleted."""
    if not uids:
        return 0
    result = auth.delete_users(uids)   # Firebase can delete up to 1000 at once
    return result.success_count