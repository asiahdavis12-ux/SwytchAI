# email_service.py — SwytchAI Email Notification Service
from flask_mail import Mail, Message
from flask import current_app
import os

mail = Mail()

def init_mail(app):
    """Initialize Flask-Mail with app config."""
    app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
    app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", "noreply@swytchai.net")
    mail.init_app(app)


def send_email(to, subject, body_html):
    """Send an email notification."""
    try:
        if not current_app.config.get("MAIL_USERNAME"):
            print(f"[EMAIL SKIPPED] No mail configured. Would send to {to}: {subject}")
            return False
        msg = Message(subject=subject, recipients=[to], html=body_html)
        mail.send(msg)
        print(f"[EMAIL SENT] To: {to} | Subject: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def email_change_proposed(approver_email, approver_name, change):
    """Notify approver that a new change needs review."""
    subject = f"SwytchAI — New Change #{change['change_id']} Needs Your Approval"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a1929; color: #e0e0e0; padding: 2rem; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h1 style="color: #00e5ff; margin: 0;">⚡ SwytchAI</h1>
        </div>
        <h2 style="color: #ffffff;">New Change Pending Approval</h2>
        <p>Hi {approver_name},</p>
        <p>A new configuration change has been proposed and requires your review:</p>
        <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <p><strong>Change ID:</strong> #{change['change_id']}</p>
            <p><strong>Device:</strong> {change.get('host', 'N/A')}</p>
            <p><strong>Description:</strong> {change.get('description', 'No description')}</p>
            <p><strong>Proposed By:</strong> {change.get('proposed_by', 'Unknown')}</p>
        </div>
        <div style="text-align: center; margin-top: 1.5rem;">
            <a href="https://swytchai.net/changes" style="background: #00e5ff; color: #0a1929; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">Review Change</a>
        </div>
        <p style="color: #78909c; font-size: 0.85rem; margin-top: 2rem; text-align: center;">You're receiving this because you have approval permissions in SwytchAI.</p>
    </div>
    """
    return send_email(approver_email, subject, body)


def email_change_approved(proposer_email, proposer_name, change, reviewer_name):
    """Notify proposer that their change was approved."""
    subject = f"SwytchAI — Change #{change['change_id']} Approved ✅"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a1929; color: #e0e0e0; padding: 2rem; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h1 style="color: #00e5ff; margin: 0;">⚡ SwytchAI</h1>
        </div>
        <h2 style="color: #4caf50;">✅ Change Approved & Pushed</h2>
        <p>Hi {proposer_name},</p>
        <p>Great news! Your configuration change has been approved and pushed to the device:</p>
        <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <p><strong>Change ID:</strong> #{change['change_id']}</p>
            <p><strong>Device:</strong> {change.get('host', 'N/A')}</p>
            <p><strong>Description:</strong> {change.get('description', 'No description')}</p>
            <p><strong>Approved By:</strong> {reviewer_name}</p>
        </div>
        <div style="text-align: center; margin-top: 1.5rem;">
            <a href="https://swytchai.net/changes" style="background: #4caf50; color: #ffffff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">View Changes</a>
        </div>
        <p style="color: #78909c; font-size: 0.85rem; margin-top: 2rem; text-align: center;">You're receiving this because you proposed this change in SwytchAI.</p>
    </div>
    """
    return send_email(proposer_email, subject, body)


def email_change_rejected(proposer_email, proposer_name, change, reviewer_name):
    """Notify proposer that their change was rejected."""
    subject = f"SwytchAI — Change #{change['change_id']} Rejected 🚫"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a1929; color: #e0e0e0; padding: 2rem; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h1 style="color: #00e5ff; margin: 0;">⚡ SwytchAI</h1>
        </div>
        <h2 style="color: #ff5252;">🚫 Change Rejected</h2>
        <p>Hi {proposer_name},</p>
        <p>Your configuration change has been rejected:</p>
        <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <p><strong>Change ID:</strong> #{change['change_id']}</p>
            <p><strong>Device:</strong> {change.get('host', 'N/A')}</p>
            <p><strong>Description:</strong> {change.get('description', 'No description')}</p>
            <p><strong>Rejected By:</strong> {reviewer_name}</p>
        </div>
        <p>Please review the feedback and submit a revised change if needed.</p>
        <div style="text-align: center; margin-top: 1.5rem;">
            <a href="https://swytchai.net/changes" style="background: #ff5252; color: #ffffff; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">View Changes</a>
        </div>
        <p style="color: #78909c; font-size: 0.85rem; margin-top: 2rem; text-align: center;">You're receiving this because you proposed this change in SwytchAI.</p>
    </div>
    """
    return send_email(proposer_email, subject, body)


def email_welcome(user_email, user_name, org_name):
    """Send welcome email to new signups."""
    subject = "Welcome to SwytchAI! ⚡"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a1929; color: #e0e0e0; padding: 2rem; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h1 style="color: #00e5ff; margin: 0;">⚡ SwytchAI</h1>
        </div>
        <h2 style="color: #ffffff;">Welcome to SwytchAI!</h2>
        <p>Hi {user_name},</p>
        <p>Your organization <strong>{org_name}</strong> has been created and your 14-day free trial has started!</p>
        <div style="background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <h3 style="color: #00e5ff;">Quick Start Guide:</h3>
            <ol>
                <li>Add your first network device</li>
                <li>Pull a configuration backup</li>
                <li>Try the AI Config Assistant</li>
                <li>Invite your team members</li>
            </ol>
        </div>
        <div style="text-align: center; margin-top: 1.5rem;">
            <a href="https://swytchai.net/dashboard" style="background: #00e5ff; color: #0a1929; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">Go to Dashboard</a>
        </div>
        <p style="color: #78909c; font-size: 0.85rem; margin-top: 2rem; text-align: center;">Your trial ends in 14 days. Upgrade anytime from the Billing page.</p>
    </div>
    """
    return send_email(user_email, subject, body)


def email_team_invite(member_email, member_name, org_name, inviter_name):
    """Notify new team member they've been added."""
    subject = f"You've been invited to {org_name} on SwytchAI! ⚡"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a1929; color: #e0e0e0; padding: 2rem; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h1 style="color: #00e5ff; margin: 0;">⚡ SwytchAI</h1>
        </div>
        <h2 style="color: #ffffff;">You've Been Invited!</h2>
        <p>Hi {member_name},</p>
        <p><strong>{inviter_name}</strong> has added you to the <strong>{org_name}</strong> team on SwytchAI.</p>
        <p>SwytchAI is an AI-powered network automation platform. You can now:</p>
        <ul>
            <li>View and manage network devices</li>
            <li>Pull and compare configurations</li>
            <li>Propose and review changes</li>
            <li>Use the AI Config Assistant</li>
        </ul>
        <div style="text-align: center; margin-top: 1.5rem;">
            <a href="https://swytchai.net/login" style="background: #00e5ff; color: #0a1929; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">Log In Now</a>
        </div>
        <p style="color: #78909c; font-size: 0.85rem; margin-top: 2rem; text-align: center;">Contact your admin if you need your login credentials.</p>
    </div>
    """
    return send_email(member_email, subject, body)
