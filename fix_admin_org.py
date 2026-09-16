from database import init_db, db_create_org, get_db

init_db()

# Create org for your existing admin account
conn = get_db()
admin = conn.execute("SELECT * FROM users WHERE username = 'asiahdavis'").fetchone()
if admin:
    org_id = db_create_org("SwytchAI HQ", "swytchai-hq", "asiahdavis", "enterprise")
    if org_id:
        print(f"Created org 'SwytchAI HQ' with ID {org_id}")
        print("Admin account linked to org")
    else:
        print("Org might already exist")
else:
    # Try your actual username
    users = conn.execute("SELECT username FROM users").fetchall()
    print("Existing users:", [u["username"] for u in users])
conn.close()
