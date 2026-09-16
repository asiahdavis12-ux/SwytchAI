f = open("database.py", "r", encoding="utf-8")
lines = f.readlines()
f.close()

# First, remove the misplaced db_get_user from inside init_db
new_lines = []
skip = False
for line in lines:
    if "def db_get_user" in line:
        skip = True
        continue
    if skip:
        if line.strip().startswith("def ") and "db_get_user" not in line:
            skip = False
            new_lines.append(line)
        elif line.strip().startswith("# ==") and skip:
            skip = False
            new_lines.append(line)
        continue
    new_lines.append(line)

# Now find the USER FUNCTIONS comment and add db_get_user after it
final_lines = []
for i, line in enumerate(new_lines):
    final_lines.append(line)
    if "USER FUNCTIONS" in line and "====" in line:
        # Skip the next line if it's also ====
        pass
    if "USER FUNCTIONS" in line:
        # Add after the next ==== line
        continue
    if i > 0 and "USER FUNCTIONS" in new_lines[i-1]:
        final_lines.append("\n")
        final_lines.append("def db_get_user(username):\n")
        final_lines.append("    conn = get_db()\n")
        final_lines.append("    cursor = conn.cursor()\n")
        final_lines.append("    cursor.execute(\"SELECT * FROM users WHERE username = ?\", (username,))\n")
        final_lines.append("    row = cursor.fetchone()\n")
        final_lines.append("    conn.close()\n")
        final_lines.append("    if not row:\n")
        final_lines.append("        return None\n")
        final_lines.append("    cols = [desc[0] for desc in cursor.description]\n")
        final_lines.append("    return dict(zip(cols, row))\n")
        final_lines.append("\n")

f = open("database.py", "w", encoding="utf-8")
f.writelines(final_lines)
f.close()
print("DONE! db_get_user fixed and repositioned.")
