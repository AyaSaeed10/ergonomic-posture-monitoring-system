import json
from pathlib import Path

# 1. Find the path of the JSON file
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "secrets" / "firebase_config.json"

# 2. Read the JSON file
with open(CONFIG_PATH, encoding="utf-8") as f:
    config = json.load(f)

# 3. Keep the two values we need
API_KEY = config["apiKey"]
PROJECT_ID = config["projectId"]