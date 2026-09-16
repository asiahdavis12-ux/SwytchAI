
# notifications.py — SwytchAI Notification System
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


# ============================================================
# NOTIFICATION STORAGE — File-based for now
# ============================================================
NOTIFICATION_FILE = "notifications.json"


def load_notifications():
    """Loads all notifications from file."""
    if os.path.exists(NOTIFICATION_FILE):
        with open(NOTIFICATION_FILE, "r") as f:
            return json.load(f)
    return {"notifications": []}


def save_notifications(data):
    """Saves notifications to file."""
    with open(NOTIFICATION_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_next_notification_id():
    """Gets the next available notification ID."""
    data = load_notifications()
    if data["notifications"]:
        return max(n["id"] for n in data["notifications"]) + 1
    return 1


# ============================================================
# IN-APP NOTIFICATIONS
# ============================================================
def create_notification(recipient, title, message, notif_type="info", link=None):
    """
    Creates an in-app notification for a specific user.

    Args:
        recipient:  Username who should see this notification
        title:      Short title (e.g. "New Change Proposed")
        message:    Full message text
        notif_type: "info", "success", "warning", "danger"
        link:       Optional URL to link to (e.g. /changes)
    """
    data = load_notifications()

    notification = {
        "id": get_next_notification_id(),
        "recipient": recipient,
        "title": title,
        "message": message,
        "type": notif_type,
        "link": link,
        "read": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    data["notifications"].append(notification)
    save_notifications(data)

    return notification


def get_user_notifications(username, unread_only=False):
    """Gets all notifications for a specific user."""
    data = load_notifications()
    notifications = [
        n for n in data["notifications"]
        if n["recipient"] == username
    ]

    if unread_only:
        notifications = [n for n in notifications if not n["read"]]

    # Return newest first
    notifications.sort(key=lambda x: x["created_at"], reverse=True)
    return notifications


def get_unread_count(username):
    """Gets the count of unread notifications for a user."""
    return len(get_user_notifications(username, unread_only=True))


def mark_as_read(notification_id):
    """Marks a single notification as read."""
    data = load_notifications()
    for n in data["notifications"]:
        if n["id"] == notification_id:
            n["read"] = True
            break
    save_notifications(data)


def mark_all_as_read(username):
    """Marks all notifications for a user as read."""
    data = load_notifications()
    for n in data["notifications"]:
        if n["recipient"] == username:
            n["read"] = True
    save_notifications(data)


def delete_notification(notification_id):
    """Deletes a specific notification."""
    data = load_notifications()
    data["notifications"] = [
        n for n in data["notifications"]
        if n["id"] != notification_id
    ]
    save_notifications(data)


def clear_all_notifications(username):
    """Clears all notifications for a user."""
    data = load_notifications()
    data["notifications"] = [
        n for n in data["notifications"]
        if n["recipient"] != username
    ]
    save_notifications(data)


# ============================================================
# NOTIFICATION TRIGGERS — Called from the workflow
# ============================================================
def notify_change_proposed(change_record, proposer_name):
    """
    Called when a new change is proposed.
    Notifies all users with 'approve_change' permission.
    """
    from users import load_user_database, ROLES

    users = load_user_database()
    change_id = change_record["change_id"]
    description = change_record["description"]

    for username, user_info in users.items():
        role = user_info["role"]
        permissions = ROLES.get(role, {}).get("permissions", [])

        if "approve_change" in permissions:
            create_notification(
                recipient=username,
                title="New Change Needs Approval",
                message=f"Change #{change_id} proposed by {proposer_name}: {description}",
                notif_type="warning",
                link="/changes",
            )


def notify_change_approved(change_record, reviewer_name):
    """
    Called when a change is approved and pushed.
    Notifies the original proposer.
    """
    from users import load_user_database

    users = load_user_database()
    change_id = change_record["change_id"]
    proposer = change_record.get("proposed_by", "")

    # Find the proposer's username by their display name
    for username, user_info in users.items():
        if user_info["name"] == proposer:
            create_notification(
                recipient=username,
                title="Change Approved & Pushed! ✅",
                message=f"Change #{change_id} was approved by {reviewer_name} and pushed to the device.",
                notif_type="success",
                link="/changes",
            )
            break


def notify_change_rejected(change_record, reviewer_name):
    """
    Called when a change is rejected.
    Notifies the original proposer.
    """
    from users import load_user_database

    users = load_user_database()
    change_id = change_record["change_id"]
    proposer = change_record.get("proposed_by", "")

    for username, user_info in users.items():
        if user_info["name"] == proposer:
            create_notification(
                recipient=username,
                title="Change Rejected 🚫",
                message=f"Change #{change_id} was rejected by {reviewer_name}.",
                notif_type="danger",
                link="/changes",
            )
            break


def notify_change_rolled_back(change_record, roller_name):
    """
    Called when a change is rolled back.
    Notifies all users.
    """
    from users import load_user_database

    users = load_user_database()
    change_id = change_record["change_id"]

    for username in users.keys():
        create_notification(
            recipient=username,
            title="Change Rolled Back ↩️",
            message=f"Change #{change_id} was rolled back by {roller_name}.",
            notif_type="warning",
            link="/changes",
        )


def notify_new_user(username, temp_password, created_by):
    """
    Called when a new user is created.
    Notifies the new user.
    """
    create_notification(
        recipient=username,
        title="Welcome to SwytchAI! 🎉",
        message=f"Your account was created by {created_by}. Your temporary password is: {temp_password}. Please change it on your first login.",
        notif_type="info",
        link="/",
    )


# ============================================================
# EMAIL NOTIFICATIONS (Optional — configure in .env)
# ============================================================
def send_email_notification(to_email, subject, body):
    """
    Sends an email notification.
    Requires SMTP settings in .env file.
    Returns True if sent, False if email is not configured.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM", "swytchai@yourdomain.com")

    # If email isn't configured, skip silently
    if not smtp_host or not smtp_user:
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = f"[SwytchAI] {subject}"

        # Create HTML email body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #0f1923; color: #e0e0e0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #1a2736; border-radius: 12px; padding: 30px;">
                <h1 style="color: #00e676;">🔀 SwytchAI</h1>
                <h2 style="color: #ffffff;">{subject}</h2>
                <p style="color: #b0bec5; font-size: 16px; line-height: 1.6;">{body}</p>
                <hr style="border-color: #253746;">
                <p style="color: #546e7a; font-size: 12px;">
                    This is an automated notification from SwytchAI.
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP(smtp_host, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        print(f"  ⚠️  Email notification failed: {e}")
        return False


# ============================================================
# SLACK NOTIFICATIONS (Optional — configure in .env)
# ============================================================
def send_slack_notification(message):
    """
    Sends a notification to Slack via webhook.
    Requires SLACK_WEBHOOK_URL in .env file.
    Returns True if sent, False if Slack is not configured.
    """
    import urllib.request

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        return False

    try:
        payload = json.dumps({"text": f"🔀 *SwytchAI* | {message}"})
        req = urllib.request.Request(
            webhook_url,
            data=payload.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req)
        return True

    except Exception as e:
        print(f"  ⚠️  Slack notification failed: {e}")
        return False

