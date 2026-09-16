f = open("database.py", "r", encoding="utf-8")
content = f.read()
f.close()

# Add db_get_user right after db_get_all_users
func = '''
def db_get_user(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {"username": row[0], "name": row[1], "role": row[2], "site": row[3], "password_hash": row[4], "org_id": row[5], "email": row[6], "totp_secret": row[7]}

'''

target = "def db_get_all_users():"

if target in content:
    content = content.replace(target, func + target)
    f = open("database.py", "w", encoding="utf-8")
    f.write(content)
    f.close()
    print("FIXED! db_get_user added back.")
else:
    print("Could not find db_get_all_users - check database.py manually")
