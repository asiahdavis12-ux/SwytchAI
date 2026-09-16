from database import db_get_user

user = db_get_user("asiahdavis")
if user:
    print("User found!")
    print("Username:", user.get("username"))
    print("Email in DB:", repr(user.get("email")))
    print("Email type:", type(user.get("email")))
    
    # Test the exact comparison
    test_email = "asiahdavis@outlook.com"
    db_email = user.get("email", "").lower()
    print("DB email lower:", repr(db_email))
    print("Test email lower:", repr(test_email))
    print("Match:", db_email == test_email)
else:
    print("User NOT found!")
