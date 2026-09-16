# Read the file
f = open("database.py", "r", encoding="utf-8")
lines = f.readlines()
f.close()

# Find where to insert (right before db_get_all_users or db_create_user)
insert_at = None
for i, line in enumerate(lines):
    if "def db_get_all_users" in line or "def db_create_user" in line:
        insert_at = i
        break

if insert_at is None:
    print("ERROR: Could not find insertion point")
else:
    new_func = [
        "\n",
        "def db_get_user(username):\n",
        "    conn = get_db()\n",
        "    cursor = conn.cursor()\n",
        "    cursor.execute(\"SELECT * FROM users WHERE username = ?\", (username,))\n",
        "    row = cursor.fetchone()\n",
        "    conn.close()\n",
        "    if not row:\n",
        "        return None\n",
        "    return {\"username\": row[0], \"name\": row[1], \"role\": row[2], \"site\": row[3], \"password_hash\": row[4], \"org_id\": row[5], \"email\": row[6], \"totp_secret\": row[7]}\n",
        "\n",
        "\n",
    ]
    
    # Check if db_get_user already exists
    exists = any("def db_get_user" in l for l in lines)
    if exists:
        print("db_get_user already exists! Skipping.")
    else:
        for j, new_line in enumerate(new_func):
            lines.insert(insert_at + j, new_line)
        
        f = open("database.py", "w", encoding="utf-8")
        f.writelines(lines)
        f.close()
        print(f"FIXED! Inserted db_get_user before line {insert_at + 1}")
