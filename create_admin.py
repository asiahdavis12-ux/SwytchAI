from users import hash_password, save_user_database

users = {
    "asiahdavis": {
        "name": "Asiah Davis",
        "role": "admin",
        "site": "PHX026",
        "password_hash": hash_password("Imawesome12!"),
        "must_change_password": False,
    }
}

save_user_database(users)
print("Admin user created! You can now log in.")
print("Username:asiahdavis")
print("Password:Imawesome12!")
