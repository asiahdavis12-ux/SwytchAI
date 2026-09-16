
# setup_db_admin.py — Create admin user in the new database
from database import init_db, db_create_user
import bcrypt

# Initialize tables first
init_db()

# Get your info
username = input("Enter username: ").strip().lower()
name = input("Enter full name: ").strip()
password = input("Enter password: ").strip()

# Hash the password
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Create the user
success = db_create_user(username, name, "admin", "PHX026", password_hash)

if success:
    print("")
    print("=" * 40)
    print(f"  Admin user '{username}' created!")
    print(f"  You can now log in to SwytchAI.")
    print("=" * 40)
else:
    print(f"  User '{username}' already exists!")

