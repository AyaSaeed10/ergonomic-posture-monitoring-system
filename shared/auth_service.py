import requests
from shared.firebase_config import API_KEY

# The Firebase address for creating a new user
SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
LOGIN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"

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
