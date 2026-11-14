import requests
from shared.firebase_config import API_KEY

# Firebase addresses
BASE = "https://identitytoolkit.googleapis.com/v1/accounts"
SIGNUP_URL = f"{BASE}:signUp?key={API_KEY}"
LOGIN_URL = f"{BASE}:signInWithPassword?key={API_KEY}"
UPDATE_URL = f"{BASE}:update?key={API_KEY}"
SEND_EMAIL_URL = f"{BASE}:sendOobCode?key={API_KEY}"
LOOKUP_URL = f"{BASE}:lookup?key={API_KEY}"
DELETE_URL = f"{BASE}:delete?key={API_KEY}"
# Firebase "secure token" address: exchanges a refresh token for a new ID token
REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={API_KEY}"


class TokenRejected(Exception):
    """Firebase refused the refresh token (invalid, expired or revoked).
    Network problems are NOT this error - they raise requests exceptions instead."""


# ---------------------------------------------------------------- register & login

def register(email, password):
    """Create a new user in Firebase Authentication."""
    data = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(SIGNUP_URL, json=data)
    result = response.json()
    if response.ok:
        return result
    raise Exception(result["error"]["message"])


def login(email, password):
    """Check email + password with Firebase Authentication."""
    data = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(LOGIN_URL, json=data)
    result = response.json()
    if response.ok:
        return result
    raise Exception(result["error"]["message"])


# ---------------------------------------------------------------- email verification

def set_display_name(id_token, name):
    """Save the user's name inside Firebase Authentication (until the email is verified)."""
    data = {"idToken": id_token, "displayName": name, "returnSecureToken": False}
    response = requests.post(UPDATE_URL, json=data)
    result = response.json()
    if not response.ok:
        raise Exception(result["error"]["message"])


def send_verification_email(id_token):
    """Ask Firebase to send the 'verify your email' message to the user."""
    data = {"requestType": "VERIFY_EMAIL", "idToken": id_token}
    headers = {"X-Firebase-Locale": "he"}    # email language: "he" = Hebrew, "en" = English
    response = requests.post(SEND_EMAIL_URL, json=data, headers=headers)
    result = response.json()
    if not response.ok:
        raise Exception(result["error"]["message"])
    #reset passowrd
def send_password_reset_email(email):
    """Ask Firebase to send a 'reset your password' link to this email."""
    data = {"requestType": "PASSWORD_RESET", "email": email}
    headers = {"X-Firebase-Locale": "he"}    # email language: "he" = Hebrew, "en" = English
    response = requests.post(SEND_EMAIL_URL, json=data, headers=headers)
    result = response.json()
    if not response.ok:
        raise Exception(result["error"]["message"])

def is_email_verified(id_token):
    """Ask Firebase if the user already clicked the link in the email."""
    data = {"idToken": id_token}
    response = requests.post(LOOKUP_URL, json=data)
    result = response.json()
    if not response.ok:
        raise Exception(result["error"]["message"])
    return result["users"][0].get("emailVerified", False)

def delete_account(id_token):
    """Delete the user's account (used to undo a registration that failed half-way)."""
    data = {"idToken": id_token}
    response = requests.post(DELETE_URL, json=data)
    if not response.ok:
        raise Exception(response.json()["error"]["message"])
#profile page
def change_password(id_token, new_password):
    """Set a new password. Needs a FRESH id_token (log in again with the current password first).
    Firebase signs out all other devices and returns new tokens: idToken, refreshToken, expiresIn."""
    data = {"idToken": id_token, "password": new_password, "returnSecureToken": True}
    response = requests.post(UPDATE_URL, json=data)
    result = response.json()
    if response.ok:
        return result
    raise Exception(result["error"]["message"])
# ---------------------------------------------------------------- staying logged in

def refresh_id_token(refresh_token):
    """Get a new 1-hour ID token using the refresh token.

    Returns {"uid", "id_token", "refresh_token", "expires_in"} (expires_in in seconds).
    Raises TokenRejected if Firebase refuses the token, or a requests exception
    (e.g. ConnectionError, Timeout) if there is a network problem."""
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    response = requests.post(REFRESH_URL, data=data, timeout=10)   # this API expects form data
    if response.status_code in (400, 401, 403):
        raise TokenRejected(response.json().get("error", {}).get("message", "TOKEN_REJECTED"))
    response.raise_for_status()   # other errors (e.g. Firebase server down) count as "try again later"
    result = response.json()
    return {
        "uid": result["user_id"],
        "id_token": result["id_token"],
        "refresh_token": result["refresh_token"],
        "expires_in": int(result["expires_in"]),
    }