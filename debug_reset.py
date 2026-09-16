from database import db_get_user, get_db

# Method 1: Using db_get_user
user = db_get_user("asiahdavis")
print("=== db_get_user result ===")
for key, value in user.items():
    print(f"  {key}: {repr(value)}")

# Method 2: Direct database query
print("\n=== Direct DB query ===")
conn = get_db()
c = conn.cursor()
c.execute("SELECT * FROM users WHERE username = 'asiahdavis'")
row = c.fetchone()
print("Raw row:", row)
print("Column count:", len(row))

# Get column names
c.execute("PRAGMA table_info(users)")
columns = c.fetchall()
print("\nColumn definitions:")
for col in columns:
    print(f"  {col[0]}: {col[1]} ({col[2]})")
conn.close()
