
# setup_api_key.py — Generate your first SwytchAI API key
import json
import secrets
from datetime import datetime

API_KEYS_FILE = "api_keys.json"

username = input("Enter your SwytchAI username: ").strip().lower()
role = input("Enter your role (technician/team_lead/manager/admin): ").strip().lower()
label = input("Enter a label for this key (e.g. 'my-laptop'): ").strip()

new_key = "swytch_" + secrets.token_hex(24)

keys_data = {"keys": []}
try:
    with open(API_KEYS_FILE, "r") as f:
        keys_data = json.load(f)
except FileNotFoundError:
    pass

keys_data["keys"].append({
    "key": new_key,
    "username": username,
    "role": role,
    "label": label,
    "active": True,
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "created_by": "setup_script",
})

with open(API_KEYS_FILE, "w") as f:
    json.dump(keys_data, f, indent=2)

print("")
print("=" * 50)
print("  YOUR API KEY (save this somewhere safe!):")
print(f"  {new_key}")
print("=" * 50)
print("")
print("Use it in requests like this:")
print(f'  curl -H "X-API-Key: {new_key}" http://127.0.0.1:5000/api/health')

