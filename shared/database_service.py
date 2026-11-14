import requests
from datetime import datetime, timezone
from shared.firebase_config import PROJECT_ID

# The Firestore address of our database
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"


def create_user_profile(uid, id_token, first_name, last_name, email):
    # 1. Where to save: collection "users", document named by the user's ID
    url = f"{FIRESTORE_URL}/users?documentId={uid}"

    # 2. Who is asking: the user's "login certificate" (id_token)
    headers = {"Authorization": f"Bearer {id_token}"}

    # 3. What to save (Firestore needs the type of every field)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = {
        "fields": {
            "first_name": {"stringValue": first_name},   # kept separate - never split a full name
            "last_name": {"stringValue": last_name},
            "email": {"stringValue": email},
            "role": {"stringValue": "user"},
            "created_at": {"timestampValue": now},
        }
    }

    # 4. Send the request
    response = requests.post(url, json=data, headers=headers)
    result = response.json()

    # 5. Check if it succeeded
    if response.ok:
        return result
    else:
        raise Exception(result["error"]["status"])

 
def get_user_profile(uid, id_token):
    """Read the document users/{uid} and return it as a normal dictionary."""
    url = f"{FIRESTORE_URL}/users/{uid}"
    headers = {"Authorization": f"Bearer {id_token}"}

    response = requests.get(url, headers=headers)
    result = response.json()

    if response.status_code == 404:      # no profile yet (first login)
        return {}
    if not response.ok:
        raise Exception(result["error"]["status"])

    # Firestore format {"name": {"stringValue": "Aya"}}  ->  {"name": "Aya"}
    profile = {}
    for field_name, typed_value in result.get("fields", {}).items():
        profile[field_name] = list(typed_value.values())[0]
    return profile


 # Profile Page
def update_user_profile(uid, id_token, first_name, last_name):
    """Change the user's first and last name in Firestore (other fields stay as they are)."""
    # updateMask = "change ONLY these fields" (without it, Firestore would replace the whole document)
    url = (f"{FIRESTORE_URL}/users/{uid}"
           "?updateMask.fieldPaths=first_name&updateMask.fieldPaths=last_name")
    headers = {"Authorization": f"Bearer {id_token}"}
    data = {
        "fields": {
            "first_name": {"stringValue": first_name},
            "last_name": {"stringValue": last_name},
        }
    }
    response = requests.patch(url, json=data, headers=headers)
    if not response.ok:
        raise Exception(response.json()["error"]["status"])


def delete_user_profile(uid, id_token):
    """Delete the user's document users/{uid} from Firestore."""
    url = f"{FIRESTORE_URL}/users/{uid}"
    headers = {"Authorization": f"Bearer {id_token}"}
    response = requests.delete(url, headers=headers)
    if not response.ok:
        raise Exception(response.json()["error"]["status"])