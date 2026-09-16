import sqlite3
conn = sqlite3.connect("swytchai.db")
c = conn.cursor()

for table in ["changes", "audit_log", "devices", "users"]:
    c.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in c.fetchall()]
    print(f"{table}: {cols}")
conn.close()
