f = open("database.py", "r", encoding="utf-8")
lines = f.readlines()
f.close()

new_lines = []
skip_until_next_def = False

for i, line in enumerate(lines):
    if "def db_get_user" in line:
        skip_until_next_def = True
        new_lines.append("def db_get_user(username):\n")
        new_lines.append("    conn = get_db()\n")
        new_lines.append("    cursor = conn.cursor()\n")
        new_lines.append('    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))\n')
        new_lines.append("    row = cursor.fetchone()\n")
        new_lines.append("    conn.close()\n")
        new_lines.append("    if not row:\n")
        new_lines.append("        return None\n")
        new_lines.append('    return {"username": row[0], "name": row[1], "role": row[2], "site": row[3], "password_hash": row[4], "org_id": row[5], "email": row[6], "totp_secret": row[7]}\n')
        new_lines.append("\n")
        continue
    if skip_until_next_def:
        if line.strip() == "":
            continue
        if not line.startswith(" ") and not line.startswith("\t") and line.strip() != "":
            skip_until_next_def = False
            new_lines.append(line)
        continue
    new_lines.append(line)

f = open("database.py", "w", encoding="utf-8")
f.writelines(new_lines)
f.close()
print("FIXED!")
