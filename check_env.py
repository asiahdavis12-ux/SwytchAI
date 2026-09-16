from dotenv import load_dotenv
import os

load_dotenv()
username = os.getenv("MAIL_USERNAME", "NOT SET")
password = os.getenv("MAIL_PASSWORD", "NOT SET")
print(f"MAIL_USERNAME: {username}")
print(f"MAIL_PASSWORD: {password[:4]}...{password[-4:]} (length: {len(password)})")
