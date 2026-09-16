
# security.py — Input Validation & Security for SwytchAI
import re


def sanitize_input(text):
    """Removes dangerous characters from user input."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]*>', '', str(text))
    # Remove script-related keywords
    clean = re.sub(r'(?i)(javascript|script|onerror|onload|eval|alert)', '', clean)
    return clean.strip()


def validate_username(username):
    """Username must be letters, numbers, underscores only. 3-30 chars."""
    if not username:
        return False, "Username is required."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 30:
        return False, "Username must be 30 characters or less."
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores."
    return True, "Valid"


def validate_password(password):
    """Password must be at least 8 characters with a mix of types."""
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."
    return True, "Valid"


def validate_config_lines(config_text):
    """Validates config lines are safe to push."""
    if not config_text:
        return False, "Config lines cannot be empty."
    # Block dangerous commands
    dangerous = ['reload', 'erase', 'delete', 'format', 'write erase', 'factory-reset']
    for line in config_text.lower().split('\n'):
        for cmd in dangerous:
            if cmd in line.strip():
                return False, f"Blocked dangerous command: '{cmd}'"
    return True, "Valid"


def validate_description(text):
    """Description must be 1-200 characters, no scripts."""
    if not text:
        return False, "Description is required."
    clean = sanitize_input(text)
    if len(clean) > 200:
        return False, "Description must be 200 characters or less."
    return True, "Valid"

