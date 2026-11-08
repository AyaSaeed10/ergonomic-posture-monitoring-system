import requests
from shared.firebase_config import API_KEY

# The Firebase address for creating a new user
SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
LOGIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
# Firebase "secure token" address: exchanges a refresh token for a new ID token
REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={API_KEY}"


class TokenRejected(Exception):
    """Firebase refused the refresh token (invalid, expired or revoked).
    Network problems are NOT this error - they raise requests exceptions instead."""

def register(email, password):
    # 1. The data we send to Firebase
    data = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    # 2. Send the request and get the response
    response = requests.post(SIGNUP_URL, json=data)
    result = response.json()

    # 3. Check if it succeeded
    if response.ok:
        return result
    else:
        raise Exception(result["error"]["message"])



def login(email, password):
    """Check email + password with Firebase Authentication."""
    data = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(LOGIN_URL, json=data)
    result = response.json()
    if response.ok:
        return result
    raise Exception(result["error"]["message"])


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
