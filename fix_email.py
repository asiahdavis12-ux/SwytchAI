import sqlite3
import os

# Find all database files
for f in os.listdir("."):
    if f.endswith(".db"):
        print(f"Found: {f}")
        conn = sqlite3.connect(f)
        c = conn.cursor()
        c.execute("SELECT username, email FROM users WHERE username = 'asiahdavis'")
        row = c.fetchone()
        if row:
            print(f"  -> User found! Email: {row[1]}")
            # Update it
            conn.execute("UPDATE users SET email = 'asiahdavis@outlook.com' WHERE username = 'asiahdavis'")
            conn.commit()
            # Verify
            c.execute("SELECT email FROM users WHERE username = 'asiahdavis'")
            print(f"  -> Email NOW: {c.fetchone()[0]}")
        conn.close()
