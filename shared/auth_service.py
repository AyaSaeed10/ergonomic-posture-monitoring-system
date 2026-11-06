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
    print(">>> SENDING to Firebase:", {"email": email})              # <-- NEW
    response = requests.post(SIGNUP_URL, json=data)
    result = response.json()
    print("<<< FIREBASE ANSWERED:", response.status_code, result)    # <-- NEW

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


def get_user_profile(uid, id_token):
    """Read the document users/{uid} and return it as a normal dictionary."""
    url = f"{FIRESTORE_URL}/users/{uid}"
    headers = {"Authorization": f"Bearer {id_token}"}

    response = requests.get(url, headers=headers)
    result = response.json()

    if not response.ok:
        raise Exception(result["error"]["status"])

    # Firestore format {"name": {"stringValue": "Aya"}}  ->  {"name": "Aya"}
    profile = {}
    for field_name, typed_value in result.get("fields", {}).items():
        profile[field_name] = list(typed_value.values())[0]
    return profile