# webhooks.py — SwytchAI Webhook Notifications
import requests
import json

def send_slack_webhook(webhook_url, message, title="SwytchAI Alert"):
    """Sends a notification to Slack via webhook."""
    if not webhook_url:
        return False
    payload = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": title}},
            {"type": "section", "text": {"type": "mrkdwn", "text": message}}
        ]
    }
    try:
        r = requests.post(webhook_url, json=payload, timeout=5)
        return r.status_code == 200
    except Exception as e:
        print(f"Slack webhook error: {e}")
        return False


def send_teams_webhook(webhook_url, message, title="SwytchAI Alert"):
    """Sends a notification to Microsoft Teams via webhook."""
    if not webhook_url:
        return False
    payload = {
        "@type": "MessageCard",
        "themeColor": "00e5ff",
        "summary": title,
        "sections": [{
            "activityTitle": title,
            "activitySubtitle": "SwytchAI Notification",
            "text": message
        }]
    }
    try:
        r = requests.post(webhook_url, json=payload, timeout=5)
        return r.status_code == 200
    except Exception as e:
        print(f"Teams webhook error: {e}")
        return False


def notify_config_change(webhook_url, platform, user, action, device="", details=""):
    """Sends a config change notification to the configured platform."""
    message = f"**{user}** performed **{action}**"
    if device:
        message += f" on `{device}`"
    if details:
        message += f"\n> {details}"

    if platform == "slack":
        return send_slack_webhook(webhook_url, message, title=f"Config {action}")
    elif platform == "teams":
        return send_teams_webhook(webhook_url, message, title=f"Config {action}")
    return False
